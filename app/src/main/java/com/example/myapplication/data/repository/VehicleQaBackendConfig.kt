package com.example.myapplication.data.repository

data class VehicleQaBackendConfig(
    val baseUrl: String,
    val apiKey: String,
    val timeoutSeconds: Long = 45,
    val enabled: Boolean = false
) {
    companion object {
        fun disabledDefault(): VehicleQaBackendConfig = VehicleQaBackendConfig(
            baseUrl = "",
            apiKey = "",
            timeoutSeconds = 45,
            enabled = false
        )
    }
}
