package com.example.myapplication.ui.adapter

import android.bluetooth.BluetoothDevice
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.example.myapplication.R
import com.example.myapplication.utils.SignalStrength

class DeviceAdapter(
    private val onConnectClick: (BluetoothDevice) -> Unit
) : ListAdapter<DeviceAdapter.DeviceItem, DeviceAdapter.DeviceViewHolder>(DeviceDiffCallback()) {

    class DeviceDiffCallback : DiffUtil.ItemCallback<DeviceItem>() {
        override fun areItemsTheSame(oldItem: DeviceItem, newItem: DeviceItem): Boolean {
            return oldItem.device.address == newItem.device.address
        }

        override fun areContentsTheSame(oldItem: DeviceItem, newItem: DeviceItem): Boolean {
            return oldItem == newItem
        }
    }

    data class DeviceItem(
        val device: BluetoothDevice,
        val isPaired: Boolean,
        val signalStrength: SignalStrength
    )

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): DeviceViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_bluetooth_device, parent, false)
        return DeviceViewHolder(view)
    }

    override fun onBindViewHolder(holder: DeviceViewHolder, position: Int) {
        holder.bind(getItem(position), onConnectClick)
    }

    class DeviceViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val ivBluetooth: ImageView = itemView.findViewById(R.id.ivBluetooth)
        private val tvDeviceName: TextView = itemView.findViewById(R.id.tvDeviceName)
        private val tvDeviceAddress: TextView = itemView.findViewById(R.id.tvDeviceAddress)
        private val tvPairStatus: TextView = itemView.findViewById(R.id.tvPairStatus)
        private val btnConnect: Button = itemView.findViewById(R.id.btnConnect)
        fun bind(item: DeviceItem, onConnectClick: (BluetoothDevice) -> Unit) {
            val device = item.device
            tvDeviceName.text = device.name ?: "Unknown Device"
            tvDeviceAddress.text = device.address
            tvPairStatus.text = if (item.isPaired) "Paired" else "Not Paired"

            val isLikelyNonObd = isLikelyNonObdDevice(device.name)

            // UI 样式（仅供参考，不用于逻辑控制）
            itemView.alpha = if (isLikelyNonObd) 0.6f else 1.0f
            btnConnect.text = if (isLikelyNonObd) "Not OBD2" else "Connect"
            btnConnect.isEnabled = true   // 始终保持可点击，以便给出提示

            btnConnect.setOnClickListener {
                if (isLikelyNonObd) {
                    Toast.makeText(
                        itemView.context,
                        "This appears to be a non-OBD2 device. Connection will fail.",
                        Toast.LENGTH_LONG
                    ).show()
                } else {
                    onConnectClick(device)
                }
            }
        }
        
        /**
         * Check if device name suggests it's NOT an OBD2 adapter
         */
        private fun isLikelyNonObdDevice(deviceName: String?): Boolean {
            if (deviceName == null) return false
            
            val nonObdKeywords = listOf(
                "headphone", "headset", "earbud", "airpod",
                "speaker", "audio", "music", "sound",
                "watch", "band", "fitbit", "garmin",
                "tv", "display", "monitor",
                "keyboard", "mouse", "trackpad",
                "phone", "galaxy", "iphone", "pixel"
            )
            
            val obdKeywords = listOf(
                "obd", "obdii", "elm327", "elm",
                "vgate", "icar", "car",
                "adapter", "scanner", "diagnostic"
            )
            
            val lowerName = deviceName?.lowercase() ?: ""
            
            // If it contains OBD keywords, it's likely an OBD2 device
            if (obdKeywords.any { lowerName.contains(it) }) {
                return false
            }
            
            // If it contains non-OBD keywords, it's likely NOT an OBD2 device
            return nonObdKeywords.any { lowerName.contains(it) }
        }
    }

}
