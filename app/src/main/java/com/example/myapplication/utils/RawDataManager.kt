package com.example.myapplication.utils

import com.example.myapplication.data.local.VehicleData
import com.example.myapplication.data.model.ObdCommand
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.flow

/**
 * Raw OBD2 Data Manager
 *
 * Accepts raw hex responses (e.g. "410C1AF0", "41 05 5A") and uses
 * ObdDecoder to parse them into VehicleData. Designed for:
 *   1. Feeding captured real OBD2 logs back into the app for replay
 *   2. Unit / integration testing the full decode pipeline
 *   3. Simulating a real ECU without hardware
 *
 * Usage:
 *   RawDataManager.feed("410C1AF0")          // RPM = (0x1A*256+0xF0)/4 = 1756 rpm
 *   RawDataManager.feed("41055A")             // Coolant = 0x5A - 40 = 50°C
 *   val data = RawDataManager.buildVehicleData()
 *
 * Or use the continuous flow:
 *   RawDataManager.startStream(500).collect { data -> ... }
 */
object RawDataManager {

    // PID → raw response map
    private val responseBuffer = mutableMapOf<String, String>()

    // Callback for when a full snapshot is available
    private val _lastData = MutableStateFlow<VehicleData?>(null)
    val lastData: MutableStateFlow<VehicleData?> get() = _lastData

    // ---------- Single-shot API ----------

    /**
     * Feed a raw OBD2 response string.
     * Auto-detects the PID from the response header (41 + PID bytes).
     *
     * Examples:
     *   "410C1AF0"    → RPM command, data = 1AF0
     *   "41 05 5A"    → Coolant, data = 5A (spaces are OK)
     *   ">410C1AF0\r\n" → header + response (cleaned automatically)
     */
    fun feed(rawResponse: String) {
        val cleaned = ObdDecoder.cleanResponse(rawResponse)
        if (cleaned.length < 4) return

        val mode = cleaned.substring(0, 2)
        if (mode != "41") return  // Only mode 01 responses

        val pidHex = cleaned.substring(2, 4)
        responseBuffer[pidHex] = cleaned
    }

    /**
     * Feed with explicit PID (useful when the response doesn't include a header).
     * @param pid PID bytes only, e.g. "0C" for RPM
     * @param rawData Data bytes only, e.g. "1AF0"
     */
    fun feed(pid: String, rawData: String) {
        responseBuffer[pid.uppercase()] = "41${pid.uppercase()}${rawData.uppercase()}"
    }

