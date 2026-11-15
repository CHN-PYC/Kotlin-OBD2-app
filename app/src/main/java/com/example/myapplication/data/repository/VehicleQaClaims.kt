package com.example.myapplication.data.repository

import org.json.JSONArray
import org.json.JSONObject

/**
 * Client-side view of the claim-level answer returned by server-v2 (`claims` in /qa/vehicle).
 *
 * The server decides each claim's citation status; the client only displays it. A status says
 * whether a claim can be traced to the supplied evidence, not whether the claim is true.
 */
enum class ClaimKind(val wireValue: String, val label: String) {
    DEFINITION("definition", "Definition"),
    CAUSE("cause", "Possible cause"),
    CHECK("check", "Next check");

    companion object {
        fun from(value: String): ClaimKind = entries.firstOrNull { it.wireValue == value } ?: CAUSE
    }
}

enum class ClaimSupport(val wireValue: String, val label: String) {
    QUOTED("quoted", "Quote found"),
    CITED("cited", "Source cited"),
    VEHICLE_DATA("vehicle_data", "Vehicle data"),
    UNSUPPORTED("unsupported", "No source");

    companion object {
        // Unknown values fall back to the most cautious label rather than implying support.
        fun from(value: String): ClaimSupport = entries.firstOrNull { it.wireValue == value } ?: UNSUPPORTED
    }
}

/** A passage shown beside a claim. [quoteStart]/[quoteEnd] mark the verified quote, or -1 if none. */
data class ClaimEvidence(
    val chunkId: String,
    val sourceTitle: String,
    val passage: String,
    val quoteStart: Int = -1,
    val quoteEnd: Int = -1
) {
    val hasQuote: Boolean get() = quoteStart in 0 until quoteEnd
}

data class VehicleQaClaim(
    val claimId: String,
    val text: String,
    val kind: ClaimKind,
    val support: ClaimSupport,
    val evidence: ClaimEvidence?
)

/** A window of a long passage around the highlighted quote, with offsets relative to [text]. */
data class PassageExcerpt(
    val text: String,
    val highlightStart: Int,
    val highlightEnd: Int,
    val truncated: Boolean
)

object VehicleQaClaimParser {

    /** Parses claims from the raw backend body; returns empty for older responses without claims. */
    fun parse(rawOutput: String?): List<VehicleQaClaim> {
        if (rawOutput.isNullOrBlank()) return emptyList()
        val root = try {
            JSONObject(rawOutput)
        } catch (_: Exception) {
            return emptyList()
        }
        val claims = root.optJSONArray("claims") ?: return emptyList()
        val sources = sourcesByChunkId(root.optJSONArray("sources"))
        return buildList {
            for (i in 0 until claims.length()) {
                val item = claims.optJSONObject(i) ?: continue
                val text = item.optString("text").trim()
                if (text.isEmpty()) continue
                val support = ClaimSupport.from(item.optString("support"))
                add(
                    VehicleQaClaim(
                        claimId = item.optString("claim_id").ifBlank { "c${i + 1}" },
                        text = text,
                        kind = ClaimKind.from(item.optString("kind")),
                        support = support,
                        evidence = evidenceFor(item, support, sources)
                    )
                )
            }
        }
    }

    /** Cuts a long passage down to the quote plus [context] characters on each side. */
    fun excerpt(evidence: ClaimEvidence, context: Int = 160, fallbackLength: Int = 320): PassageExcerpt {
        val passage = evidence.passage
        if (!evidence.hasQuote) {
            val truncated = passage.length > fallbackLength
            return PassageExcerpt(passage.take(fallbackLength), -1, -1, truncated)
        }
        val start = (evidence.quoteStart - context).coerceAtLeast(0)
        val end = (evidence.quoteEnd + context).coerceAtMost(passage.length)
        val prefix = if (start > 0) "…" else ""
        val suffix = if (end < passage.length) "…" else ""
        return PassageExcerpt(
            text = prefix + passage.substring(start, end) + suffix,
            highlightStart = prefix.length + evidence.quoteStart - start,
            highlightEnd = prefix.length + evidence.quoteEnd - start,
            truncated = start > 0 || end < passage.length
        )
    }

    private data class SourcePassage(val title: String, val text: String)

    private fun sourcesByChunkId(sources: JSONArray?): Map<String, SourcePassage> {
        if (sources == null) return emptyMap()
        return buildMap {
            for (i in 0 until sources.length()) {
                val item = sources.optJSONObject(i) ?: continue
                val chunkId = item.optString("chunk_id")
                if (chunkId.isBlank()) continue
                val title = item.optString("title").ifBlank { item.optString("doc_id").ifBlank { chunkId } }
                put(chunkId, SourcePassage(title, item.optString("text")))
            }
        }
    }

    private fun evidenceFor(
        item: JSONObject,
        support: ClaimSupport,
        sources: Map<String, SourcePassage>
    ): ClaimEvidence? {
        if (support == ClaimSupport.QUOTED) {
            val chunkId = item.optString("quote_chunk_id")
            val source = sources[chunkId]
            val quote = item.optString("quote")
            if (source != null && quote.isNotEmpty()) {
                // The server returns the exact span it matched, so a plain search finds it.
                val start = source.text.indexOf(quote)
                if (start >= 0) {
                    return ClaimEvidence(chunkId, source.title, source.text, start, start + quote.length)
                }
                return ClaimEvidence(chunkId, source.title, source.text)
            }
        }
        if (support == ClaimSupport.QUOTED || support == ClaimSupport.CITED) {
            val ids = item.optJSONArray("source_chunk_ids") ?: JSONArray()
            for (i in 0 until ids.length()) {
                val chunkId = ids.optString(i)
                val source = sources[chunkId] ?: continue
                return ClaimEvidence(chunkId, source.title, source.text)
            }
        }
        return null
    }
}
