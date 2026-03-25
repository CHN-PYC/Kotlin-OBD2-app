package com.example.myapplication.data.local


import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "vehicle_data")
data class VehicleData(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val timestamp: Long,
    val rpm: Int,
    val coolantTemp: Int,
    val intakeTemp: Int,
    val throttlePos: Int,
    val batteryVoltage: Double
)