    /**
     * Build a VehicleData snapshot from all buffered responses.
     * Returns null if no data has been fed yet.
     */
    fun buildVehicleData(): VehicleData? {
        if (responseBuffer.isEmpty()) return null

        val timestamp = System.currentTimeMillis()
        var rpm = 0
        var coolantTemp = 0
        var intakeTemp = 0
        var throttlePos = 0
        var batteryVoltage = 0.0
        var engineLoad = 0.0
        var speed = 0
        var intakeManifoldPressure = 0.0
        var mafRate = 0.0
        var fuelPressure = 0.0
        var fuelLevel = 0.0
        var stft1 = 0.0
        var ltft1 = 0.0
        var stft2 = 0.0
        var ltft2 = 0.0
        var timingAdvance = 0.0
        var equivalenceRatio = 0.0
        var acceleratorPedalPos = 0.0
        var runTime = 0.0
        var warmups = 0
        var timeSinceCleared = 0.0

        for ((pidHex, raw) in responseBuffer) {
            val command = ObdCommand.fromPid("01$pidHex") ?: continue
            val parsed = ObdDecoder.parse(raw, command) ?: continue

            when (command) {
                ObdCommand.RPM -> rpm = parsed.toInt()
                ObdCommand.COOLANT_TEMP -> coolantTemp = parsed.toInt()
                ObdCommand.INTAKE_TEMP -> intakeTemp = parsed.toInt()
                ObdCommand.THROTTLE_POS -> throttlePos = parsed.toInt()
                ObdCommand.BATTERY_VOLTAGE -> batteryVoltage = parsed
                ObdCommand.ENGINE_LOAD -> engineLoad = parsed
                ObdCommand.SPEED -> speed = parsed.toInt()
                ObdCommand.INTAKE_MANIFOLD_PRESSURE -> intakeManifoldPressure = parsed
                ObdCommand.MAF_RATE -> mafRate = parsed
                ObdCommand.FUEL_PRESSURE -> fuelPressure = parsed
                ObdCommand.FUEL_LEVEL -> fuelLevel = parsed
                ObdCommand.SHORT_TERM_FUEL_TRIM_BANK1 -> stft1 = parsed
                ObdCommand.LONG_TERM_FUEL_TRIM_BANK1 -> ltft1 = parsed
                ObdCommand.SHORT_TERM_FUEL_TRIM_BANK2 -> stft2 = parsed
                ObdCommand.LONG_TERM_FUEL_TRIM_BANK2 -> ltft2 = parsed
                ObdCommand.TIMING_ADVANCE -> timingAdvance = parsed
                ObdCommand.EQUIVALENCE_RATIO -> equivalenceRatio = parsed
                ObdCommand.ACCELERATOR_PEDAL_POS_D -> acceleratorPedalPos = parsed
                ObdCommand.RUN_TIME -> runTime = parsed
                ObdCommand.WARMUPS_SINCE_CODES_CLEARED -> warmups = parsed.toInt()
                ObdCommand.TIME_SINCE_CODES_CLEARED -> timeSinceCleared = parsed
                else -> {}
            }
        }

        val data = VehicleData(
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
            shortTermFuelTrimBank1 = stft1,
            longTermFuelTrimBank1 = ltft1,
            shortTermFuelTrimBank2 = stft2,
            longTermFuelTrimBank2 = ltft2,
            timingAdvance = timingAdvance,
            equivalenceRatio = equivalenceRatio,
            acceleratorPedalPos = acceleratorPedalPos,
            runTime = runTime,
            warmupsSinceCodesCleared = warmups,
            timeSinceCodesCleared = timeSinceCleared
        )

        _lastData.value = data
        return data
    }

    // ---------- Batch / Multi-line API ----------

    /**
     * Feed multiple raw responses at once.
     * Each line can be a full response like "410C1AF0".
     */
    fun feedMultiple(vararg responses: String) {
        responses.forEach { feed(it) }
    }

    /**
     * Feed from a multi-line string (e.g. captured log file content).
     */
    fun feedLog(log: String) {
        log.lineSequence()
            .map { it.trim() }
            .filter { it.isNotEmpty() }
            .forEach { feed(it) }
    }

    // ---------- Stream API ----------

    /**
     * Start a continuous stream that emits VehicleData at the given interval.
     * Useful for simulating a live connection from pre-recorded raw data.
     *
     * @param intervalMs time between emissions (default 500ms)
     * @param loop whether to reset and replay from the beginning when buffer runs out
     */
    fun startStream(intervalMs: Long = 500, loop: Boolean = true): Flow<VehicleData> = flow {
        val pids = listOf(
            ObdCommand.RPM,
            ObdCommand.COOLANT_TEMP,
            ObdCommand.INTAKE_TEMP,
            ObdCommand.THROTTLE_POS,
            ObdCommand.BATTERY_VOLTAGE,
            ObdCommand.ENGINE_LOAD,
            ObdCommand.SPEED,
            ObdCommand.INTAKE_MANIFOLD_PRESSURE,
            ObdCommand.MAF_RATE,
            ObdCommand.FUEL_PRESSURE,
            ObdCommand.FUEL_LEVEL,
            ObdCommand.SHORT_TERM_FUEL_TRIM_BANK1,
            ObdCommand.LONG_TERM_FUEL_TRIM_BANK1,
            ObdCommand.SHORT_TERM_FUEL_TRIM_BANK2,
            ObdCommand.LONG_TERM_FUEL_TRIM_BANK2,
            ObdCommand.TIMING_ADVANCE,
            ObdCommand.EQUIVALENCE_RATIO,
            ObdCommand.ACCELERATOR_PEDAL_POS_D,
            ObdCommand.RUN_TIME,
            ObdCommand.WARMUPS_SINCE_CODES_CLEARED,
            ObdCommand.TIME_SINCE_CODES_CLEARED
        )

        var snapshot = 0

        while (true) {
            // Build from whatever is currently in the buffer
            val data = buildVehicleData()
            if (data != null) {
                emit(data)
                snapshot++
            }

            delay(intervalMs)
        }
    }

