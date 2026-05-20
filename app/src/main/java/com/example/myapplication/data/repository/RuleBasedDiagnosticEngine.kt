package com.example.myapplication.data.repository

import com.example.myapplication.data.local.DiagnosticReport
import com.example.myapplication.data.local.DriveSession
import com.example.myapplication.data.local.SessionStats
import com.example.myapplication.data.local.VehicleData
import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.abs

object RuleBasedDiagnosticEngine {

    data class DiagnosticFlag(
        val code: String,
        val severity: String,
        val title: String,
        val detail: String
    )

    fun analyze(
        session: DriveSession,
        stats: SessionStats,
        samples: List<VehicleData>
    ): DiagnosticReport {
        val flags = mutableListOf<DiagnosticFlag>()

        if (session.maxCoolantTemp > 105) {
            flags += DiagnosticFlag(
                code = "COOLANT_OVERHEAT",
                severity = DiagnosticReport.SEVERITY_WARNING,
                title = "Coolant temperature ran high",
                detail = "Peak coolant temperature reached ${session.maxCoolantTemp}°C, which may indicate overheating or heavy thermal load."
            )
        } else if (session.avgCoolantTemp in 1.0..69.9) {
            flags += DiagnosticFlag(
                code = "COOLANT_LOW_OPERATING_TEMP",
                severity = DiagnosticReport.SEVERITY_NOTICE,
                title = "Coolant stayed below normal operating range",
                detail = "Average coolant temperature was ${String.format("%.1f", session.avgCoolantTemp)}°C, suggesting the engine may not have fully warmed up."
            )
        }

        if (session.minBatteryVoltage in 0.1..13.19) {
            flags += DiagnosticFlag(
                code = "BATTERY_LOW_CHARGING",
                severity = DiagnosticReport.SEVERITY_WARNING,
                title = "Charging voltage looks low",
                detail = "Minimum battery voltage dropped to ${String.format("%.2f", session.minBatteryVoltage)}V. Check charging system health and electrical load."
            )
        }

        if (session.maxBatteryVoltage > 14.8) {
            flags += DiagnosticFlag(
                code = "BATTERY_HIGH_CHARGING",
                severity = DiagnosticReport.SEVERITY_NOTICE,
                title = "Charging voltage looks high",
                detail = "Maximum battery voltage reached ${String.format("%.2f", session.maxBatteryVoltage)}V. This can indicate aggressive charging or regulation issues."
            )
        }

        if (session.avgLtft1 > 10.0) {
            flags += DiagnosticFlag(
                code = "LTFT_POSITIVE_HIGH",
                severity = DiagnosticReport.SEVERITY_WARNING,
                title = "Long-term fuel trim is strongly positive",
                detail = "Average LTFT Bank 1 was ${String.format("%.1f", session.avgLtft1)}%, which may point to a lean condition, vacuum leak, or fuel delivery issue."
            )
        } else if (session.avgLtft1 < -10.0) {
            flags += DiagnosticFlag(
                code = "LTFT_NEGATIVE_HIGH",
                severity = DiagnosticReport.SEVERITY_WARNING,
                title = "Long-term fuel trim is strongly negative",
                detail = "Average LTFT Bank 1 was ${String.format("%.1f", session.avgLtft1)}%, which may point to a rich condition or sensor bias."
            )
        }

        val stftPeak = samples.maxOfOrNull { abs(it.shortTermFuelTrimBank1) } ?: 0.0
        if (stftPeak > 20.0) {
            flags += DiagnosticFlag(
                code = "STFT_SPIKE",
                severity = DiagnosticReport.SEVERITY_NOTICE,
                title = "Short-term fuel trim spiked",
                detail = "STFT Bank 1 peaked at ${String.format("%.1f", stftPeak)}%, suggesting transient fueling corrections under load changes."
            )
        }

        if (session.maxEngineLoad > 90.0) {
            flags += DiagnosticFlag(
                code = "HIGH_ENGINE_LOAD",
                severity = DiagnosticReport.SEVERITY_NOTICE,
                title = "Engine operated under high load",
                detail = "Maximum engine load reached ${String.format("%.1f", session.maxEngineLoad)}%. Treat some high-temp or trim behavior in that context."
            )
        }

        if (session.avgLambda > 1.05) {
            flags += DiagnosticFlag(
                code = "LAMBDA_LEAN",
                severity = DiagnosticReport.SEVERITY_NOTICE,
                title = "Average lambda leaned above target",
                detail = "Average lambda was ${String.format("%.3f", session.avgLambda)}, which may indicate a mild lean tendency."
            )
        } else if (session.avgLambda in 0.01..0.95) {
            flags += DiagnosticFlag(
                code = "LAMBDA_RICH",
                severity = DiagnosticReport.SEVERITY_NOTICE,
                title = "Average lambda ran rich",
                detail = "Average lambda was ${String.format("%.3f", session.avgLambda)}, which may indicate a mild rich tendency."
            )
        }

        val severity = when {
            flags.any { it.severity == DiagnosticReport.SEVERITY_WARNING } -> DiagnosticReport.SEVERITY_WARNING
            flags.any { it.severity == DiagnosticReport.SEVERITY_NOTICE } -> DiagnosticReport.SEVERITY_NOTICE
            else -> DiagnosticReport.SEVERITY_NORMAL
        }

        val summary = when {
            flags.isEmpty() -> "No obvious rule-based issues detected in this session."
            flags.size == 1 -> flags.first().title
            else -> "${flags.size} rule-based findings detected; review thermal, fueling, and charging indicators."
        }

        val findingsJson = JSONArray().apply {
            flags.forEach { flag ->
                put(JSONObject().apply {
                    put("code", flag.code)
                    put("severity", flag.severity)
                    put("title", flag.title)
                    put("detail", flag.detail)
                })
            }
        }.toString()

        val recommendations = buildRecommendations(flags)
        val recommendationsJson = JSONArray(recommendations).toString()
        val rawInputSnapshotJson = JSONObject().apply {
            put("sessionId", session.id)
            put("sourceType", session.sourceType)
            put("sampleCount", stats.sampleCount)
            put("durationSec", session.durationSec)
            put("avgSpeed", session.avgSpeed)
            put("maxRpm", session.maxRpm)
            put("avgCoolantTemp", session.avgCoolantTemp)
            put("maxCoolantTemp", session.maxCoolantTemp)
            put("avgBatteryVoltage", session.avgBatteryVoltage)
            put("minBatteryVoltage", session.minBatteryVoltage)
            put("maxBatteryVoltage", session.maxBatteryVoltage)
            put("avgEngineLoad", session.avgEngineLoad)
            put("maxEngineLoad", session.maxEngineLoad)
            put("avgStft1", session.avgStft1)
            put("avgLtft1", session.avgLtft1)
            put("avgLambda", session.avgLambda)
        }.toString()

        return DiagnosticReport(
            sessionId = session.id,
            createdAt = System.currentTimeMillis(),
            reportType = DiagnosticReport.TYPE_RULE_BASED,
            modelName = "rule-engine-v1",
            severity = severity,
            summary = summary,
            findingsJson = findingsJson,
            recommendationsJson = recommendationsJson,
            rawInputSnapshotJson = rawInputSnapshotJson,
            rawOutputText = null
        )
    }

