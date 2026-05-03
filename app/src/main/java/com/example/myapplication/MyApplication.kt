package com.example.myapplication

import android.app.Application
import com.example.myapplication.data.bluetooth.ObdBluetoothManager
import com.example.myapplication.data.local.AppDatabase
import com.example.myapplication.data.repository.VehicleRepository

class MyApplication : Application() {

    // Global Repository instance
    lateinit var repository: VehicleRepository
        private set

    // Global Bluetooth Manager instance (for ConnectionActivity)
    lateinit var bluetoothManager: ObdBluetoothManager
        private set

    override fun onCreate() {
        super.onCreate()

        val database = AppDatabase.getDatabase(this)
        bluetoothManager = ObdBluetoothManager(this)
        repository = VehicleRepository(bluetoothManager, database.vehicleDataDao())
    }
}