    // ---------- Utility ----------

    /**
     * Clear all buffered responses.
     */
    fun clear() {
        responseBuffer.clear()
        _lastData.value = null
    }

    /**
     * Get the raw response stored for a specific PID.
     */
    fun getRaw(pid: String): String? = responseBuffer[pid.uppercase()]

    /**
     * Check if the buffer is empty.
     */
    fun isEmpty(): Boolean = responseBuffer.isEmpty()

    /**
     * Get the number of PID responses currently buffered.
     */
    fun size(): Int = responseBuffer.size

    /**
     * Generate a raw hex response for a given PID and value.
     * (Inverse of parse — useful for creating test fixtures.)
     */
    fun encode(command: ObdCommand, value: Double): String {
        val dataBytes = when (command) {
            ObdCommand.ENGINE_LOAD -> {
                listOf((value * 255.0 / 100.0).toInt().coerceIn(0, 255))
            }
            ObdCommand.COOLANT_TEMP, ObdCommand.INTAKE_TEMP -> {
                listOf((value + 40).toInt().coerceIn(0, 255))
            }
            ObdCommand.RPM -> {
                val v = (value * 4).toInt().coerceIn(0, 65535)
                listOf(v / 256, v % 256)
            }
            ObdCommand.SPEED -> {
                listOf(value.toInt().coerceIn(0, 255))
            }
            ObdCommand.INTAKE_MANIFOLD_PRESSURE -> {
                listOf(value.toInt().coerceIn(0, 255))
            }
            ObdCommand.MAF_RATE -> {
                val v = (value * 100).toInt().coerceIn(0, 65535)
                listOf(v / 256, v % 256)
            }
            ObdCommand.FUEL_PRESSURE -> {
                listOf((value / 3.0).toInt().coerceIn(0, 255))
            }
            ObdCommand.FUEL_LEVEL -> {
                listOf((value * 255.0 / 100.0).toInt().coerceIn(0, 255))
            }
            ObdCommand.SHORT_TERM_FUEL_TRIM_BANK1,
            ObdCommand.LONG_TERM_FUEL_TRIM_BANK1,
            ObdCommand.SHORT_TERM_FUEL_TRIM_BANK2,
            ObdCommand.LONG_TERM_FUEL_TRIM_BANK2 -> {
                listOf((value * 128.0 / 100.0 + 128).toInt().coerceIn(0, 255))
            }
            ObdCommand.TIMING_ADVANCE -> {
                listOf(((value + 64) * 2).toInt().coerceIn(0, 255))
            }
            ObdCommand.THROTTLE_POS, ObdCommand.ACCELERATOR_PEDAL_POS_D -> {
                listOf((value * 255.0 / 100.0).toInt().coerceIn(0, 255))
            }
            ObdCommand.BATTERY_VOLTAGE -> {
                val v = (value * 1000).toInt().coerceIn(0, 65535)
                listOf(v / 256, v % 256)
            }
            ObdCommand.EQUIVALENCE_RATIO -> {
                val v = (value * 32768).toInt().coerceIn(0, 65535)
                listOf(v / 256, v % 256)
            }
            ObdCommand.RUN_TIME,
            ObdCommand.WARMUPS_SINCE_CODES_CLEARED,
            ObdCommand.TIME_SINCE_CODES_CLEARED -> {
                val v = value.toInt().coerceIn(0, 65535)
                listOf(v / 256, v % 256)
            }
            else -> listOf(0)
        }

        val dataHex = dataBytes.joinToString("") { String.format("%02X", it) }
        return "41${command.pid.substring(2)}$dataHex"
    }
}
