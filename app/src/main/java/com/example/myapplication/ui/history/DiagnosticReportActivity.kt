package com.example.myapplication.ui.history

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.myapplication.MyApplication
import com.example.myapplication.R
import com.example.myapplication.databinding.ActivityDiagnosticReportBinding
import kotlinx.coroutines.launch
import org.json.JSONArray
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class DiagnosticReportActivity : AppCompatActivity() {

    private lateinit var binding: ActivityDiagnosticReportBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDiagnosticReportBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnBack.setOnClickListener { finish() }

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
            binding.tvSeverity.setTextColor(
                when (report.severity) {
                    "HIGH", "WARNING" -> getColor(R.color.warning)
                    "NOTICE" -> getColor(R.color.info)
                    else -> getColor(R.color.success)
                }
            )
            binding.tvSummary.text = report.summary
            binding.tvFindings.text = formatJsonLines(report.findingsJson)
            binding.tvRecommendations.text = formatJsonLines(report.recommendationsJson)
            binding.tvRawOutput.text = report.rawOutputText ?: report.rawInputSnapshotJson ?: "No raw output"
        }
    }

    private fun formatJsonLines(json: String): String {
        return try {
            val array = JSONArray(json)
            if (array.length() == 0) return "No items"
            buildString {
                for (i in 0 until array.length()) {
                    val item = array.get(i)
                    when (item) {
                        is String -> appendLine("• $item")
                        is org.json.JSONObject -> {
                            val title = item.optString("title")
                            val detail = item.optString("detail")
                            appendLine("• $title")
                            if (detail.isNotBlank()) appendLine("  $detail")
                        }
                    }
                }
            }.trim()
        } catch (_: Exception) {
            json
        }
    }

    companion object {
        const val EXTRA_REPORT_ID = "report_id"
        const val EXTRA_REPORT_TYPE = "report_type"
    }
}
