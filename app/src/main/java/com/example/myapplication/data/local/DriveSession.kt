package com.example.myapplication.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "drive_session")
data class DriveSession(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val startedAt: Long,
    val endedAt: Long? = null,
    val sourceType: String,
    val title: String? = null,
    val notes: String? = null,
    val vehicleName: String? = null,
    val isFavorite: Boolean = false,
    val status: String = STATUS_ACTIVE,
    val sampleCount: Int = 0,
    val durationSec: Long = 0,
    val avgSpeed: Double = 0.0,
    val maxSpeed: Int = 0,
    val avgRpm: Double = 0.0,
    val maxRpm: Int = 0,
    val avgCoolantTemp: Double = 0.0,
    val maxCoolantTemp: Int = 0,
    val avgBatteryVoltage: Double = 0.0,
    val minBatteryVoltage: Double = 0.0,
    val maxBatteryVoltage: Double = 0.0,
    val avgEngineLoad: Double = 0.0,
    val maxEngineLoad: Double = 0.0,
    val avgStft1: Double = 0.0,
    val avgLtft1: Double = 0.0,
    val avgLambda: Double = 0.0
) {
    companion object {
        const val STATUS_ACTIVE = "ACTIVE"
        const val STATUS_COMPLETED = "COMPLETED"
        const val STATUS_INTERRUPTED = "INTERRUPTED"

        const val SOURCE_REAL = "REAL"
        const val SOURCE_DEMO = "DEMO"
        const val SOURCE_REPLAY = "REPLAY"
    }
}
