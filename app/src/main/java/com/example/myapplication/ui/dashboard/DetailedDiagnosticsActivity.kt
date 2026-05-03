package com.example.myapplication.ui.dashboard

import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.myapplication.MyApplication
import com.example.myapplication.R
import com.example.myapplication.data.local.DriveSession
import com.example.myapplication.data.local.VehicleData
import com.example.myapplication.databinding.ActivityDetailedDiagnosticsBinding
import com.example.myapplication.utils.SimulatedOBD2Manager
import com.github.mikephil.charting.components.XAxis
import com.github.mikephil.charting.data.Entry
import com.github.mikephil.charting.data.LineData
import com.github.mikephil.charting.data.LineDataSet
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

/**
 * 详细诊断仪表板
 * 显示所有扩展 OBD2 参数，用于深度车辆诊断
 */
class DetailedDiagnosticsActivity : AppCompatActivity() {

    private lateinit var binding: ActivityDetailedDiagnosticsBinding
    private val repository by lazy { (application as MyApplication).repository }
    private val rpmEntries = mutableListOf<Entry>()
    private val stftEntries = mutableListOf<Entry>()  // 短期燃油修正
    private val ltftEntries = mutableListOf<Entry>()  // 长期燃油修正
    private var xIndex = 0
    private var isSimulationMode = false
    private var sessionOpened = false
    private val timeFormat = SimpleDateFormat("HH:mm:ss", Locale.getDefault())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDetailedDiagnosticsBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Setup toolbar
        binding.btnBack.setOnClickListener { finish() }

        isSimulationMode = intent.getBooleanExtra("simulation_mode", false)
        if (isSimulationMode) {
            binding.tvTitle.text = "Detailed Diagnostics • Demo"
            Toast.makeText(this, "Detailed diagnostics in demo mode", Toast.LENGTH_SHORT).show()
        }

        lifecycleScope.launch {
            val source = if (isSimulationMode) DriveSession.SOURCE_DEMO else DriveSession.SOURCE_REAL
            repository.startSession(
                sourceType = source,
                title = if (isSimulationMode) "Detailed Demo Session" else "Detailed Live Session"
            )
            sessionOpened = true
        }

        // Setup charts
        setupRpmChart()
        setupFuelTrimChart()

