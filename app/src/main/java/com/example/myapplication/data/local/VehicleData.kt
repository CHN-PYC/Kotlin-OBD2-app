package com.example.myapplication.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * 车辆数据实体类
 * 存储一次完整的 OBD2 数据采集结果
 */
@Entity(tableName = "vehicle_data")
data class VehicleData(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    
    // 时间戳
    val timestamp: Long,
    
    // ==================== 核心参数 (原有) ====================
    
    /** 发动机转速 (RPM) */
    val rpm: Int,
    
    /** 冷却液温度 (°C) */
    val coolantTemp: Int,
    
    /** 进气温度 (°C) */
    val intakeTemp: Int,
    
    /** 节气门位置 (%) */
    val throttlePos: Int,
    
    /** 电池电压 (V) */
    val batteryVoltage: Double,
    
    // ==================== 扩展诊断参数 (新增) ====================
    
    /** 发动机负荷 (%) */
    val engineLoad: Double = 0.0,
    
    /** 车速 (km/h) */
    val speed: Int = 0,
    
    /** 进气歧管压力 (kPa) */
    val intakeManifoldPressure: Double = 0.0,
    
    /** 空气质量流量 (g/s) */
    val mafRate: Double = 0.0,
    
    /** 燃油压力 (kPa) */
    val fuelPressure: Double = 0.0,
    
    /** 燃油液位 (%) */
    val fuelLevel: Double = 0.0,
    
    /** 短期燃油修正 - 组 1 (%) */
    val shortTermFuelTrimBank1: Double = 0.0,
    
    /** 长期燃油修正 - 组 1 (%) */
    val longTermFuelTrimBank1: Double = 0.0,
    
    /** 短期燃油修正 - 组 2 (%) */
    val shortTermFuelTrimBank2: Double = 0.0,
    
    /** 长期燃油修正 - 组 2 (%) */
    val longTermFuelTrimBank2: Double = 0.0,
    
    /** 点火提前角 (°) */
    val timingAdvance: Double = 0.0,
    
    /** 空燃比当量比 (Lambda) */
    val equivalenceRatio: Double = 0.0,
    
    /** 油门踏板位置 D (%) */
    val acceleratorPedalPos: Double = 0.0,
    
    /** 发动机运行时间 (秒) */
    val runTime: Double = 0.0,
    
    /** 暖机循环次数 */
    val warmupsSinceCodesCleared: Int = 0,
    
    /** 故障后运行时间 (分钟) */
    val timeSinceCodesCleared: Double = 0.0
) {
    companion object {
        /**
         * 创建空数据对象 (用于初始化)
         */
        fun empty(): VehicleData = VehicleData(
            timestamp = System.currentTimeMillis(),
            rpm = 0,
            coolantTemp = 0,
            intakeTemp = 0,
            throttlePos = 0,
            batteryVoltage = 0.0
        )
    }
}
