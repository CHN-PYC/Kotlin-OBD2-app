package com.example.myapplication.ui.history

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Intent
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.text.SpannableString
import android.text.Spanned
import android.text.style.BackgroundColorSpan
import android.text.style.ForegroundColorSpan
import android.text.style.StyleSpan
import android.text.method.LinkMovementMethod
import android.view.View
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.cardview.widget.CardView
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.example.myapplication.MyApplication
import com.example.myapplication.R
import com.example.myapplication.data.repository.ClaimSupport
import com.example.myapplication.data.repository.VehicleQaClaim
import com.example.myapplication.data.repository.VehicleQaClaimParser
import com.example.myapplication.databinding.ActivityDiagnosticReportBinding
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class DiagnosticReportActivity : AppCompatActivity() {

    private lateinit var binding: ActivityDiagnosticReportBinding
    private var rawExpanded = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDiagnosticReportBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnBack.setOnClickListener { finish() }
        binding.btnToggleRaw.setOnClickListener {
            rawExpanded = !rawExpanded
            binding.tvRawOutput.maxLines = if (rawExpanded) Int.MAX_VALUE else 14
            binding.btnToggleRaw.text = if (rawExpanded) "Show less" else "Show more"
        }

        val reportId = intent.getLongExtra(EXTRA_REPORT_ID, -1L)
        val reportType = intent.getStringExtra(EXTRA_REPORT_TYPE)

        if (reportId <= 0L) {
            binding.tvSummary.text = "Missing report id"
            return
        }

        lifecycleScope.launch {
            val repository = (application as MyApplication).diagnosticRepository
            val report = repository.getReportById(reportId)
            if (report == null) {
                binding.tvSummary.text = "No diagnostic report found for this session yet."
                return@launch
            }

            binding.tvTitle.text = reportType ?: "Diagnostic Report"
            binding.tvTimestamp.text = SimpleDateFormat("MM-dd HH:mm", Locale.getDefault())
                .format(Date(report.createdAt))
            binding.tvSeverity.text = report.severity
            applySeverityBadge(report.severity)
            binding.tvMeta.text = listOfNotNull(
                report.reportType,
                report.modelName?.takeIf { it.isNotBlank() },
                report.modelVersion?.takeIf { it.isNotBlank() }
            ).joinToString(" • ")
            binding.tvSummary.text = report.summary
            val claims = VehicleQaClaimParser.parse(report.rawOutputText)
            renderClaims(claims)
            renderFindings(report.findingsJson, skipPlainFindings = claims.isNotEmpty())
            val recommendationsText = if (claims.isNotEmpty()) {
                // Check claims already appear above with their evidence; avoid showing them twice.
                binding.tvFindingsHeader.text = "Agent details"
                binding.tvRecommendationsHeader.visibility = View.GONE
                binding.containerRecommendations.visibility = View.GONE
                claimsShareText(claims)
            } else {
                renderRecommendations(report.recommendationsJson)
            }
            val rawText = report.rawOutputText ?: report.rawInputSnapshotJson ?: "No raw output"
            renderSources(report.rawOutputText)
            val inputText = report.rawInputSnapshotJson ?: "No input snapshot"
            binding.tvRawOutput.text = rawText
            binding.btnCopyRaw.setOnClickListener { copyToClipboard("diagnostic_raw", rawText) }
            binding.btnCopyInput.setOnClickListener { copyToClipboard("diagnostic_input", inputText) }
            binding.btnCopyPrompt.setOnClickListener {
                lifecycleScope.launch {
                    try {
                        val prompt = repository.buildLlmPromptText(report.sessionId)
                        copyToClipboard("diagnostic_prompt", prompt)
                    } catch (e: Exception) {
                        Toast.makeText(this@DiagnosticReportActivity, "Prompt unavailable: ${e.message}", Toast.LENGTH_SHORT).show()
                    }
                }
            }
            binding.btnShareSummary.setOnClickListener {
                shareText("${report.summary}\n\n$recommendationsText")
            }
        }
    }

    private fun applySeverityBadge(severity: String) {
        when (severity) {
            "HIGH", "WARNING" -> {
                binding.tvSeverity.setBackgroundResource(R.drawable.badge_warning)
                binding.tvSeverity.setTextColor(getColor(R.color.background_dark))
            }
            "NOTICE" -> {
                binding.tvSeverity.setBackgroundResource(R.drawable.badge_info)
                binding.tvSeverity.setTextColor(getColor(R.color.white))
            }
            else -> {
                binding.tvSeverity.setBackgroundResource(R.drawable.badge_success)
                binding.tvSeverity.setTextColor(getColor(R.color.background_dark))
            }
        }
    }

    private fun renderFindings(json: String, skipPlainFindings: Boolean = false) {
        binding.containerFindings.removeAllViews()
        val items = parseJsonArray(json).filterNot { item ->
            skipPlainFindings && item is JSONObject && item.optString("title") == "Finding"
        }
        if (items.isEmpty()) {
            binding.containerFindings.addView(buildTextCard("No findings", null, null))
            return
        }
        items.forEach { item ->
            if (item is JSONObject) {
                val kind = item.optString("kind").ifBlank { "observation" }
                val title = when (kind) {
                    "hypothesis" -> "Hypothesis"
                    "note" -> "Guardrail note"
                    else -> item.optString("title").ifBlank { "Observation" }
                }
                binding.containerFindings.addView(
                    buildTextCard(
                        title,
                        item.optString("detail").ifBlank { null },
                        item.optString("severity").ifBlank { null }
                    )
                )
            } else if (item is String) {
                binding.containerFindings.addView(buildTextCard(item, null, null))
            }
        }
    }

    private fun renderClaims(claims: List<VehicleQaClaim>) {
        binding.containerClaims.removeAllViews()
        val visibility = if (claims.isEmpty()) View.GONE else View.VISIBLE
        binding.tvClaimsHeader.visibility = visibility
        binding.tvClaimsHint.visibility = visibility
        binding.containerClaims.visibility = visibility
        claims.forEach { binding.containerClaims.addView(buildClaimCard(it)) }
    }

    private fun claimsShareText(claims: List<VehicleQaClaim>): String =
        claims.joinToString("\n") { "• [${it.kind.label} | ${it.support.label}] ${it.text}" }

    private fun supportColor(support: ClaimSupport): Int = getColor(
        when (support) {
            ClaimSupport.QUOTED -> R.color.success
            ClaimSupport.CITED -> R.color.info
            ClaimSupport.VEHICLE_DATA -> R.color.accent
            ClaimSupport.UNSUPPORTED -> R.color.error
        }
    )

    private fun buildClaimCard(claim: VehicleQaClaim): CardView {
        val card = CardView(this).apply {
            radius = 18f
            cardElevation = 2f
            setCardBackgroundColor(ContextCompat.getColor(context, R.color.card_background))
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply { bottomMargin = 12 }
        }
        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 20, 24, 24)
        }

        val headerRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        headerRow.addView(TextView(this).apply {
            text = claim.kind.label.uppercase(Locale.ROOT)
            setTextColor(getColor(R.color.text_secondary))
            textSize = 11f
            setTypeface(typeface, Typeface.BOLD)
            layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
        })
        headerRow.addView(TextView(this).apply {
            text = claim.support.label
            textSize = 11f
            setTypeface(typeface, Typeface.BOLD)
            setTextColor(supportColor(claim.support))
            setPadding(14, 4, 14, 4)
            background = GradientDrawable().apply {
                cornerRadius = 40f
                setStroke(2, supportColor(claim.support))
            }
        })
        container.addView(headerRow)

        container.addView(TextView(this).apply {
            text = claim.text
            setTextColor(getColor(R.color.text_primary))
            textSize = 15f
            setPadding(0, 12, 0, 0)
        })

        container.addView(buildEvidenceBlock(claim))
        card.addView(container)
        return card
    }

    /** The passage (or the reason there is none) placed directly under the claim it relates to. */
    private fun buildEvidenceBlock(claim: VehicleQaClaim): View {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(0, 16, 0, 0)
        }
        row.addView(View(this).apply {
            setBackgroundColor(supportColor(claim.support))
            layoutParams = LinearLayout.LayoutParams(6, ViewGroup.LayoutParams.MATCH_PARENT).apply { rightMargin = 18 }
        })
        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
        }
        row.addView(column)

        fun note(message: String) = TextView(this).apply {
            text = message
            setTextColor(getColor(R.color.text_secondary))
            textSize = 12f
            setTypeface(typeface, Typeface.ITALIC)
        }

        val evidence = claim.evidence
        when {
            claim.support == ClaimSupport.VEHICLE_DATA -> column.addView(
                note("The model says this is based on your trip data. It was not compared with the recorded values.")
            )
            evidence == null -> column.addView(
                note("No retrieved passage is linked to this statement. Treat it as unverified.")
            )
            else -> {
                column.addView(TextView(this).apply {
                    text = "From: ${evidence.sourceTitle}"
                    setTextColor(getColor(R.color.text_secondary))
                    textSize = 12f
                    setTypeface(typeface, Typeface.BOLD)
                })
                val excerpt = VehicleQaClaimParser.excerpt(evidence)
                val passageView = TextView(this).apply {
                    text = highlighted(excerpt.text, excerpt.highlightStart, excerpt.highlightEnd)
                    setTextColor(getColor(R.color.text_secondary))
                    textSize = 13f
                    setPadding(0, 6, 0, 0)
                }
                column.addView(passageView)
                if (!evidence.hasQuote) {
                    column.addView(
                        note("No exact quote was found. Check whether this passage supports the statement.").apply {
                            setPadding(0, 8, 0, 0)
                        }
                    )
                }
                if (excerpt.truncated) {
                    var expanded = false
                    val toggle = TextView(this).apply {
                        text = "Show full passage"
                        setTextColor(getColor(R.color.accent))
                        textSize = 12f
                        setPadding(0, 10, 0, 0)
                    }
                    toggle.setOnClickListener {
                        expanded = !expanded
                        passageView.text = if (expanded) {
                            highlighted(evidence.passage, evidence.quoteStart, evidence.quoteEnd)
                        } else {
                            highlighted(excerpt.text, excerpt.highlightStart, excerpt.highlightEnd)
                        }
                        toggle.text = if (expanded) "Show less" else "Show full passage"
                    }
                    column.addView(toggle)
                }
            }
        }
        return row
    }

    private fun highlighted(text: String, start: Int, end: Int): CharSequence {
        if (start !in 0 until end || end > text.length) return text
        return SpannableString(text).apply {
            setSpan(BackgroundColorSpan(0x554CAF50), start, end, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            setSpan(ForegroundColorSpan(getColor(R.color.text_primary)), start, end, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            setSpan(StyleSpan(Typeface.BOLD), start, end, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        }
    }

    private fun renderRecommendations(json: String): String {
        binding.containerRecommendations.removeAllViews()
        val items = parseJsonArray(json)
        if (items.isEmpty()) {
            binding.containerRecommendations.addView(buildTextCard("No recommendations", null, null))
            return "No recommendations"
        }
        val lines = mutableListOf<String>()
        items.forEach { item ->
            val text = if (item is String) item else item.toString()
            lines += "• $text"
            binding.containerRecommendations.addView(buildTextCard(text, null, null))
        }
        return lines.joinToString("\n")
    }

    private fun renderSources(rawOutputText: String?) {
        binding.containerSources.removeAllViews()
        if (rawOutputText.isNullOrBlank()) {
            binding.tvSourcesHeader.visibility = View.GONE
            binding.containerSources.visibility = View.GONE
            return
        }

        val sources = parseSourcesFromRawOutput(rawOutputText)
        if (sources.isEmpty()) {
            binding.tvSourcesHeader.visibility = View.GONE
            binding.containerSources.visibility = View.GONE
            return
        }

        binding.tvSourcesHeader.visibility = View.VISIBLE
        binding.containerSources.visibility = View.VISIBLE

        sources.forEach { source ->
            binding.containerSources.addView(buildSourceCard(source))
        }
    }

    private fun parseSourcesFromRawOutput(rawOutputText: String): List<RetrievedSourceItem> {
        return try {
            val root = JSONObject(rawOutputText)
            val array = root.optJSONArray("sources") ?: return emptyList()
            buildList {
                for (i in 0 until array.length()) {
                    val item = array.optJSONObject(i) ?: continue
                    add(
                        RetrievedSourceItem(
                            title = item.optString("title").ifBlank {
                                item.optString("doc_id").ifBlank { "Source ${i + 1}" }
                            },
                            url = item.optString("source_url"),
                            scoreText = item.optDouble("score", Double.NaN)
                                .let { score -> if (score.isNaN()) "" else "score=${String.format("%.3f", score)}" },
                            preview = item.optString("text").take(240)
                        )
                    )
                }
            }
        } catch (_: Exception) {
            emptyList()
        }
    }

    private fun parseJsonArray(json: String): List<Any> {
        return try {
            val array = JSONArray(json)
            buildList {
                for (i in 0 until array.length()) add(array.get(i))
            }
        } catch (_: Exception) {
            listOf(json)
        }
    }

    private fun buildTextCard(title: String, detail: String?, severity: String?): CardView {
        val card = CardView(this).apply {
            radius = 18f
            cardElevation = 2f
            setCardBackgroundColor(ContextCompat.getColor(context, R.color.card_background))
            val params = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            )
            params.bottomMargin = 12
            layoutParams = params
        }

        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 24, 24, 24)
        }

        val headerRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
        }

        val titleView = TextView(this).apply {
            text = "• $title"
            setTextColor(ContextCompat.getColor(context, R.color.text_primary))
            textSize = 14f
            setTypeface(typeface, android.graphics.Typeface.BOLD)
            layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
        }
        headerRow.addView(titleView)

        if (!severity.isNullOrBlank()) {
            val severityView = TextView(this).apply {
                text = severity
                setPadding(12, 6, 12, 6)
                textSize = 11f
                setTypeface(typeface, android.graphics.Typeface.BOLD)
            }
            when (severity) {
                "HIGH", "WARNING" -> {
                    severityView.setBackgroundResource(R.drawable.badge_warning)
                    severityView.setTextColor(ContextCompat.getColor(this@DiagnosticReportActivity, R.color.background_dark))
                }
                "NOTICE" -> {
                    severityView.setBackgroundResource(R.drawable.badge_info)
                    severityView.setTextColor(ContextCompat.getColor(this@DiagnosticReportActivity, R.color.white))
                }
                else -> {
                    severityView.setBackgroundResource(R.drawable.badge_success)
                    severityView.setTextColor(ContextCompat.getColor(this@DiagnosticReportActivity, R.color.background_dark))
                }
            }
            headerRow.addView(severityView)
        }

        container.addView(headerRow)

        if (!detail.isNullOrBlank()) {
            val detailView = TextView(this).apply {
                text = detail
                setTextColor(ContextCompat.getColor(context, R.color.text_secondary))
                textSize = 13f
                setPadding(0, 10, 0, 0)
            }
            container.addView(detailView)
        }

        card.addView(container)
        return card
    }

    private fun buildSourceCard(source: RetrievedSourceItem): CardView {
        val card = CardView(this).apply {
            radius = 18f
            cardElevation = 2f
            setCardBackgroundColor(ContextCompat.getColor(context, R.color.card_background))
            val params = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            )
            params.bottomMargin = 12
            layoutParams = params
        }

        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 24, 24, 24)
        }

        val titleView = TextView(this).apply {
            text = "• ${source.title}"
            setTextColor(ContextCompat.getColor(context, R.color.text_primary))
            textSize = 14f
            setTypeface(typeface, android.graphics.Typeface.BOLD)
        }
        container.addView(titleView)

        if (source.url.isNotBlank()) {
            val urlView = TextView(this).apply {
                text = source.url
                setTextColor(ContextCompat.getColor(context, R.color.accent))
                textSize = 12f
                setPadding(0, 10, 0, 0)
                autoLinkMask = android.text.util.Linkify.WEB_URLS
                movementMethod = LinkMovementMethod.getInstance()
                linksClickable = true
            }
            container.addView(urlView)
        }

        if (source.scoreText.isNotBlank()) {
            val scoreView = TextView(this).apply {
                text = source.scoreText
                setTextColor(ContextCompat.getColor(context, R.color.text_secondary))
                textSize = 12f
                setPadding(0, 8, 0, 0)
            }
            container.addView(scoreView)
        }

        if (source.preview.isNotBlank()) {
            val previewView = TextView(this).apply {
                text = source.preview
                setTextColor(ContextCompat.getColor(context, R.color.text_secondary))
                textSize = 13f
                setPadding(0, 12, 0, 0)
            }
            container.addView(previewView)
        }

        card.addView(container)
        return card
    }

    private fun copyToClipboard(label: String, text: String) {
        val clipboard = getSystemService(ClipboardManager::class.java)
        clipboard.setPrimaryClip(ClipData.newPlainText(label, text))
        Toast.makeText(this, "Copied", Toast.LENGTH_SHORT).show()
    }

    private fun shareText(text: String) {
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_TEXT, text)
        }
        startActivity(Intent.createChooser(intent, "Share diagnosis"))
    }

    companion object {
        const val EXTRA_REPORT_ID = "report_id"
        const val EXTRA_REPORT_TYPE = "report_type"
    }

    private data class RetrievedSourceItem(
        val title: String,
        val url: String,
        val scoreText: String,
        val preview: String
    )
}
