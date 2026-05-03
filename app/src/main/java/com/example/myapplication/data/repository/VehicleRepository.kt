package com.example.myapplication.data.repository

import android.bluetooth.BluetoothDevice
import com.example.myapplication.data.bluetooth.ObdBluetoothManager
import com.example.myapplication.data.local.DriveSession
import com.example.myapplication.data.local.DriveSessionDao
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
    private val dao: VehicleDataDao,
    private val sessionDao: DriveSessionDao
) {

    private var activeSessionId: Long? = null
    private var activeSourceType: String = DriveSession.SOURCE_REAL

    suspend fun connectToDevice(device: BluetoothDevice): Boolean {
        return bluetoothManager.connect(device.address)
    }

    suspend fun startSession(
        sourceType: String = DriveSession.SOURCE_REAL,
        title: String? = null,
        notes: String? = null,
        vehicleName: String? = null
    ): Long {
        val existing = activeSessionId
        if (existing != null) return existing

        val sessionId = sessionDao.insert(
            DriveSession(
                startedAt = System.currentTimeMillis(),
                sourceType = sourceType,
                title = title,
                notes = notes,
                vehicleName = vehicleName,
                status = DriveSession.STATUS_ACTIVE
            )
        )
        activeSessionId = sessionId
        activeSourceType = sourceType
        return sessionId
    }

    suspend fun ensureSession(sourceType: String = activeSourceType): Long {
        return activeSessionId ?: startSession(sourceType = sourceType)
    }

    suspend fun endActiveSession(status: String = DriveSession.STATUS_COMPLETED) {
        val sessionId = activeSessionId ?: return
        val startedAt = sessionDao.getById(sessionId)?.startedAt ?: System.currentTimeMillis()
        val endedAt = System.currentTimeMillis()
        val stats = dao.getSessionStats(sessionId)

        sessionDao.closeSession(sessionId, endedAt, status)
        sessionDao.updateSummary(
            sessionId = sessionId,
            sampleCount = stats.sampleCount,
            durationSec = ((endedAt - startedAt) / 1000).coerceAtLeast(0),
            avgSpeed = stats.avgSpeed ?: 0.0,
            maxSpeed = stats.maxSpeed ?: 0,
            avgRpm = stats.avgRpm ?: 0.0,
            maxRpm = stats.maxRpm ?: 0,
            avgCoolantTemp = stats.avgCoolantTemp ?: 0.0,
            maxCoolantTemp = stats.maxCoolantTemp ?: 0,
            avgBatteryVoltage = stats.avgBatteryVoltage ?: 0.0,
            minBatteryVoltage = stats.minBatteryVoltage ?: 0.0,
            maxBatteryVoltage = stats.maxBatteryVoltage ?: 0.0,
            avgEngineLoad = stats.avgEngineLoad ?: 0.0,
            maxEngineLoad = stats.maxEngineLoad ?: 0,
            avgStft1 = stats.avgStft1 ?: 0.0,
            avgLtft1 = stats.avgLtft1 ?: 0.0,
            avgLambda = stats.avgLambda ?: 0.0
        )

        activeSessionId = null
    }

    fun getActiveSessionId(): Long? = activeSessionId

    suspend fun requestVehicleData(
        sessionId: Long? = activeSessionId,
        sourceType: String = activeSourceType
    ): VehicleData? = withContext(Dispatchers.IO) {
        val timestamp = System.currentTimeMillis()

        val rpmResponse = bluetoothManager.sendCommand(ObdCommand.RPM.pid)
        val rpm = ObdDecoder.parse(rpmResponse, ObdCommand.RPM)?.toInt() ?: return@withContext null

        val tempResponse = bluetoothManager.sendCommand(ObdCommand.COOLANT_TEMP.pid)
        val coolantTemp = ObdDecoder.parse(tempResponse, ObdCommand.COOLANT_TEMP)?.toInt() ?: return@withContext null

        val intakeResponse = bluetoothManager.sendCommand(ObdCommand.INTAKE_TEMP.pid)
        val intakeTemp = ObdDecoder.parse(intakeResponse, ObdCommand.INTAKE_TEMP)?.toInt() ?: return@withContext null

        val throttleResponse = bluetoothManager.sendCommand(ObdCommand.THROTTLE_POS.pid)
        val throttlePos = ObdDecoder.parse(throttleResponse, ObdCommand.THROTTLE_POS)?.toInt() ?: return@withContext null

        val voltageResponse = bluetoothManager.sendCommand(ObdCommand.BATTERY_VOLTAGE.pid)
        val batteryVoltage = ObdDecoder.parse(voltageResponse, ObdCommand.BATTERY_VOLTAGE) ?: return@withContext null

        val engineLoad = ObdDecoder.parse(bluetoothManager.sendCommand(ObdCommand.ENGINE_LOAD.pid), ObdCommand.ENGINE_LOAD) ?: 0.0
        val speed = ObdDecoder.parse(bluetoothManager.sendCommand(ObdCommand.SPEED.pid), ObdCommand.SPEED)?.toInt() ?: 0
        val intakeManifoldPressure = ObdDecoder.parse(bluetoothManager.sendCommand(ObdCommand.INTAKE_MANIFOLD_PRESSURE.pid), ObdCommand.INTAKE_MANIFOLD_PRESSURE) ?: 0.0
        val mafRate = ObdDecoder.parse(bluetoothManager.sendCommand(ObdCommand.MAF_RATE.pid), ObdCommand.MAF_RATE) ?: 0.0
        val fuelPressure = ObdDecoder.parse(bluetoothManager.sendCommand(ObdCommand.FUEL_PRESSURE.pid), ObdCommand.FUEL_PRESSURE) ?: 0.0
        val fuelLevel = ObdDecoder.parse(bluetoothManager.sendCommand(ObdCommand.FUEL_LEVEL.pid), ObdCommand.FUEL_LEVEL) ?: 0.0
        val shortTermFuelTrimBank1 = ObdDecoder.parse(bluetoothManager.sendCommand(ObdCommand.SHORT_TERM_FUEL_TRIM_BANK1.pid), ObdCommand.SHORT_TERM_FUEL_TRIM_BANK1) ?: 0.0
        val longTermFuelTrimBank1 = ObdDecoder.parse(bluetoothManager.sendCommand(ObdCommand.LONG_TERM_FUEL_TRIM_BANK1.pid), ObdCommand.LONG_TERM_FUEL_TRIM_BANK1) ?: 0.0
        val shortTermFuelTrimBank2 = ObdDecoder.parse(bluetoothManager.sendCommand(ObdCommand.SHORT_TERM_FUEL_TRIM_BANK2.pid), ObdCommand.SHORT_TERM_FUEL_TRIM_BANK2) ?: 0.0
        val longTermFuelTrimBank2 = ObdDecoder.parse(bluetoothManager.sendCommand(ObdCommand.LONG_TERM_FUEL_TRIM_BANK2.pid), ObdCommand.LONG_TERM_FUEL_TRIM_BANK2) ?: 0.0
        val timingAdvance = ObdDecoder.parse(bluetoothManager.sendCommand(ObdCommand.TIMING_ADVANCE.pid), ObdCommand.TIMING_ADVANCE) ?: 0.0
        val equivalenceRatio = ObdDecoder.parse(bluetoothManager.sendCommand(ObdCommand.EQUIVALENCE_RATIO.pid), ObdCommand.EQUIVALENCE_RATIO) ?: 0.0
        val acceleratorPedalPos = ObdDecoder.parse(bluetoothManager.sendCommand(ObdCommand.ACCELERATOR_PEDAL_POS_D.pid), ObdCommand.ACCELERATOR_PEDAL_POS_D) ?: 0.0
        val runTime = ObdDecoder.parse(bluetoothManager.sendCommand(ObdCommand.RUN_TIME.pid), ObdCommand.RUN_TIME) ?: 0.0
        val warmupsSinceCodesCleared = ObdDecoder.parse(bluetoothManager.sendCommand(ObdCommand.WARMUPS_SINCE_CODES_CLEARED.pid), ObdCommand.WARMUPS_SINCE_CODES_CLEARED)?.toInt() ?: 0
        val timeSinceCodesCleared = ObdDecoder.parse(bluetoothManager.sendCommand(ObdCommand.TIME_SINCE_CODES_CLEARED.pid), ObdCommand.TIME_SINCE_CODES_CLEARED) ?: 0.0

        VehicleData(
            sessionId = sessionId ?: 0,
            sourceType = sourceType,
            timestamp = timestamp,
            rpm = rpm,
            coolantTemp = coolantTemp,
            intakeTemp = intakeTemp,
            throttlePos = throttlePos,
            batteryVoltage = batteryVoltage,
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

    fun startLiveDataStream(
        sourceType: String = DriveSession.SOURCE_REAL,
        autoStartSession: Boolean = true
    ): Flow<VehicleData> = flow {
        if (autoStartSession) {
            ensureSession(sourceType)
        }
        while (true) {
            val data = requestVehicleData(sourceType = sourceType)
            if (data != null) {
                emit(data)
                dao.insert(data)
            }
            delay(500)
        }
    }

    suspend fun saveVehicleData(data: VehicleData) {
        val sessionId = if (data.sessionId != 0L) data.sessionId else ensureSession(data.sourceType)
        dao.insert(data.copy(sessionId = sessionId))
    }

    fun getHistory(): Flow<List<VehicleData>> = dao.getAllHistory()

    fun getHistoryBySession(sessionId: Long): Flow<List<VehicleData>> = dao.getBySession(sessionId)

    fun getHistoryByTimeRange(startTime: Long, endTime: Long): Flow<List<VehicleData>> =
        dao.getRecordsInTimeRange(startTime, endTime)

    suspend fun cleanOldData() {
        val thirtyDaysAgo = System.currentTimeMillis() - 30L * 24 * 60 * 60 * 1000
        dao.deleteOldRecords(thirtyDaysAgo)
    }

    fun disconnect() {
        bluetoothManager.close()
    }
}
