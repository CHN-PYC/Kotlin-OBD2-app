package com.example.myapplication.utils

import android.content.Context
import androidx.core.content.FileProvider
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
    suspend fun exportToCsv(context: Context, repository: VehicleRepository): File {
        // Get all history data
        val data = repository.getHistory().first()
        
        if (data.isEmpty()) {
            throw Exception("No data to export")
        }

        // Create CSV file
        val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())
        val fileName = "obd2_export_$timestamp.csv"
        val file = File(context.cacheDir, fileName)

        FileWriter(file).use { writer ->
            // Write header
            writer.appendLine("Timestamp,RPM,CoolantTemp(°C),IntakeTemp(°C),ThrottlePos(%),BatteryVoltage(V)")
            
            // Write data rows
            data.sortedBy { it.timestamp }.forEach { vehicleData ->
                val timeStr = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault())
                    .format(Date(vehicleData.timestamp))
                
                writer.appendLine(
                    "$timeStr," +
                    "${vehicleData.rpm}," +
                    "${vehicleData.coolantTemp}," +
                    "${vehicleData.intakeTemp}," +
                    "${vehicleData.throttlePos}," +
                    "${String.format("%.2f", vehicleData.batteryVoltage)}"
                )
            }
        }

        return file
    }
}
