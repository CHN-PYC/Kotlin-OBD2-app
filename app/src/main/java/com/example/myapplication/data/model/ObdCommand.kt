package com.example.myapplication.data.model

/**
 * OBD2 PID 命令枚举
 * 
 * 标准 OBD2 协议 (SAE J1979) 定义的参数 ID
 * 模式 01 = 显示当前数据
 * 模式 02 = 显示冻结帧数据
 * 模式 03 = 显示故障码
 * 模式 04 = 清除故障码
 */
enum class ObdCommand(
    val pid: String,
    val responseBytes: Int,
    val formula: (List<Int>) -> Double,
    val displayName: String,
    val unit: String,
    val minRange: Double,
    val maxRange: Double,
    val category: PidCategory
) {
    // ==================== 基础发动机参数 ====================
    
    /** 0104 - 发动机负荷 (%) */
    ENGINE_LOAD("0104", 1, 
        { bytes -> (bytes[0] * 100.0 / 255.0) },
        "Engine Load", "%", 0.0, 100.0, PidCategory.ENGINE),
    
    /** 0105 - 发动机冷却液温度 (°C) */
    COOLANT_TEMP("0105", 1, 
        { bytes -> (bytes[0] - 40).toDouble() },
        "Coolant Temp", "°C", -40.0, 215.0, PidCategory.TEMPERATURE),
    
    /** 010C - 发动机转速 (RPM) */
    RPM("010C", 2, 
        { bytes -> ((bytes[0] * 256) + bytes[1]) / 4.0 },
        "Engine Speed", "rpm", 0.0, 16383.75, PidCategory.ENGINE),
    
    /** 010D - 车速 (km/h) */
    SPEED("010D", 1, 
        { bytes -> bytes[0].toDouble() },
        "Vehicle Speed", "km/h", 0.0, 255.0, PidCategory.VEHICLE),
    
    // ==================== 进气系统参数 ====================
    
    /** 010B - 进气歧管绝对压力 (kPa) */
    INTAKE_MANIFOLD_PRESSURE("010B", 1, 
        { bytes -> bytes[0].toDouble() },
        "Intake Manifold Pressure", "kPa", 0.0, 255.0, PidCategory.INTAKE),
    
    /** 010F - 进气温度 (°C) */
    INTAKE_TEMP("010F", 1, 
        { bytes -> (bytes[0] - 40).toDouble() },
        "Intake Air Temp", "°C", -40.0, 215.0, PidCategory.TEMPERATURE),
    
    /** 0110 - 空气质量流量 (g/s) */
    MAF_RATE("0110", 2, 
        { bytes -> ((bytes[0] * 256) + bytes[1]) / 100.0 },
        "MAF Flow Rate", "g/s", 0.0, 655.35, PidCategory.INTAKE),
    
    // ==================== 燃油系统参数 ====================
    
    /** 010A - 燃油压力 (kPa) */
    FUEL_PRESSURE("010A", 1, 
        { bytes -> (bytes[0] * 3.0) },
        "Fuel Pressure", "kPa", 0.0, 765.0, PidCategory.FUEL),
    
    /** 012F - 燃油液位 (%) */
    FUEL_LEVEL("012F", 1, 
        { bytes -> (bytes[0] * 100.0 / 255.0) },
        "Fuel Level", "%", 0.0, 100.0, PidCategory.FUEL),
    
    // ==================== 燃油修正参数 (重要诊断指标) ====================
    
    /** 0106 - 短期燃油修正 - 组 1 (%) */
    SHORT_TERM_FUEL_TRIM_BANK1("0106", 1, 
        { bytes -> ((bytes[0] - 128) * 100.0 / 128.0) },
        "STFT Bank 1", "%", -100.0, 99.2, PidCategory.FUEL_TRIM),
    
    /** 0107 - 长期燃油修正 - 组 1 (%) */
    LONG_TERM_FUEL_TRIM_BANK1("0107", 1, 
        { bytes -> ((bytes[0] - 128) * 100.0 / 128.0) },
        "LTFT Bank 1", "%", -100.0, 99.2, PidCategory.FUEL_TRIM),
    
    /** 0108 - 短期燃油修正 - 组 2 (%) */
    SHORT_TERM_FUEL_TRIM_BANK2("0108", 1, 
        { bytes -> ((bytes[0] - 128) * 100.0 / 128.0) },
        "STFT Bank 2", "%", -100.0, 99.2, PidCategory.FUEL_TRIM),
    
    /** 0109 - 长期燃油修正 - 组 2 (%) */
    LONG_TERM_FUEL_TRIM_BANK2("0109", 1, 
        { bytes -> ((bytes[0] - 128) * 100.0 / 128.0) },
        "LTFT Bank 2", "%", -100.0, 99.2, PidCategory.FUEL_TRIM),
    
    // ==================== 点火系统参数 ====================
    
    /** 010E - 点火提前角 (°) */
    TIMING_ADVANCE("010E", 1, 
        { bytes -> (bytes[0] / 2.0) - 64.0 },
        "Ignition Timing Advance", "°", -64.0, 63.5, PidCategory.IGNITION),
    
    // ==================== 排气/氧传感器参数 (重要诊断指标) ====================
    
    /** 0114 - 空燃比传感器 1 电压 (V) */
    AIR_FUEL_RATIO_BANK1_SENSOR1("0114", 2, 
        { bytes -> ((bytes[0] * 256) + bytes[1]) * (8.0 / 65536.0) },
        "A/F Ratio B1S1", "", 0.0, 8.0, PidCategory.OXYGEN),
    
    /** 0115 - 空燃比传感器 2 电压 (V) */
    AIR_FUEL_RATIO_BANK1_SENSOR2("0115", 2, 
        { bytes -> ((bytes[0] * 256) + bytes[1]) * (8.0 / 65536.0) },
        "A/F Ratio B1S2", "", 0.0, 8.0, PidCategory.OXYGEN),
    
    /** 0116 - 空燃比传感器 3 电压 (V) */
    AIR_FUEL_RATIO_BANK2_SENSOR1("0116", 2, 
        { bytes -> ((bytes[0] * 256) + bytes[1]) * (8.0 / 65536.0) },
        "A/F Ratio B2S1", "", 0.0, 8.0, PidCategory.OXYGEN),
    
    /** 0117 - 空燃比传感器 4 电压 (V) */
    AIR_FUEL_RATIO_BANK2_SENSOR2("0117", 2, 
        { bytes -> ((bytes[0] * 256) + bytes[1]) * (8.0 / 65536.0) },
        "A/F Ratio B2S2", "", 0.0, 8.0, PidCategory.OXYGEN),
    
    /** 0124 - 空燃比当量比 (Lambda) */
    EQUIVALENCE_RATIO("0124", 2, 
        { bytes -> ((bytes[0] * 256) + bytes[1]) / 32768.0 },
        "Equivalence Ratio (λ)", "", 0.0, 2.0, PidCategory.OXYGEN),
    
    // ==================== 节气门/踏板参数 ====================
    
    /** 0111 - 节气门位置 (%) */
    THROTTLE_POS("0111", 1, 
        { bytes -> (bytes[0] * 100.0 / 255.0) },
        "Throttle Position", "%", 0.0, 100.0, PidCategory.THROTTLE),
    
    /** 012C - 油门踏板位置 D (%) */
    ACCELERATOR_PEDAL_POS_D("012C", 1, 
        { bytes -> (bytes[0] * 100.0 / 255.0) },
        "Accelerator Pedal D", "%", 0.0, 100.0, PidCategory.THROTTLE),
    
    // ==================== 电气系统参数 ====================
    
    /** 0142 - 控制模块电压 (V) */
    BATTERY_VOLTAGE("0142", 2, 
        { bytes -> ((bytes[0] * 256) + bytes[1]) / 1000.0 },
        "Control Module Voltage", "V", 0.0, 65.535, PidCategory.ELECTRICAL),
    
    // ==================== 运行状态参数 ====================
    
    /** 011F - 运行时间 (秒) */
    RUN_TIME("011F", 2, 
        { bytes -> ((bytes[0] * 256) + bytes[1]).toDouble() },
        "Engine Run Time", "s", 0.0, 65535.0, PidCategory.STATUS),
    
    /** 0131 - 暖机循环次数 */
    WARMUPS_SINCE_CODES_CLEARED("0131", 2, 
        { bytes -> ((bytes[0] * 256) + bytes[1]).toDouble() },
        "Warm-ups Since DTC Clear", "cycles", 0.0, 65535.0, PidCategory.STATUS),
    
    /** 0133 - 故障后运行时间 (秒) */
    TIME_SINCE_CODES_CLEARED("0133", 2, 
        { bytes -> ((bytes[0] * 256) + bytes[1]).toDouble() },
        "Time Since DTC Cleared", "min", 0.0, 65535.0, PidCategory.STATUS);

    companion object {
        /**
         * 根据 PID 字符串查找命令
         * @param pid PID 字符串 (如 "0104")
         * @return 对应的 ObdCommand 或 null
         */
        fun fromPid(pid: String): ObdCommand? = values().find { it.pid == pid }
        
        /**
         * 根据类别获取 PID 列表
         * @param category PID 类别
         * @return 该类别下的所有 PID
         */
        fun getByCategory(category: PidCategory): List<ObdCommand> = 
            values().filter { it.category == category }
        
        /**
         * 获取推荐的基础诊断 PID 列表 (适合实时采集)
         * 包含最有诊断价值的 12 个参数
         */
        fun getRecommendedPids(): List<ObdCommand> = listOf(
            // 核心发动机参数
            RPM,
            ENGINE_LOAD,
            COOLANT_TEMP,
            
            // 进气系统
            INTAKE_MANIFOLD_PRESSURE,
            INTAKE_TEMP,
            MAF_RATE,
            
            // 燃油系统 (关键诊断)
            FUEL_PRESSURE,
            SHORT_TERM_FUEL_TRIM_BANK1,
            LONG_TERM_FUEL_TRIM_BANK1,
            
            // 点火系统
            TIMING_ADVANCE,
            
            // 排气/氧传感器 (关键诊断)
            EQUIVALENCE_RATIO,
            
            // 电气系统
            BATTERY_VOLTAGE
        )
        
        /**
         * 获取扩展诊断 PID 列表 (完整采集)
         */
        fun getExtendedPids(): List<ObdCommand> = values().toList()
    }
}

/**
 * PID 分类枚举
 * 用于 UI 分组和数据分析
 */
enum class PidCategory {
    ENGINE,         // 发动机核心参数
    TEMPERATURE,    // 温度相关
    INTAKE,         // 进气系统
    FUEL,           // 燃油系统
    FUEL_TRIM,      // 燃油修正 (关键诊断)
    IGNITION,       // 点火系统
    OXYGEN,         // 氧传感器/排气
    THROTTLE,       // 节气门/踏板
    ELECTRICAL,     // 电气系统
    VEHICLE,        // 车辆状态
    STATUS          // 运行状态
}
