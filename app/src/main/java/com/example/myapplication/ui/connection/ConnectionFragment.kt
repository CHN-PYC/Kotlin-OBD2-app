package com.example.myapplication.ui.connection

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.myapplication.MyApplication
import com.example.myapplication.R
import com.example.myapplication.databinding.ActivityConnectionBinding
import com.example.myapplication.ui.adapter.DeviceAdapter
import com.example.myapplication.utils.SignalStrength
import kotlinx.coroutines.launch

class ConnectionFragment : Fragment() {

    private var _binding: ActivityConnectionBinding? = null
    private val binding get() = _binding!!

    private var bluetoothAdapter: BluetoothAdapter? = null
    private var deviceAdapter: DeviceAdapter? = null
    private var connectedDevice: BluetoothDevice? = null

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val allGranted = permissions.entries.all { it.value }
        if (allGranted) {
            scanDevices()
        } else {
            Toast.makeText(requireContext(), "Permission denied", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = ActivityConnectionBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // Initialize Bluetooth
        val manager = requireContext().getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
        bluetoothAdapter = manager.adapter

        // Setup RecyclerView
        setupDeviceList()

        // Setup buttons
        binding.btnRefresh.setOnClickListener { scanDevices() }
        binding.btnScan.setOnClickListener { scanDevices() }
        binding.btnDisconnect.setOnClickListener { disconnectDevice() }

        // Initial scan
        scanDevices()
    }

    private fun setupDeviceList() {
        deviceAdapter = DeviceAdapter { device ->
            connectToDevice(device)
        }

        binding.recyclerDevices.apply {
            layoutManager = LinearLayoutManager(requireContext())
            adapter = deviceAdapter
        }
    }

    @SuppressLint("MissingPermission")
    private fun scanDevices() {
        if (!checkPermissions()) {
            requestPermissions()
            return
        }

        binding.tvHeader.text = "Scanning..."
        val pairedDevices = bluetoothAdapter?.bondedDevices ?: emptySet()

        if (pairedDevices.isEmpty()) {
            binding.recyclerDevices.visibility = View.GONE
            binding.btnScan.visibility = View.VISIBLE
            binding.tvAvailableTitle.text = "No paired devices found"
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
            binding.tvHeader.text = "Bluetooth Connection"
        }
    }

    @SuppressLint("MissingPermission")
    private fun connectToDevice(device: BluetoothDevice) {
        lifecycleScope.launch {
            binding.tvHeader.text = "Connecting..."
            val repository = (requireActivity().application as MyApplication).repository
            
            // Note: In a real app, you'd use the bluetooth manager directly
            // For now, we'll just simulate connection
            connectedDevice = device
            
            // Update UI
            binding.cardConnected.visibility = View.VISIBLE
            binding.tvConnectedDevice.text = device.name ?: "Unknown"
            binding.tvConnectedStatus.text = "Signal: ${estimateSignalStrength(device).name}"
            
            // Navigate to dashboard
            Toast.makeText(requireContext(), "Connected to ${device.name}", Toast.LENGTH_SHORT).show()
            
            // Switch to dashboard tab
            requireActivity().findViewById<com.google.android.material.bottomnavigation.BottomNavigationView>(
                R.id.bottomNavigation
            )?.selectedItemId = R.id.nav_dashboard
        }
    }

    private fun disconnectDevice() {
        connectedDevice = null
        binding.cardConnected.visibility = View.GONE
        Toast.makeText(requireContext(), "Disconnected", Toast.LENGTH_SHORT).show()
    }

    private fun checkPermissions(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            ContextCompat.checkSelfPermission(requireContext(), Manifest.permission.BLUETOOTH_SCAN) == PackageManager.PERMISSION_GRANTED &&
                    ContextCompat.checkSelfPermission(requireContext(), Manifest.permission.BLUETOOTH_CONNECT) == PackageManager.PERMISSION_GRANTED
        } else {
            ContextCompat.checkSelfPermission(requireContext(), Manifest.permission.BLUETOOTH) == PackageManager.PERMISSION_GRANTED &&
                    ContextCompat.checkSelfPermission(requireContext(), Manifest.permission.BLUETOOTH_ADMIN) == PackageManager.PERMISSION_GRANTED &&
                    ContextCompat.checkSelfPermission(requireContext(), Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
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

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
