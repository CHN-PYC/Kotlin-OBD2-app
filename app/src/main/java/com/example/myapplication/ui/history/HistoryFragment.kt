package com.example.myapplication.ui.history

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.myapplication.MyApplication
import com.example.myapplication.databinding.ActivityHistoryBinding
import com.example.myapplication.ui.adapter.TripAdapter
import kotlinx.coroutines.launch

class HistoryFragment : Fragment() {

    private var _binding: ActivityHistoryBinding? = null
    private val binding get() = _binding!!

    private var tripAdapter: TripAdapter? = null

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = ActivityHistoryBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // Setup RecyclerView
        setupTripList()

        // Setup export button
        binding.btnExport.setOnClickListener {
            exportData()
        }

        // Load trip data
        loadTrips()
    }

    private fun setupTripList() {
        tripAdapter = TripAdapter { tripItem ->
            // View details click
            Toast.makeText(requireContext(), "Viewing trip: ${tripItem.date}", Toast.LENGTH_SHORT).show()
        }

        binding.recyclerTrips.apply {
            layoutManager = LinearLayoutManager(requireContext())
            adapter = tripAdapter
        }
    }

    private fun loadTrips() {
        lifecycleScope.launch {
            val repository = (requireActivity().application as MyApplication).repository
            
            repository.getHistory().collect { vehicleDataList ->
                if (vehicleDataList.isEmpty()) {
                    // Show empty state
                    binding.recyclerTrips.visibility = View.GONE
                    binding.emptyState.visibility = View.VISIBLE
                } else {
                    // Show trip list
                    binding.emptyState.visibility = View.GONE
                    binding.recyclerTrips.visibility = View.VISIBLE

                    // Convert vehicle data to trip items
                    val tripItems = TripAdapter.createTripItems(vehicleDataList)
                    tripAdapter?.submitList(tripItems)
                }
            }
        }
    }

    private fun exportData() {
        // TODO: Implement export functionality (CSV, PDF, etc.)
        Toast.makeText(requireContext(), "Export coming soon", Toast.LENGTH_SHORT).show()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
