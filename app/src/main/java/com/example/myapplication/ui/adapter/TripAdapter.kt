package com.example.myapplication.ui.adapter

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.example.myapplication.R
import com.example.myapplication.data.local.DriveSession
import java.text.SimpleDateFormat
import java.util.*

class TripAdapter(
    private val onViewDetailsClick: (TripItem) -> Unit
) : ListAdapter<TripAdapter.TripItem, TripAdapter.TripViewHolder>(TripDiffCallback()) {

    data class TripItem(
        val id: Long,
        val date: Long,
        val duration: Long, // in minutes
        val distance: Double, // km
        val avgSpeed: Double, // km/h
        val maxRpm: Int,
        val sourceType: String,
        val sampleCount: Int,
        val avgCoolantTemp: Double,
        val maxCoolantTemp: Int,
        val avgBatteryVoltage: Double,
        val maxEngineLoad: Double
    )

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): TripViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_trip_history, parent, false)
        return TripViewHolder(view)
    }

    override fun onBindViewHolder(holder: TripViewHolder, position: Int) {
        holder.bind(getItem(position), onViewDetailsClick)
    }

    class TripViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val tvTripDate: TextView = itemView.findViewById(R.id.tvTripDate)
        private val tvTripTime: TextView = itemView.findViewById(R.id.tvTripTime)
        private val tvTripDuration: TextView = itemView.findViewById(R.id.tvTripDuration)
        private val tvDistance: TextView = itemView.findViewById(R.id.tvDistance)
        private val tvAvgSpeed: TextView = itemView.findViewById(R.id.tvAvgSpeed)
        private val tvMaxRpm: TextView = itemView.findViewById(R.id.tvMaxRpm)
        private val btnViewDetails: TextView = itemView.findViewById(R.id.btnViewDetails)

        fun bind(item: TripItem, onViewDetailsClick: (TripItem) -> Unit) {
            val context = itemView.context
            val calendar = Calendar.getInstance().apply { timeInMillis = item.date }
            
            // Format date
            val dateFormat = SimpleDateFormat("MMM d, yyyy", Locale.getDefault())
            tvTripDate.text = dateFormat.format(calendar.time)
            
            // Format time (assuming trip duration, show start-end time)
            val timeFormat = SimpleDateFormat("HH:mm", Locale.getDefault())
            val endTime = timeFormat.format(calendar.time)
            calendar.add(Calendar.MINUTE, -item.duration.toInt())
            val startTime = timeFormat.format(calendar.time)
            tvTripTime.text = "$startTime - $endTime"
            
            // Duration
            tvTripDuration.text = "${item.duration} min"
            
            // Metrics
            tvDistance.text = String.format("%.1f km", item.distance)
            tvAvgSpeed.text = "${item.avgSpeed.toInt()} km/h"
            tvMaxRpm.text = "${String.format("%,d", item.maxRpm)} • ${item.sourceType}"
            
            btnViewDetails.setOnClickListener {
                onViewDetailsClick(item)
            }
        }
    }

    class TripDiffCallback : DiffUtil.ItemCallback<TripItem>() {
        override fun areItemsTheSame(oldItem: TripItem, newItem: TripItem): Boolean {
            return oldItem.id == newItem.id
        }

        override fun areContentsTheSame(oldItem: TripItem, newItem: TripItem): Boolean {
            return oldItem == newItem
        }
    }
    
    companion object {
        fun createTripItems(sessions: List<DriveSession>): List<TripItem> {
            return sessions.map { session ->
                val durationMinutes = (session.durationSec / 60).coerceAtLeast(1)
                val distance = session.avgSpeed * (session.durationSec / 3600.0)
                TripItem(
                    id = session.id,
                    date = session.endedAt ?: session.startedAt,
                    duration = durationMinutes,
                    distance = distance,
                    avgSpeed = session.avgSpeed,
                    maxRpm = session.maxRpm,
                    sourceType = session.sourceType,
                    sampleCount = session.sampleCount,
                    avgCoolantTemp = session.avgCoolantTemp,
                    maxCoolantTemp = session.maxCoolantTemp,
                    avgBatteryVoltage = session.avgBatteryVoltage,
                    maxEngineLoad = session.maxEngineLoad
                )
            }.sortedByDescending { it.date }
        }
    }
}
