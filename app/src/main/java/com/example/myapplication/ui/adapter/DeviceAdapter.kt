package com.example.myapplication.ui.adapter

import android.bluetooth.BluetoothDevice
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.ImageView
import android.widget.TextView
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.example.myapplication.R
import com.example.myapplication.utils.SignalStrength

class DeviceAdapter(
    private val onConnectClick: (BluetoothDevice) -> Unit
) : ListAdapter<DeviceAdapter.DeviceItem, DeviceAdapter.DeviceViewHolder>(DeviceDiffCallback()) {

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
            
            // Signal strength color
            val signalColor = when (item.signalStrength) {
                SignalStrength.EXCELLENT -> R.color.signal_excellent
                SignalStrength.GOOD -> R.color.signal_good
                SignalStrength.FAIR -> R.color.signal_fair
                SignalStrength.WEAK -> R.color.signal_weak
            }
            // Note: Signal strength text not shown in this simple layout
            
            btnConnect.setOnClickListener {
                onConnectClick(device)
            }
        }
    }

    class DeviceDiffCallback : DiffUtil.ItemCallback<DeviceItem>() {
        override fun areItemsTheSame(oldItem: DeviceItem, newItem: DeviceItem): Boolean {
            return oldItem.device.address == newItem.device.address
        }

        override fun areContentsTheSame(oldItem: DeviceItem, newItem: DeviceItem): Boolean {
            return oldItem == newItem
        }
    }
}
