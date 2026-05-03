package com.example.myapplication.data.repository

import com.example.myapplication.data.local.DiagnosticReportDao
import com.example.myapplication.data.local.DriveSession
import com.example.myapplication.data.local.DriveSessionDao
import com.example.myapplication.data.local.SessionStats
import com.example.myapplication.data.local.VehicleDataDao
import kotlinx.coroutines.flow.Flow

class SessionRepository(
    private val sessionDao: DriveSessionDao,
    private val vehicleDataDao: VehicleDataDao,
    private val reportDao: DiagnosticReportDao
) {

    suspend fun startSession(
        sourceType: String,
        title: String? = null,
        notes: String? = null,
        vehicleName: String? = null
    ): Long {
        return sessionDao.insert(
            DriveSession(
                startedAt = System.currentTimeMillis(),
                sourceType = sourceType,
                title = title,
                notes = notes,
                vehicleName = vehicleName,
                status = DriveSession.STATUS_ACTIVE
            )
        )
    }

    suspend fun closeSession(sessionId: Long, status: String = DriveSession.STATUS_COMPLETED) {
        val session = sessionDao.getById(sessionId) ?: return
        val endedAt = System.currentTimeMillis()
        sessionDao.closeSession(sessionId, endedAt, status)
        recomputeSummary(sessionId, session.startedAt, endedAt)
    }

    fun getAllSessions(): Flow<List<DriveSession>> = sessionDao.getAllSessions()

    fun getSessionsBySource(sourceType: String): Flow<List<DriveSession>> =
        sessionDao.getSessionsBySource(sourceType)

    suspend fun recomputeSummary(
        sessionId: Long,
        startedAt: Long? = null,
        endedAt: Long? = null
    ) {
        val baseSession = sessionDao.getById(sessionId) ?: return
        val stats: SessionStats = vehicleDataDao.getSessionStats(sessionId)
        val effectiveStart = startedAt ?: baseSession.startedAt
        val effectiveEnd = endedAt ?: baseSession.endedAt ?: System.currentTimeMillis()
        val durationSec = ((effectiveEnd - effectiveStart) / 1000).coerceAtLeast(0)

        sessionDao.updateSummary(
            sessionId = sessionId,
            sampleCount = stats.sampleCount,
            durationSec = durationSec,
            avgSpeed = stats.avgSpeed ?: 0.0,
            maxSpeed = stats.maxSpeed ?: 0,
            avgRpm = stats.avgRpm ?: 0.0,
            maxRpm = stats.maxRpm ?: 0,
            avgCoolantTemp = stats.avgCoolantTemp ?: 0.0,
            maxCoolantTemp = stats.maxCoolantTemp ?: 0,
            avgBatteryVoltage = stats.avgBatteryVoltage ?: 0.0,
            minBatteryVoltage = stats.minBatteryVoltage ?: 0.0,
            maxBatteryVoltage = stats.maxBatteryVoltage ?: 0.0,
            avgEngineLoad = stats.avgEngineLoad ?: 0.0,
            maxEngineLoad = stats.maxEngineLoad ?: 0.0,
            avgStft1 = stats.avgStft1 ?: 0.0,
            avgLtft1 = stats.avgLtft1 ?: 0.0,
            avgLambda = stats.avgLambda ?: 0.0
        )
    }

    suspend fun deleteSessionCascade(sessionId: Long) {
        reportDao.deleteBySession(sessionId)
        vehicleDataDao.deleteBySession(sessionId)
        sessionDao.deleteById(sessionId)
    }
}
