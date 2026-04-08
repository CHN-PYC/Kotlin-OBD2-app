package com.example.myapplication.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

/**
 * Room 数据库实现
 * 存储车辆 OBD2 数据
 */
@Database(
    entities = [VehicleData::class],
    version = 1,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    
    /**
     * 获取 VehicleDataDao 实例
     */
    abstract fun vehicleDataDao(): VehicleDataDao

    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null

        /**
         * 获取数据库单例实例
         * @param context Android 上下文
         * @return AppDatabase 实例
         */
        fun getDatabase(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "obd_database"
                )
                    .fallbackToDestructiveMigration() // 允许破坏性迁移
                    .build()
                INSTANCE = instance
                instance
            }
        }
    }
}
