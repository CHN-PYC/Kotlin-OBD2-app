package com.example.myapplication.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "diagnostic_report")
data class DiagnosticReport(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val sessionId: Long,
    val createdAt: Long,
    val reportType: String,
    val modelName: String? = null,
    val modelVersion: String? = null,
    val promptVersion: String? = null,
    val severity: String,
    val summary: String,
    val findingsJson: String,
    val recommendationsJson: String,
    val rawInputSnapshotJson: String? = null,
    val rawOutputText: String? = null
) {
    companion object {
        const val TYPE_RULE_BASED = "RULE_BASED"
        const val TYPE_LLM = "LLM"
        const val TYPE_HYBRID = "HYBRID"

        const val SEVERITY_NORMAL = "NORMAL"
        const val SEVERITY_NOTICE = "NOTICE"
        const val SEVERITY_WARNING = "WARNING"
        const val SEVERITY_HIGH = "HIGH"
    }
}
