package com.example.myapplication.data.model

/**
 * 枚举类
 */
enum class ObdCommand(
    val pid: String,
    val responseBytes: Int,
    val formula: (List<Int>) -> Double
) {
    RPM("010C", 2, { bytes -> ((bytes[0] * 256) + bytes[1]) / 4.0 }),
    COOLANT_TEMP("0105", 1, { bytes -> (bytes[0] - 40).toDouble() }),
    SPEED("010D", 1, { bytes -> bytes[0].toDouble() }), // 如果后期需要车速
    INTAKE_TEMP("010F", 1, { bytes -> (bytes[0] - 40).toDouble() }),
    THROTTLE_POS("0111", 1, { bytes -> (bytes[0] * 100 / 255).toDouble() }),
    BATTERY_VOLTAGE("0142", 2, { bytes -> ((bytes[0] * 256) + bytes[1]) / 1000.0 });

    companion object {
        fun fromPid(pid: String): ObdCommand? = values().find { it.pid == pid }
    }
}