    private fun buildRecommendations(flags: List<DiagnosticFlag>): List<String> {
        if (flags.isEmpty()) {
            return listOf("Keep collecting more real-world sessions before drawing stronger conclusions.")
        }

        val recommendations = mutableListOf<String>()
        if (flags.any { it.code == "COOLANT_OVERHEAT" }) {
            recommendations += "Inspect coolant level, fan operation, radiator airflow, and thermostat behavior."
        }
        if (flags.any { it.code == "BATTERY_LOW_CHARGING" || it.code == "BATTERY_HIGH_CHARGING" }) {
            recommendations += "Check alternator output, battery condition, and ground/charging connections."
        }
        if (flags.any { it.code == "LTFT_POSITIVE_HIGH" || it.code == "STFT_SPIKE" || it.code == "LAMBDA_LEAN" }) {
            recommendations += "Inspect intake leaks, MAF cleanliness, fuel pressure stability, and upstream oxygen sensor behavior."
        }
        if (flags.any { it.code == "LTFT_NEGATIVE_HIGH" || it.code == "LAMBDA_RICH" }) {
            recommendations += "Check for rich fueling causes such as injector leakage, biased sensors, or excessive fuel pressure."
        }
        if (flags.any { it.code == "HIGH_ENGINE_LOAD" }) {
            recommendations += "Interpret high-temperature and trim events alongside load and throttle demand before treating them as faults."
        }
        return recommendations.distinct()
    }
}
