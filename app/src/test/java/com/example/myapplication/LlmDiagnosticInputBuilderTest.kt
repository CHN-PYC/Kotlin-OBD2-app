package com.example.myapplication

import com.example.myapplication.data.local.DiagnosticReport
import com.example.myapplication.data.local.DiagnosticReportDao
import com.example.myapplication.data.local.DriveSessionDao
import com.example.myapplication.data.local.VehicleDataDao
import com.example.myapplication.data.repository.LlmDiagnosticInput
import com.example.myapplication.data.repository.LlmDiagnosticInputBuilder
import com.example.myapplication.data.repository.PromptHintsPayload
import com.example.myapplication.data.repository.RuleFindingPayload
import com.example.myapplication.data.repository.RuleSummaryPayload
import com.example.myapplication.data.repository.SampleHighlightsPayload
import com.example.myapplication.data.repository.SamplePointPayload
import com.example.myapplication.data.repository.SessionSummaryPayload
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.emptyFlow
import org.junit.Assert.assertTrue
import org.junit.Test

class LlmDiagnosticInputBuilderTest {

    @Test
    fun toJson_andPrompt_includeExpectedFields() {
        val builder = LlmDiagnosticInputBuilder(FakeDriveSessionDao(), FakeVehicleDataDao(), FakeDiagnosticReportDao())
        val input = LlmDiagnosticInput(
            sessionId = 7,
            sourceType = "DEMO",
            createdAt = 123L,
            sessionSummary = SessionSummaryPayload(600, 20, 45.0, 90, 2200.0, 4200, 91.0, 104, 14.1, 13.6, 14.4, 48.0, 88.0, 2.0, 8.5, 1.02),
            ruleSummary = RuleSummaryPayload(
                severity = "NOTICE",
                summary = "Mild lean tendency",
                findings = listOf(RuleFindingPayload("LAMBDA_LEAN", "NOTICE", "Lambda leaned above target", "Average lambda was elevated")),
                recommendations = listOf("Inspect intake leaks")
            ),
            sampleHighlights = SampleHighlightsPayload(
                hottestSample = SamplePointPayload(1, 3000, 70, 104, 13.8, 80.0, 12.0, 8.0, 1.03, 55.0, 14.0, 35),
                lowestVoltageSample = null,
                highestLoadSample = null,
                highestStftSample = null,
                representativeCruiseSample = null
            ),
            promptHints = PromptHintsPayload(true, true, "This is simulated demo data")
        )

        val json = builder.toJson(input)
        val prompt = builder.toPromptText(input)

        assertTrue(json.contains("\"sessionId\": 7"))
        assertTrue(json.contains("\"sourceType\": \"DEMO\""))
        assertTrue(json.contains("likely lean") || json.contains("Mild lean tendency"))
        assertTrue(prompt.contains("Session ID: 7"))
        assertTrue(prompt.contains("Source Type: DEMO"))
        assertTrue(prompt.contains("Inspect intake leaks"))
        assertTrue(prompt.contains("simulated demo data"))
    }

    private class FakeDriveSessionDao : DriveSessionDao {
        override suspend fun insert(session: com.example.myapplication.data.local.DriveSession): Long = 0
        override suspend fun update(session: com.example.myapplication.data.local.DriveSession) = Unit
        override suspend fun getById(sessionId: Long) = null
        override fun getAllSessions(): Flow<List<com.example.myapplication.data.local.DriveSession>> = emptyFlow()
        override fun getSessionsBySource(sourceType: String): Flow<List<com.example.myapplication.data.local.DriveSession>> = emptyFlow()
        override suspend fun getLatestSession() = null
        override suspend fun closeSession(sessionId: Long, endedAt: Long, status: String) = Unit
        override suspend fun updateSummary(sessionId: Long, sampleCount: Int, durationSec: Long, avgSpeed: Double, maxSpeed: Int, avgRpm: Double, maxRpm: Int, avgCoolantTemp: Double, maxCoolantTemp: Int, avgBatteryVoltage: Double, minBatteryVoltage: Double, maxBatteryVoltage: Double, avgEngineLoad: Double, maxEngineLoad: Double, avgStft1: Double, avgLtft1: Double, avgLambda: Double) = Unit
        override suspend fun deleteById(sessionId: Long) = Unit
    }

    private class FakeVehicleDataDao : VehicleDataDao {
        override suspend fun insert(vehicleData: com.example.myapplication.data.local.VehicleData) = Unit
        override suspend fun insertAll(items: List<com.example.myapplication.data.local.VehicleData>) = Unit
        override fun getAllHistory(): Flow<List<com.example.myapplication.data.local.VehicleData>> = emptyFlow()
        override fun getBySession(sessionId: Long): Flow<List<com.example.myapplication.data.local.VehicleData>> = emptyFlow()
        override suspend fun getBySessionOnce(sessionId: Long) = emptyList<com.example.myapplication.data.local.VehicleData>()
        override suspend fun deleteBySession(sessionId: Long) = Unit
        override suspend fun deleteOldRecords(cutoffTime: Long) = Unit
        override suspend fun deleteAll() = Unit
        override fun getRecordsInTimeRange(startTime: Long, endTime: Long): Flow<List<com.example.myapplication.data.local.VehicleData>> = emptyFlow()
        override suspend fun getSessionStats(sessionId: Long) = throw UnsupportedOperationException()
    }

    private class FakeDiagnosticReportDao : DiagnosticReportDao {
        override suspend fun insert(report: DiagnosticReport): Long = 0
        override suspend fun update(report: DiagnosticReport) = Unit
        override suspend fun getById(reportId: Long): DiagnosticReport? = null
        override fun getBySession(sessionId: Long): Flow<List<DiagnosticReport>> = emptyFlow()
        override suspend fun getLatestBySession(sessionId: Long): DiagnosticReport? = null
        override suspend fun deleteBySession(sessionId: Long) = Unit
    }
}
