package com.example.myapplication.data.repository

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class RemoteLlmApiClient(
    private val config: LlmProviderConfig
) {

    data class RemoteLlmApiResult(
        val rawText: String,
        val parsedText: String,
        val responseJson: String
    )

    private val client: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .connectTimeout(config.timeoutSeconds, TimeUnit.SECONDS)
            .readTimeout(config.timeoutSeconds, TimeUnit.SECONDS)
            .writeTimeout(config.timeoutSeconds, TimeUnit.SECONDS)
            .build()
    }

    fun runDiagnosis(prompt: String): RemoteLlmApiResult {
        require(config.enabled) { "Remote LLM is disabled" }
        require(config.baseUrl.isNotBlank()) { "Remote LLM baseUrl is missing" }
        require(config.apiKey.isNotBlank()) { "Remote LLM apiKey is missing" }
        require(config.model.isNotBlank()) { "Remote LLM model is missing" }

        val payload = JSONObject().apply {
            put("model", config.model)
            put("messages", JSONArray().apply {
                put(JSONObject().apply {
                    put("role", "system")
                    put("content", "You are a helpful automotive diagnostic assistant. Return ONLY valid JSON. Do not use markdown fences. Do not add commentary outside JSON. Required keys: severity, summary, observations, hypotheses, recommendedChecks, confidence, notes.")
                })
                put(JSONObject().apply {
                    put("role", "user")
                    put("content", prompt)
                })
            })
        }

        val request = Request.Builder()
            .url(config.baseUrl)
            .addHeader("Authorization", "Bearer ${config.apiKey}")
            .addHeader("Content-Type", "application/json")
            .post(payload.toString().toRequestBody("application/json".toMediaType()))
            .build()

        client.newCall(request).execute().use { response ->
            val bodyText = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                throw IllegalStateException("Remote LLM request failed: HTTP ${response.code} ${response.message}; body=${bodyText.take(800)}")
            }

            if (bodyText.isBlank()) {
                throw IllegalStateException("Remote LLM returned an empty body")
            }

            val parsedText = extractContent(bodyText)
            return RemoteLlmApiResult(
                rawText = bodyText,
                parsedText = parsedText,
                responseJson = bodyText
            )
        }
    }

    private fun extractContent(responseBody: String): String {
        return try {
            val json = JSONObject(responseBody)
            val choices = json.optJSONArray("choices")
            if (choices != null && choices.length() > 0) {
                val first = choices.getJSONObject(0)
                first.optJSONObject("message")
                    ?.optString("content")
                    ?.takeIf { it.isNotBlank() }
                    ?: first.optString("text").takeIf { it.isNotBlank() }
                    ?: responseBody
            } else {
                responseBody
            }
        } catch (_: Exception) {
            responseBody
        }
    }
}
