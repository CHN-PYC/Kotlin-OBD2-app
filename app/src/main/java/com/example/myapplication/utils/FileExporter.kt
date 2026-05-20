package com.example.myapplication.utils

import android.content.Context
import com.example.myapplication.data.local.VehicleData
import com.example.myapplication.data.repository.VehicleRepository
import kotlinx.coroutines.flow.first
import java.io.File
import java.io.FileWriter
import java.text.SimpleDateFormat
import java.util.*

object FileExporter {

    /**
     * Export vehicle data to CSV file
     * @param context Android context
     * @param repository Vehicle repository to get data
     * @return File object for the exported CSV
     */
    suspend fun exportToCsv(context: Context, repository: VehicleRepository, sessionId: Long? = null): File {
        val data = if (sessionId != null) {
            repository.getHistoryBySession(sessionId).first()
        } else {
            repository.getHistory().first()
        }

        if (data.isEmpty()) {
            throw Exception("No data to export")
        }

        val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())
        val scope = if (sessionId != null) "session_${sessionId}" else "all"
        val fileName = "obd2_export_${scope}_$timestamp.csv"
        val file = File(context.cacheDir, fileName)

        FileWriter(file).use { writer ->
            writer.appendLine(
                "Timestamp,RPM,CoolantTempC,IntakeTempC,ThrottlePosPct,BatteryVoltageV,EngineLoadPct,SpeedKmh,MAPkPa,MAFgPerSec,FuelPressurekPa,FuelLevelPct,STFT1Pct,LTFT1Pct,STFT2Pct,LTFT2Pct,TimingAdvanceDeg,Lambda,PedalPosPct,RunTimeSec,Warmups,TimeSinceCodesClearedMin"
            )

            data.sortedBy { it.timestamp }.forEach { vehicleData ->
                val timeStr = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault())
                    .format(Date(vehicleData.timestamp))

                writer.appendLine(
                    listOf(
                        timeStr,
                        vehicleData.rpm,
                        vehicleData.coolantTemp,
                        vehicleData.intakeTemp,
                        vehicleData.throttlePos,
                        String.format("%.2f", vehicleData.batteryVoltage),
                        String.format("%.1f", vehicleData.engineLoad),
                        vehicleData.speed,
                        String.format("%.1f", vehicleData.intakeManifoldPressure),
                        String.format("%.2f", vehicleData.mafRate),
                        String.format("%.1f", vehicleData.fuelPressure),
                        String.format("%.1f", vehicleData.fuelLevel),
                        String.format("%.1f", vehicleData.shortTermFuelTrimBank1),
                        String.format("%.1f", vehicleData.longTermFuelTrimBank1),
                        String.format("%.1f", vehicleData.shortTermFuelTrimBank2),
                        String.format("%.1f", vehicleData.longTermFuelTrimBank2),
                        String.format("%.1f", vehicleData.timingAdvance),
                        String.format("%.3f", vehicleData.equivalenceRatio),
                        String.format("%.1f", vehicleData.acceleratorPedalPos),
                        String.format("%.1f", vehicleData.runTime),
                        vehicleData.warmupsSinceCodesCleared,
                        String.format("%.1f", vehicleData.timeSinceCodesCleared)
                    ).joinToString(",")
                )
            }
        }

        return file
    }
}
