package com.example.myapplication.ui.dashboard

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.myapplication.MyApplication
import com.example.myapplication.R
import com.example.myapplication.data.local.VehicleData
import com.example.myapplication.databinding.ActivityDashboardBinding
import com.github.mikephil.charting.components.XAxis
import com.github.mikephil.charting.data.Entry
import com.github.mikephil.charting.data.LineData
import com.github.mikephil.charting.data.LineDataSet
import kotlinx.coroutines.launch

class DashboardActivity : AppCompatActivity() {

    private lateinit var binding: ActivityDashboardBinding

    // 通过 Application 获取全局 Repository
    private val repository by lazy { (application as MyApplication).repository }

    // 用于存储最近60个RPM数据点（30秒 @ 500ms）
    private val rpmEntries = mutableListOf<Entry>()
    private var xIndex = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setupChart()
        observeData()
    }

    private fun setupChart() {
        binding.lineChart.apply {
            description.isEnabled = false
            setTouchEnabled(true)
            isDragEnabled = true
            setScaleEnabled(true)
            setPinchZoom(true)

            xAxis.position = XAxis.XAxisPosition.BOTTOM
            xAxis.setDrawGridLines(false)
            xAxis.granularity = 1f

            axisLeft.setDrawGridLines(true)
            axisRight.isEnabled = false
            legend.isEnabled = false
        }
    }

    private fun observeData() {
        lifecycleScope.launch {
            // 从仓库获取实时数据流
            repository.startLiveDataStream().collect { data ->
                updateUI(data)
                updateChart(data)
            }
        }
    }

    private fun updateUI(data: VehicleData) {
        binding.tvRpm.text = "RPM: ${data.rpm}"
        binding.tvCoolantTemp.text = "水温: ${data.coolantTemp} °C"
        binding.tvIntakeTemp.text = "进气温度: ${data.intakeTemp} °C"
        binding.tvThrottle.text = "节气门: ${data.throttlePos} %"
        binding.tvBattery.text = "电池电压: ${data.batteryVoltage} V"
    }

    private fun updateChart(data: VehicleData) {
        // 添加新数据点
        rpmEntries.add(Entry(xIndex.toFloat(), data.rpm.toFloat()))
        xIndex++

        // 保持最近60个点
        if (rpmEntries.size > 60) {
            rpmEntries.removeAt(0)
            // 重新索引x值，使图表平滑滚动
            for (i in rpmEntries.indices) {
                rpmEntries[i] = Entry(i.toFloat(), rpmEntries[i].y)
            }
            xIndex = rpmEntries.size
        }

        val dataSet = LineDataSet(rpmEntries, "RPM").apply {
            color = resources.getColor(android.R.color.holo_blue_dark, theme)
            setCircleColor(resources.getColor(android.R.color.holo_blue_dark, theme))
            lineWidth = 2f
            circleRadius = 3f
            setDrawCircleHole(false)
            setDrawValues(false)
        }

        binding.lineChart.data = LineData(dataSet)
        binding.lineChart.notifyDataSetChanged()
        binding.lineChart.invalidate()
    }
}