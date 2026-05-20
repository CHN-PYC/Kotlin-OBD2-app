package com.example.myapplication.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface VehicleDataDao {
    @Insert
    suspend fun insert(vehicleData: VehicleData)

    @Insert
    suspend fun insertAll(items: List<VehicleData>)

    @Query("SELECT * FROM vehicle_data ORDER BY timestamp DESC")
    fun getAllHistory(): Flow<List<VehicleData>>

    @Query("SELECT * FROM vehicle_data WHERE sessionId = :sessionId ORDER BY timestamp ASC")
    fun getBySession(sessionId: Long): Flow<List<VehicleData>>

    @Query("SELECT * FROM vehicle_data WHERE sessionId = :sessionId ORDER BY timestamp ASC")
    suspend fun getBySessionOnce(sessionId: Long): List<VehicleData>

    @Query("DELETE FROM vehicle_data WHERE sessionId = :sessionId")
    suspend fun deleteBySession(sessionId: Long)

    @Query("DELETE FROM vehicle_data WHERE timestamp < :cutoffTime")
    suspend fun deleteOldRecords(cutoffTime: Long)

    @Query("DELETE FROM vehicle_data")
    suspend fun deleteAll()

    @Query("SELECT * FROM vehicle_data WHERE timestamp BETWEEN :startTime AND :endTime ORDER BY timestamp ASC")
    fun getRecordsInTimeRange(startTime: Long, endTime: Long): Flow<List<VehicleData>>

    @Query(
        """
        SELECT
            COUNT(*) AS sampleCount,
            AVG(speed) AS avgSpeed,
            MAX(speed) AS maxSpeed,
            AVG(rpm) AS avgRpm,
            MAX(rpm) AS maxRpm,
            AVG(coolantTemp) AS avgCoolantTemp,
            MAX(coolantTemp) AS maxCoolantTemp,
            AVG(batteryVoltage) AS avgBatteryVoltage,
            MIN(batteryVoltage) AS minBatteryVoltage,
            MAX(batteryVoltage) AS maxBatteryVoltage,
            AVG(engineLoad) AS avgEngineLoad,
            MAX(engineLoad) AS maxEngineLoad,
            AVG(shortTermFuelTrimBank1) AS avgStft1,
            AVG(longTermFuelTrimBank1) AS avgLtft1,
            AVG(equivalenceRatio) AS avgLambda
        FROM vehicle_data
        WHERE sessionId = :sessionId
        """
    )
    suspend fun getSessionStats(sessionId: Long): SessionStats
}
