package com.example.myapplication.ui.dashboard

import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.view.animation.AnimationUtils
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.myapplication.MyApplication
import com.example.myapplication.R
import com.example.myapplication.data.local.VehicleData
import com.example.myapplication.databinding.DashboardBinding
import com.example.myapplication.utils.SimulatedDataManager
import com.github.mikephil.charting.charts.LineChart
import com.github.mikephil.charting.components.XAxis
import com.github.mikephil.charting.data.Entry
import com.github.mikephil.charting.data.LineData
import com.github.mikephil.charting.data.LineDataSet
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

/**
 * Dashboard Activity - Real-time OBD2 monitoring
 * Displays 6 key metrics with status indicators and RPM chart
 * 
 * Features:
 * - Real-time data streaming (500ms interval)
 * - Status indicators with color coding
 * - RPM history chart (30 seconds)
 * - Session statistics tracking
 * - Simulation mode for demo
 */
class DashboardActivity : AppCompatActivity() {

    private lateinit var binding: DashboardBinding
    private val repository by lazy { (application as MyApplication).repository }
    
    // Chart data
    private val rpmEntries = mutableListOf<Entry>()
    private var xIndex = 0
    
    // Session tracking
    private var sessionStartTime: Long = 0
    private val rpmValues = mutableListOf<Int>()
    private var maxRpm = 0
    
    // Simulation mode
    private var isSimulationMode = false
    
    // UI helpers
    private val handler = Handler(Looper.getMainLooper())
    private val timeFormat = SimpleDateFormat("HH:mm:ss", Locale.getDefault())
    
