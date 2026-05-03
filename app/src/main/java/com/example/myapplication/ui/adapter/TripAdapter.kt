package com.example.myapplication.ui.adapter

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.example.myapplication.R
import com.example.myapplication.data.local.VehicleData
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
        val maxRpm: Int
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
            tvDistance.text = String.format("%.1f", item.distance)
            tvAvgSpeed.text = item.avgSpeed.toInt().toString()
            tvMaxRpm.text = String.format("%,d", item.maxRpm)
            
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
        /**
         * Convert VehicleData list to TripItem list
         * Groups data by trips (simplified: each continuous session is a trip)
         */
        fun createTripItems(data: List<VehicleData>): List<TripItem> {
            if (data.isEmpty()) return emptyList()
            
            val sorted = data.sortedBy { it.timestamp }
            val trips = mutableListOf<List<VehicleData>>()
            val currentTrip = mutableListOf<VehicleData>()
            val tripGapMs = 30 * 60 * 1000L

            for (point in sorted) {
                if (currentTrip.isEmpty()) {
                    currentTrip.add(point)
                    continue
                }

                val previous = currentTrip.last()
                if (point.timestamp - previous.timestamp > tripGapMs) {
                    trips.add(currentTrip.toList())
                    currentTrip.clear()
                }
                currentTrip.add(point)
            }

            if (currentTrip.isNotEmpty()) trips.add(currentTrip.toList())

            return trips.map { trip ->
                val duration = ((trip.last().timestamp - trip.first().timestamp) / 60000).coerceAtLeast(1)
                val avgSpeed = trip.map { it.speed }.filter { it > 0 }.average().let { if (it.isNaN()) 0.0 else it }
                val fallbackSpeed = trip.map { it.rpm }.average() * 0.01
                val effectiveAvgSpeed = if (avgSpeed > 0) avgSpeed else fallbackSpeed
                val distance = effectiveAvgSpeed * (duration / 60.0)

                TripItem(
                    id = trip.first().id,
                    date = trip.last().timestamp,
                    duration = duration,
                    distance = distance,
                    avgSpeed = effectiveAvgSpeed,
                    maxRpm = trip.maxOf { it.rpm }
                )
            }.sortedByDescending { it.date }
        }
    }
}
