package com.example.myapplication.data.repository

import com.example.myapplication.data.local.DiagnosticReport
import org.json.JSONArray
import org.json.JSONObject

class LlmDiagnosisExecutor {

    data class LlmExecutionResult(
        val severity: String,
        val summary: String,
        val findingsJson: String,
        val recommendationsJson: String,
        val rawOutputText: String
    )

    fun run(input: LlmDiagnosticInput): LlmExecutionResult {
        val likelyCauses = mutableListOf<String>()
        val recommendations = input.ruleSummary.recommendations.toMutableList()

        input.ruleSummary.findings.forEach { finding ->
            when (finding.code) {
                "COOLANT_OVERHEAT" -> likelyCauses += "Cooling system inefficiency, heavy thermal load, or low coolant flow"
                "BATTERY_LOW_CHARGING" -> likelyCauses += "Weak charging output, electrical load, or battery/ground issue"
                "BATTERY_HIGH_CHARGING" -> likelyCauses += "Over-active regulation or charging control issue"
                "LTFT_POSITIVE_HIGH", "LAMBDA_LEAN" -> likelyCauses += "Lean tendency, intake leak, MAF contamination, or fuel delivery weakness"
                "LTFT_NEGATIVE_HIGH", "LAMBDA_RICH" -> likelyCauses += "Rich tendency, sensor bias, or excess fuel delivery"
                "STFT_SPIKE" -> likelyCauses += "Transient fueling instability during load transitions"
                "HIGH_ENGINE_LOAD" -> likelyCauses += "High driver demand or heavy operating conditions affecting readings"
            }
        }

        if (likelyCauses.isEmpty()) {
            likelyCauses += "No strong fault pattern identified from current structured data"
        }

        val confidence = when {
            input.promptHints.isDemoData -> "low"
            input.ruleSummary.findings.size >= 3 -> "medium"
            input.ruleSummary.findings.isNotEmpty() -> "medium"
            else -> "low"
        }

        val summary = buildSummary(input)
        val findingsJson = JSONArray().apply {
            input.ruleSummary.findings.forEach { finding ->
                put(JSONObject().apply {
                    put("code", finding.code)
                    put("severity", finding.severity)
                    put("title", finding.title)
                    put("detail", finding.detail)
                })
            }
            likelyCauses.distinct().forEach { cause ->
                put(JSONObject().apply {
                    put("code", "LIKELY_CAUSE")
                    put("severity", input.ruleSummary.severity)
                    put("title", "Likely cause")
                    put("detail", cause)
                })
            }
        }.toString()

        val recommendationsJson = JSONArray(recommendations.distinct()).toString()
        val rawOutputText = JSONObject().apply {
            put("severity", input.ruleSummary.severity)
            put("summary", summary)
            put("likelyCauses", JSONArray(likelyCauses.distinct()))
            put("recommendedChecks", JSONArray(recommendations.distinct()))
            put("confidence", confidence)
            put("notes", JSONArray().apply {
                put(if (input.promptHints.isDemoData) "This analysis is based on simulated demo data." else "This analysis is based on captured session data.")
                put("Use this as guidance, not a definitive fault confirmation.")
            })
        }.toString(2)

        return LlmExecutionResult(
            severity = input.ruleSummary.severity,
            summary = summary,
            findingsJson = findingsJson,
            recommendationsJson = recommendationsJson,
            rawOutputText = rawOutputText
        )
    }

    fun toDiagnosticReport(
        sessionId: Long,
        inputJson: String,
        result: LlmExecutionResult,
        modelName: String = "local-llm-prep-v1",
        promptVersion: String = "v1"
    ): DiagnosticReport {
        return DiagnosticReport(
            sessionId = sessionId,
            createdAt = System.currentTimeMillis(),
            reportType = DiagnosticReport.TYPE_LLM,
            modelName = modelName,
            modelVersion = "offline",
            promptVersion = promptVersion,
            severity = result.severity,
            summary = result.summary,
            findingsJson = result.findingsJson,
            recommendationsJson = result.recommendationsJson,
            rawInputSnapshotJson = inputJson,
            rawOutputText = result.rawOutputText
        )
    }

    private fun buildSummary(input: LlmDiagnosticInput): String {
        return when {
            input.promptHints.isDemoData -> "Simulated session suggests: ${input.ruleSummary.summary.lowercase()}"
            input.ruleSummary.findings.isEmpty() -> "No strong issue pattern detected from this captured session; continue gathering more real-world data."
            else -> "Structured diagnostic review suggests: ${input.ruleSummary.summary.lowercase()}"
        }
    }
}
