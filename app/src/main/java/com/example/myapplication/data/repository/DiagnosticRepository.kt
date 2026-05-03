package com.example.myapplication.data.repository

import com.example.myapplication.data.local.DiagnosticReport
import com.example.myapplication.data.local.DiagnosticReportDao
import kotlinx.coroutines.flow.Flow

class DiagnosticRepository(
    private val reportDao: DiagnosticReportDao
) {
    fun getReportsBySession(sessionId: Long): Flow<List<DiagnosticReport>> =
        reportDao.getBySession(sessionId)

    suspend fun saveReport(report: DiagnosticReport): Long = reportDao.insert(report)

    suspend fun getLatestReport(sessionId: Long): DiagnosticReport? =
        reportDao.getLatestBySession(sessionId)
}
