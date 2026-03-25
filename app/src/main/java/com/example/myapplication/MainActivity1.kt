package com.example.myapplication

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import com.example.myapplication.data.bluetooth.ObdBluetoothManager
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.*


class MainActivity1 : AppCompatActivity() {
    private lateinit var statusText: TextView
    private lateinit var scanButton: Button
    private lateinit var connectButton: Button
    private lateinit var sendAtzButton: Button
    private lateinit var deviceList: TextView

    private lateinit var OBDBluetoothManager: ObdBluetoothManager
    private val foundDevices = mutableListOf<BluetoothDevice>()

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val allGranted = permissions.entries.all { it.value }
        if (allGranted) {
            checkBluetoothAndScan()
        } else {
            Toast.makeText(this, "需要蓝牙权限", Toast.LENGTH_SHORT).show()
        }
    }


    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // 初始化蓝牙管理器
        OBDBluetoothManager = ObdBluetoothManager(this)

        // ... 初始化视图 ...
        statusText = findViewById(R.id.statusText)
        scanButton = findViewById(R.id.scanButton)
        connectButton = findViewById(R.id.connectButton)
        sendAtzButton = findViewById(R.id.sendAtzButton)
        deviceList = findViewById(R.id.deviceList)

        scanButton.setOnClickListener {
            if (checkPermissions()) {
                checkBluetoothAndScan()
            } else {
                requestPermissions()
            }
        }

        connectButton.setOnClickListener {
            if (!checkPermissions()) {
                requestPermissions()
                return@setOnClickListener
            }
            try {
                val elmDevice = foundDevices.firstOrNull { it.name?.contains("OBD", true) == true }
                if (elmDevice != null) {
                    connectToDevice(elmDevice)
                } else {
                    Toast.makeText(this, "未找到 ELM327 设备，请先扫描", Toast.LENGTH_SHORT).show()
                }
            } catch (e: SecurityException) {
                Toast.makeText(this, "权限不足", Toast.LENGTH_SHORT).show()
            }
        }

        sendAtzButton.setOnClickListener {
            lifecycleScope.launch {
                val response = OBDBluetoothManager.sendCommand("ATZ")
                statusText.text = "响应: $response"
            }
        }
    }

    // 权限检查方法保持不变（checkPermissions, requestPermissions）
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
    private fun checkBluetoothAndScan() {
        if (!OBDBluetoothManager.isBluetoothEnabled()) {
            val enableIntent = Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE)
            startActivityForResult(enableIntent, 100)
        } else {
            scanDevices()
        }
    }

    @SuppressLint("MissingPermission")
    private fun scanDevices() {
        foundDevices.clear()
        deviceList.text = "扫描中...\n"

        val pairedDevices = OBDBluetoothManager.getPairedDevices()
        foundDevices.addAll(pairedDevices)
        pairedDevices.forEach { device ->
            deviceList.append("已配对: ${device.name} [${device.address}]\n")
        }

        if (foundDevices.isEmpty()) {
            deviceList.text = "没有找到已配对设备，请在系统设置中先配对 ELM327"
        } else {
            statusText.text = "找到 ${foundDevices.size} 个设备"
        }
    }

    @SuppressLint("MissingPermission")
    private fun connectToDevice(device: BluetoothDevice) {
        lifecycleScope.launch {
            statusText.text = "正在连接 ${device.name}..."
            val success = OBDBluetoothManager.connect(device.address)
            if (success) {
                statusText.text = "已连接到 ${device.name}"
                Toast.makeText(this@MainActivity1, "连接成功", Toast.LENGTH_SHORT).show()
            } else {
                statusText.text = "连接失败"
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        OBDBluetoothManager.close()
    }

    @Deprecated("Deprecated in Java")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == 100 && resultCode == RESULT_OK) {
            scanDevices()
        }
    }
}