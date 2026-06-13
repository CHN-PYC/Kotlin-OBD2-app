package com.example.myapplication.data.repository

import android.content.Context
import com.example.myapplication.BuildConfig
import com.example.myapplication.data.local.DiagnosticReport
import com.example.myapplication.data.local.DiagnosticReportDao
import com.example.myapplication.data.local.DriveSessionDao
import com.example.myapplication.data.local.VehicleDataDao
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext

class DiagnosticRepository(
    private val appContext: Context,
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
    private val remoteConfig = if (BuildConfig.REMOTE_LLM_ENABLED) {
        LlmProviderConfig(
            providerName = BuildConfig.REMOTE_LLM_PROVIDER,
            baseUrl = BuildConfig.REMOTE_LLM_BASE_URL,
            apiKey = BuildConfig.REMOTE_LLM_API_KEY,
            model = BuildConfig.REMOTE_LLM_MODEL,
            timeoutSeconds = BuildConfig.REMOTE_LLM_TIMEOUT_SECONDS,
            enabled = true
        )
    } else {
        LlmProviderConfig.disabledDefault()
    }
    private val vehicleQaBackendConfig = if (BuildConfig.VEHICLE_QA_BACKEND_ENABLED) {
        VehicleQaBackendConfig(
            baseUrl = BuildConfig.VEHICLE_QA_BACKEND_BASE_URL,
            apiKey = BuildConfig.VEHICLE_QA_BACKEND_API_KEY,
            timeoutSeconds = BuildConfig.VEHICLE_QA_BACKEND_TIMEOUT_SECONDS,
            enabled = true
        )
    } else {
        VehicleQaBackendConfig.disabledDefault()
    }
    fun getReportsBySession(sessionId: Long): Flow<List<DiagnosticReport>> =
        reportDao.getBySession(sessionId)

    suspend fun saveReport(report: DiagnosticReport): Long = reportDao.insert(report)

    suspend fun getLatestReport(sessionId: Long): DiagnosticReport? =
        reportDao.getLatestBySession(sessionId)

    suspend fun getReportById(reportId: Long): DiagnosticReport? =
        reportDao.getById(reportId)

    suspend fun runRuleBasedDiagnosis(sessionId: Long): DiagnosticReport {
        val session = sessionDao.getById(sessionId)
            ?: throw IllegalArgumentException("Session not found: $sessionId")
        val stats = vehicleDataDao.getSessionStats(sessionId)
        val samples = vehicleDataDao.getBySessionOnce(sessionId)
        val report = RuleBasedDiagnosticEngine.analyze(session, stats, samples)
        val reportId = reportDao.insert(report)
        return report.copy(id = reportId)
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
        val reportId = reportDao.insert(report)
        return report.copy(id = reportId)
    }

    suspend fun runRemoteLlmDiagnosis(sessionId: Long): DiagnosticReport = withContext(Dispatchers.IO) {
        require(remoteConfig.enabled) { "Remote LLM is not configured yet. Enable REMOTE_LLM_ENABLED and provide BuildConfig values." }
        require(remoteConfig.baseUrl.isNotBlank()) { "Remote LLM base URL is missing" }
        require(remoteConfig.apiKey.isNotBlank()) { "Remote LLM API key is missing" }
        require(remoteConfig.model.isNotBlank()) { "Remote LLM model is missing" }

        val input = buildLlmInput(sessionId)
        val inputJson = llmInputBuilder.toJson(input)
        val prompt = llmInputBuilder.toPromptText(input)
        val apiClient = RemoteLlmApiClient(remoteConfig)
        val executor = RemoteLlmDiagnosisExecutor(apiClient, remoteConfig)
        val report = executor.run(
            sessionId = sessionId,
            input = input,
            prompt = prompt,
            inputJson = inputJson
        )
        val reportId = reportDao.insert(report)
        report.copy(id = reportId)
    }

    suspend fun runVehicleQa(sessionId: Long, question: String): DiagnosticReport = withContext(Dispatchers.IO) {
        require(vehicleQaBackendConfig.enabled) { "Vehicle QA backend is not configured yet. Enable VEHICLE_QA_BACKEND_ENABLED and provide backend BuildConfig values." }
        require(question.isNotBlank()) { "Question must not be blank" }

        val input = buildLlmInput(sessionId)
        val backendClient = VehicleQaBackendApiClient(vehicleQaBackendConfig)
        val result = backendClient.askQuestion(
            sessionId = sessionId,
            question = question,
            input = input
        )
        val report = DiagnosticReport(
            sessionId = sessionId,
            createdAt = System.currentTimeMillis(),
            reportType = DiagnosticReport.TYPE_RAG_QA,
            modelName = "vehicle-rag-backend",
            modelVersion = vehicleQaBackendConfig.baseUrl,
            promptVersion = "vehicle-rag-backend-v1",
            severity = result.severity,
            summary = result.answer,
            findingsJson = result.findingsJson,
            recommendationsJson = result.recommendationsJson,
            rawInputSnapshotJson = result.requestJson,
            rawOutputText = result.rawText
        )
        val reportId = reportDao.insert(report)
        report.copy(id = reportId)
    }
}
