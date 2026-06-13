package com.example.myapplication.data.repository

import android.content.Context
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.util.concurrent.TimeUnit

class KnowledgeDocumentDownloader(
    context: Context,
    timeoutSeconds: Long = 30
) {

    private val cacheDir = File(context.filesDir, "rag_kb").apply { mkdirs() }

    private val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(timeoutSeconds, TimeUnit.SECONDS)
        .readTimeout(timeoutSeconds, TimeUnit.SECONDS)
        .writeTimeout(timeoutSeconds, TimeUnit.SECONDS)
        .build()

    data class DownloadedKnowledgeDocument(
        val source: VehicleQaKnowledgeSource,
        val cacheFile: File,
        val text: String,
        val fromCache: Boolean
    )

    fun download(source: VehicleQaKnowledgeSource, forceRefresh: Boolean = false): DownloadedKnowledgeDocument {
        val cacheFile = File(cacheDir, "${source.id}.txt")
        if (!forceRefresh && cacheFile.exists() && cacheFile.length() > 64) {
            return DownloadedKnowledgeDocument(
                source = source,
                cacheFile = cacheFile,
                text = cacheFile.readText(),
                fromCache = true
            )
        }

        val request = Request.Builder()
            .url(source.url)
            .header("User-Agent", "Mozilla/5.0 Kotlin-OBD2-App RAG Downloader")
            .build()

        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                throw IllegalStateException("Failed to download ${source.url}: HTTP ${response.code}")
            }
            val body = response.body?.string().orEmpty()
            if (body.isBlank()) {
                throw IllegalStateException("Downloaded empty knowledge document from ${source.url}")
            }
            val cleaned = cleanDocument(body)
            cacheFile.writeText(cleaned)
            return DownloadedKnowledgeDocument(
                source = source,
                cacheFile = cacheFile,
                text = cleaned,
                fromCache = false
            )
        }
    }

    private fun cleanDocument(raw: String): String {
        return raw
            .replace(Regex("<script[\\s\\S]*?</script>", RegexOption.IGNORE_CASE), " ")
            .replace(Regex("<style[\\s\\S]*?</style>", RegexOption.IGNORE_CASE), " ")
            .replace(Regex("<[^>]+>"), " ")
            .replace("&nbsp;", " ")
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace(Regex("\\s+"), " ")
            .trim()
    }
}
