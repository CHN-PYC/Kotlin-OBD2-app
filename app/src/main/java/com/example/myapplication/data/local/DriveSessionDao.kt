package com.example.myapplication.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

@Dao
interface DriveSessionDao {

    @Insert
    suspend fun insert(session: DriveSession): Long

    @Update
    suspend fun update(session: DriveSession)

    @Query("SELECT * FROM drive_session WHERE id = :sessionId LIMIT 1")
    suspend fun getById(sessionId: Long): DriveSession?

    @Query("SELECT * FROM drive_session ORDER BY startedAt DESC")
    fun getAllSessions(): Flow<List<DriveSession>>

    @Query("SELECT * FROM drive_session WHERE sourceType = :sourceType ORDER BY startedAt DESC")
    fun getSessionsBySource(sourceType: String): Flow<List<DriveSession>>

    @Query("SELECT * FROM drive_session ORDER BY startedAt DESC LIMIT 1")
    suspend fun getLatestSession(): DriveSession?

    @Query("UPDATE drive_session SET endedAt = :endedAt, status = :status WHERE id = :sessionId")
    suspend fun closeSession(
        sessionId: Long,
        endedAt: Long,
        status: String = DriveSession.STATUS_COMPLETED
    )

    @Query(
        """
        UPDATE drive_session
        SET sampleCount = :sampleCount,
            durationSec = :durationSec,
            avgSpeed = :avgSpeed,
            maxSpeed = :maxSpeed,
            avgRpm = :avgRpm,
            maxRpm = :maxRpm,
            avgCoolantTemp = :avgCoolantTemp,
            maxCoolantTemp = :maxCoolantTemp,
            avgBatteryVoltage = :avgBatteryVoltage,
            minBatteryVoltage = :minBatteryVoltage,
            maxBatteryVoltage = :maxBatteryVoltage,
            avgEngineLoad = :avgEngineLoad,
            maxEngineLoad = :maxEngineLoad,
            avgStft1 = :avgStft1,
            avgLtft1 = :avgLtft1,
            avgLambda = :avgLambda
        WHERE id = :sessionId
        """
    )
    suspend fun updateSummary(
        sessionId: Long,
        sampleCount: Int,
        durationSec: Long,
        avgSpeed: Double,
        maxSpeed: Int,
        avgRpm: Double,
        maxRpm: Int,
        avgCoolantTemp: Double,
        maxCoolantTemp: Int,
        avgBatteryVoltage: Double,
        minBatteryVoltage: Double,
        maxBatteryVoltage: Double,
        avgEngineLoad: Double,
        maxEngineLoad: Double,
        avgStft1: Double,
        avgLtft1: Double,
        avgLambda: Double
    )

    @Query("DELETE FROM drive_session WHERE id = :sessionId")
    suspend fun deleteById(sessionId: Long)
}
