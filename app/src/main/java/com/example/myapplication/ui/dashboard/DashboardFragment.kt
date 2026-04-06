package com.example.myapplication.ui.dashboard

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import com.example.myapplication.MyApplication
import com.example.myapplication.R
import com.example.myapplication.data.local.VehicleData
import com.example.myapplication.databinding.ActivityDashboardBinding
import com.github.mikephil.charting.charts.LineChart
import com.github.mikephil.charting.components.XAxis
import com.github.mikephil.charting.data.Entry
import com.github.mikephil.charting.data.LineData
import com.github.mikephil.charting.data.LineDataSet
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

class DashboardFragment : Fragment() {

    private var _binding: ActivityDashboardBinding? = null
    private val binding get() = _binding!!

    private val repository by lazy { (requireActivity().application as MyApplication).repository }
    private val rpmEntries = mutableListOf<Entry>()
    private var xIndex = 0

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = ActivityDashboardBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
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
            xAxis.textColor = resources.getColor(R.color.text_secondary, null)

            axisLeft.setDrawGridLines(true)
            axisLeft.textColor = resources.getColor(R.color.text_secondary, null)
            axisRight.isEnabled = false
            legend.isEnabled = false
            
            setNoDataText("No data")
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
        val timeFormat = SimpleDateFormat("HH:mm:ss", Locale.getDefault())
        binding.tvTimestamp.text = "Live • ${timeFormat.format(Date(data.timestamp))}"
    }

    private fun updateChart(data: VehicleData) {
        rpmEntries.add(Entry(xIndex.toFloat(), data.rpm.toFloat()))
        xIndex++

        if (rpmEntries.size > 60) {
            rpmEntries.removeAt(0)
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

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
