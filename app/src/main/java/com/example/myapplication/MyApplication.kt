package com.example.myapplication

import android.app.Application
import com.example.myapplication.data.bluetooth.ObdBluetoothManager
import com.example.myapplication.data.local.AppDatabase
import com.example.myapplication.data.repository.DiagnosticRepository
import com.example.myapplication.data.repository.SessionRepository
import com.example.myapplication.data.repository.VehicleRepository

class MyApplication : Application() {

    lateinit var repository: VehicleRepository
        private set

    lateinit var sessionRepository: SessionRepository
        private set

    lateinit var diagnosticRepository: DiagnosticRepository
        private set

    lateinit var bluetoothManager: ObdBluetoothManager
        private set

    override fun onCreate() {
        super.onCreate()

        val database = AppDatabase.getDatabase(this)
        bluetoothManager = ObdBluetoothManager(this)

        repository = VehicleRepository(
            bluetoothManager = bluetoothManager,
            dao = database.vehicleDataDao(),
            sessionDao = database.driveSessionDao()
        )

        sessionRepository = SessionRepository(
            sessionDao = database.driveSessionDao(),
            vehicleDataDao = database.vehicleDataDao(),
            reportDao = database.diagnosticReportDao()
        )

        diagnosticRepository = DiagnosticRepository(
            reportDao = database.diagnosticReportDao(),
            sessionDao = database.driveSessionDao(),
            vehicleDataDao = database.vehicleDataDao()
        )
    }
}