        // Observe data
        observeData()
    }

    private fun setupRpmChart() {
        binding.chartRpm.apply {
            description.isEnabled = false
            setTouchEnabled(true)
            isDragEnabled = true
            setScaleEnabled(true)
            setPinchZoom(true)

            xAxis.position = XAxis.XAxisPosition.BOTTOM
            xAxis.setDrawGridLines(false)
            xAxis.granularity = 1f
            xAxis.textColor = resources.getColor(R.color.text_secondary, null)

            axisLeft.setDrawGridLines(true)
            axisLeft.textColor = resources.getColor(R.color.text_secondary, null)
            axisRight.isEnabled = false
            legend.isEnabled = false
            
            setNoDataText("Waiting for data...")
            setNoDataTextColor(resources.getColor(R.color.text_secondary, null))
        }
    }

    private fun setupFuelTrimChart() {
        binding.chartFuelTrim.apply {
            description.isEnabled = false
            setTouchEnabled(true)
            isDragEnabled = true
            setScaleEnabled(true)
            setPinchZoom(true)

            xAxis.position = XAxis.XAxisPosition.BOTTOM
            xAxis.setDrawGridLines(false)
            xAxis.granularity = 1f
            xAxis.textColor = resources.getColor(R.color.text_secondary, null)

            axisLeft.setDrawGridLines(true)
            axisLeft.textColor = resources.getColor(R.color.text_secondary, null)
            axisLeft.axisMinimum = -100f
            axisLeft.axisMaximum = 100f
            axisRight.isEnabled = false
            legend.isEnabled = true
            
            // 添加零线参考
            setDrawGridBackground(false)
            
            setNoDataText("Waiting for data...")
            setNoDataTextColor(resources.getColor(R.color.text_secondary, null))
        }
    }

    private fun observeData() {
        lifecycleScope.launch {
            val dataFlow = if (isSimulationMode) {
                SimulatedOBD2Manager.setMode(SimulatedOBD2Manager.SimulationMode.IDLE)
                SimulatedOBD2Manager.startSimulation()
            } else {
                repository.startLiveDataStream(sourceType = DriveSession.SOURCE_REAL)
            }

            dataFlow.collect { data ->
                if (isSimulationMode) {
                    repository.saveVehicleData(data.copy(sourceType = DriveSession.SOURCE_DEMO))
                }
                updateUI(data)
                updateCharts(data)
            }
        }
    }

    private fun updateUI(data: VehicleData) {
        // 核心参数
        binding.tvRpm.text = data.rpm.toString()
        binding.tvCoolantTemp.text = "${data.coolantTemp} °C"
        binding.tvIntakeTemp.text = "${data.intakeTemp} °C"
        binding.tvBattery.text = "${String.format("%.2f", data.batteryVoltage)} V"
        
        // 扩展诊断参数
        binding.tvEngineLoad.text = "${String.format("%.1f", data.engineLoad)} %"
        binding.tvSpeed.text = "${data.speed} km/h"
        binding.tvMap.text = "${String.format("%.1f", data.intakeManifoldPressure)} kPa"
        binding.tvMaf.text = "${String.format("%.2f", data.mafRate)} g/s"
        binding.tvFuelPressure.text = "${String.format("%.1f", data.fuelPressure)} kPa"
        binding.tvFuelLevel.text = "${String.format("%.1f", data.fuelLevel)} %"
        
        // 燃油修正 (关键诊断参数)
        binding.tvStft1.text = "${String.format("%.1f", data.shortTermFuelTrimBank1)} %"
        binding.tvLtft1.text = "${String.format("%.1f", data.longTermFuelTrimBank1)} %"
        binding.tvStft2.text = "${String.format("%.1f", data.shortTermFuelTrimBank2)} %"
        binding.tvLtft2.text = "${String.format("%.1f", data.longTermFuelTrimBank2)} %"
        
        // 点火和空燃比
        binding.tvTimingAdvance.text = "${String.format("%.1f", data.timingAdvance)} °"
        binding.tvLambda.text = "${String.format("%.3f", data.equivalenceRatio)} λ"
        binding.tvThrottle.text = "${data.throttlePos} %"
        binding.tvPedalPos.text = "${String.format("%.1f", data.acceleratorPedalPos)} %"
        
        // 状态信息
        binding.tvRunTime.text = formatRunTime(data.runTime)
        binding.tvWarmups.text = data.warmupsSinceCodesCleared.toString()
        binding.tvTimestamp.text = "Live • ${timeFormat.format(Date(data.timestamp))}"
        
        // 燃油修正状态指示
        updateFuelTrimStatus(data)
    }

    private fun updateFuelTrimStatus(data: VehicleData) {
        // 燃油修正正常范围：±10% 以内为良好
        val stft1 = data.shortTermFuelTrimBank1
        val ltft1 = data.longTermFuelTrimBank1
        
        when {
            kotlin.math.abs(stft1) < 10 && kotlin.math.abs(ltft1) < 10 -> {
                binding.tvFuelTrimStatus.text = "✓ Normal"
                binding.tvFuelTrimStatus.setTextColor(resources.getColor(R.color.success, null))
            }
            kotlin.math.abs(stft1) < 20 && kotlin.math.abs(ltft1) < 20 -> {
                binding.tvFuelTrimStatus.text = "⚠ Check"
                binding.tvFuelTrimStatus.setTextColor(resources.getColor(R.color.warning, null))
            }
            else -> {
                binding.tvFuelTrimStatus.text = "✗ Fault"
                binding.tvFuelTrimStatus.setTextColor(resources.getColor(R.color.error, null))
            }
        }
    }

    private fun updateCharts(data: VehicleData) {
        // RPM 图表
        rpmEntries.add(Entry(xIndex.toFloat(), data.rpm.toFloat()))
        
        // 燃油修正图表
        stftEntries.add(Entry(xIndex.toFloat(), data.shortTermFuelTrimBank1.toFloat()))
        ltftEntries.add(Entry(xIndex.toFloat(), data.longTermFuelTrimBank1.toFloat()))
        
        xIndex++

        // 保持最近 60 个点 (30 秒)
        if (rpmEntries.size > 60) {
            listOf(rpmEntries, stftEntries, ltftEntries).forEach { entries ->
                entries.removeAt(0)
                for (i in entries.indices) {
                    entries[i] = Entry(i.toFloat(), entries[i].y)
                }
            }
            xIndex = rpmEntries.size
        }

        // 更新 RPM 图表
        val rpmDataSet = LineDataSet(rpmEntries, "RPM").apply {
            color = resources.getColor(R.color.accent, null)
            setCircleColor(resources.getColor(R.color.accent, null))
            lineWidth = 2f
            circleRadius = 3f
            setDrawCircleHole(false)
            setDrawValues(false)
        }
        binding.chartRpm.data = LineData(rpmDataSet)
        binding.chartRpm.notifyDataSetChanged()
        binding.chartRpm.invalidate()

        // 更新燃油修正图表
        val stftDataSet = LineDataSet(stftEntries, "STFT").apply {
            color = resources.getColor(R.color.info, null)
            setCircleColor(resources.getColor(R.color.info, null))
            lineWidth = 2f
            circleRadius = 2f
            setDrawCircleHole(false)
            setDrawValues(false)
        }
        
        val ltftDataSet = LineDataSet(ltftEntries, "LTFT").apply {
            color = resources.getColor(R.color.warning, null)
            setCircleColor(resources.getColor(R.color.warning, null))
            lineWidth = 2f
            circleRadius = 2f
            setDrawCircleHole(false)
            setDrawValues(false)
        }
        
        binding.chartFuelTrim.data = LineData(stftDataSet, ltftDataSet)
        binding.chartFuelTrim.notifyDataSetChanged()
        binding.chartFuelTrim.invalidate()
    }

    private fun formatRunTime(seconds: Double): String {
        val hours = (seconds / 3600).toInt()
        val minutes = ((seconds % 3600) / 60).toInt()
        val secs = (seconds % 60).toInt()
        return String.format("%02d:%02d:%02d", hours, minutes, secs)
    }

    override fun onDestroy() {
        super.onDestroy()
        lifecycleScope.launch {
            if (sessionOpened) {
                repository.endActiveSession()
            }
        }
        if (isSimulationMode) {
            SimulatedOBD2Manager.stopSimulation()
        }
    }
}
