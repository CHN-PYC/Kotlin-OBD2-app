package com.example.myapplication.data.repository

import com.example.myapplication.data.local.DiagnosticReport
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class VehicleQaBackendApiClient(
    private val config: VehicleQaBackendConfig
) {

    data class VehicleQaBackendResult(
        val rawText: String,
        val requestJson: String,
        val answer: String,
        val severity: String,
        val findingsJson: String,
        val recommendationsJson: String
    )

    private val client: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .connectTimeout(config.timeoutSeconds, TimeUnit.SECONDS)
            .readTimeout(config.timeoutSeconds, TimeUnit.SECONDS)
            .writeTimeout(config.timeoutSeconds, TimeUnit.SECONDS)
            .build()
    }

    fun askQuestion(sessionId: Long, question: String, input: LlmDiagnosticInput): VehicleQaBackendResult {
        require(config.enabled) { "Vehicle QA backend is disabled" }
        require(config.baseUrl.isNotBlank()) { "Vehicle QA backend baseUrl is missing" }

        val vehicleContext = JSONObject().apply {
            put("sessionSummary", input.sessionSummary.toJson())
            put("sampleHighlights", input.sampleHighlights.toJson())
            put("promptHints", input.promptHints.toJson())
            put("sourceType", input.sourceType)
            put("createdAt", input.createdAt)
        }
        val ruleSummary = input.ruleSummary.toJson()
        val payload = JSONObject().apply {
            put("session_id", sessionId.toString())
            put("question", question)
            put("vehicle_context", vehicleContext)
            put("rule_summary", ruleSummary)
            put("top_k", 5)
        }

        val requestBuilder = Request.Builder()
            .url(config.baseUrl.trimEnd('/') + "/qa/vehicle")
            .addHeader("Content-Type", "application/json")

        if (config.apiKey.isNotBlank()) {
            requestBuilder.addHeader("Authorization", "Bearer ${config.apiKey}")
        }

        val request = requestBuilder
            .post(payload.toString().toRequestBody("application/json".toMediaType()))
            .build()

        client.newCall(request).execute().use { response ->
            val bodyText = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                throw IllegalStateException("Vehicle QA backend request failed: HTTP ${response.code} ${response.message}; body=${bodyText.take(800)}")
            }
            if (bodyText.isBlank()) {
                throw IllegalStateException("Vehicle QA backend returned an empty body")
            }
            val json = JSONObject(bodyText)
            val answer = json.optString("answer").ifBlank { bodyText.take(800) }
            val severity = json.optString("severity").ifBlank { DiagnosticReport.SEVERITY_NOTICE }
            val findings = json.optJSONArray("findings") ?: JSONArray()
            val recommendations = json.optJSONArray("recommendations") ?: JSONArray()
            val sources = json.optJSONArray("sources") ?: JSONArray()

            return VehicleQaBackendResult(
                rawText = bodyText,
                requestJson = payload.toString(),
                answer = answer,
                severity = severity,
                findingsJson = findingsToJson(findings, sources, severity),
                recommendationsJson = recommendationsToJson(recommendations)
            )
        }
    }

    private fun findingsToJson(findings: JSONArray, sources: JSONArray, severity: String): String {
        return JSONArray().apply {
            for (i in 0 until findings.length()) {
                put(JSONObject().apply {
                    put("title", "Finding")
                    put("detail", findings.optString(i))
                    put("severity", severity)
                })
            }
            if (sources.length() > 0) {
                val lines = (0 until sources.length()).joinToString("\n") { index ->
                    val item = sources.optJSONObject(index)
                    if (item == null) {
                        "• ${sources.opt(index)}"
                    } else {
                        val title = item.optString("title").ifBlank { item.optString("doc_id") }
                        val url = item.optString("source_url")
                        val score = item.optDouble("score", Double.NaN)
                        buildString {
                            append("• ")
                            append(title)
                            if (url.isNotBlank()) append(" ($url)")
                            if (!score.isNaN()) append(" score=${String.format("%.3f", score)}")
                        }
                    }
                }
                put(JSONObject().apply {
                    put("title", "Retrieved sources")
                    put("detail", lines)
                    put("severity", DiagnosticReport.SEVERITY_NOTICE)
                })
            }
        }.toString()
    }

    private fun recommendationsToJson(recommendations: JSONArray): String {
        return JSONArray().apply {
            for (i in 0 until recommendations.length()) {
                put(recommendations.optString(i))
            }
        }.toString()
    }

    private fun SessionSummaryPayload.toJson(): JSONObject = JSONObject().apply {
        put("durationSec", durationSec)
        put("sampleCount", sampleCount)
        put("avgSpeed", avgSpeed)
        put("maxSpeed", maxSpeed)
        put("avgRpm", avgRpm)
        put("maxRpm", maxRpm)
        put("avgCoolantTemp", avgCoolantTemp)
        put("maxCoolantTemp", maxCoolantTemp)
        put("avgBatteryVoltage", avgBatteryVoltage)
        put("minBatteryVoltage", minBatteryVoltage)
        put("maxBatteryVoltage", maxBatteryVoltage)
        put("avgEngineLoad", avgEngineLoad)
        put("maxEngineLoad", maxEngineLoad)
        put("avgStft1", avgStft1)
        put("avgLtft1", avgLtft1)
        put("avgLambda", avgLambda)
    }

    private fun RuleSummaryPayload.toJson(): JSONObject = JSONObject().apply {
        put("severity", severity)
        put("summary", summary)
        put("findings", JSONArray().apply {
            findings.forEach { finding ->
                put(JSONObject().apply {
                    put("code", finding.code)
                    put("severity", finding.severity)
                    put("title", finding.title)
                    put("detail", finding.detail)
                })
            }
        })
        put("recommendations", JSONArray(recommendations))
    }

    private fun SampleHighlightsPayload.toJson(): JSONObject = JSONObject().apply {
        put("hottestSample", hottestSample?.toJson())
        put("lowestVoltageSample", lowestVoltageSample?.toJson())
        put("highestLoadSample", highestLoadSample?.toJson())
        put("highestStftSample", highestStftSample?.toJson())
        put("representativeCruiseSample", representativeCruiseSample?.toJson())
    }

    private fun PromptHintsPayload.toJson(): JSONObject = JSONObject().apply {
        put("isDemoData", isDemoData)
        put("shouldAvoidHardFaultClaims", shouldAvoidHardFaultClaims)
        put("instruction", instruction)
    }

    private fun SamplePointPayload.toJson(): JSONObject = JSONObject().apply {
        put("timestamp", timestamp)
        put("rpm", rpm)
        put("speed", speed)
        put("coolantTemp", coolantTemp)
        put("batteryVoltage", batteryVoltage)
        put("engineLoad", engineLoad)
        put("shortTermFuelTrimBank1", shortTermFuelTrimBank1)
        put("longTermFuelTrimBank1", longTermFuelTrimBank1)
        put("equivalenceRatio", equivalenceRatio)
        put("intakeManifoldPressure", intakeManifoldPressure)
        put("mafRate", mafRate)
        put("throttlePos", throttlePos)
    }
}
