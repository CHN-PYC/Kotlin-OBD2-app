package com.example.myapplication

import com.example.myapplication.data.repository.LlmDiagnosticInput
import com.example.myapplication.data.repository.PromptHintsPayload
import com.example.myapplication.data.repository.RuleSummaryPayload
import com.example.myapplication.data.repository.SampleHighlightsPayload
import com.example.myapplication.data.repository.SessionSummaryPayload
import com.example.myapplication.data.repository.VehicleQaKnowledgeCatalog
import org.junit.Assert.assertTrue
import org.junit.Test

class VehicleQaKnowledgeCatalogTest {

    @Test
    fun `matches fuel trim sources for fuel trim question`() {
        val input = sampleInput(summary = "Fuel trim is elevated")
        val matched = VehicleQaKnowledgeCatalog.matchSources(
            question = "Why is my STFT and LTFT so high?",
            input = input,
            maxSources = 3
        )

        assertTrue(matched.isNotEmpty())
        assertTrue(matched.any { it.id.contains("fuel_trim") || it.id.contains("obd2") })
    }

    private fun sampleInput(summary: String): LlmDiagnosticInput {
        return LlmDiagnosticInput(
            sessionId = 1,
            sourceType = "demo",
            createdAt = 0,
            sessionSummary = SessionSummaryPayload(
                durationSec = 100,
                sampleCount = 3,
                avgSpeed = 30.0,
                maxSpeed = 50,
                avgRpm = 1800.0,
                maxRpm = 2500,
                avgCoolantTemp = 92.0,
                maxCoolantTemp = 104,
                avgBatteryVoltage = 13.8,
                minBatteryVoltage = 13.2,
                maxBatteryVoltage = 14.1,
                avgEngineLoad = 32.0,
                maxEngineLoad = 68.0,
                avgStft1 = 12.0,
                avgLtft1 = 8.0,
                avgLambda = 1.01
            ),
            ruleSummary = RuleSummaryPayload(
                severity = "NOTICE",
                summary = summary,
                findings = emptyList(),
                recommendations = emptyList()
            ),
            sampleHighlights = SampleHighlightsPayload(null, null, null, null, null),
            promptHints = PromptHintsPayload(
                isDemoData = true,
                shouldAvoidHardFaultClaims = true,
                instruction = "be careful"
            )
        )
    }
}
