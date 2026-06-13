package com.example.myapplication.data.repository

import android.content.Context
import com.example.myapplication.data.local.DiagnosticReport
import org.json.JSONArray
import org.json.JSONObject

class VehicleQaRagService(
    context: Context,
    private val llmInputBuilder: LlmDiagnosticInputBuilder,
    private val apiClient: RemoteLlmApiClient,
    private val config: LlmProviderConfig
) {

    private val downloader = KnowledgeDocumentDownloader(context, config.timeoutSeconds)
    private val retriever = KnowledgeSnippetRetriever()

    fun run(sessionId: Long, question: String, input: LlmDiagnosticInput): DiagnosticReport {
        require(config.enabled) { "Remote LLM is disabled" }
        require(question.isNotBlank()) { "Question must not be blank" }

        val selectedSources = VehicleQaKnowledgeCatalog.matchSources(question, input)
        val downloadedDocs = selectedSources.map { downloader.download(it) }
        val snippets = retriever.retrieve(question, downloadedDocs)
        val sourceJson = JSONArray().apply {
            downloadedDocs.forEach { doc ->
                put(JSONObject().apply {
                    put("id", doc.source.id)
                    put("title", doc.source.title)
                    put("url", doc.source.url)
                    put("fromCache", doc.fromCache)
                })
            }
        }
        val snippetJson = JSONArray().apply {
            snippets.forEach { snippet ->
                put(JSONObject().apply {
                    put("sourceId", snippet.sourceId)
                    put("sourceTitle", snippet.sourceTitle)
                    put("sourceUrl", snippet.sourceUrl)
                    put("score", snippet.score)
                    put("text", snippet.text)
                })
            }
        }

        val prompt = buildPrompt(question, input, snippets)
        val apiResult = apiClient.runChat(
            systemPrompt = buildSystemPrompt(),
            userPrompt = prompt
        )
        val parsed = parseResponse(apiResult.parsedText, snippets)
        val rawInputJson = JSONObject().apply {
            put("question", question)
            put("sessionId", sessionId)
            put("vehicleInput", JSONObject(llmInputBuilder.toJson(input)))
            put("sources", sourceJson)
            put("snippets", snippetJson)
        }.toString()

        return DiagnosticReport(
            sessionId = sessionId,
            createdAt = System.currentTimeMillis(),
            reportType = DiagnosticReport.TYPE_RAG_QA,
            modelName = config.providerName,
            modelVersion = config.model,
            promptVersion = "vehicle-rag-v1",
            severity = parsed.severity,
            summary = parsed.answer,
            findingsJson = parsed.findingsJson,
            recommendationsJson = parsed.recommendationsJson,
            rawInputSnapshotJson = rawInputJson,
            rawOutputText = apiResult.rawText
        )
    }

    private fun buildSystemPrompt(): String =
        "You are an automotive diagnostic Q&A assistant. Use the provided vehicle telemetry summary and retrieved knowledge snippets to answer carefully. Return ONLY valid JSON with keys: severity, answer, findings, recommendations, citedSources. findings and recommendations must be arrays. citedSources must be an array of source titles or URLs actually used. If evidence is weak, say so plainly."

    private fun buildPrompt(
        question: String,
        input: LlmDiagnosticInput,
        snippets: List<KnowledgeSnippetRetriever.RetrievedSnippet>
    ): String {
        val telemetryJson = llmInputBuilder.toJson(input)
        val contextText = if (snippets.isEmpty()) {
            "No external knowledge snippets were retrieved. Answer cautiously using the telemetry and rule-based findings only."
        } else {
            snippets.mapIndexed { index, snippet ->
                "[Snippet ${index + 1}] ${snippet.sourceTitle} (${snippet.sourceUrl})\n${snippet.text}"
            }.joinToString("\n\n")
        }

        return buildString {
            appendLine("User question:")
            appendLine(question)
            appendLine()
            appendLine("Vehicle telemetry and rule summary:")
            appendLine(telemetryJson)
            appendLine()
            appendLine("Retrieved knowledge snippets:")
            appendLine(contextText)
            appendLine()
            appendLine("Answer the user's question with grounded diagnostic guidance. Do not invent unsupported fault claims.")
        }
    }

    private fun parseResponse(
        text: String,
        snippets: List<KnowledgeSnippetRetriever.RetrievedSnippet>
    ): ParsedQaResponse {
        val normalized = text
            .replace("```json", "")
            .replace("```JSON", "")
            .replace("```", "")
            .trim()
        val jsonCandidate = extractFirstJsonObject(normalized)

        return try {
            val json = JSONObject(jsonCandidate ?: normalized)
            val answer = json.optString("answer").ifBlank { normalized.take(800) }
            val severity = json.optString("severity").ifBlank { DiagnosticReport.SEVERITY_NOTICE }
            val findings = json.optJSONArray("findings") ?: JSONArray().apply {
                put("Retrieved ${snippets.size} knowledge snippets for grounding.")
            }
            val recommendations = json.optJSONArray("recommendations") ?: JSONArray()
            val cited = json.optJSONArray("citedSources") ?: JSONArray()

            ParsedQaResponse(
                severity = severity,
                answer = answer,
                findingsJson = JSONArray().apply {
                    for (i in 0 until findings.length()) {
                        val item = findings.get(i)
                        if (item is JSONObject) put(item) else put(
                            JSONObject().apply {
                                put("title", "Finding")
                                put("detail", item.toString())
                                put("severity", severity)
                            }
                        )
                    }
                    if (cited.length() > 0) {
                        put(JSONObject().apply {
                            put("title", "Cited sources")
                            put("detail", (0 until cited.length()).joinToString("\n") { idx -> "• ${cited.get(idx)}" })
                            put("severity", "NOTICE")
                        })
                    }
                }.toString(),
                recommendationsJson = JSONArray().apply {
                    for (i in 0 until recommendations.length()) {
                        put(recommendations.get(i).toString())
                    }
                }.toString()
            )
        } catch (_: Exception) {
            ParsedQaResponse(
                severity = DiagnosticReport.SEVERITY_NOTICE,
                answer = normalized.take(800),
                findingsJson = JSONArray().apply {
                    put(JSONObject().apply {
                        put("title", "Fallback")
                        put("detail", "Remote answer could not be parsed as structured JSON.")
                        put("severity", DiagnosticReport.SEVERITY_NOTICE)
                    })
                }.toString(),
                recommendationsJson = JSONArray().toString()
            )
        }
    }

    private fun extractFirstJsonObject(text: String): String? {
        val start = text.indexOf('{')
        if (start < 0) return null
        var depth = 0
        for (i in start until text.length) {
            when (text[i]) {
                '{' -> depth++
                '}' -> {
                    depth--
                    if (depth == 0) return text.substring(start, i + 1)
                }
            }
        }
        return null
    }

    private data class ParsedQaResponse(
        val severity: String,
        val answer: String,
        val findingsJson: String,
        val recommendationsJson: String
    )
}
