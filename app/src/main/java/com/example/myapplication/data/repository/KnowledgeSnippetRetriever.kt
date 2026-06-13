package com.example.myapplication.data.repository

class KnowledgeSnippetRetriever {

    data class RetrievedSnippet(
        val sourceId: String,
        val sourceTitle: String,
        val sourceUrl: String,
        val text: String,
        val score: Int
    )

    fun retrieve(
        question: String,
        documents: List<KnowledgeDocumentDownloader.DownloadedKnowledgeDocument>,
        maxSnippets: Int = 5
    ): List<RetrievedSnippet> {
        val tokens = tokenize(question)
        return documents.flatMap { doc ->
            chunkText(doc.text).map { chunk ->
                RetrievedSnippet(
                    sourceId = doc.source.id,
                    sourceTitle = doc.source.title,
                    sourceUrl = doc.source.url,
                    text = chunk,
                    score = score(chunk, tokens)
                )
            }
        }
            .filter { it.score > 0 }
            .sortedByDescending { it.score }
            .take(maxSnippets)
    }

    internal fun chunkText(text: String, chunkSize: Int = 520, overlap: Int = 120): List<String> {
        if (text.isBlank()) return emptyList()
        val normalized = text.replace(Regex("\\s+"), " ").trim()
        if (normalized.length <= chunkSize) return listOf(normalized)

        val chunks = mutableListOf<String>()
        var start = 0
        while (start < normalized.length) {
            val end = minOf(normalized.length, start + chunkSize)
            chunks += normalized.substring(start, end).trim()
            if (end == normalized.length) break
            start = maxOf(0, end - overlap)
        }
        return chunks
    }

    private fun score(chunk: String, tokens: Set<String>): Int {
        if (tokens.isEmpty()) return 0
        val lower = chunk.lowercase()
        val overlap = tokens.count { lower.contains(it) }
        val exactPhraseBonus = tokens.sumOf { token -> if (" $token " in " $lower ") 1 else 0 }
        return overlap * 3 + exactPhraseBonus
    }

    private fun tokenize(text: String): Set<String> {
        return text.lowercase()
            .split(Regex("[^a-z0-9一-龥+.-]+"))
            .map { it.trim() }
            .filter { it.length >= 2 }
            .toSet()
    }
}
