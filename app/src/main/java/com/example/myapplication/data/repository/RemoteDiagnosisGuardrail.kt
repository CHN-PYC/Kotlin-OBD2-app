package com.example.myapplication.data.repository

import com.example.myapplication.data.local.DiagnosticReport
import org.json.JSONArray
import org.json.JSONObject

object RemoteDiagnosisGuardrail {

    data class ValidatedOutput(
        val severity: String,
        val summary: String,
        val observations: List<String>,
        val hypotheses: List<String>,
        val recommendations: List<String>,
        val confidence: String,
        val notes: List<String>
    )

    fun validate(
        rawJson: JSONObject,
        input: LlmDiagnosticInput,
        fallbackSeverity: String,
        fallbackSummary: String,
        fallbackRecommendations: List<String>
    ): ValidatedOutput {
        val severity = normalizeSeverity(rawJson.optString("severity"), fallbackSeverity)
        val summary = rawJson.optString("summary").ifBlank { fallbackSummary }.take(400)
        val observations = parseStringArray(rawJson, listOf("observations", "facts", "signals"))
        val hypotheses = parseStringArray(rawJson, listOf("hypotheses", "likelyCauses", "likely_causes", "causes", "possibleCauses"))
        val recommendations = parseStringArray(rawJson, listOf("recommendedChecks", "recommended_checks", "recommendations", "nextChecks"))
            .ifEmpty { fallbackRecommendations }
            .map { softenDangerousClaim(it) }
            .distinct()
        val confidence = normalizeConfidence(rawJson.optString("confidence"))
        val notes = mutableListOf<String>()

        if (input.promptHints.isDemoData) {
            notes += "Simulated demo data: conclusions should be treated as explanatory, not as real fault confirmation."
        }
        if (containsHardClaim(summary) || hypotheses.any(::containsHardClaim)) {
            notes += "Some remote wording was softened because it sounded more certain than the supporting evidence."
        }
        if (severity == DiagnosticReport.SEVERITY_HIGH && input.ruleSummary.severity == DiagnosticReport.SEVERITY_NOTICE) {
            notes += "Remote severity was reduced by guardrail if the rule engine evidence did not justify a hard escalation."
        }

        return ValidatedOutput(
            severity = coerceSeverityAgainstRuleEngine(severity, input.ruleSummary.severity),
            summary = softenDangerousClaim(summary),
            observations = observations.ifEmpty { deriveObservations(input) },
            hypotheses = hypotheses.map(::softenDangerousClaim),
            recommendations = recommendations,
            confidence = confidence,
            notes = notes.distinct()
        )
    }

    fun buildFindingsJson(input: LlmDiagnosticInput, validated: ValidatedOutput): String {
        return JSONArray().apply {
            input.ruleSummary.findings.forEach { finding ->
                put(JSONObject().apply {
                    put("kind", "observation")
                    put("code", finding.code)
                    put("severity", finding.severity)
                    put("title", finding.title)
                    put("detail", finding.detail)
                })
            }
            validated.observations.forEach { observation ->
                put(JSONObject().apply {
                    put("kind", "observation")
                    put("code", "REMOTE_OBSERVATION")
                    put("severity", validated.severity)
                    put("title", "Observation")
                    put("detail", observation)
                })
            }
            validated.hypotheses.forEach { hypothesis ->
                put(JSONObject().apply {
                    put("kind", "hypothesis")
                    put("code", "REMOTE_HYPOTHESIS")
                    put("severity", validated.severity)
                    put("title", "Hypothesis")
                    put("detail", hypothesis)
                })
            }
            validated.notes.forEach { note ->
                put(JSONObject().apply {
                    put("kind", "note")
                    put("code", "GUARDRAIL_NOTE")
                    put("severity", DiagnosticReport.SEVERITY_NOTICE)
                    put("title", "Guardrail note")
                    put("detail", note)
                })
            }
        }.toString()
    }

    fun buildRecommendationsJson(validated: ValidatedOutput): String =
        JSONArray(validated.recommendations).toString()

    private fun deriveObservations(input: LlmDiagnosticInput): List<String> = buildList {
        add("Session duration was ${input.sessionSummary.durationSec} seconds across ${input.sessionSummary.sampleCount} samples.")
        add("Average coolant temperature was ${String.format("%.1f", input.sessionSummary.avgCoolantTemp)}°C.")
        add("Battery ranged from ${String.format("%.2f", input.sessionSummary.minBatteryVoltage)}V to ${String.format("%.2f", input.sessionSummary.maxBatteryVoltage)}V.")
    }

    private fun normalizeSeverity(value: String, fallback: String): String {
        return when (value.trim().uppercase()) {
            DiagnosticReport.SEVERITY_NORMAL,
            DiagnosticReport.SEVERITY_NOTICE,
            DiagnosticReport.SEVERITY_WARNING,
            DiagnosticReport.SEVERITY_HIGH -> value.trim().uppercase()
            else -> fallback
        }
    }

    private fun normalizeConfidence(value: String): String {
        return when (value.trim().lowercase()) {
            "low", "medium", "high" -> value.trim().lowercase()
            else -> "medium"
        }
    }

    private fun coerceSeverityAgainstRuleEngine(remote: String, rule: String): String {
        val rank = mapOf(
            DiagnosticReport.SEVERITY_NORMAL to 0,
            DiagnosticReport.SEVERITY_NOTICE to 1,
            DiagnosticReport.SEVERITY_WARNING to 2,
            DiagnosticReport.SEVERITY_HIGH to 3
        )
        return if ((rank[remote] ?: 0) > (rank[rule] ?: 0) + 1) rule else remote
    }

    private fun parseStringArray(json: JSONObject, keys: List<String>): List<String> {
        for (key in keys) {
            val array = json.optJSONArray(key) ?: continue
            val values = buildList {
                for (i in 0 until array.length()) {
                    val value = array.optString(i)
                    if (value.isNotBlank()) add(value.trim())
                }
            }
            if (values.isNotEmpty()) return values
        }
        return emptyList()
    }

    private fun containsHardClaim(text: String): Boolean {
        val normalized = text.lowercase()
        return listOf("definitely", "certainly", "must replace", "guaranteed", "confirmed fault").any { normalized.contains(it) }
    }

    private fun softenDangerousClaim(text: String): String {
        return text
            .replace("definitely", "likely", ignoreCase = true)
            .replace("certainly", "possibly", ignoreCase = true)
            .replace("must replace", "should inspect", ignoreCase = true)
            .replace("confirmed fault", "suspected issue", ignoreCase = true)
            .trim()
    }
}
