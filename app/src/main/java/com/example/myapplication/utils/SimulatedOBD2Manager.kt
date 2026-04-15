package com.example.myapplication.utils

import com.example.myapplication.data.local.VehicleData
import com.example.myapplication.data.model.ObdCommand
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlin.random.Random

/**
 * Simulated OBD2 Device Manager
 * Simulates a real OBD2 adapter responding to PID queries
 * Generates realistic responses based on simulated vehicle state
 */
object SimulatedOBD2Manager {

    // Simulated vehicle state
    private var currentRpm = 850
    private var currentCoolantTemp = 90
    private var currentIntakeTemp = 35
    private var currentThrottlePos = 0
    private var currentBatteryVoltage = 14.2
    private var currentSpeed = 0
    private var currentEngineLoad = 15.0
    private var currentIntakeManifoldPressure = 35.0
    private var currentMafRate = 3.0
    private var currentFuelPressure = 350.0
    private var currentFuelLevel = 75.0
    private var currentStft1 = 0.0
    private var currentLtft1 = 0.0
    private var currentStft2 = 0.0
    private var currentLtft2 = 0.0
    private var currentTimingAdvance = 25.0
    private var currentEquivalenceRatio = 1.0
    private var currentAcceleratorPedalPos = 0.0
    private var currentRunTime = 0L
    private var sessionStartTime = System.currentTimeMillis()

    // Simulation mode
    enum class SimulationMode {
        IDLE,           // 怠速
        DRIVING,        // 巡航
        ACCELERATING,   // 加速
        HIGH_RPM,       // 高转速
        DECELERATING    // 减速
    }

    private var simulationMode = SimulationMode.IDLE

    /**
     * Set simulation mode
     */
    fun setMode(mode: SimulationMode) {
        simulationMode = mode
    }

    /**
     * Get current simulation mode name
     */
    fun getModeName(): String = when (simulationMode) {
        SimulationMode.IDLE -> "Idle"
        SimulationMode.DRIVING -> "Cruising"
        SimulationMode.ACCELERATING -> "Accelerating"
        SimulationMode.HIGH_RPM -> "High RPM"
        SimulationMode.DECELERATING -> "Decelerating"
    }

