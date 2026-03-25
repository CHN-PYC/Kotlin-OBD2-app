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
     * 请求一次完整的车辆数据
     * @return VehicleData 对象，若任何参数失败则返回 null
     */
    suspend fun requestVehicleData(): VehicleData? = withContext(Dispatchers.IO) {
        val timestamp = System.currentTimeMillis()

        // 1. 请求 RPM
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

        // 所有参数成功，构建对象
        VehicleData(
            timestamp = timestamp,
            rpm = rpm,
            coolantTemp = coolantTemp,
            intakeTemp = intakeTemp,
            throttlePos = throttlePos,
            batteryVoltage = batteryVoltage
        )
    }

    /**
     * 实时数据流：每500ms获取一次数据，并通过 Flow 发射
     */
    fun startLiveDataStream(): Flow<VehicleData> = flow {
        while (true) {
            val data = requestVehicleData()
            if (data != null) {
                // 发射给 UI
                emit(data)
                // 可选：保存到数据库
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
     * 清理旧数据（如30天前）
     */
    suspend fun cleanOldData() {
        val thirtyDaysAgo = System.currentTimeMillis() - 30L * 24 * 60 * 60 * 1000
        dao.deleteOldRecords(thirtyDaysAgo)
    }
}