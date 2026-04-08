package com.example.myapplication.ui.dashboard

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.myapplication.MyApplication
import com.example.myapplication.R
import com.example.myapplication.data.local.VehicleData
import com.example.myapplication.databinding.DashboardBinding
import com.github.mikephil.charting.charts.LineChart
import com.github.mikephil.charting.components.XAxis
import com.github.mikephil.charting.data.Entry
import com.github.mikephil.charting.data.LineData
import com.github.mikephil.charting.data.LineDataSet
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

class DashboardActivity : AppCompatActivity() {

    private lateinit var binding: DashboardBinding
    private val repository by lazy { (application as MyApplication).repository }
    private val rpmEntries = mutableListOf<Entry>()
    private var xIndex = 0
    private val timeFormat = SimpleDateFormat("HH:mm:ss", Locale.getDefault())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = DashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Setup toolbar
        binding.btnExport.setOnClickListener {
            // TODO: Export current data
        }

        // Setup chart
        setupChart()

        // Observe data
        observeData()

        // Setup bottom navigation
        binding.bottomNavigation.selectedItemId = R.id.nav_home
        binding.bottomNavigation.setOnItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_home -> {
                    startActivity(Intent(this, com.example.myapplication.MainActivity::class.java))
                    true
                }
                R.id.nav_connection -> {
                    startActivity(Intent(this, com.example.myapplication.ui.connection.ConnectionActivity::class.java))
                    true
                }
                R.id.nav_history -> {
                    startActivity(Intent(this, com.example.myapplication.ui.history.HistoryActivity::class.java))
                    true
                }
                else -> false
            }
        }
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
            xAxis.textColor = resources.getColor(R.color.text_secondary, null)

            axisLeft.setDrawGridLines(true)
            axisLeft.textColor = resources.getColor(R.color.text_secondary, null)
            axisRight.isEnabled = false
            legend.isEnabled = false
            
            setNoDataText("Waiting for data...")
            setNoDataTextColor(resources.getColor(R.color.text_secondary, null))
        }
    }

    private fun observeData() {
        lifecycleScope.launch {
            repository.startLiveDataStream().collect { data ->
                updateUI(data)
                updateChart(data)
            }
        }
    }

    private fun updateUI(data: VehicleData) {
        binding.tvRpm.text = data.rpm.toString()
        binding.tvCoolantTemp.text = "${data.coolantTemp} °C"
        binding.tvIntakeTemp.text = "${data.intakeTemp} °C"
        binding.tvThrottle.text = "${data.throttlePos} %"
        binding.tvBattery.text = "${String.format("%.2f", data.batteryVoltage)} V"
        binding.tvSpeed.text = "${calculateSpeed(data.rpm)} km/h"
        
        // Update timestamp
        binding.tvTimestamp.text = "Live • ${timeFormat.format(Date(data.timestamp))}"
    }

    private fun updateChart(data: VehicleData) {
        rpmEntries.add(Entry(xIndex.toFloat(), data.rpm.toFloat()))
        xIndex++

        // Keep last 60 points (30 seconds at 500ms interval)
        if (rpmEntries.size > 60) {
            rpmEntries.removeAt(0)
            // Re-index x values for smooth scrolling
            for (i in rpmEntries.indices) {
                rpmEntries[i] = Entry(i.toFloat(), rpmEntries[i].y)
            }
            xIndex = rpmEntries.size
        }

        val dataSet = LineDataSet(rpmEntries, "RPM").apply {
            color = resources.getColor(R.color.accent, null)
            setCircleColor(resources.getColor(R.color.accent, null))
            lineWidth = 2f
            circleRadius = 3f
            setDrawCircleHole(false)
            setDrawValues(false)
            setDrawFilled(true)
            fillColor = resources.getColor(R.color.accent_light, null)
            fillAlpha = 50
        }

        binding.lineChart.data = LineData(dataSet)
        binding.lineChart.notifyDataSetChanged()
        binding.lineChart.invalidate()
    }

    private fun calculateSpeed(rpm: Int): Int {
        // Simplified speed calculation (actual would need gear ratio, wheel size, etc.)
        return (rpm * 0.03).toInt()
    }
}
