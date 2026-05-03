package com.example.myapplication.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

@Dao
interface DiagnosticReportDao {

    @Insert
    suspend fun insert(report: DiagnosticReport): Long

    @Update
    suspend fun update(report: DiagnosticReport)

    @Query("SELECT * FROM diagnostic_report WHERE id = :reportId LIMIT 1")
    suspend fun getById(reportId: Long): DiagnosticReport?

    @Query("SELECT * FROM diagnostic_report WHERE sessionId = :sessionId ORDER BY createdAt DESC")
    fun getBySession(sessionId: Long): Flow<List<DiagnosticReport>>

    @Query("SELECT * FROM diagnostic_report WHERE sessionId = :sessionId ORDER BY createdAt DESC LIMIT 1")
    suspend fun getLatestBySession(sessionId: Long): DiagnosticReport?

    @Query("DELETE FROM diagnostic_report WHERE sessionId = :sessionId")
    suspend fun deleteBySession(sessionId: Long)
}
