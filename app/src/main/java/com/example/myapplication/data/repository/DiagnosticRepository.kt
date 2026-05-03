package com.example.myapplication.data.repository

import com.example.myapplication.data.local.DiagnosticReport
import com.example.myapplication.data.local.DiagnosticReportDao
import com.example.myapplication.data.local.DriveSessionDao
import com.example.myapplication.data.local.VehicleDataDao
import kotlinx.coroutines.flow.Flow

class DiagnosticRepository(
    private val reportDao: DiagnosticReportDao,
    private val sessionDao: DriveSessionDao,
    private val vehicleDataDao: VehicleDataDao
) {
    private val llmInputBuilder = LlmDiagnosticInputBuilder(
        sessionDao = sessionDao,
        vehicleDataDao = vehicleDataDao,
        reportDao = reportDao
    )
    private val llmExecutor = LlmDiagnosisExecutor()
    fun getReportsBySession(sessionId: Long): Flow<List<DiagnosticReport>> =
        reportDao.getBySession(sessionId)

    suspend fun saveReport(report: DiagnosticReport): Long = reportDao.insert(report)

    suspend fun getLatestReport(sessionId: Long): DiagnosticReport? =
        reportDao.getLatestBySession(sessionId)

    suspend fun runRuleBasedDiagnosis(sessionId: Long): DiagnosticReport {
        val session = sessionDao.getById(sessionId)
            ?: throw IllegalArgumentException("Session not found: $sessionId")
        val stats = vehicleDataDao.getSessionStats(sessionId)
        val samples = vehicleDataDao.getBySessionOnce(sessionId)
        val report = RuleBasedDiagnosticEngine.analyze(session, stats, samples)
        reportDao.insert(report)
        return report
    }

    suspend fun buildLlmInput(sessionId: Long): LlmDiagnosticInput =
        llmInputBuilder.build(sessionId)

    suspend fun buildLlmInputJson(sessionId: Long): String =
        llmInputBuilder.toJson(buildLlmInput(sessionId))

    suspend fun buildLlmPromptText(sessionId: Long): String =
        llmInputBuilder.toPromptText(buildLlmInput(sessionId))

    suspend fun runLlmDiagnosis(sessionId: Long): DiagnosticReport {
        val input = buildLlmInput(sessionId)
        val inputJson = llmInputBuilder.toJson(input)
        val result = llmExecutor.run(input)
        val report = llmExecutor.toDiagnosticReport(
            sessionId = sessionId,
            inputJson = inputJson,
            result = result
        )
        reportDao.insert(report)
        return report
    }
}