    /**
     * Update simulated vehicle state based on current mode
     */
    private fun updateState() {
        // Random variation
        val variation = { base: Int, range: Int -> base + Random.nextInt(-range, range + 1) }
        val variationDouble = { base: Double, range: Double -> base + Random.nextDouble(-range, range) }

        when (simulationMode) {
            SimulationMode.IDLE -> {
                currentRpm = variation(850, 50)
                currentCoolantTemp = variation(90, 2)
                currentIntakeTemp = variation(35, 5)
                currentThrottlePos = variation(0, 2)
                currentSpeed = variation(0, 1)
                currentEngineLoad = variationDouble(15.0, 2.0)
                currentIntakeManifoldPressure = variationDouble(35.0, 2.0)
                currentMafRate = variationDouble(3.0, 0.5)
                currentAcceleratorPedalPos = variationDouble(0.0, 2.0)
            }
            SimulationMode.DRIVING -> {
                currentRpm = variation(2500, 200)
                currentCoolantTemp = variation(95, 2)
                currentIntakeTemp = variation(40, 5)
                currentThrottlePos = variation(15, 5)
                currentSpeed = variation(60, 5)
                currentEngineLoad = variationDouble(35.0, 5.0)
                currentIntakeManifoldPressure = variationDouble(55.0, 5.0)
                currentMafRate = variationDouble(25.0, 3.0)
                currentAcceleratorPedalPos = variationDouble(20.0, 5.0)
            }
            SimulationMode.ACCELERATING -> {
                currentRpm = minOf(6000, currentRpm + Random.nextInt(200, 500))
                currentThrottlePos = minOf(100, currentThrottlePos + Random.nextInt(5, 15))
                currentSpeed = minOf(120, currentSpeed + Random.nextInt(2, 5))
                currentEngineLoad = variationDouble(70.0, 10.0)
                currentIntakeManifoldPressure = variationDouble(80.0, 5.0)
                currentMafRate = variationDouble(60.0, 5.0)
                currentAcceleratorPedalPos = variationDouble(70.0, 10.0)
            }
            SimulationMode.HIGH_RPM -> {
                currentRpm = variation(5500, 200)
                currentThrottlePos = variation(80, 10)
                currentSpeed = variation(100, 5)
                currentEngineLoad = variationDouble(85.0, 5.0)
                currentIntakeManifoldPressure = variationDouble(90.0, 5.0)
                currentMafRate = variationDouble(80.0, 5.0)
                currentAcceleratorPedalPos = variationDouble(90.0, 5.0)
            }
            SimulationMode.DECELERATING -> {
                currentRpm = maxOf(800, currentRpm - Random.nextInt(100, 300))
                currentThrottlePos = maxOf(0, currentThrottlePos - Random.nextInt(5, 15))
                currentSpeed = maxOf(0, currentSpeed - Random.nextInt(2, 5))
                currentEngineLoad = variationDouble(10.0, 3.0)
                currentIntakeManifoldPressure = variationDouble(25.0, 3.0)
                currentMafRate = variationDouble(2.0, 0.5)
                currentAcceleratorPedalPos = variationDouble(0.0, 2.0)
            }
        }

        // Always update
        currentBatteryVoltage = variationDouble(14.2, 0.2)
        currentFuelPressure = variationDouble(350.0, 10.0)
        currentFuelLevel = variationDouble(75.0, 0.5)
        currentStft1 = variationDouble(0.0, 2.0)
        currentLtft1 = variationDouble(0.0, 1.0)
        currentStft2 = variationDouble(0.0, 2.0)
        currentLtft2 = variationDouble(0.0, 1.0)
        currentTimingAdvance = variationDouble(25.0, 5.0)
        currentEquivalenceRatio = variationDouble(1.0, 0.05)
        currentRunTime = (System.currentTimeMillis() - sessionStartTime) / 1000
    }

    /**
     * Send command to simulated OBD2 device
     * @param pid PID string (e.g., "010C")
     * @return Raw response string (e.g., "41 0C 1A F0")
     */
    fun sendCommand(pid: String): String {
        updateState()

        // Extract mode and PID
        val mode = pid.substring(0, 2)
        val pidBytes = pid.substring(2, 4)

        // Only support mode 01 (Show Current Data)
        if (mode != "01") {
            return "NO DATA"
        }

        // Generate response based on PID
        val responseData = generateResponse(pidBytes) ?: return "NO DATA"

        // Response format: 41 + PID bytes + data bytes
        return "41$pidBytes$responseData"
    }

