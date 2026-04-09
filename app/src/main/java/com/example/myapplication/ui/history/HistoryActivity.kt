package com.example.myapplication.ui.history

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.myapplication.MyApplication
import com.example.myapplication.data.local.VehicleData
import com.example.myapplication.databinding.ActivityHistoryBinding
import com.example.myapplication.ui.adapter.TripAdapter
import com.example.myapplication.utils.FileExporter
import kotlinx.coroutines.launch
import com.example.myapplication.R

class HistoryActivity : AppCompatActivity() {

    private lateinit var binding: ActivityHistoryBinding
    private var tripAdapter: TripAdapter? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityHistoryBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Setup RecyclerView
        setupTripList()

        // Setup export button
        binding.btnExport.setOnClickListener {
            exportData()
        }

        // Setup bottom navigation
        binding.bottomNavigation.selectedItemId = R.id.nav_history
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
                R.id.nav_history -> true
                else -> false
            }
        }

        // Load trip data
        loadTrips()
    }

    private fun setupTripList() {
        tripAdapter = TripAdapter { tripItem ->
            // View details click - show dialog with full details
            showTripDetails(tripItem)
        }

        binding.recyclerTrips.apply {
            layoutManager = LinearLayoutManager(this@HistoryActivity)
            adapter = tripAdapter
        }
    }

    private fun loadTrips() {
        lifecycleScope.launch {
            val repository = (application as MyApplication).repository
            
            repository.getHistory().collect { vehicleDataList: kotlin.collections.List<VehicleData> ->
                if (vehicleDataList.isEmpty()) {
                    // Show empty state
                    binding.recyclerTrips.visibility = View.GONE
                    binding.emptyState.visibility = View.VISIBLE
                } else {
                    // Show trip list
                    binding.emptyState.visibility = View.GONE
                    binding.recyclerTrips.visibility = View.VISIBLE

                    // Convert vehicle data to trip items
                    val tripItems = TripAdapter.createTripItems(vehicleDataList)
                    tripAdapter?.submitList(tripItems)
                }
            }
        }
    }

    private fun showTripDetails(tripItem: TripAdapter.TripItem) {
        val dateFormat = java.text.SimpleDateFormat("MMM d, yyyy HH:mm", java.util.Locale.getDefault())
        // Show dialog with trip details
        androidx.appcompat.app.AlertDialog.Builder(this)
            .setTitle("Trip Details")
            .setMessage(
                "Date: ${java.text.SimpleDateFormat("MMM d, yyyy HH:mm", java.util.Locale.getDefault()).format(java.util.Date(tripItem.date))}\n\n" +
                "Duration: ${tripItem.duration} min\n" +
                "Distance: ${String.format("%.2f", tripItem.distance)} km\n" +
                "Avg Speed: ${String.format("%.1f", tripItem.avgSpeed)} km/h\n" +
                "Max RPM: ${tripItem.maxRpm}"
            )
            .setPositiveButton("OK", null)
            .show()
    }

    private fun exportData() {
        lifecycleScope.launch {
            try {
                val csvFile = FileExporter.exportToCsv(this@HistoryActivity, (application as MyApplication).repository)
                
                // Share the file
                val shareIntent = Intent(Intent.ACTION_SEND).apply {
                    type = "text/csv"
                    putExtra(Intent.EXTRA_STREAM, androidx.core.content.FileProvider.getUriForFile(
                        this@HistoryActivity,
                        "${packageName}.fileprovider",
                        csvFile
                    ))
                    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                }
                
                startActivity(Intent.createChooser(shareIntent, "Export trip data"))
            } catch (e: Exception) {
                Toast.makeText(this@HistoryActivity, "Export failed: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }
}
