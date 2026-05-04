package com.example.myapplication.data.repository

import com.example.myapplication.data.local.DiagnosticReport
import org.json.JSONArray
import org.json.JSONObject

class RemoteLlmDiagnosisExecutor(
    private val apiClient: RemoteLlmApiClient,
    private val config: LlmProviderConfig
) {

    fun run(sessionId: Long, input: LlmDiagnosticInput, prompt: String, inputJson: String): DiagnosticReport {
        val apiResult = apiClient.runDiagnosis(prompt)
        val parsed = parseRemoteOutput(apiResult.parsedText, input)
        return DiagnosticReport(
            sessionId = sessionId,
            createdAt = System.currentTimeMillis(),
            reportType = DiagnosticReport.TYPE_LLM,
            modelName = config.providerName,
            modelVersion = config.model,
            promptVersion = "remote-v1",
            severity = parsed.severity,
            summary = parsed.summary,
            findingsJson = parsed.findingsJson,
            recommendationsJson = parsed.recommendationsJson,
            rawInputSnapshotJson = inputJson,
            rawOutputText = apiResult.rawText
        )
    }

    private fun parseRemoteOutput(text: String, input: LlmDiagnosticInput): ParsedRemoteOutput {
        val normalized = stripMarkdownCodeFence(text)
        val candidate = extractFirstJsonObject(normalized) ?: normalized

        return try {
            val json = JSONObject(candidate)
            val severity = json.optString("severity").ifBlank { input.ruleSummary.severity }
            val summary = json.optString("summary").ifBlank { input.ruleSummary.summary }
            val likelyCauses = parseStringArray(json, "likelyCauses")
            val recommendedChecks = parseStringArray(json, "recommendedChecks")

            val findingsJson = JSONArray().apply {
                input.ruleSummary.findings.forEach { finding ->
                    put(JSONObject().apply {
                        put("code", finding.code)
                        put("severity", finding.severity)
                        put("title", finding.title)
                        put("detail", finding.detail)
                    })
                }
                likelyCauses.forEach { cause ->
                    put(JSONObject().apply {
                        put("code", "REMOTE_LIKELY_CAUSE")
                        put("severity", severity)
                        put("title", "Likely cause")
                        put("detail", cause)
                    })
                }
            }.toString()

            val recommendationsJson = JSONArray().apply {
                if (recommendedChecks.isEmpty()) {
                    input.ruleSummary.recommendations.forEach { put(it) }
                } else {
                    recommendedChecks.forEach { put(it) }
                }
            }.toString()

            ParsedRemoteOutput(severity, summary, findingsJson, recommendationsJson)
        } catch (_: Exception) {
            ParsedRemoteOutput(
                severity = input.ruleSummary.severity,
                summary = normalized.take(500).ifBlank { input.ruleSummary.summary },
                findingsJson = JSONArray().apply {
                    input.ruleSummary.findings.forEach { finding ->
                        put(JSONObject().apply {
                            put("code", finding.code)
                            put("severity", finding.severity)
                            put("title", finding.title)
                            put("detail", finding.detail)
                        })
                    }
                }.toString(),
                recommendationsJson = JSONArray(input.ruleSummary.recommendations).toString()
            )
        }
    }

    private fun stripMarkdownCodeFence(text: String): String {
        return text
            .replace("```json", "")
            .replace("```JSON", "")
            .replace("```", "")
            .trim()
    }

    private fun extractFirstJsonObject(text: String): String? {
        val start = text.indexOf('{')
        if (start < 0) return null

        var depth = 0
        for (index in start until text.length) {
            when (text[index]) {
                '{' -> depth++
                '}' -> {
                    depth--
                    if (depth == 0) {
                        return text.substring(start, index + 1)
                    }
                }
            }
        }
        return null
    }

    private fun parseStringArray(json: JSONObject, key: String): List<String> {
        val keys = when (key) {
            "likelyCauses" -> listOf("likelyCauses", "likely_causes", "causes", "possibleCauses")
            "recommendedChecks" -> listOf("recommendedChecks", "recommended_checks", "recommendations", "nextChecks")
            else -> listOf(key)
        }

        for (candidateKey in keys) {
            val array = json.optJSONArray(candidateKey) ?: continue
            val values = buildList {
                for (i in 0 until array.length()) {
                    val value = array.optString(i)
                    if (value.isNotBlank()) add(value)
                }
            }
            if (values.isNotEmpty()) return values
        }
        return emptyList()
    }

    private data class ParsedRemoteOutput(
        val severity: String,
        val summary: String,
        val findingsJson: String,
        val recommendationsJson: String
    )
}
