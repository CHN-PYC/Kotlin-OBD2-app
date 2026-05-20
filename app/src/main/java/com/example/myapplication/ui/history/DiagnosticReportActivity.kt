package com.example.myapplication.ui.history

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Intent
import android.os.Bundle
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.cardview.widget.CardView
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.example.myapplication.MyApplication
import com.example.myapplication.R
import com.example.myapplication.databinding.ActivityDiagnosticReportBinding
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class DiagnosticReportActivity : AppCompatActivity() {

    private lateinit var binding: ActivityDiagnosticReportBinding
    private var rawExpanded = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDiagnosticReportBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnBack.setOnClickListener { finish() }
        binding.btnToggleRaw.setOnClickListener {
            rawExpanded = !rawExpanded
            binding.tvRawOutput.maxLines = if (rawExpanded) Int.MAX_VALUE else 14
            binding.btnToggleRaw.text = if (rawExpanded) "Show less" else "Show more"
        }

        val reportId = intent.getLongExtra(EXTRA_REPORT_ID, -1L)
        val reportType = intent.getStringExtra(EXTRA_REPORT_TYPE)

        if (reportId <= 0L) {
            binding.tvSummary.text = "Missing report id"
            return
        }

        lifecycleScope.launch {
            val repository = (application as MyApplication).diagnosticRepository
            val report = repository.getReportById(reportId)
            if (report == null) {
                binding.tvSummary.text = "No diagnostic report found for this session yet."
                return@launch
            }

            binding.tvTitle.text = reportType ?: "Diagnostic Report"
            binding.tvTimestamp.text = SimpleDateFormat("MM-dd HH:mm", Locale.getDefault())
                .format(Date(report.createdAt))
            binding.tvSeverity.text = report.severity
            applySeverityBadge(report.severity)
            binding.tvMeta.text = listOfNotNull(
                report.reportType,
                report.modelName?.takeIf { it.isNotBlank() },
                report.modelVersion?.takeIf { it.isNotBlank() }
            ).joinToString(" • ")
            binding.tvSummary.text = report.summary
            renderFindings(report.findingsJson)
            val recommendationsText = renderRecommendations(report.recommendationsJson)
            val rawText = report.rawOutputText ?: report.rawInputSnapshotJson ?: "No raw output"
            val inputText = report.rawInputSnapshotJson ?: "No input snapshot"
            binding.tvRawOutput.text = rawText
            binding.btnCopyRaw.setOnClickListener { copyToClipboard("diagnostic_raw", rawText) }
            binding.btnCopyInput.setOnClickListener { copyToClipboard("diagnostic_input", inputText) }
            binding.btnCopyPrompt.setOnClickListener {
                lifecycleScope.launch {
                    try {
                        val prompt = repository.buildLlmPromptText(report.sessionId)
                        copyToClipboard("diagnostic_prompt", prompt)
                    } catch (e: Exception) {
                        Toast.makeText(this@DiagnosticReportActivity, "Prompt unavailable: ${e.message}", Toast.LENGTH_SHORT).show()
                    }
                }
            }
            binding.btnShareSummary.setOnClickListener {
                shareText("${report.summary}\n\n$recommendationsText")
            }
        }
    }

    private fun applySeverityBadge(severity: String) {
        when (severity) {
            "HIGH", "WARNING" -> {
                binding.tvSeverity.setBackgroundResource(R.drawable.badge_warning)
                binding.tvSeverity.setTextColor(getColor(R.color.background_dark))
            }
            "NOTICE" -> {
                binding.tvSeverity.setBackgroundResource(R.drawable.badge_info)
                binding.tvSeverity.setTextColor(getColor(R.color.white))
            }
            else -> {
                binding.tvSeverity.setBackgroundResource(R.drawable.badge_success)
                binding.tvSeverity.setTextColor(getColor(R.color.background_dark))
            }
        }
    }

    private fun renderFindings(json: String) {
        binding.containerFindings.removeAllViews()
        val items = parseJsonArray(json)
        if (items.isEmpty()) {
            binding.containerFindings.addView(buildTextCard("No findings", null, null))
            return
        }
        items.forEach { item ->
            if (item is JSONObject) {
                val kind = item.optString("kind").ifBlank { "observation" }
                val title = when (kind) {
                    "hypothesis" -> "Hypothesis"
                    "note" -> "Guardrail note"
                    else -> item.optString("title").ifBlank { "Observation" }
                }
                binding.containerFindings.addView(
                    buildTextCard(
                        title,
                        item.optString("detail").ifBlank { null },
                        item.optString("severity").ifBlank { null }
                    )
                )
            } else if (item is String) {
                binding.containerFindings.addView(buildTextCard(item, null, null))
            }
        }
    }

    private fun renderRecommendations(json: String): String {
        binding.containerRecommendations.removeAllViews()
        val items = parseJsonArray(json)
        if (items.isEmpty()) {
            binding.containerRecommendations.addView(buildTextCard("No recommendations", null, null))
            return "No recommendations"
        }
        val lines = mutableListOf<String>()
        items.forEach { item ->
            val text = if (item is String) item else item.toString()
            lines += "• $text"
            binding.containerRecommendations.addView(buildTextCard(text, null, null))
        }
        return lines.joinToString("\n")
    }

    private fun parseJsonArray(json: String): List<Any> {
        return try {
            val array = JSONArray(json)
            buildList {
                for (i in 0 until array.length()) add(array.get(i))
            }
        } catch (_: Exception) {
            listOf(json)
        }
    }

    private fun buildTextCard(title: String, detail: String?, severity: String?): CardView {
        val card = CardView(this).apply {
            radius = 18f
            cardElevation = 2f
            setCardBackgroundColor(ContextCompat.getColor(context, R.color.card_background))
            val params = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            )
            params.bottomMargin = 12
            layoutParams = params
        }

        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 24, 24, 24)
        }

        val headerRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
        }

        val titleView = TextView(this).apply {
            text = "• $title"
            setTextColor(ContextCompat.getColor(context, R.color.text_primary))
            textSize = 14f
            setTypeface(typeface, android.graphics.Typeface.BOLD)
            layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
        }
        headerRow.addView(titleView)

        if (!severity.isNullOrBlank()) {
            val severityView = TextView(this).apply {
                text = severity
                setPadding(12, 6, 12, 6)
                textSize = 11f
                setTypeface(typeface, android.graphics.Typeface.BOLD)
            }
            when (severity) {
                "HIGH", "WARNING" -> {
                    severityView.setBackgroundResource(R.drawable.badge_warning)
                    severityView.setTextColor(ContextCompat.getColor(context, R.color.background_dark))
                }
                "NOTICE" -> {
                    severityView.setBackgroundResource(R.drawable.badge_info)
                    severityView.setTextColor(ContextCompat.getColor(context, R.color.white))
                }
                else -> {
                    severityView.setBackgroundResource(R.drawable.badge_success)
                    severityView.setTextColor(ContextCompat.getColor(context, R.color.background_dark))
                }
            }
            headerRow.addView(severityView)
        }

        container.addView(headerRow)

        if (!detail.isNullOrBlank()) {
            val detailView = TextView(this).apply {
                text = detail
                setTextColor(ContextCompat.getColor(context, R.color.text_secondary))
                textSize = 13f
                setPadding(0, 10, 0, 0)
            }
            container.addView(detailView)
        }

        card.addView(container)
        return card
    }

    private fun copyToClipboard(label: String, text: String) {
        val clipboard = getSystemService(ClipboardManager::class.java)
        clipboard.setPrimaryClip(ClipData.newPlainText(label, text))
        Toast.makeText(this, "Copied", Toast.LENGTH_SHORT).show()
    }

    private fun shareText(text: String) {
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_TEXT, text)
        }
        startActivity(Intent.createChooser(intent, "Share diagnosis"))
    }

    companion object {
        const val EXTRA_REPORT_ID = "report_id"
        const val EXTRA_REPORT_TYPE = "report_type"
    }
}
