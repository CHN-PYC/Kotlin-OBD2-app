package com.example.myapplication.data.local

data class SessionStats(
    val sampleCount: Int,
    val avgSpeed: Double?,
    val maxSpeed: Int?,
    val avgRpm: Double?,
    val maxRpm: Int?,
    val avgCoolantTemp: Double?,
    val maxCoolantTemp: Int?,
    val avgBatteryVoltage: Double?,
    val minBatteryVoltage: Double?,
    val maxBatteryVoltage: Double?,
    val avgEngineLoad: Double?,
    val maxEngineLoad: Double?,
    val avgStft1: Double?,
    val avgLtft1: Double?,
    val avgLambda: Double?
)
