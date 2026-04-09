package com.example.myapplication.ui.connection

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.BluetoothDevice
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.myapplication.MyApplication
import com.example.myapplication.R
import com.example.myapplication.databinding.ActivityConnectionBinding
import com.example.myapplication.ui.adapter.DeviceAdapter
import com.example.myapplication.ui.dashboard.DashboardActivity
import com.example.myapplication.utils.SignalStrength
import kotlinx.coroutines.launch

class ConnectionActivity : AppCompatActivity() {

    private lateinit var binding: ActivityConnectionBinding
    private var deviceAdapter: DeviceAdapter? = null

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val allGranted = permissions.entries.all { it.value }
        if (allGranted) {
            scanDevices()
        } else {
            Toast.makeText(this, "Permission denied", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityConnectionBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Setup toolbar
        binding.btnBack.setOnClickListener { finish() }
        binding.btnRefresh.setOnClickListener { scanDevices() }

        // Setup RecyclerView
        setupDeviceList()

        // Setup scan button
        binding.btnScan.setOnClickListener { scanDevices() }

        // Setup bottom navigation
        binding.bottomNavigation.selectedItemId = R.id.nav_connection
        binding.bottomNavigation.setOnItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_home -> {
                    startActivity(Intent(this, com.example.myapplication.MainActivity::class.java))
                    true
                }
                R.id.nav_connection -> true
                R.id.nav_history -> {
                    startActivity(Intent(this, com.example.myapplication.ui.history.HistoryActivity::class.java))
                    true
                }
                else -> false
            }
        }

        // Initial scan
        if (checkPermissions()) {
            scanDevices()
        } else {
            requestPermissions()
        }
    }

    private fun setupDeviceList() {
        deviceAdapter = DeviceAdapter { device ->
            connectToDevice(device)
        }

        binding.recyclerDevices.apply {
            layoutManager = LinearLayoutManager(this@ConnectionActivity)
            adapter = deviceAdapter
        }
    }

    @SuppressLint("MissingPermission")
    private fun scanDevices() {
        if (!checkPermissions()) {
            requestPermissions()
            return
        }

        binding.tvStatus.text = "Scanning..."
        binding.progressBar.visibility = View.VISIBLE

        val pairedDevices = (application as MyApplication)
            .bluetoothManager
            .getPairedDevices()

        binding.progressBar.visibility = View.GONE

        if (pairedDevices.isEmpty()) {
            binding.recyclerDevices.visibility = View.GONE
            binding.btnScan.visibility = View.VISIBLE
            binding.tvStatus.text = "No paired devices found. Please pair your device in Bluetooth settings."
        } else {
            binding.btnScan.visibility = View.GONE
            binding.recyclerDevices.visibility = View.VISIBLE

            val devices = pairedDevices.map { device ->
                DeviceAdapter.DeviceItem(
                    device = device,
                    isPaired = true,
                    signalStrength = estimateSignalStrength(device)
                )
            }

            deviceAdapter?.submitList(devices)
            binding.tvStatus.text = "Found ${pairedDevices.size} paired device(s)"
            
            // Show hint about OBD2 requirement
            if (pairedDevices.none { it.name?.contains("OBD", true) == true }) {
                Toast.makeText(
                    this, 
                    "💡 Tip: For best experience, use an OBD2 Bluetooth adapter (ELM327)", 
                    Toast.LENGTH_LONG
                ).show()
            }
        }
    }

    @SuppressLint("MissingPermission")
    private fun connectToDevice(device: BluetoothDevice) {
        lifecycleScope.launch {
            binding.tvStatus.text = "Connecting to ${device.name}..."
            binding.progressBar.visibility = View.VISIBLE
            binding.btnScan.isEnabled = false

            val repository = (application as MyApplication).repository
            val connected = repository.connectToDevice(device)

            binding.progressBar.visibility = View.GONE
            binding.btnScan.isEnabled = true

            if (connected) {
                Toast.makeText(this@ConnectionActivity, "Connected to ${device.name}", Toast.LENGTH_SHORT).show()
                
                // Navigate to dashboard
                val intent = Intent(this@ConnectionActivity, DashboardActivity::class.java)
                startActivity(intent)
                finish()
            } else {
                Toast.makeText(this@ConnectionActivity, "Connection failed", Toast.LENGTH_SHORT).show()
                binding.tvStatus.text = "Connection failed. Try again."
            }
        }
    }

    private fun checkPermissions(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_SCAN) == PackageManager.PERMISSION_GRANTED &&
                    ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_CONNECT) == PackageManager.PERMISSION_GRANTED
        } else {
            ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH) == PackageManager.PERMISSION_GRANTED &&
                    ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_ADMIN) == PackageManager.PERMISSION_GRANTED &&
                    ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
        }
    }

    private fun requestPermissions() {
        val permissions = mutableListOf(
            Manifest.permission.BLUETOOTH_SCAN,
            Manifest.permission.BLUETOOTH_CONNECT,
            Manifest.permission.ACCESS_FINE_LOCATION
        )
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            permissions.remove(Manifest.permission.ACCESS_FINE_LOCATION)
        }
        requestPermissionLauncher.launch(permissions.toTypedArray())
    }

    @SuppressLint("MissingPermission")
    private fun estimateSignalStrength(device: BluetoothDevice): SignalStrength {
        // Simplified: in production, you'd use RSSI from Bluetooth scan results
        return SignalStrength.GOOD
    }
}
