package com.example.myapplication

import android.app.Application
import com.example.myapplication.data.bluetooth.ObdBluetoothManager
import com.example.myapplication.data.repository.VehicleRepository

class MyApplication : Application() {

    // 全局 Repository 实例
    lateinit var repository: VehicleRepository
        private set

    override fun onCreate() {
        super.onCreate()

        // 初始化数据库
        val database = AppDatabase.getDatabase(this)

        // 初始化蓝牙管理器
        val obdbluetoothManager = ObdBluetoothManager(this)

        // 初始化 Repository
        repository = VehicleRepository(obdbluetoothManager, database.vehicleDataDao())
    }
}