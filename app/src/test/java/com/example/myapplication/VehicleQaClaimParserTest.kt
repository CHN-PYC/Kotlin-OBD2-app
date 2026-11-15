package com.example.myapplication

import com.example.myapplication.data.repository.ClaimEvidence
import com.example.myapplication.data.repository.ClaimKind
import com.example.myapplication.data.repository.ClaimSupport
import com.example.myapplication.data.repository.VehicleQaClaimParser
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

// Robolectric supplies a working org.json; the plain JVM android.jar only has stubs.
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [28])
class VehicleQaClaimParserTest {

    private val passage = "Air-mass sensor function\nThe air-mass sensor measures the intake  air mass."

    private val body = """
        {
          "answer": "Summary.",
          "sources": [
            {"chunk_id": "maf-1", "doc_id": "hella", "title": "Air mass sensor", "text": ${org.json.JSONObject.quote(passage)}},
            {"chunk_id": "maf-2", "doc_id": "hella", "title": "Air mass sensor", "text": "Possible causes include contact faults."}
          ],
          "claims": [
            {"claim_id": "c1", "text": "Measures intake air.", "kind": "definition", "support": "quoted",
             "source_chunk_ids": ["maf-1"], "quote": "The air-mass sensor measures the intake  air mass.", "quote_chunk_id": "maf-1"},
            {"claim_id": "c2", "text": "Contacts can fail.", "kind": "cause", "support": "cited",
             "source_chunk_ids": ["maf-2"], "quote": null, "quote_chunk_id": null},
            {"claim_id": "c3", "text": "Coolant hit 108 C.", "kind": "cause", "support": "vehicle_data", "source_chunk_ids": []},
            {"claim_id": "c4", "text": "Check the connector.", "kind": "check", "support": "unsupported", "source_chunk_ids": []}
          ]
        }
    """.trimIndent()

    @Test
    fun parse_attachesEvidenceAccordingToServerStatus() {
        val claims = VehicleQaClaimParser.parse(body)

        assertEquals(listOf("c1", "c2", "c3", "c4"), claims.map { it.claimId })
        assertEquals(
            listOf(ClaimSupport.QUOTED, ClaimSupport.CITED, ClaimSupport.VEHICLE_DATA, ClaimSupport.UNSUPPORTED),
            claims.map { it.support }
        )
        assertEquals(ClaimKind.CHECK, claims[3].kind)

        val quoted = claims[0].evidence!!
        assertTrue(quoted.hasQuote)
        assertEquals("The air-mass sensor measures the intake  air mass.", passage.substring(quoted.quoteStart, quoted.quoteEnd))

        val cited = claims[1].evidence!!
        assertEquals("maf-2", cited.chunkId)
        assertFalse(cited.hasQuote)

        assertNull(claims[2].evidence)
        assertNull(claims[3].evidence)
    }

    @Test
    fun parse_returnsEmptyForLegacyOrInvalidBodies() {
        assertTrue(VehicleQaClaimParser.parse("""{"answer": "x", "findings": ["a"]}""").isEmpty())
        assertTrue(VehicleQaClaimParser.parse("not json").isEmpty())
        assertTrue(VehicleQaClaimParser.parse(null).isEmpty())
    }

    @Test
    fun parse_treatsUnknownStatusAsUnsupported() {
        val claims = VehicleQaClaimParser.parse(
            """{"claims": [{"text": "x", "kind": "other", "support": "verified"}]}"""
        )

        assertEquals(ClaimSupport.UNSUPPORTED, claims.single().support)
        assertEquals("c1", claims.single().claimId)
    }

    @Test
    fun excerpt_keepsHighlightAlignedWhenPassageIsTrimmed() {
        val long = "a".repeat(400) + "THE QUOTE" + "b".repeat(400)
        val evidence = ClaimEvidence("x", "t", long, 400, 409)

        val excerpt = VehicleQaClaimParser.excerpt(evidence, context = 20)

        assertTrue(excerpt.truncated)
        assertEquals("THE QUOTE", excerpt.text.substring(excerpt.highlightStart, excerpt.highlightEnd))
        assertTrue(excerpt.text.startsWith("…") && excerpt.text.endsWith("…"))
    }
}
