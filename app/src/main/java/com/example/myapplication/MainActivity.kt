package com.example.myapplication

import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.animation.AnimationUtils
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.example.myapplication.R
import com.example.myapplication.databinding.ActivityMainBinding
import com.example.myapplication.ui.connection.ConnectionActivity
import com.example.myapplication.ui.history.HistoryActivity
import java.text.SimpleDateFormat
import java.util.*

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private var bluetoothAdapter: BluetoothAdapter? = null
    private val handler = Handler(Looper.getMainLooper())
    private val timeFormat = SimpleDateFormat("HH:mm", Locale.getDefault())
    private var isConnected = false

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val allGranted = permissions.entries.all { it.value }
        if (allGranted) {
            initializeBluetooth()
        } else {
            Toast.makeText(this, "Bluetooth permissions required", Toast.LENGTH_SHORT).show()
            updateConnectionStatus(false, "Permissions denied")
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        try {
            binding = ActivityMainBinding.inflate(layoutInflater)
            setContentView(binding.root)

        // Setup card clicks with animation
        setupCardAnimations()

        // Setup bottom navigation
        setupBottomNavigation()

        // Start time update
        startTimeUpdate()

        // Check and request permissions FIRST
        if (checkPermissions()) {
            initializeBluetooth()
        } else {
            requestPermissions()
        }
        } catch (e: Exception) {
            e.printStackTrace()
            Toast.makeText(this, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
        }
    }

    private fun setupCardAnimations() {
        val fadeIn = AnimationUtils.loadAnimation(this, R.anim.fade_in)

        binding.cardConnect.setOnClickListener {
            it.startAnimation(fadeIn)
            if (checkPermissions()) {
                startActivity(Intent(this, ConnectionActivity::class.java))
                overridePendingTransition(R.anim.slide_in_right, R.anim.slide_out_left)
            } else {
                requestPermissions()
            }
        }

        binding.cardHistory.setOnClickListener {
            it.startAnimation(fadeIn)
            startActivity(Intent(this, HistoryActivity::class.java))
            overridePendingTransition(R.anim.slide_in_right, R.anim.slide_out_left)
        }
        
        // Long press for detailed diagnostics
        binding.cardConnect.setOnLongClickListener {
            Toast.makeText(this, "Opening detailed diagnostics...", Toast.LENGTH_SHORT).show()
            startActivity(Intent(this, com.example.myapplication.ui.dashboard.DetailedDiagnosticsActivity::class.java))
            overridePendingTransition(R.anim.slide_in_right, R.anim.slide_out_left)
            true
        }
    }

    private fun setupBottomNavigation() {
        binding.bottomNavigation.selectedItemId = R.id.nav_home
        binding.bottomNavigation.setOnItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_home -> true
                R.id.nav_connection -> {
                    if (checkPermissions()) {
                        startActivity(Intent(this, ConnectionActivity::class.java))
                        overridePendingTransition(R.anim.slide_in_right, R.anim.slide_out_left)
                    } else {
                        requestPermissions()
                    }
                    true
                }
                R.id.nav_history -> {
                    startActivity(Intent(this, HistoryActivity::class.java))
                    overridePendingTransition(R.anim.slide_in_right, R.anim.slide_out_left)
                    true
                }
                else -> false
            }
        }
    }

    private fun startTimeUpdate() {
        handler.post(object : Runnable {
            override fun run() {
                binding.tvCurrentTime.text = timeFormat.format(Date())
                handler.postDelayed(this, 1000)
            }
        })
    }

    private fun initializeBluetooth() {
        try {
            val manager = getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
            bluetoothAdapter = manager.adapter
            checkBluetoothAndShow()
        } catch (e: SecurityException) {
            updateConnectionStatus(false, "Bluetooth access denied")
        }
    }

    private fun checkBluetoothAndShow() {
        try {
            when {
                bluetoothAdapter == null -> {
                    updateConnectionStatus(false, "Bluetooth not supported")
                }
                bluetoothAdapter?.isEnabled == false -> {
                    updateConnectionStatus(false, "Bluetooth is disabled")
                }
                else -> {
                    updateConnectionStatus(false, "Ready to connect")
                }
            }
        } catch (e: SecurityException) {
            updateConnectionStatus(false, "Bluetooth access denied")
        }
    }

    private fun updateConnectionStatus(connected: Boolean, message: String) {
        isConnected = connected
        binding.tvConnectionStatus.text = if (connected) {
            "● Connected"
        } else {
            "● Disconnected"
        }
        binding.tvConnectionStatus.setTextColor(
            if (connected) getColor(R.color.success) else getColor(R.color.text_hint)
        )
        binding.tvStatus.text = message
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
            Manifest.permission.BLUETOOTH_CONNECT
        )
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) {
            permissions.add(Manifest.permission.ACCESS_FINE_LOCATION)
        }
        requestPermissionLauncher.launch(permissions.toTypedArray())
    }

    override fun onResume() {
        super.onResume()
        // Refresh connection status when returning to app
        checkBluetoothAndShow()
    }

    override fun onDestroy() {
        super.onDestroy()
        handler.removeCallbacksAndMessages(null)
    }
}