    // Status thresholds
    private val rpmNormalRange = 600..4000
    private val coolantNormalRange = 75..105
    private val batteryNormalRange = 13.5..14.8
    private val intakeNormalRange = 20..60

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        try {
            // Initialize ViewBinding
            binding = DashboardBinding.inflate(layoutInflater)
            setContentView(binding.root)

            // Start session tracking
            sessionStartTime = System.currentTimeMillis()
            
            // Check if launched in simulation mode from MainActivity
            isSimulationMode = intent.getBooleanExtra("simulation_mode", false)
            
            // Setup UI components
            setupToolbar()
            setupChart()
            setupBottomNavigation()
            
            // Start data observation
            observeData()
            
            // Show connection status
            showConnectionBanner()
            
            // Show demo mode hint on first launch
            showDemoHint()
            
            // If launched in simulation mode, show confirmation
            if (isSimulationMode) {
                Toast.makeText(this, "🎉 Demo Mode Enabled", Toast.LENGTH_SHORT).show()
            }
        } catch (e: Exception) {
            e.printStackTrace()
            Toast.makeText(this, "Error: ${e.message}", Toast.LENGTH_LONG).show()
            finish()
        }
    }

    /**
     * Setup toolbar buttons
     */
    private fun setupToolbar() {
        // Simulation toggle button
        binding.btnSimulation.setOnClickListener {
            toggleSimulationMode()
        }
        
        // Refresh button
        binding.btnRefresh.setOnClickListener {
            refreshData()
        }

        // Export button
        binding.btnExport.setOnClickListener {
            exportData()
        }
        
        // Long press refresh to toggle simulation (alternative method)
        binding.btnRefresh.setOnLongClickListener {
            toggleSimulationMode()
            true
        }
    }

    /**
     * Configure RPM chart with optimal settings
     */
    private fun setupChart() {
        binding.lineChart.apply {
            description.isEnabled = false
            setTouchEnabled(true)
            isDragEnabled = true
            setScaleEnabled(true)
            setPinchZoom(true)

            // X-axis configuration
            xAxis.position = XAxis.XAxisPosition.BOTTOM
            xAxis.setDrawGridLines(false)
            xAxis.granularity = 1f
            xAxis.textColor = resources.getColor(R.color.text_secondary, null)

            // Y-axis configuration
            axisLeft.setDrawGridLines(true)
            axisLeft.textColor = resources.getColor(R.color.text_secondary, null)
            axisLeft.axisMinimum = 0f
            axisLeft.axisMaximum = 8000f
            axisRight.isEnabled = false
            
            // Legend and styling
            legend.isEnabled = false
            
            // Empty state
            setNoDataText("Waiting for OBD2 data...")
            setNoDataTextColor(resources.getColor(R.color.text_secondary, null))
            
            // Initial animation
            animateY(1000)
        }
    }

    /**
     * Observe data stream from repository or simulation
     */
    private fun observeData() {
        lifecycleScope.launch {
            try {
                val dataFlow = if (isSimulationMode) {
                    // 确保模拟模式已设置
                    SimulatedDataManager.setSimulationMode(SimulatedDataManager.SimulationMode.IDLE)
                    SimulatedDataManager.startSimulation()
                } else {
                    repository.startLiveDataStream()
                }

                // 收集数据流并更新UI
                dataFlow.collect { data ->
                    // 确保在主线程更新UI
                    runOnUiThread {
                        updateUI(data)
                        updateChart(data)
                        updateSessionStats(data)
                    }
                }
            } catch (e: Exception) {
                e.printStackTrace()
                Toast.makeText(this@DashboardActivity, "Data error: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    /**
     * Update all UI elements with new data
     */
    private fun updateUI(data: VehicleData) {
        // Update metric values with fade animation
        animateTextView(binding.tvRpm, data.rpm.toString())
        animateTextView(binding.tvCoolantTemp, "${data.coolantTemp} °C")
        animateTextView(binding.tvIntakeTemp, "${data.intakeTemp} °C")
        animateTextView(binding.tvThrottle, "${data.throttlePos} %")
        animateTextView(binding.tvBattery, "${String.format("%.2f", data.batteryVoltage)} V")
        animateTextView(binding.tvSpeed, "${calculateSpeed(data.rpm)} km/h")
        
        // Update status indicators with color coding
        updateStatusIndicator(binding.tvRpmStatus, checkRpmStatus(data.rpm))
        updateStatusIndicator(binding.tvCoolantStatus, checkCoolantStatus(data.coolantTemp))
        updateStatusIndicator(binding.tvBatteryStatus, checkBatteryStatus(data.batteryVoltage))
        updateStatusIndicator(binding.tvIntakeStatus, checkIntakeStatus(data.intakeTemp))
        updateStatusIndicator(binding.tvThrottleStatus, checkThrottleStatus(data.throttlePos))
        
        // Update timestamp with pulse animation
        binding.tvTimestamp.text = "Live • ${timeFormat.format(Date(data.timestamp))}"
        pulseAnimation(binding.connectionIndicator)
    }

    /**
     * Update RPM chart with new data point
     */
    private fun updateChart(data: VehicleData) {
        rpmEntries.add(Entry(xIndex.toFloat(), data.rpm.toFloat()))
        xIndex++

        // Keep last 60 points (30 seconds at 500ms interval)
        if (rpmEntries.size > 60) {
            rpmEntries.removeAt(0)
            // Re-index for smooth scrolling
            for (i in rpmEntries.indices) {
                rpmEntries[i] = Entry(i.toFloat(), rpmEntries[i].y)
            }
            xIndex = rpmEntries.size
        }

        // Configure chart dataset
        val dataSet = LineDataSet(rpmEntries, "RPM").apply {
            color = resources.getColor(R.color.accent, null)
            setCircleColor(resources.getColor(R.color.accent, null))
            lineWidth = 2.5f
            circleRadius = 3f
            setDrawCircleHole(false)
            setDrawValues(false)
            setDrawFilled(true)
            fillColor = resources.getColor(R.color.accent_light, null)
            fillAlpha = 60
            mode = LineDataSet.Mode.CUBIC_BEZIER // Smooth curves
            cubicIntensity = 0.2f
        }

        binding.lineChart.data = LineData(dataSet)
        binding.lineChart.notifyDataSetChanged()
        binding.lineChart.invalidate()
    }

    /**
     * Update session statistics
     */
    private fun updateSessionStats(data: VehicleData) {
        rpmValues.add(data.rpm)
        if (data.rpm > maxRpm) maxRpm = data.rpm
        
        val avgRpm = rpmValues.average().toInt()
        val duration = (System.currentTimeMillis() - sessionStartTime) / 1000
        
        binding.tvAvgRpm.text = avgRpm.toString()
        binding.tvMaxRpm.text = maxRpm.toString()
        binding.tvDuration.text = formatDuration(duration)
    }

    // ==================== Status Check Functions ====================

    private fun checkRpmStatus(rpm: Int): Status {
        return when {
            rpm < 600 -> Status.Warning("Low")
            rpm > 6000 -> Status.Danger("High")
            else -> Status.Normal("Normal")
        }
    }

    private fun checkCoolantStatus(temp: Int): Status {
        return when {
            temp < 75 -> Status.Warning("Cold")
            temp > 105 -> Status.Danger("Hot")
            else -> Status.Normal("Normal")
        }
    }

    private fun checkBatteryStatus(voltage: Double): Status {
        return when {
            voltage < 13.5 -> Status.Warning("Low")
            voltage > 14.8 -> Status.Danger("High")
            else -> Status.Normal("Normal")
        }
    }

    private fun checkIntakeStatus(temp: Int): Status {
        return when {
            temp < 20 -> Status.Warning("Cold")
            temp > 60 -> Status.Warning("Hot")
            else -> Status.Normal("Normal")
        }
    }

    private fun checkThrottleStatus(pos: Int): Status {
        return when {
            pos > 90 -> Status.Warning("WOT")
            else -> Status.Normal("Normal")
        }
    }

    private fun updateStatusIndicator(textView: android.widget.TextView, status: Status) {
        textView.text = status.text
        textView.setTextColor(
            when (status) {
                is Status.Normal -> resources.getColor(R.color.success, null)
                is Status.Warning -> resources.getColor(R.color.warning, null)
                is Status.Danger -> resources.getColor(R.color.error, null)
            }
        )
    }

    // ==================== UI Helper Functions ====================

    private fun animateTextView(textView: android.widget.TextView, value: String) {
        val fadeIn = AnimationUtils.loadAnimation(this, R.anim.fade_in)
        fadeIn.duration = 200
        textView.startAnimation(fadeIn)
        textView.text = value
    }

    private fun pulseAnimation(view: View) {
        val pulse = AnimationUtils.loadAnimation(this, R.anim.fade_in)
        pulse.duration = 1000
        view.startAnimation(pulse)
    }

    private fun refreshData() {
        Toast.makeText(this, "Refreshing data...", Toast.LENGTH_SHORT).show()
    }

    private fun exportData() {
        Toast.makeText(this, "Export coming soon", Toast.LENGTH_SHORT).show()
    }

    private fun toggleSimulationMode() {
        isSimulationMode = !isSimulationMode
        SimulatedDataManager.setSimulationMode(SimulatedDataManager.SimulationMode.IDLE)
        
        val modeText = if (isSimulationMode) "SIMULATION ON" else "LIVE DATA"
        Toast.makeText(this, modeText, Toast.LENGTH_SHORT).show()
        
        // Update UI
        binding.tvTitle.text = if (isSimulationMode) "OBD2 Demo Mode" else "OBD2 Diagnostics"
        binding.btnSimulation.setImageResource(
            if (isSimulationMode) R.drawable.ic_check_circle else R.drawable.ic_info
        )
        
        // Update connection banner
        showConnectionBanner()
    }

    private fun showConnectionBanner() {
        binding.cardConnectionBanner.visibility = View.VISIBLE
        
        if (isSimulationMode) {
            binding.tvConnectedDevice.text = "Demo Mode - Simulated Data"
            binding.tvConnectionQuality.text = "📊 Simulation Active"
            binding.tvConnectionQuality.setTextColor(
                resources.getColor(R.color.info, null)
            )
            binding.connectionIndicator.visibility = View.GONE
            binding.simulationIndicator.visibility = View.VISIBLE
        } else {
            binding.tvConnectedDevice.text = "OBD-II Scanner"
            binding.tvConnectionQuality.text = "Signal: Excellent"
            binding.tvConnectionQuality.setTextColor(
                resources.getColor(R.color.signal_excellent, null)
            )
            binding.connectionIndicator.visibility = View.VISIBLE
            binding.simulationIndicator.visibility = View.GONE
        }
    }

    private fun setupBottomNavigation() {
        binding.bottomNavigation.selectedItemId = R.id.nav_home
        binding.bottomNavigation.setOnItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_home -> true
                R.id.nav_connection -> {
                    startActivity(Intent(this, com.example.myapplication.ui.connection.ConnectionActivity::class.java))
                    overridePendingTransition(R.anim.slide_in_right, R.anim.slide_out_left)
                    true
                }
                R.id.nav_history -> {
                    startActivity(Intent(this, com.example.myapplication.ui.history.HistoryActivity::class.java))
                    overridePendingTransition(R.anim.slide_in_right, R.anim.slide_out_left)
                    true
                }
                else -> false
            }
        }
    }
    
    /**
     * Show hint about demo mode on first launch
     */
    private fun showDemoHint() {
        // Only show if no data received yet and not in simulation mode
        if (rpmValues.isEmpty() && !isSimulationMode) {
            Toast.makeText(
                this, 
                "💡 Tip: Tap the button to enable demo mode without OBD2 device", 
                Toast.LENGTH_LONG
            ).show()
        }
    }

    private fun calculateSpeed(rpm: Int): Int {
        return (rpm * 0.03).toInt()
    }

    private fun formatDuration(seconds: Long): String {
        val minutes = seconds / 60
        val secs = seconds % 60
        return String.format("%02d:%02d", minutes, secs)
    }

    override fun onDestroy() {
        super.onDestroy()
        handler.removeCallbacksAndMessages(null)
        if (!isSimulationMode) {
            repository.disconnect()
        } else {
            SimulatedDataManager.stopSimulation()
        }
    }
}

// Status sealed class for type-safe status handling
sealed class Status(val text: String) {
    class Normal(text: String) : Status(text)
    class Warning(text: String) : Status(text)
    class Danger(text: String) : Status(text)
}
