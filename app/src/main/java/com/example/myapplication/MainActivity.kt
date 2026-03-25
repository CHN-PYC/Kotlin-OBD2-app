package com.example.myapplication

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothSocket
import android.content.Context
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
import kotlinx.coroutines.*
import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import java.util.UUID

class MainActivity : AppCompatActivity() {

    private lateinit var statusText: TextView
    private lateinit var scanButton: Button
    private lateinit var connectButton: Button
    private lateinit var sendAtzButton: Button
    private lateinit var deviceList: TextView

    private var bluetoothAdapter: BluetoothAdapter? = null
    private var bluetoothSocket: BluetoothSocket? = null
    private var inputStream: InputStream? = null
    private var outputStream: OutputStream? = null
    private val mainScope = MainScope()

    // 标准 SPP UUID（ELM327 使用）
    private val sppUuid = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")

    // 存储扫描到的设备（这里简单显示，实际可用列表）
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

        statusText = findViewById(R.id.statusText)
        scanButton = findViewById(R.id.scanButton)
        connectButton = findViewById(R.id.connectButton)
        sendAtzButton = findViewById(R.id.sendAtzButton)
        deviceList = findViewById(R.id.deviceList)

        // 初始化蓝牙适配器
        val manager = getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
        bluetoothAdapter = manager.adapter

        scanButton.setOnClickListener {
            if (checkPermissions()) {
                checkBluetoothAndScan()
            } else {
                requestPermissions()
            }
        }

        connectButton.setOnClickListener {
            // 1. 再次检查权限
            if (!checkPermissions()) {
                requestPermissions()
                return@setOnClickListener
            }

            // 2. 使用 try-catch 捕获可能的 SecurityException
            try {
                val elmDevice = foundDevices.firstOrNull { it.name?.contains("OBD", true) == true }
                if (elmDevice != null) {
                    connectToDevice(elmDevice)
                } else {
                    Toast.makeText(this, "未找到 ELM327 设备，请先扫描", Toast.LENGTH_SHORT).show()
                }
            } catch (e: SecurityException) {
                Toast.makeText(this, "权限不足，无法访问设备信息", Toast.LENGTH_SHORT).show()
                // 可选：重新请求权限
                requestPermissions()
            }
        }
        sendAtzButton.setOnClickListener {
            mainScope.launch {
                sendCommand("ATZ")
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
    private fun checkBluetoothAndScan() {
        if (bluetoothAdapter?.isEnabled == false) {
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

        // 获取已配对设备
        val pairedDevices = bluetoothAdapter?.bondedDevices
        pairedDevices?.forEach { device ->
            foundDevices.add(device)
            deviceList.append("已配对: ${device.name} [${device.address}]\n")
        }

        // 这里简化：直接显示已配对，不实时扫描（如需扫描需注册 BroadcastReceiver）
        // 因为只是测试，通常 ELM327 需要先配对，所以已配对列表足够了
        if (foundDevices.isEmpty()) {
            deviceList.text = "没有找到已配对设备，请在系统设置中先配对 ELM327"
        } else {
            statusText.text = "找到 ${foundDevices.size} 个设备"
        }
    }

    @SuppressLint("MissingPermission")
    private fun connectToDevice(device: BluetoothDevice) {
        mainScope.launch {
            statusText.text = "正在连接 ${device.name}..."
            try {
                withContext(Dispatchers.IO) {
                    // 连接超时控制（协程超时）
                    withTimeout(10000) {
                        bluetoothSocket = device.createInsecureRfcommSocketToServiceRecord(sppUuid)
                        bluetoothSocket?.connect()
                        inputStream = bluetoothSocket?.inputStream
                        outputStream = bluetoothSocket?.outputStream
                    }
                }
                statusText.text = "已连接到 ${device.name}"
                Toast.makeText(this@MainActivity, "连接成功", Toast.LENGTH_SHORT).show()
            } catch (e: TimeoutCancellationException) {
                statusText.text = "连接超时"
                closeConnection()
            } catch (e: IOException) {
                statusText.text = "连接失败: ${e.message}"
                closeConnection()
            } catch (e: SecurityException) {
                statusText.text = "权限不足"
            }
        }
    }

    private suspend fun sendCommand(command: String): String = withContext(Dispatchers.IO) {
        if (bluetoothSocket?.isConnected != true) {
            withContext(Dispatchers.Main) {
                statusText.text = "未连接"
            }
            return@withContext ""
        }
        return@withContext try {
            val cmd = "$command\r"
            outputStream?.write(cmd.toByteArray())
            outputStream?.flush()

            // 读取响应直到 '>'
            val buffer = StringBuilder()
            withTimeout(3000) {
                while (true) {
                    val b = inputStream?.read() ?: break
                    val c = b.toChar()
                    if (c == '>') break
                    buffer.append(c)
                }
            }
            val response = buffer.toString().trim()
            withContext(Dispatchers.Main) {
                statusText.text = "命令: $command\n响应: $response"
            }
            response
        } catch (e: TimeoutCancellationException) {
            withContext(Dispatchers.Main) {
                statusText.text = "读取响应超时"
            }
            ""
        } catch (e: IOException) {
            withContext(Dispatchers.Main) {
                statusText.text = "IO 错误: ${e.message}"
            }
            ""
        }
    }

    private fun closeConnection() {
        try {
            bluetoothSocket?.close()
        } catch (e: IOException) {
            e.printStackTrace()
        } finally {
            bluetoothSocket = null
            inputStream = null
            outputStream = null
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        mainScope.cancel()
        closeConnection()
    }

    @Deprecated("Deprecated in Java")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == 100 && resultCode == RESULT_OK) {
            scanDevices()
        }
    }

}