    /**
     * Simulate a full vehicle data request — mirrors VehicleRepository.requestVehicleData()
     * but requires NO Bluetooth connection.
     *
     * Pipeline: simulated hex response → ObdDecoder.parse() → VehicleData
     * Use this to verify ObdDecoder can correctly parse hex into physical values
     * without any real OBD2 device.
     */
    fun requestVehicleData(): VehicleData? {
        val timestamp = System.currentTimeMillis()
        updateState()

        // ==================== Core params (must succeed) ====================

        val rpmResponse = sendCommand(ObdCommand.RPM.pid)
        val rpm = ObdDecoder.parse(rpmResponse, ObdCommand.RPM)?.toInt()
            ?: return null  // core param failed

        val coolantResponse = sendCommand(ObdCommand.COOLANT_TEMP.pid)
        val coolantTemp = ObdDecoder.parse(coolantResponse, ObdCommand.COOLANT_TEMP)?.toInt()
            ?: return null

        val intakeResponse = sendCommand(ObdCommand.INTAKE_TEMP.pid)
        val intakeTemp = ObdDecoder.parse(intakeResponse, ObdCommand.INTAKE_TEMP)?.toInt()
            ?: return null

        val throttleResponse = sendCommand(ObdCommand.THROTTLE_POS.pid)
        val throttlePos = ObdDecoder.parse(throttleResponse, ObdCommand.THROTTLE_POS)?.toInt()
            ?: return null

        val voltageResponse = sendCommand(ObdCommand.BATTERY_VOLTAGE.pid)
        val batteryVoltage = ObdDecoder.parse(voltageResponse, ObdCommand.BATTERY_VOLTAGE)
            ?: return null

        // ==================== Extended params (optional, fail → 0) ====================

        val engineLoad = ObdDecoder.parse(sendCommand(ObdCommand.ENGINE_LOAD.pid), ObdCommand.ENGINE_LOAD) ?: 0.0
        val speed = ObdDecoder.parse(sendCommand(ObdCommand.SPEED.pid), ObdCommand.SPEED)?.toInt() ?: 0
        val intakeManifoldPressure = ObdDecoder.parse(sendCommand(ObdCommand.INTAKE_MANIFOLD_PRESSURE.pid), ObdCommand.INTAKE_MANIFOLD_PRESSURE) ?: 0.0
        val mafRate = ObdDecoder.parse(sendCommand(ObdCommand.MAF_RATE.pid), ObdCommand.MAF_RATE) ?: 0.0
        val fuelPressure = ObdDecoder.parse(sendCommand(ObdCommand.FUEL_PRESSURE.pid), ObdCommand.FUEL_PRESSURE) ?: 0.0
        val fuelLevel = ObdDecoder.parse(sendCommand(ObdCommand.FUEL_LEVEL.pid), ObdCommand.FUEL_LEVEL) ?: 0.0
        val stft1 = ObdDecoder.parse(sendCommand(ObdCommand.SHORT_TERM_FUEL_TRIM_BANK1.pid), ObdCommand.SHORT_TERM_FUEL_TRIM_BANK1) ?: 0.0
        val ltft1 = ObdDecoder.parse(sendCommand(ObdCommand.LONG_TERM_FUEL_TRIM_BANK1.pid), ObdCommand.LONG_TERM_FUEL_TRIM_BANK1) ?: 0.0
        val stft2 = ObdDecoder.parse(sendCommand(ObdCommand.SHORT_TERM_FUEL_TRIM_BANK2.pid), ObdCommand.SHORT_TERM_FUEL_TRIM_BANK2) ?: 0.0
        val ltft2 = ObdDecoder.parse(sendCommand(ObdCommand.LONG_TERM_FUEL_TRIM_BANK2.pid), ObdCommand.LONG_TERM_FUEL_TRIM_BANK2) ?: 0.0
        val timingAdvance = ObdDecoder.parse(sendCommand(ObdCommand.TIMING_ADVANCE.pid), ObdCommand.TIMING_ADVANCE) ?: 0.0
        val equivalenceRatio = ObdDecoder.parse(sendCommand(ObdCommand.EQUIVALENCE_RATIO.pid), ObdCommand.EQUIVALENCE_RATIO) ?: 0.0
        val acceleratorPedalPos = ObdDecoder.parse(sendCommand(ObdCommand.ACCELERATOR_PEDAL_POS_D.pid), ObdCommand.ACCELERATOR_PEDAL_POS_D) ?: 0.0
        val runTime = ObdDecoder.parse(sendCommand(ObdCommand.RUN_TIME.pid), ObdCommand.RUN_TIME) ?: 0.0
        val warmups = ObdDecoder.parse(sendCommand(ObdCommand.WARMUPS_SINCE_CODES_CLEARED.pid), ObdCommand.WARMUPS_SINCE_CODES_CLEARED)?.toInt() ?: 0
        val timeSinceCleared = ObdDecoder.parse(sendCommand(ObdCommand.TIME_SINCE_CODES_CLEARED.pid), ObdCommand.TIME_SINCE_CODES_CLEARED) ?: 0.0

        return VehicleData(
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
    }

    /**
     * One-shot demo request: requestVehicleData() + raw hex logging
     * Returns a debug string showing each PID's raw hex response and decoded value.
     * Useful for verifying ObdDecoder correctness at a glance.
     */
    fun requestVehicleDataWithDebug(): Pair<VehicleData?, String> {
        updateState()
        val commands = listOf(
            ObdCommand.ENGINE_LOAD, ObdCommand.COOLANT_TEMP, ObdCommand.RPM,
            ObdCommand.SPEED, ObdCommand.INTAKE_MANIFOLD_PRESSURE, ObdCommand.INTAKE_TEMP,
            ObdCommand.MAF_RATE, ObdCommand.FUEL_PRESSURE, ObdCommand.FUEL_LEVEL,
            ObdCommand.SHORT_TERM_FUEL_TRIM_BANK1, ObdCommand.LONG_TERM_FUEL_TRIM_BANK1,
            ObdCommand.SHORT_TERM_FUEL_TRIM_BANK2, ObdCommand.LONG_TERM_FUEL_TRIM_BANK2,
            ObdCommand.TIMING_ADVANCE, ObdCommand.THROTTLE_POS, ObdCommand.BATTERY_VOLTAGE,
            ObdCommand.ACCELERATOR_PEDAL_POS_D, ObdCommand.EQUIVALENCE_RATIO,
            ObdCommand.RUN_TIME, ObdCommand.WARMUPS_SINCE_CODES_CLEARED,
            ObdCommand.TIME_SINCE_CODES_CLEARED
        )

        val sb = StringBuilder("=== Simulated OBD2 Decode Test ===\n")
        for (cmd in commands) {
            val raw = sendCommand(cmd.pid)
            val decoded = ObdDecoder.parse(raw, cmd)
            sb.appendLine("${cmd.pid}  ${cmd.displayName}")
            sb.appendLine("  raw:     $raw")
            sb.appendLine("  decoded: $decoded ${cmd.unit}")
            sb.appendLine()
        }
        val data = requestVehicleData()
        return Pair(data, sb.toString())
    }

    /**
     * Generate response data bytes for a given PID
     */
    private fun generateResponse(pidBytes: String): String? {
        return when (pidBytes) {
            // 0104 - Engine Load
            "04" -> {
                val byte = (currentEngineLoad * 255.0 / 100.0).toInt().coerceIn(0, 255)
                String.format("%02X", byte)
            }
            // 0105 - Coolant Temperature
            "05" -> {
                val byte = (currentCoolantTemp + 40).coerceIn(0, 255)
                String.format("%02X", byte)
            }
            // 010C - RPM (2 bytes)
            "0C" -> {
                val rpmValue = (currentRpm * 4).coerceIn(0, 16383)
                val byte1 = (rpmValue / 256).toInt()
                val byte2 = (rpmValue % 256)
                String.format("%02X%02X", byte1, byte2)
            }
            // 010D - Speed
            "0D" -> {
                String.format("%02X", currentSpeed.coerceIn(0, 255))
            }
            // 010B - Intake Manifold Pressure
            "0B" -> {
                String.format("%02X", currentIntakeManifoldPressure.toInt().coerceIn(0, 255))
            }
            // 010F - Intake Temperature
            "0F" -> {
                val byte = (currentIntakeTemp + 40).coerceIn(0, 255)
                String.format("%02X", byte)
            }
            // 0110 - MAF Rate (2 bytes)
            "10" -> {
                val mafValue = (currentMafRate * 100).toInt().coerceIn(0, 65535)
                val byte1 = (mafValue / 256)
                val byte2 = (mafValue % 256)
                String.format("%02X%02X", byte1, byte2)
            }
            // 010A - Fuel Pressure
            "0A" -> {
                val byte = (currentFuelPressure / 3.0).toInt().coerceIn(0, 255)
                String.format("%02X", byte)
            }
            // 012F - Fuel Level
            "2F" -> {
                val byte = (currentFuelLevel * 255.0 / 100.0).toInt().coerceIn(0, 255)
                String.format("%02X", byte)
            }
            // 0106 - Short Term Fuel Trim Bank 1
            "06" -> {
                val byte = ((currentStft1 * 128.0 / 100.0) + 128).toInt().coerceIn(0, 255)
                String.format("%02X", byte)
            }
            // 0107 - Long Term Fuel Trim Bank 1
            "07" -> {
                val byte = ((currentLtft1 * 128.0 / 100.0) + 128).toInt().coerceIn(0, 255)
                String.format("%02X", byte)
            }
            // 0108 - Short Term Fuel Trim Bank 2
            "08" -> {
                val byte = ((currentStft2 * 128.0 / 100.0) + 128).toInt().coerceIn(0, 255)
                String.format("%02X", byte)
            }
            // 0109 - Long Term Fuel Trim Bank 2
            "09" -> {
                val byte = ((currentLtft2 * 128.0 / 100.0) + 128).toInt().coerceIn(0, 255)
                String.format("%02X", byte)
            }
            // 010E - Timing Advance
            "0E" -> {
                val byte = ((currentTimingAdvance + 64) * 2).toInt().coerceIn(0, 255)
                String.format("%02X", byte)
            }
            // 0111 - Throttle Position
            "11" -> {
                val byte = (currentThrottlePos * 255.0 / 100.0).toInt().coerceIn(0, 255)
                String.format("%02X", byte)
            }
            // 012C - Accelerator Pedal Position D
            "2C" -> {
                val byte = (currentAcceleratorPedalPos * 255.0 / 100.0).toInt().coerceIn(0, 255)
                String.format("%02X", byte)
            }
            // 0142 - Battery Voltage (2 bytes)
            "42" -> {
                val voltValue = (currentBatteryVoltage * 1000).toInt().coerceIn(0, 65535)
                val byte1 = (voltValue / 256)
                val byte2 = (voltValue % 256)
                String.format("%02X%02X", byte1, byte2)
            }
            // 011F - Engine Run Time (2 bytes)
            "1F" -> {
                val timeValue = currentRunTime.toInt().coerceIn(0, 65535)
                val byte1 = (timeValue / 256)
                val byte2 = (timeValue % 256)
                String.format("%02X%02X", byte1, byte2)
            }
            // 0131 - Warm-ups Since DTC Cleared (2 bytes)
            "31" -> {
                val byte1 = 0
                val byte2 = 15 // 15 warm-ups
                String.format("%02X%02X", byte1, byte2)
            }
            // 0133 - Time Since DTC Cleared (2 bytes)
            "33" -> {
                val minutes = 120 // 2 hours
                val byte1 = (minutes / 256)
                val byte2 = (minutes % 256)
                String.format("%02X%02X", byte1, byte2)
            }
            // 0124 - Equivalence Ratio (Lambda) (2 bytes)
            "24" -> {
                val lambdaValue = (currentEquivalenceRatio * 32768).toInt().coerceIn(0, 65535)
                val byte1 = (lambdaValue / 256)
                val byte2 = (lambdaValue % 256)
                String.format("%02X%02X", byte1, byte2)
            }
            else -> null
        }
    }

    /**
     * Get current vehicle state as VehicleData
     */
    fun getCurrentVehicleData(): com.example.myapplication.data.local.VehicleData {
        return com.example.myapplication.data.local.VehicleData(
            timestamp = System.currentTimeMillis(),
            rpm = currentRpm,
            coolantTemp = currentCoolantTemp,
            intakeTemp = currentIntakeTemp,
            throttlePos = currentThrottlePos,
            batteryVoltage = currentBatteryVoltage,
            engineLoad = currentEngineLoad,
            speed = currentSpeed,
            intakeManifoldPressure = currentIntakeManifoldPressure,
            mafRate = currentMafRate,
            fuelPressure = currentFuelPressure,
            fuelLevel = currentFuelLevel,
            shortTermFuelTrimBank1 = currentStft1,
            longTermFuelTrimBank1 = currentLtft1,
            shortTermFuelTrimBank2 = currentStft2,
            longTermFuelTrimBank2 = currentLtft2,
            timingAdvance = currentTimingAdvance,
            equivalenceRatio = currentEquivalenceRatio,
            acceleratorPedalPos = currentAcceleratorPedalPos,
            runTime = currentRunTime.toDouble(),
            warmupsSinceCodesCleared = 15,
            timeSinceCodesCleared = 120.0
        )
    }

    /**
     * Reset session
     */
    fun resetSession() {
        sessionStartTime = System.currentTimeMillis()
        currentRpm = 850
        currentCoolantTemp = 90
        currentRunTime = 0
    }

    /**
     * Randomly change simulation mode (for automatic demo)
     */
    fun autoChangeMode() {
        simulationMode = when (Random.nextInt(5)) {
            0 -> SimulationMode.IDLE
            1 -> SimulationMode.DRIVING
            2 -> SimulationMode.ACCELERATING
            3 -> SimulationMode.HIGH_RPM
            else -> SimulationMode.DECELERATING
        }
    }

    /**
     * Start a simulated data stream using raw OBD2 commands
     * This mimics a real OBD2 connection by sending PIDs and parsing responses
     * @return Flow of VehicleData
     */
    fun startSimulation(): Flow<VehicleData> = flow {
        sessionStartTime = System.currentTimeMillis()

        // Core PIDs for real-time monitoring
        val corePids = listOf(
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
            ObdCommand.TIMING_ADVANCE,
            ObdCommand.EQUIVALENCE_RATIO,
            ObdCommand.ACCELERATOR_PEDAL_POS_D,
            ObdCommand.RUN_TIME
        )

        while (true) {
            // Auto change mode occasionally
            if (Random.nextInt(100) < 30) {
                autoChangeMode()
            }

            // Collect data using raw OBD2 commands
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
            var timingAdvance = 0.0
            var equivalenceRatio = 0.0
            var acceleratorPedalPos = 0.0
            var runTime = 0.0

            // Send each PID and parse response using ObdDecoder
            for (command in corePids) {
                val response = sendCommand(command.pid)
                val parsed = ObdDecoder.parse(response, command)

                when (command) {
                    ObdCommand.RPM -> rpm = parsed?.toInt() ?: 0
                    ObdCommand.COOLANT_TEMP -> coolantTemp = parsed?.toInt() ?: 0
                    ObdCommand.INTAKE_TEMP -> intakeTemp = parsed?.toInt() ?: 0
                    ObdCommand.THROTTLE_POS -> throttlePos = parsed?.toInt() ?: 0
                    ObdCommand.BATTERY_VOLTAGE -> batteryVoltage = parsed ?: 0.0
                    ObdCommand.ENGINE_LOAD -> engineLoad = parsed ?: 0.0
                    ObdCommand.SPEED -> speed = parsed?.toInt() ?: 0
                    ObdCommand.INTAKE_MANIFOLD_PRESSURE -> intakeManifoldPressure = parsed ?: 0.0
                    ObdCommand.MAF_RATE -> mafRate = parsed ?: 0.0
                    ObdCommand.FUEL_PRESSURE -> fuelPressure = parsed ?: 0.0
                    ObdCommand.FUEL_LEVEL -> fuelLevel = parsed ?: 0.0
                    ObdCommand.SHORT_TERM_FUEL_TRIM_BANK1 -> stft1 = parsed ?: 0.0
                    ObdCommand.LONG_TERM_FUEL_TRIM_BANK1 -> ltft1 = parsed ?: 0.0
                    ObdCommand.TIMING_ADVANCE -> timingAdvance = parsed ?: 0.0
                    ObdCommand.EQUIVALENCE_RATIO -> equivalenceRatio = parsed ?: 0.0
                    ObdCommand.ACCELERATOR_PEDAL_POS_D -> acceleratorPedalPos = parsed ?: 0.0
                    ObdCommand.RUN_TIME -> runTime = parsed ?: 0.0
                    else -> {}
                }
            }

            // Create VehicleData from parsed values
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
                shortTermFuelTrimBank2 = 0.0,
                longTermFuelTrimBank2 = 0.0,
                timingAdvance = timingAdvance,
                equivalenceRatio = equivalenceRatio,
                acceleratorPedalPos = acceleratorPedalPos,
                runTime = runTime,
                warmupsSinceCodesCleared = 15,
                timeSinceCodesCleared = 120.0
            )

            emit(data)
            delay(500) // 500ms sampling rate
        }
    }

    /**
     * Stop simulation (placeholder for future use)
     */
    fun stopSimulation() {
        // Could be used to clean up resources
    }
}
