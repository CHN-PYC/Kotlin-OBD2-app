package com.example.myapplication.data.repository

data class LlmDiagnosticInput(
    val sessionId: Long,
    val sourceType: String,
    val createdAt: Long,
    val sessionSummary: SessionSummaryPayload,
    val ruleSummary: RuleSummaryPayload,
    val sampleHighlights: SampleHighlightsPayload,
    val promptHints: PromptHintsPayload
)

data class SessionSummaryPayload(
    val durationSec: Long,
    val sampleCount: Int,
    val avgSpeed: Double,
    val maxSpeed: Int,
    val avgRpm: Double,
    val maxRpm: Int,
    val avgCoolantTemp: Double,
    val maxCoolantTemp: Int,
    val avgBatteryVoltage: Double,
    val minBatteryVoltage: Double,
    val maxBatteryVoltage: Double,
    val avgEngineLoad: Double,
    val maxEngineLoad: Double,
    val avgStft1: Double,
    val avgLtft1: Double,
    val avgLambda: Double
)

data class RuleSummaryPayload(
    val severity: String,
    val summary: String,
    val findings: List<RuleFindingPayload>,
    val recommendations: List<String>
)

data class RuleFindingPayload(
    val code: String,
    val severity: String,
    val title: String,
    val detail: String
)

data class SampleHighlightsPayload(
    val hottestSample: SamplePointPayload?,
    val lowestVoltageSample: SamplePointPayload?,
    val highestLoadSample: SamplePointPayload?,
    val highestStftSample: SamplePointPayload?,
    val representativeCruiseSample: SamplePointPayload?
)

data class SamplePointPayload(
    val timestamp: Long,
    val rpm: Int,
    val speed: Int,
    val coolantTemp: Int,
    val batteryVoltage: Double,
    val engineLoad: Double,
    val shortTermFuelTrimBank1: Double,
    val longTermFuelTrimBank1: Double,
    val equivalenceRatio: Double,
    val intakeManifoldPressure: Double,
    val mafRate: Double,
    val throttlePos: Int
)

data class PromptHintsPayload(
    val isDemoData: Boolean,
    val shouldAvoidHardFaultClaims: Boolean,
    val instruction: String
)
