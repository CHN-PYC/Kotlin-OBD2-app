package com.example.myapplication.data.repository

data class LlmProviderConfig(
    val providerName: String,
    val baseUrl: String,
    val apiKey: String,
    val model: String,
    val timeoutSeconds: Long = 45,
    val enabled: Boolean = false
) {
    companion object {
        fun disabledDefault(): LlmProviderConfig = LlmProviderConfig(
            providerName = "remote-disabled",
            baseUrl = "",
            apiKey = "",
            model = "",
            timeoutSeconds = 45,
            enabled = false
        )
    }
}
