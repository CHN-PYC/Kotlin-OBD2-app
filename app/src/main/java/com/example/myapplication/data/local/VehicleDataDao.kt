package com.example.myapplication.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface VehicleDataDao {
    /**
     * 插入一条车辆数据
     * @param vehicleData 插入数据对象
     */
    @Insert
    suspend fun insert(vehicleDataDao: VehicleData)
    /**
     * 获取所有的历史记录，按时间戳降序
     */
    @Query("SELECT * FROM vehicle_data ORDER BY timestamp DESC")
    fun getAllHistory(): Flow<kotlin.collections.List<VehicleData>>

    /**
     * 删除早于指定时间戳的记录
     * @param cutoffTime 阈值时间戳（毫秒），早于此时间的记录将被删除
     */
    @Query("DELETE FROM vehicle_data WHERE timestamp < :cutoffTime")
    suspend fun deleteOldRecords(cutoffTime: Long)

    /**
     * 删除所有记录（用于用户手动清除数据）
     */
    @Query("DELETE FROM vehicle_data")
    suspend fun deleteAll()

    /**
     * 可选：根据时间范围查询
     * @param startTime 起始时间戳
     * @param endTime 结束时间戳
     */
    @Query("SELECT * FROM vehicle_data WHERE timestamp BETWEEN :startTime AND :endTime ORDER BY timestamp ASC")
    fun getRecordsInTimeRange(startTime: Long, endTime: Long): Flow<kotlin.collections.List<VehicleData>>
}