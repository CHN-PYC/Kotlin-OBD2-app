package com.example.myapplication

import com.example.myapplication.data.repository.KnowledgeSnippetRetriever
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class KnowledgeSnippetRetrieverTest {

    @Test
    fun `chunking splits long text into multiple overlapping segments`() {
        val retriever = KnowledgeSnippetRetriever()
        val text = buildString {
            repeat(80) { append("coolant temperature high radiator fan thermostat ") }
        }

        val chunks = retriever.chunkText(text, chunkSize = 120, overlap = 30)

        assertTrue(chunks.size > 1)
        assertTrue(chunks.first().contains("coolant"))
    }

    @Test
    fun `retrieve prefers chunks with overlapping terms`() {
        val retriever = KnowledgeSnippetRetriever()
        val docs = listOf(
            fakeDoc(
                id = "coolant",
                title = "Coolant guide",
                url = "https://example.com/coolant",
                text = "Coolant temperature rises when the radiator fan fails or the thermostat sticks."
            ),
            fakeDoc(
                id = "battery",
                title = "Battery guide",
                url = "https://example.com/battery",
                text = "Battery voltage under load can point to charging system issues."
            )
        )

        val results = retriever.retrieve("Why is coolant temperature high?", docs, maxSnippets = 2)

        assertFalse(results.isEmpty())
        assertTrue(results.first().sourceId == "coolant")
    }

    private fun fakeDoc(
        id: String,
        title: String,
        url: String,
        text: String
    ): com.example.myapplication.data.repository.KnowledgeDocumentDownloader.DownloadedKnowledgeDocument {
        return com.example.myapplication.data.repository.KnowledgeDocumentDownloader.DownloadedKnowledgeDocument(
            source = com.example.myapplication.data.repository.VehicleQaKnowledgeSource(
                id = id,
                title = title,
                url = url,
                keywords = emptyList(),
                summary = ""
            ),
            cacheFile = kotlin.io.path.createTempFile().toFile(),
            text = text,
            fromCache = false
        )
    }
}
