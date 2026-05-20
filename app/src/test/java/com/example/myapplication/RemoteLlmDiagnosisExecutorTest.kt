package com.example.myapplication

import com.example.myapplication.data.repository.LlmDiagnosticInput
import com.example.myapplication.data.repository.PromptHintsPayload
import com.example.myapplication.data.repository.RemoteLlmDiagnosisExecutor
import com.example.myapplication.data.repository.RuleFindingPayload
import com.example.myapplication.data.repository.RuleSummaryPayload
import com.example.myapplication.data.repository.SampleHighlightsPayload
import com.example.myapplication.data.repository.SessionSummaryPayload
import org.json.JSONArray
import org.junit.Assert.assertTrue
import org.junit.Test

class RemoteLlmDiagnosisExecutorTest {

    @Test
    fun parseRemoteOutput_handlesMarkdownAndAliasKeys() {
        val executorClass = Class.forName("com.example.myapplication.data.repository.RemoteLlmDiagnosisExecutor")
        val method = executorClass.getDeclaredMethod("parseRemoteOutput", String::class.java, LlmDiagnosticInput::class.java)
        method.isAccessible = true

        val input = LlmDiagnosticInput(
            sessionId = 1,
            sourceType = "REAL",
            createdAt = 1,
            sessionSummary = SessionSummaryPayload(60, 1, 10.0, 20, 1000.0, 2000, 90.0, 95, 14.0, 13.9, 14.2, 20.0, 40.0, 1.0, 2.0, 1.0),
            ruleSummary = RuleSummaryPayload(
                severity = "NOTICE",
                summary = "Base summary",
                findings = listOf(RuleFindingPayload("BASE", "NOTICE", "Base finding", "Base detail")),
                recommendations = listOf("Base recommendation")
            ),
            sampleHighlights = SampleHighlightsPayload(null, null, null, null, null),
            promptHints = PromptHintsPayload(false, false, "Use care")
        )

        val unsafe = java.lang.reflect.Field::class.java
        val ctor = executorClass.declaredConstructors.first()
        ctor.isAccessible = true
        val executor = ctor.newInstance(null, com.example.myapplication.data.repository.LlmProviderConfig.disabledDefault())

        val text = """
            ```json
            {
              "severity": "WARNING",
              "summary": "Remote detected issue",
              "causes": ["Vacuum leak"],
              "recommendations": ["Inspect intake tract"]
            }
            ```
        """.trimIndent()

        val result = method.invoke(executor, text, input)
        val severity = result.javaClass.getDeclaredField("severity").apply { isAccessible = true }.get(result) as String
        val summary = result.javaClass.getDeclaredField("summary").apply { isAccessible = true }.get(result) as String
        val findingsJson = result.javaClass.getDeclaredField("findingsJson").apply { isAccessible = true }.get(result) as String
        val recommendationsJson = result.javaClass.getDeclaredField("recommendationsJson").apply { isAccessible = true }.get(result) as String

        assertTrue(severity == "WARNING")
        assertTrue(summary.contains("Remote detected issue"))
        assertTrue(JSONArray(findingsJson).toString().contains("Vacuum leak"))
        assertTrue(JSONArray(recommendationsJson).toString().contains("Inspect intake tract"))
    }
}
