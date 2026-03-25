package com.example.myapplication.data.bluetooth

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothSocket
import android.content.Context
import com.example.myapplication.utils.Constants
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.TimeoutCancellationException
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeout
import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import java.util.UUID

class ObdBluetoothManager(private val context: Context) {

    private var bluetoothSocket: BluetoothSocket? = null
    private var inputStream: InputStream? = null
    private var outputStream: OutputStream? = null

    private val bluetoothAdapter: BluetoothAdapter? by lazy {
        val manager = context.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
        manager.adapter
    }
    // 标准 SPP UUID
    private val sppUuid = UUID.fromString(Constants.SPP_UUID)

    /**
     * 连接到指定的蓝牙设备
     * @param address 设备 MAC 地址
     * @return true 表示连接成功
     */
    suspend fun connect(address: String): Boolean = withContext(Dispatchers.IO) {
        // 先关闭可能存在的旧连接
        close()
        val device = bluetoothAdapter?.getRemoteDevice(address) ?: return@withContext false
        return@withContext try {
            withTimeout(Constants.CONNECTION_TIMEOUT) { // 10 秒超时
                bluetoothSocket = device.createInsecureRfcommSocketToServiceRecord(sppUuid)
                bluetoothSocket?.connect()
                inputStream = bluetoothSocket?.inputStream
                outputStream = bluetoothSocket?.outputStream
            }
            true
        } catch (e: TimeoutCancellationException) {
            close()
            false
        } catch (e: IOException) {
            close()
            false
        }
    }

    /**
     * 发送命令并读取响应
     * @param command 要发送的命令字符串（无需添加 \r）
     * @return 响应字符串（已去除末尾提示符和空白）
     */
    suspend fun sendCommand(command: String): String = withContext(Dispatchers.IO) {
        if (bluetoothSocket?.isConnected != true) {
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
            buffer.toString().trim()
        } catch (e: TimeoutCancellationException) {
            ""
        } catch (e: IOException) {
            ""
        }
    }

    /**
     * 获取已配对设备列表
     * 注意：调用前需确保有 BLUETOOTH_CONNECT 权限（Android 12+）
     */
    @SuppressLint("MissingPermission")
    fun getPairedDevices(): List<BluetoothDevice> {
        return bluetoothAdapter?.bondedDevices?.toList() ?: emptyList()
    }

    /**
     * 检查蓝牙是否开启
     */
    fun isBluetoothEnabled(): Boolean {
        return bluetoothAdapter?.isEnabled == true
    }

    /**
     * 关闭连接并释放资源
     */
    fun close() {
        try {
            inputStream?.close()
            outputStream?.close()
            bluetoothSocket?.close()
        } catch (e: IOException) {
            e.printStackTrace()
        } finally {
            inputStream = null
            outputStream = null
            bluetoothSocket = null
        }
    }
}