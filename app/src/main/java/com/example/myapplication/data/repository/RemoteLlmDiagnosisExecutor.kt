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
            val validated = RemoteDiagnosisGuardrail.validate(
                rawJson = json,
                input = input,
                fallbackSeverity = input.ruleSummary.severity,
                fallbackSummary = input.ruleSummary.summary,
                fallbackRecommendations = input.ruleSummary.recommendations
            )

            ParsedRemoteOutput(
                severity = validated.severity,
                summary = validated.summary,
                findingsJson = RemoteDiagnosisGuardrail.buildFindingsJson(input, validated),
                recommendationsJson = RemoteDiagnosisGuardrail.buildRecommendationsJson(validated)
            )
        } catch (_: Exception) {
            val validated = RemoteDiagnosisGuardrail.ValidatedOutput(
                severity = input.ruleSummary.severity,
                summary = normalized.take(500).ifBlank { input.ruleSummary.summary },
                observations = listOf("Remote output could not be parsed as trusted JSON."),
                hypotheses = emptyList(),
                recommendations = input.ruleSummary.recommendations,
                confidence = "low",
                notes = listOf("Guardrail fallback used because remote output was malformed or unsupported.")
            )
            ParsedRemoteOutput(
                severity = validated.severity,
                summary = validated.summary,
                findingsJson = RemoteDiagnosisGuardrail.buildFindingsJson(input, validated),
                recommendationsJson = RemoteDiagnosisGuardrail.buildRecommendationsJson(validated)
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

    private data class ParsedRemoteOutput(
        val severity: String,
        val summary: String,
        val findingsJson: String,
        val recommendationsJson: String
    )
}
