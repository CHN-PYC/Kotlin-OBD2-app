package com.example.myapplication.data.repository

import com.example.myapplication.data.local.DiagnosticReport
import com.example.myapplication.data.local.DiagnosticReportDao
import com.example.myapplication.data.local.DriveSessionDao
import com.example.myapplication.data.local.SessionStats
import com.example.myapplication.data.local.VehicleData
import com.example.myapplication.data.local.VehicleDataDao
import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.abs

class LlmDiagnosticInputBuilder(
    private val sessionDao: DriveSessionDao,
    private val vehicleDataDao: VehicleDataDao,
    private val reportDao: DiagnosticReportDao
) {

    suspend fun build(sessionId: Long): LlmDiagnosticInput {
        val session = sessionDao.getById(sessionId)
            ?: throw IllegalArgumentException("Session not found: $sessionId")
        val stats = vehicleDataDao.getSessionStats(sessionId)
        val samples = vehicleDataDao.getBySessionOnce(sessionId)

        var ruleReport = reportDao.getLatestBySession(sessionId)
        if (ruleReport == null || ruleReport.reportType != DiagnosticReport.TYPE_RULE_BASED) {
            ruleReport = RuleBasedDiagnosticEngine.analyze(session, stats, samples)
        }

        return LlmDiagnosticInput(
            sessionId = session.id,
            sourceType = session.sourceType,
            createdAt = System.currentTimeMillis(),
            sessionSummary = buildSessionSummary(session, stats),
            ruleSummary = buildRuleSummary(ruleReport),
            sampleHighlights = buildSampleHighlights(samples),
            promptHints = buildPromptHints(session.sourceType)
        )
    }

    fun toJson(input: LlmDiagnosticInput): String {
        return JSONObject().apply {
            put("sessionId", input.sessionId)
            put("sourceType", input.sourceType)
            put("createdAt", input.createdAt)
            put("sessionSummary", JSONObject().apply {
                put("durationSec", input.sessionSummary.durationSec)
                put("sampleCount", input.sessionSummary.sampleCount)
                put("avgSpeed", input.sessionSummary.avgSpeed)
                put("maxSpeed", input.sessionSummary.maxSpeed)
                put("avgRpm", input.sessionSummary.avgRpm)
                put("maxRpm", input.sessionSummary.maxRpm)
                put("avgCoolantTemp", input.sessionSummary.avgCoolantTemp)
                put("maxCoolantTemp", input.sessionSummary.maxCoolantTemp)
                put("avgBatteryVoltage", input.sessionSummary.avgBatteryVoltage)
                put("minBatteryVoltage", input.sessionSummary.minBatteryVoltage)
                put("maxBatteryVoltage", input.sessionSummary.maxBatteryVoltage)
                put("avgEngineLoad", input.sessionSummary.avgEngineLoad)
                put("maxEngineLoad", input.sessionSummary.maxEngineLoad)
                put("avgStft1", input.sessionSummary.avgStft1)
                put("avgLtft1", input.sessionSummary.avgLtft1)
                put("avgLambda", input.sessionSummary.avgLambda)
            })
            put("ruleSummary", JSONObject().apply {
                put("severity", input.ruleSummary.severity)
                put("summary", input.ruleSummary.summary)
                put("findings", JSONArray().apply {
                    input.ruleSummary.findings.forEach { finding ->
                        put(JSONObject().apply {
                            put("code", finding.code)
                            put("severity", finding.severity)
                            put("title", finding.title)
                            put("detail", finding.detail)
                        })
                    }
                })
                put("recommendations", JSONArray(input.ruleSummary.recommendations))
            })
            put("sampleHighlights", JSONObject().apply {
                put("hottestSample", input.sampleHighlights.hottestSample?.toJson())
                put("lowestVoltageSample", input.sampleHighlights.lowestVoltageSample?.toJson())
                put("highestLoadSample", input.sampleHighlights.highestLoadSample?.toJson())
                put("highestStftSample", input.sampleHighlights.highestStftSample?.toJson())
                put("representativeCruiseSample", input.sampleHighlights.representativeCruiseSample?.toJson())
            })
            put("promptHints", JSONObject().apply {
                put("isDemoData", input.promptHints.isDemoData)
                put("shouldAvoidHardFaultClaims", input.promptHints.shouldAvoidHardFaultClaims)
                put("instruction", input.promptHints.instruction)
            })
        }.toString(2)
    }

    fun toPromptText(input: LlmDiagnosticInput): String {
        return buildString {
            appendLine("You are an automotive diagnostic assistant.")
            appendLine("Use the structured session data below to identify likely issues, uncertainty, and next checks.")
            appendLine("Do not overclaim. Distinguish observations, hypotheses, and suggested inspections.")
            appendLine()
            appendLine("Session ID: ${input.sessionId}")
            appendLine("Source Type: ${input.sourceType}")
            appendLine("Duration: ${input.sessionSummary.durationSec} sec")
            appendLine("Samples: ${input.sessionSummary.sampleCount}")
            appendLine("Avg Speed: ${String.format("%.1f", input.sessionSummary.avgSpeed)} km/h")
            appendLine("Max RPM: ${input.sessionSummary.maxRpm}")
            appendLine("Avg Coolant: ${String.format("%.1f", input.sessionSummary.avgCoolantTemp)} °C")
            appendLine("Max Coolant: ${input.sessionSummary.maxCoolantTemp} °C")
            appendLine("Battery Range: ${String.format("%.2f", input.sessionSummary.minBatteryVoltage)}V - ${String.format("%.2f", input.sessionSummary.maxBatteryVoltage)}V")
            appendLine("Avg LTFT1: ${String.format("%.1f", input.sessionSummary.avgLtft1)} %")
            appendLine("Avg STFT1: ${String.format("%.1f", input.sessionSummary.avgStft1)} %")
            appendLine("Avg Lambda: ${String.format("%.3f", input.sessionSummary.avgLambda)}")
            appendLine()
            appendLine("Rule Summary: ${input.ruleSummary.summary}")
            appendLine("Rule Severity: ${input.ruleSummary.severity}")
            appendLine("Findings:")
            input.ruleSummary.findings.forEach { finding ->
                appendLine("- [${finding.severity}] ${finding.title}: ${finding.detail}")
            }
            appendLine("Recommendations:")
            input.ruleSummary.recommendations.forEach { recommendation ->
                appendLine("- $recommendation")
            }
            appendLine()
            appendLine("Prompt Hint: ${input.promptHints.instruction}")
            appendLine()
            appendLine("Key Samples:")
            appendLine("- Hottest: ${input.sampleHighlights.hottestSample?.summaryLine() ?: "n/a"}")
            appendLine("- Lowest Voltage: ${input.sampleHighlights.lowestVoltageSample?.summaryLine() ?: "n/a"}")
            appendLine("- Highest Load: ${input.sampleHighlights.highestLoadSample?.summaryLine() ?: "n/a"}")
            appendLine("- Highest STFT: ${input.sampleHighlights.highestStftSample?.summaryLine() ?: "n/a"}")
            appendLine("- Cruise Sample: ${input.sampleHighlights.representativeCruiseSample?.summaryLine() ?: "n/a"}")
        }
    }

    private fun buildSessionSummary(session: com.example.myapplication.data.local.DriveSession, stats: SessionStats): SessionSummaryPayload {
        return SessionSummaryPayload(
            durationSec = session.durationSec,
            sampleCount = stats.sampleCount,
            avgSpeed = session.avgSpeed,
            maxSpeed = session.maxSpeed,
            avgRpm = session.avgRpm,
            maxRpm = session.maxRpm,
            avgCoolantTemp = session.avgCoolantTemp,
            maxCoolantTemp = session.maxCoolantTemp,
            avgBatteryVoltage = session.avgBatteryVoltage,
            minBatteryVoltage = session.minBatteryVoltage,
            maxBatteryVoltage = session.maxBatteryVoltage,
            avgEngineLoad = session.avgEngineLoad,
            maxEngineLoad = session.maxEngineLoad,
            avgStft1 = session.avgStft1,
            avgLtft1 = session.avgLtft1,
            avgLambda = session.avgLambda
        )
    }

    private fun buildRuleSummary(report: DiagnosticReport): RuleSummaryPayload {
        val findings = JSONArray(report.findingsJson)
        val recommendations = JSONArray(report.recommendationsJson)
        return RuleSummaryPayload(
            severity = report.severity,
            summary = report.summary,
            findings = List(findings.length()) { index ->
                val finding = findings.getJSONObject(index)
                RuleFindingPayload(
                    code = finding.optString("code"),
                    severity = finding.optString("severity"),
                    title = finding.optString("title"),
                    detail = finding.optString("detail")
                )
            },
            recommendations = List(recommendations.length()) { index ->
                recommendations.getString(index)
            }
        )
    }

    private fun buildSampleHighlights(samples: List<VehicleData>): SampleHighlightsPayload {
        return SampleHighlightsPayload(
            hottestSample = samples.maxByOrNull { it.coolantTemp }?.toPayload(),
            lowestVoltageSample = samples.minByOrNull { it.batteryVoltage }?.toPayload(),
            highestLoadSample = samples.maxByOrNull { it.engineLoad }?.toPayload(),
            highestStftSample = samples.maxByOrNull { abs(it.shortTermFuelTrimBank1) }?.toPayload(),
            representativeCruiseSample = samples
                .filter { it.speed >= 40 }
                .minByOrNull { abs(it.engineLoad - 35.0) }
                ?.toPayload()
        )
    }

    private fun buildPromptHints(sourceType: String): PromptHintsPayload {
        val isDemo = sourceType == com.example.myapplication.data.local.DriveSession.SOURCE_DEMO
        return PromptHintsPayload(
            isDemoData = isDemo,
            shouldAvoidHardFaultClaims = isDemo,
            instruction = if (isDemo) {
                "This is simulated demo data. Do not treat it as real vehicle fault evidence; focus on explaining what the pattern would mean in a real car."
            } else {
                "This is real captured session data. Provide careful, non-overconfident diagnostic guidance and recommended next checks."
            }
        )
    }

    private fun VehicleData.toPayload(): SamplePointPayload {
        return SamplePointPayload(
            timestamp = timestamp,
            rpm = rpm,
            speed = speed,
            coolantTemp = coolantTemp,
            batteryVoltage = batteryVoltage,
            engineLoad = engineLoad,
            shortTermFuelTrimBank1 = shortTermFuelTrimBank1,
            longTermFuelTrimBank1 = longTermFuelTrimBank1,
            equivalenceRatio = equivalenceRatio,
            intakeManifoldPressure = intakeManifoldPressure,
            mafRate = mafRate,
            throttlePos = throttlePos
        )
    }

    private fun SamplePointPayload.toJson(): JSONObject {
        return JSONObject().apply {
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

    private fun SamplePointPayload.summaryLine(): String {
        return "rpm=$rpm, speed=$speed km/h, coolant=$coolantTemp°C, battery=${String.format("%.2f", batteryVoltage)}V, load=${String.format("%.1f", engineLoad)}%, stft=${String.format("%.1f", shortTermFuelTrimBank1)}%, ltft=${String.format("%.1f", longTermFuelTrimBank1)}%, lambda=${String.format("%.3f", equivalenceRatio)}"
    }
}
