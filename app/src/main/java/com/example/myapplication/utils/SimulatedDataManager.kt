package com.example.myapplication.utils

import com.example.myapplication.data.local.VehicleData
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlin.random.Random

/**
 * 模拟数据管理器
 * 用于演示和测试，无需真实 OBD2 设备
 */
object SimulatedDataManager {

    // 模拟数据范围
    private const val RPM_MIN = 800
    private const val RPM_MAX = 6000
    private const val RPM_IDLE = 850
    private const val COOLANT_NORMAL = 90
    private const val INTAKE_NORMAL = 35
    private const val THROTTLE_IDLE = 0
    private const val BATTERY_NORMAL = 14.2

    // 模拟状态
    private var isSimulating = false
    private var simulationMode = SimulationMode.IDLE
    private var sessionStartTime = 0L

    /**
     * 模拟模式
     */
    enum class SimulationMode {
        IDLE,       // 怠速
        DRIVING,    // 行驶
        ACCELERATING, // 加速
        HIGH_RPM    // 高转速
    }

    /**
     * 启动模拟数据流
     */
    fun startSimulation(): Flow<VehicleData> = flow {
        isSimulating = true
        sessionStartTime = System.currentTimeMillis()
        
        var rpm = RPM_IDLE
        var coolantTemp = 20.0 // 冷启动
        var targetRpm = RPM_IDLE
        
        while (isSimulating) {
            // 模拟 RPM 变化
            when (simulationMode) {
                SimulationMode.IDLE -> {
                    targetRpm = RPM_IDLE + Random.nextInt(-50, 50)
                }
                SimulationMode.DRIVING -> {
                    targetRpm = 2500 + Random.nextInt(-200, 200)
                }
                SimulationMode.ACCELERATING -> {
                    targetRpm = minOf(RPM_MAX, rpm + Random.nextInt(200, 500))
                }
                SimulationMode.HIGH_RPM -> {
                    targetRpm = 5500 + Random.nextInt(-200, 200)
                }
            }

            // 平滑 RPM 变化
            rpm += (targetRpm - rpm) / 10

            // 模拟水温上升（冷启动到正常工作温度）
            if (coolantTemp < COOLANT_NORMAL) {
                coolantTemp += 0.1
            } else {
                coolantTemp = COOLANT_NORMAL + Random.nextDouble(-2.0, 2.0)
            }

            // 生成模拟数据
            val data = VehicleData(
                timestamp = System.currentTimeMillis(),
                rpm = rpm.toInt(),
                coolantTemp = coolantTemp.toInt(),
                intakeTemp = INTAKE_NORMAL + Random.nextInt(-5, 10),
                throttlePos = when (simulationMode) {
                    SimulationMode.IDLE -> THROTTLE_IDLE
                    SimulationMode.DRIVING -> 15 + Random.nextInt(0, 10)
                    SimulationMode.ACCELERATING -> 50 + Random.nextInt(0, 30)
                    SimulationMode.HIGH_RPM -> 80 + Random.nextInt(0, 20)
                },
                batteryVoltage = BATTERY_NORMAL + Random.nextDouble(-0.2, 0.2),
                
                // 扩展参数
                engineLoad = when (simulationMode) {
                    SimulationMode.IDLE -> 15.0 + Random.nextDouble(-2.0, 2.0)
                    SimulationMode.DRIVING -> 35.0 + Random.nextDouble(-5.0, 5.0)
                    SimulationMode.ACCELERATING -> 70.0 + Random.nextDouble(-10.0, 10.0)
                    SimulationMode.HIGH_RPM -> 85.0 + Random.nextDouble(-5.0, 5.0)
                },
                speed = when (simulationMode) {
                    SimulationMode.IDLE -> 0
                    SimulationMode.DRIVING -> 60 + Random.nextInt(-5, 5)
                    SimulationMode.ACCELERATING -> minOf(120, (rpm * 0.03).toInt())
                    SimulationMode.HIGH_RPM -> 100 + Random.nextInt(-5, 5)
                },
                intakeManifoldPressure = when (simulationMode) {
                    SimulationMode.IDLE -> 35.0 + Random.nextDouble(-2.0, 2.0)
                    SimulationMode.DRIVING -> 55.0 + Random.nextDouble(-5.0, 5.0)
                    SimulationMode.ACCELERATING -> 80.0 + Random.nextDouble(-5.0, 5.0)
                    SimulationMode.HIGH_RPM -> 90.0 + Random.nextDouble(-5.0, 5.0)
                },
                mafRate = when (simulationMode) {
                    SimulationMode.IDLE -> 3.0 + Random.nextDouble(-0.5, 0.5)
                    SimulationMode.DRIVING -> 25.0 + Random.nextDouble(-3.0, 3.0)
                    SimulationMode.ACCELERATING -> 60.0 + Random.nextDouble(-5.0, 5.0)
                    SimulationMode.HIGH_RPM -> 80.0 + Random.nextDouble(-5.0, 5.0)
                },
                fuelPressure = 350.0 + Random.nextDouble(-10.0, 10.0),
                fuelLevel = 75.0,
                shortTermFuelTrimBank1 = Random.nextDouble(-5.0, 5.0),
                longTermFuelTrimBank1 = Random.nextDouble(-3.0, 3.0),
                shortTermFuelTrimBank2 = Random.nextDouble(-5.0, 5.0),
                longTermFuelTrimBank2 = Random.nextDouble(-3.0, 3.0),
                timingAdvance = 25.0 + Random.nextDouble(-5.0, 5.0),
                equivalenceRatio = 1.0 + Random.nextDouble(-0.05, 0.05),
                acceleratorPedalPos = when (simulationMode) {
                    SimulationMode.IDLE -> 0.0
                    SimulationMode.DRIVING -> 20.0 + Random.nextDouble(-5.0, 5.0)
                    SimulationMode.ACCELERATING -> 70.0 + Random.nextDouble(-10.0, 10.0)
                    SimulationMode.HIGH_RPM -> 90.0 + Random.nextDouble(-5.0, 5.0)
                },
                runTime = ((System.currentTimeMillis() - sessionStartTime) / 1000.0),
                warmupsSinceCodesCleared = 15,
                timeSinceCodesCleared = 120.0
            )

            emit(data)
            
            // 500ms 采样率
            kotlinx.coroutines.delay(500)
            
            // 自动切换模拟模式（演示用）
            if (Random.nextInt(100) < 5) {
                changeSimulationMode()
            }
        }
    }

    /**
     * 停止模拟
     */
    fun stopSimulation() {
        isSimulating = false
    }

    /**
     * 设置模拟模式
     */
    fun setSimulationMode(mode: SimulationMode) {
        simulationMode = mode
    }

    /**
     * 随机切换模式（用于自动演示）
     */
    private fun changeSimulationMode() {
        simulationMode = when (Random.nextInt(4)) {
            0 -> SimulationMode.IDLE
            1 -> SimulationMode.DRIVING
            2 -> SimulationMode.ACCELERATING
            else -> SimulationMode.HIGH_RPM
        }
    }

    /**
     * 获取模拟模式名称
     */
    fun getModeName(): String {
        return when (simulationMode) {
            SimulationMode.IDLE -> "Idle"
            SimulationMode.DRIVING -> "Cruising"
            SimulationMode.ACCELERATING -> "Accelerating"
            SimulationMode.HIGH_RPM -> "High RPM"
        }
    }
}
