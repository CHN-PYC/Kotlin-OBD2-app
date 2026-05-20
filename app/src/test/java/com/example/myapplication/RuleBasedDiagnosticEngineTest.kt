package com.example.myapplication

import com.example.myapplication.data.local.DiagnosticReport
import com.example.myapplication.data.local.DriveSession
import com.example.myapplication.data.local.SessionStats
import com.example.myapplication.data.local.VehicleData
import com.example.myapplication.data.repository.RuleBasedDiagnosticEngine
import org.json.JSONArray
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class RuleBasedDiagnosticEngineTest {

    @Test
    fun analyze_detectsOverheatAndLeanIndicators() {
        val session = DriveSession(
            id = 1,
            startedAt = 1,
            endedAt = 2,
            sourceType = DriveSession.SOURCE_REAL,
            durationSec = 600,
            avgSpeed = 42.0,
            maxRpm = 4200,
            avgCoolantTemp = 96.0,
            maxCoolantTemp = 108,
            avgBatteryVoltage = 13.9,
            minBatteryVoltage = 12.9,
            maxBatteryVoltage = 14.2,
            avgEngineLoad = 55.0,
            maxEngineLoad = 92.0,
            avgStft1 = 6.0,
            avgLtft1 = 12.5,
            avgLambda = 1.06
        )
        val stats = SessionStats(20, 42.0, 88, 2500.0, 4200, 96.0, 108, 13.9, 12.9, 14.2, 55.0, 92.0, 6.0, 12.5, 1.06)
        val samples = listOf(
            VehicleData(timestamp = 1, rpm = 1800, coolantTemp = 100, intakeTemp = 30, throttlePos = 20, batteryVoltage = 13.6, shortTermFuelTrimBank1 = 25.0),
            VehicleData(timestamp = 2, rpm = 3200, coolantTemp = 108, intakeTemp = 34, throttlePos = 40, batteryVoltage = 12.9, shortTermFuelTrimBank1 = 10.0)
        )

        val report = RuleBasedDiagnosticEngine.analyze(session, stats, samples)
        val findings = JSONArray(report.findingsJson)

        assertEquals(DiagnosticReport.SEVERITY_WARNING, report.severity)
        assertTrue(report.summary.contains("findings") || report.summary.contains("Coolant"))
        assertTrue(findings.toString().contains("COOLANT_OVERHEAT"))
        assertTrue(findings.toString().contains("LTFT_POSITIVE_HIGH"))
        assertTrue(findings.toString().contains("STFT_SPIKE"))
    }

    @Test
    fun analyze_returnsNormalWhenNoFlags() {
        val session = DriveSession(
            id = 2,
            startedAt = 1,
            endedAt = 2,
            sourceType = DriveSession.SOURCE_REAL,
            durationSec = 300,
            avgSpeed = 38.0,
            maxRpm = 2600,
            avgCoolantTemp = 88.0,
            maxCoolantTemp = 92,
            avgBatteryVoltage = 14.1,
            minBatteryVoltage = 13.8,
            maxBatteryVoltage = 14.4,
            avgEngineLoad = 35.0,
            maxEngineLoad = 60.0,
            avgStft1 = 1.2,
            avgLtft1 = 0.5,
            avgLambda = 1.0
        )
        val stats = SessionStats(10, 38.0, 60, 1800.0, 2600, 88.0, 92, 14.1, 13.8, 14.4, 35.0, 60.0, 1.2, 0.5, 1.0)
        val samples = listOf(
            VehicleData(timestamp = 1, rpm = 1500, coolantTemp = 87, intakeTemp = 28, throttlePos = 12, batteryVoltage = 14.0, shortTermFuelTrimBank1 = 2.0)
        )

        val report = RuleBasedDiagnosticEngine.analyze(session, stats, samples)

        assertEquals(DiagnosticReport.SEVERITY_NORMAL, report.severity)
        assertTrue(report.summary.contains("No obvious rule-based issues"))
        assertEquals(0, JSONArray(report.findingsJson).length())
    }
}
