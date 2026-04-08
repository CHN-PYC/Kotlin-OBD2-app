package com.example.myapplication.data.repository

import com.example.myapplication.data.bluetooth.ObdBluetoothManager
import com.example.myapplication.data.local.VehicleData
import com.example.myapplication.data.local.VehicleDataDao
import com.example.myapplication.data.model.ObdCommand
import com.example.myapplication.utils.ObdDecoder
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.withContext

class VehicleRepository(
    private val bluetoothManager: ObdBluetoothManager,
    private val dao: VehicleDataDao
) {

    /**
     * 连接 OBD2 设备
     * @param device 蓝牙设备
     * @return 连接是否成功
     */
    suspend fun connectToDevice(device: android.bluetooth.BluetoothDevice): Boolean {
        return bluetoothManager.connect(device.address)
    }

    /**
     * 请求一次完整的车辆数据 (扩展诊断模式)
     * 采集 15+ 个关键参数
     * @return VehicleData 对象，若核心参数失败则返回 null
     */
    suspend fun requestVehicleData(): VehicleData? = withContext(Dispatchers.IO) {
        val timestamp = System.currentTimeMillis()

        // ==================== 核心参数 (必须成功) ====================
        
        // 1. 请求 RPM (发动机转速)
        val rpmResponse = bluetoothManager.sendCommand(ObdCommand.RPM.pid)
        val rpm = ObdDecoder.parse(rpmResponse, ObdCommand.RPM)?.toInt() ?: return@withContext null

        // 2. 请求冷却液温度
        val tempResponse = bluetoothManager.sendCommand(ObdCommand.COOLANT_TEMP.pid)
        val coolantTemp = ObdDecoder.parse(tempResponse, ObdCommand.COOLANT_TEMP)?.toInt() ?: return@withContext null

        // 3. 请求进气温度
        val intakeResponse = bluetoothManager.sendCommand(ObdCommand.INTAKE_TEMP.pid)
        val intakeTemp = ObdDecoder.parse(intakeResponse, ObdCommand.INTAKE_TEMP)?.toInt() ?: return@withContext null

        // 4. 请求节气门位置
        val throttleResponse = bluetoothManager.sendCommand(ObdCommand.THROTTLE_POS.pid)
        val throttlePos = ObdDecoder.parse(throttleResponse, ObdCommand.THROTTLE_POS)?.toInt() ?: return@withContext null

        // 5. 请求电池电压
        val voltageResponse = bluetoothManager.sendCommand(ObdCommand.BATTERY_VOLTAGE.pid)
        val batteryVoltage = ObdDecoder.parse(voltageResponse, ObdCommand.BATTERY_VOLTAGE) ?: return@withContext null

        // ==================== 扩展诊断参数 (可选，失败不影响核心数据) ====================
        
        // 6. 发动机负荷
        val loadResponse = bluetoothManager.sendCommand(ObdCommand.ENGINE_LOAD.pid)
        val engineLoad = ObdDecoder.parse(loadResponse, ObdCommand.ENGINE_LOAD) ?: 0.0

        // 7. 车速
        val speedResponse = bluetoothManager.sendCommand(ObdCommand.SPEED.pid)
        val speed = ObdDecoder.parse(speedResponse, ObdCommand.SPEED)?.toInt() ?: 0

        // 8. 进气歧管压力 (MAP)
        val mapResponse = bluetoothManager.sendCommand(ObdCommand.INTAKE_MANIFOLD_PRESSURE.pid)
        val intakeManifoldPressure = ObdDecoder.parse(mapResponse, ObdCommand.INTAKE_MANIFOLD_PRESSURE) ?: 0.0

        // 9. 空气质量流量 (MAF)
        val mafResponse = bluetoothManager.sendCommand(ObdCommand.MAF_RATE.pid)
        val mafRate = ObdDecoder.parse(mafResponse, ObdCommand.MAF_RATE) ?: 0.0

        // 10. 燃油压力
        val fuelPressResponse = bluetoothManager.sendCommand(ObdCommand.FUEL_PRESSURE.pid)
        val fuelPressure = ObdDecoder.parse(fuelPressResponse, ObdCommand.FUEL_PRESSURE) ?: 0.0

        // 11. 燃油液位
        val fuelLevelResponse = bluetoothManager.sendCommand(ObdCommand.FUEL_LEVEL.pid)
        val fuelLevel = ObdDecoder.parse(fuelLevelResponse, ObdCommand.FUEL_LEVEL) ?: 0.0

        // 12. 短期燃油修正 - 组 1 (关键诊断参数)
        val stft1Response = bluetoothManager.sendCommand(ObdCommand.SHORT_TERM_FUEL_TRIM_BANK1.pid)
        val shortTermFuelTrimBank1 = ObdDecoder.parse(stft1Response, ObdCommand.SHORT_TERM_FUEL_TRIM_BANK1) ?: 0.0

        // 13. 长期燃油修正 - 组 1 (关键诊断参数)
        val ltft1Response = bluetoothManager.sendCommand(ObdCommand.LONG_TERM_FUEL_TRIM_BANK1.pid)
        val longTermFuelTrimBank1 = ObdDecoder.parse(ltft1Response, ObdCommand.LONG_TERM_FUEL_TRIM_BANK1) ?: 0.0

        // 14. 短期燃油修正 - 组 2 (V6/V8 发动机)
        val stft2Response = bluetoothManager.sendCommand(ObdCommand.SHORT_TERM_FUEL_TRIM_BANK2.pid)
        val shortTermFuelTrimBank2 = ObdDecoder.parse(stft2Response, ObdCommand.SHORT_TERM_FUEL_TRIM_BANK2) ?: 0.0

        // 15. 长期燃油修正 - 组 2 (V6/V8 发动机)
        val ltft2Response = bluetoothManager.sendCommand(ObdCommand.LONG_TERM_FUEL_TRIM_BANK2.pid)
        val longTermFuelTrimBank2 = ObdDecoder.parse(ltft2Response, ObdCommand.LONG_TERM_FUEL_TRIM_BANK2) ?: 0.0

        // 16. 点火提前角
        val timingResponse = bluetoothManager.sendCommand(ObdCommand.TIMING_ADVANCE.pid)
        val timingAdvance = ObdDecoder.parse(timingResponse, ObdCommand.TIMING_ADVANCE) ?: 0.0

        // 17. 空燃比当量比 (Lambda)
        val lambdaResponse = bluetoothManager.sendCommand(ObdCommand.EQUIVALENCE_RATIO.pid)
        val equivalenceRatio = ObdDecoder.parse(lambdaResponse, ObdCommand.EQUIVALENCE_RATIO) ?: 0.0

        // 18. 油门踏板位置
        val pedalResponse = bluetoothManager.sendCommand(ObdCommand.ACCELERATOR_PEDAL_POS_D.pid)
        val acceleratorPedalPos = ObdDecoder.parse(pedalResponse, ObdCommand.ACCELERATOR_PEDAL_POS_D) ?: 0.0

        // 19. 发动机运行时间
        val runTimeResponse = bluetoothManager.sendCommand(ObdCommand.RUN_TIME.pid)
        val runTime = ObdDecoder.parse(runTimeResponse, ObdCommand.RUN_TIME) ?: 0.0

        // 20. 暖机循环次数
        val warmupsResponse = bluetoothManager.sendCommand(ObdCommand.WARMUPS_SINCE_CODES_CLEARED.pid)
        val warmupsSinceCodesCleared = ObdDecoder.parse(warmupsResponse, ObdCommand.WARMUPS_SINCE_CODES_CLEARED)?.toInt() ?: 0

        // 21. 故障后运行时间
        val timeClearedResponse = bluetoothManager.sendCommand(ObdCommand.TIME_SINCE_CODES_CLEARED.pid)
        val timeSinceCodesCleared = ObdDecoder.parse(timeClearedResponse, ObdCommand.TIME_SINCE_CODES_CLEARED) ?: 0.0

        // 所有参数采集完成，构建对象
        VehicleData(
            timestamp = timestamp,
            rpm = rpm,
            coolantTemp = coolantTemp,
            intakeTemp = intakeTemp,
            throttlePos = throttlePos,
            batteryVoltage = batteryVoltage,
            
            // 扩展参数
            engineLoad = engineLoad,
            speed = speed,
            intakeManifoldPressure = intakeManifoldPressure,
            mafRate = mafRate,
            fuelPressure = fuelPressure,
            fuelLevel = fuelLevel,
            shortTermFuelTrimBank1 = shortTermFuelTrimBank1,
            longTermFuelTrimBank1 = longTermFuelTrimBank1,
            shortTermFuelTrimBank2 = shortTermFuelTrimBank2,
            longTermFuelTrimBank2 = longTermFuelTrimBank2,
            timingAdvance = timingAdvance,
            equivalenceRatio = equivalenceRatio,
            acceleratorPedalPos = acceleratorPedalPos,
            runTime = runTime,
            warmupsSinceCodesCleared = warmupsSinceCodesCleared,
            timeSinceCodesCleared = timeSinceCodesCleared
        )
    }

    /**
     * 实时数据流：每 500ms 获取一次数据，并通过 Flow 发射
     * 包含所有扩展诊断参数
     */
    fun startLiveDataStream(): Flow<VehicleData> = flow {
        while (true) {
            val data = requestVehicleData()
            if (data != null) {
                // 发射给 UI
                emit(data)
                // 保存到数据库
                dao.insert(data)
            }
            delay(500) // 控制采样频率
        }
    }

    /**
     * 获取历史数据
     */
    fun getHistory(): Flow<List<VehicleData>> = dao.getAllHistory()

    /**
     * 清理旧数据（如 30 天前）
     */
    suspend fun cleanOldData() {
        val thirtyDaysAgo = System.currentTimeMillis() - 30L * 24 * 60 * 60 * 1000
        dao.deleteOldRecords(thirtyDaysAgo)
    }

    /**
     * 获取特定时间范围的数据
     */
    fun getHistoryByTimeRange(startTime: Long, endTime: Long): Flow<List<VehicleData>> =
        dao.getRecordsInTimeRange(startTime, endTime)
}
