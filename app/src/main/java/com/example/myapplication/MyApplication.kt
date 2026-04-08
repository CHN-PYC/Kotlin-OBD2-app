package com.example.myapplication

import android.app.Application
import com.example.myapplication.data.bluetooth.ObdBluetoothManager
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

        // Initialize database
        val database = AppDatabase.getDatabase(this)

        // Initialize bluetooth manager
        bluetoothManager = ObdBluetoothManager(this)

        // Initialize Repository
        repository = VehicleRepository(bluetoothManager, database.vehicleDataDao())
    }
}
