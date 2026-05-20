package com.example.myapplication.ui.history

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.ProgressBar
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.myapplication.MyApplication
import com.example.myapplication.data.local.DriveSession
import com.example.myapplication.data.local.VehicleData
import com.example.myapplication.databinding.ActivityHistoryBinding
import com.example.myapplication.ui.adapter.TripAdapter
import com.example.myapplication.utils.FileExporter
import kotlinx.coroutines.launch
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import com.example.myapplication.R
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin

class HistoryActivity : AppCompatActivity() {

    private lateinit var binding: ActivityHistoryBinding
    private var tripAdapter: TripAdapter? = null
    private var testSeedInserted = false
    private var isDiagnosisRunning = false
    private var loadingDialog: androidx.appcompat.app.AlertDialog? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityHistoryBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Setup RecyclerView
        setupTripList()

        // Setup export button
        binding.btnExport.setOnClickListener {
            exportData()
        }

        binding.tvSubtitle.text = "Trips, demo sessions, and saved diagnostics"

        // Setup bottom navigation
        binding.bottomNavigation.selectedItemId = R.id.nav_history
        binding.bottomNavigation.setOnItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_home -> {
                    startActivity(Intent(this, com.example.myapplication.MainActivity::class.java))
                    true
                }
                R.id.nav_connection -> {
                    startActivity(Intent(this, com.example.myapplication.ui.connection.ConnectionActivity::class.java))
                    true
                }
                R.id.nav_history -> true
                else -> false
            }
        }

        // Load trip data
        loadTrips()
    }

    private fun setupTripList() {
        tripAdapter = TripAdapter { tripItem ->
            // View details click - show dialog with full details
            showTripDetails(tripItem)
        }

        binding.recyclerTrips.apply {
            layoutManager = LinearLayoutManager(this@HistoryActivity)
            adapter = tripAdapter
        }
    }

    private fun loadTrips() {
        lifecycleScope.launch {
            val app = application as MyApplication
            val sessionRepository = app.sessionRepository
            val diagnosticRepository = app.diagnosticRepository

            sessionRepository.getAllSessions().collect { sessions: List<DriveSession> ->
                val visibleSessions = sessions.filter { it.sampleCount > 0 }
                if (visibleSessions.isEmpty()) {
                    binding.recyclerTrips.visibility = View.GONE
                    binding.emptyState.visibility = View.VISIBLE

                    if (!testSeedInserted) {
                        testSeedInserted = true
                        injectTestData()
                    }
                } else {
                    binding.emptyState.visibility = View.GONE
                    binding.recyclerTrips.visibility = View.VISIBLE
                    val latestReportMap = visibleSessions.associate { session ->
                        val latest = diagnosticRepository.getLatestReport(session.id)
                        val typeLabel = when (latest?.reportType) {
                            "RULE_BASED" -> "RULE"
                            "LLM" -> "LLM"
                            "HYBRID" -> "HYBRID"
                            else -> null
                        }
                        session.id to if (latest != null && !typeLabel.isNullOrBlank()) {
                            Pair(typeLabel, latest.severity)
                        } else {
                            Pair("", "")
                        }
                    }
                    tripAdapter?.submitList(TripAdapter.createTripItems(visibleSessions, latestReportMap))
                }
            }
        }
    }

    /**
     * Insert a batch of test vehicle data to verify history activity renders correctly.
     * Simulates ~15 min trip with varying RPM, speed, temps, etc.
     */
    private fun injectTestData() {
        lifecycleScope.launch(Dispatchers.IO) {
            val app = application as MyApplication
            val repository = app.repository
            val sessionId = repository.startSession(
                sourceType = DriveSession.SOURCE_DEMO,
                title = "History Demo Session"
            )
            val baseTime = System.currentTimeMillis() - 15 * 60 * 1000 // 15 min ago

            // Generate ~20 data points across a 15-minute trip
            val testData = List(20) { i ->
                val elapsedMs = i * 45_000L // 45s between samples
                val progress = i / 19.0 // 0.0 → 1.0 across the trip

                VehicleData(
                    sessionId = sessionId,
                    sourceType = DriveSession.SOURCE_DEMO,
                    timestamp = baseTime + elapsedMs,
                    rpm = (800 + (1500 * sin(progress * PI * 2)) + 500).toInt(),
                    coolantTemp = (85 + (10 * sin(progress * PI))).toInt(),
                    intakeTemp = (25 + (5 * cos(progress * PI * 2))).toInt(),
                    throttlePos = (15 + (40 * sin(progress * PI * 2))).toInt().coerceIn(0, 100),
                    batteryVoltage = 13.8 + (0.3 * sin(progress * PI * 3)),

                    // Extended diagnostics
                    engineLoad = (35.0 + (25.0 * sin(progress * PI * 2))).coerceIn(0.0, 100.0),
                    speed = (30 + (60 * sin(progress * PI * 2) + 20)).toInt().coerceIn(0, 120),
                    intakeManifoldPressure = 45.0 + (15.0 * sin(progress * PI * 2)),
                    mafRate = 5.0 + (8.0 * sin(progress * PI * 2)),
                    fuelPressure = 350.0,
                    fuelLevel = 68.0 - (3.0 * progress),
                    shortTermFuelTrimBank1 = 1.5 + (0.5 * sin(progress * PI)),
                    longTermFuelTrimBank1 = -0.8,
                    shortTermFuelTrimBank2 = 0.0,
                    longTermFuelTrimBank2 = 0.0,
                    timingAdvance = 12.0 + (8.0 * sin(progress * PI * 2)),
                    equivalenceRatio = 1.0 + (0.02 * sin(progress * PI * 2)),
                    acceleratorPedalPos = (10.0 + (35.0 * sin(progress * PI * 2))).coerceIn(0.0, 100.0),
                    runTime = 3600.0 + (elapsedMs / 1000.0),
                    warmupsSinceCodesCleared = 3,
                    timeSinceCodesCleared = 1440.0
                )
            }

            testData.forEach { repository.saveVehicleData(it) }
            repository.endActiveSession()

            withContext(Dispatchers.Main) {
                Toast.makeText(this@HistoryActivity, "🧪 Test data inserted — 15 min trip simulated", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun showTripDetails(tripItem: TripAdapter.TripItem) {
        androidx.appcompat.app.AlertDialog.Builder(this)
            .setTitle("Session Details")
            .setMessage(
                "Date: ${java.text.SimpleDateFormat("MMM d, yyyy HH:mm", java.util.Locale.getDefault()).format(java.util.Date(tripItem.date))}\n\n" +
                "Source: ${tripItem.sourceType}\n" +
                "Duration: ${tripItem.duration} min\n" +
                "Distance: ${String.format("%.2f", tripItem.distance)} km\n" +
                "Avg Speed: ${String.format("%.1f", tripItem.avgSpeed)} km/h\n" +
                "Max RPM: ${tripItem.maxRpm}\n" +
                "Samples: ${tripItem.sampleCount}\n" +
                "Avg Coolant: ${String.format("%.1f", tripItem.avgCoolantTemp)} °C\n" +
                "Max Coolant: ${tripItem.maxCoolantTemp} °C\n" +
                "Avg Battery: ${String.format("%.2f", tripItem.avgBatteryVoltage)} V\n" +
                "Max Load: ${String.format("%.1f", tripItem.maxEngineLoad)} %"
            )
            .setNeutralButton("Run Diagnosis") { _, _ ->
                runRuleDiagnosis(tripItem.id)
            }
            .setNegativeButton("Preview LLM") { _, _ ->
                showLlmPreviewOptions(tripItem.id)
            }
            .setPositiveButton("OK", null)
            .show()
    }

    private fun runRuleDiagnosis(sessionId: Long) {
        if (!beginDiagnosisRun("Running rule-based diagnosis...")) return
        lifecycleScope.launch {
            try {
                val report = (application as MyApplication)
                    .diagnosticRepository
                    .runRuleBasedDiagnosis(sessionId)

                startActivity(
                    Intent(this@HistoryActivity, DiagnosticReportActivity::class.java)
                        .putExtra(DiagnosticReportActivity.EXTRA_REPORT_ID, report.id)
                        .putExtra(DiagnosticReportActivity.EXTRA_REPORT_TYPE, "Rule-Based Diagnosis")
                )
            } catch (e: Exception) {
                Toast.makeText(this@HistoryActivity, "Diagnosis failed: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                endDiagnosisRun()
            }
        }
    }

    private fun showLlmPreviewOptions(sessionId: Long) {
        val items = arrayOf("Preview JSON Input", "Preview Prompt Text", "Run LLM Diagnosis", "Run Remote LLM Diagnosis")
        androidx.appcompat.app.AlertDialog.Builder(this)
            .setTitle("LLM Input Preview")
            .setItems(items) { _, which ->
                when (which) {
                    0 -> previewLlmJson(sessionId)
                    1 -> previewLlmPrompt(sessionId)
                    2 -> runLlmDiagnosis(sessionId)
                    3 -> runRemoteLlmDiagnosis(sessionId)
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun previewLlmJson(sessionId: Long) {
        lifecycleScope.launch {
            try {
                val json = (application as MyApplication)
                    .diagnosticRepository
                    .buildLlmInputJson(sessionId)

                androidx.appcompat.app.AlertDialog.Builder(this@HistoryActivity)
                    .setTitle("LLM JSON Input")
                    .setMessage(json.take(12000))
                    .setPositiveButton("OK", null)
                    .show()
            } catch (e: Exception) {
                Toast.makeText(this@HistoryActivity, "Preview failed: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun previewLlmPrompt(sessionId: Long) {
        lifecycleScope.launch {
            try {
                val prompt = (application as MyApplication)
                    .diagnosticRepository
                    .buildLlmPromptText(sessionId)

                androidx.appcompat.app.AlertDialog.Builder(this@HistoryActivity)
                    .setTitle("LLM Prompt Preview")
                    .setMessage(prompt.take(12000))
                    .setPositiveButton("OK", null)
                    .show()
            } catch (e: Exception) {
                Toast.makeText(this@HistoryActivity, "Preview failed: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun runLlmDiagnosis(sessionId: Long) {
        if (!beginDiagnosisRun("Running local LLM diagnosis...")) return
        lifecycleScope.launch {
            try {
                val report = (application as MyApplication)
                    .diagnosticRepository
                    .runLlmDiagnosis(sessionId)

                startActivity(
                    Intent(this@HistoryActivity, DiagnosticReportActivity::class.java)
                        .putExtra(DiagnosticReportActivity.EXTRA_REPORT_ID, report.id)
                        .putExtra(DiagnosticReportActivity.EXTRA_REPORT_TYPE, "LLM Diagnosis")
                )
            } catch (e: Exception) {
                Toast.makeText(this@HistoryActivity, "LLM diagnosis failed: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                endDiagnosisRun()
            }
        }
    }

    private fun runRemoteLlmDiagnosis(sessionId: Long) {
        if (!beginDiagnosisRun("Calling remote LLM...")) return
        lifecycleScope.launch {
            try {
                val report = (application as MyApplication)
                    .diagnosticRepository
                    .runRemoteLlmDiagnosis(sessionId)

                startActivity(
                    Intent(this@HistoryActivity, DiagnosticReportActivity::class.java)
                        .putExtra(DiagnosticReportActivity.EXTRA_REPORT_ID, report.id)
                        .putExtra(DiagnosticReportActivity.EXTRA_REPORT_TYPE, "Remote LLM Diagnosis")
                )
            } catch (e: Exception) {
                e.printStackTrace()
                val detail = e.message ?: "no message"
                Toast.makeText(this@HistoryActivity, "Remote LLM failed: ${e.javaClass.simpleName}: ${detail.take(180)}", Toast.LENGTH_LONG).show()
            } finally {
                endDiagnosisRun()
            }
        }
    }

    private fun beginDiagnosisRun(message: String): Boolean {
        if (isDiagnosisRunning) {
            Toast.makeText(this, "A diagnosis is already running...", Toast.LENGTH_SHORT).show()
            return false
        }
        isDiagnosisRunning = true
        showLoadingDialog(message)
        return true
    }

    private fun endDiagnosisRun() {
        isDiagnosisRunning = false
        loadingDialog?.dismiss()
        loadingDialog = null
    }

    private fun showLoadingDialog(message: String) {
        val container = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.HORIZONTAL
            setPadding(48, 40, 48, 40)
            gravity = android.view.Gravity.CENTER_VERTICAL
        }

        val progressBar = ProgressBar(this).apply {
            isIndeterminate = true
        }
        container.addView(progressBar)

        val textView = android.widget.TextView(this).apply {
            text = message
            setTextColor(getColor(R.color.text_primary))
            textSize = 15f
            setPadding(24, 0, 0, 0)
        }
        container.addView(textView)

        loadingDialog?.dismiss()
        loadingDialog = androidx.appcompat.app.AlertDialog.Builder(this)
            .setView(container)
            .setCancelable(false)
            .create()
        loadingDialog?.show()
    }

    private fun exportData() {
        lifecycleScope.launch {
            try {
                val csvFile = FileExporter.exportToCsv(this@HistoryActivity, (application as MyApplication).repository)

                val shareIntent = Intent(Intent.ACTION_SEND).apply {
                    type = "text/csv"
                    putExtra(Intent.EXTRA_STREAM, androidx.core.content.FileProvider.getUriForFile(
                        this@HistoryActivity,
                        "${packageName}.fileprovider",
                        csvFile
                    ))
                    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                }

                startActivity(Intent.createChooser(shareIntent, "Export trip data"))
            } catch (e: Exception) {
                Toast.makeText(this@HistoryActivity, "Export failed: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }
}
