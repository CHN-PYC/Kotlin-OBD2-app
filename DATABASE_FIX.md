# AppDatabase 异常修复

## ✅ 已修复的问题

### 问题 1: 缺少包声明
**症状：** `Class not found` 或 `Package not found` 错误  
**原因：** `AppDatabase.kt` 文件顶部缺少 `package` 声明  
**修复：**
```kotlin
// ✅ 已添加
package com.example.myapplication.data.local
```

### 问题 2: Import 语句缺失
**症状：** `Unresolved reference: List`  
**原因：** `VehicleDataDao.kt` 缺少 `java.util.List` 导入  
**修复：**
```kotlin
// ✅ 已添加
import java.util.List
```

### 问题 3: 数据库迁移问题
**症状：** `IllegalStateException: Room cannot verify the data version`  
**原因：** 数据库 schema 变更但没有迁移策略  
**修复：**
```kotlin
Room.databaseBuilder(...)
    .fallbackToDestructiveMigration() // ✅ 允许破坏性迁移
    .build()
```

---

## 📋 完整的 AppDatabase.kt

```kotlin
package com.example.myapplication.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(
    entities = [VehicleData::class],
    version = 1,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    
    abstract fun vehicleDataDao(): VehicleDataDao

    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null

        fun getDatabase(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "obd_database"
                )
                    .fallbackToDestructiveMigration()
                    .build()
                INSTANCE = instance
                instance
            }
        }
    }
}
```

---

## 📋 完整的 VehicleDataDao.kt

```kotlin
package com.example.myapplication.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import kotlinx.coroutines.flow.Flow
import java.util.List

@Dao
interface VehicleDataDao {
    @Insert
    suspend fun insert(vehicleData: VehicleData)
    
    @Query("SELECT * FROM vehicle_data ORDER BY timestamp DESC")
    fun getAllHistory(): Flow<List<VehicleData>>
    
    @Query("DELETE FROM vehicle_data WHERE timestamp < :cutoffTime")
    suspend fun deleteOldRecords(cutoffTime: Long)
    
    @Query("DELETE FROM vehicle_data")
    suspend fun deleteAll()
    
    @Query("SELECT * FROM vehicle_data WHERE timestamp BETWEEN :startTime AND :endTime ORDER BY timestamp ASC")
    fun getRecordsInTimeRange(startTime: Long, endTime: Long): Flow<List<VehicleData>>
}
```

---

## 🔍 常见 Room 异常及解决方案

### 1. `Room cannot find implementation`
**原因：** KSP 处理器未正确配置  
**解决：**
```kotlin
// build.gradle.kts
plugins {
    id("com.google.devtools.ksp")
}

dependencies {
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    ksp("androidx.room:room-compiler:2.6.1")
}
```

### 2. `Database version mismatch`
**原因：** 数据库版本变更但没有迁移  
**解决：**
```kotlin
Room.databaseBuilder(context, AppDatabase::class.java, "obd_database")
    .fallbackToDestructiveMigration() // 测试期间使用
    // .addMigration(MIGRATION_1_2) // 生产环境使用
    .build()
```

### 3. `Cannot run invalidation tracker`
**原因：** Flow/LiveData 在主线程外使用  
**解决：** 确保在协程或生命周期作用域中观察

### 4. `Entity class doesn't have an accessible no-arg constructor`
**原因：** Entity 类缺少主键或构造函数  
**解决：**
```kotlin
@Entity(tableName = "vehicle_data")
data class VehicleData(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    // ... 其他字段
)
```

---

## 🛠️ 清理并重新编译

如果仍然有问题，执行以下命令：

```bash
# 1. 清理构建缓存
./gradlew clean

# 2. 删除旧的数据库文件（在手机上）
adb shell pm clear com.example.myapplication

# 3. 重新编译
./gradlew build

# 4. 重新安装
./gradlew installDebug
```

---

## 📊 数据库结构

**表名：** `vehicle_data`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER (PK) | 自增主键 |
| timestamp | INTEGER | 时间戳 |
| rpm | INTEGER | 发动机转速 |
| coolantTemp | INTEGER | 冷却液温度 |
| intakeTemp | INTEGER | 进气温度 |
| throttlePos | INTEGER | 节气门位置 |
| batteryVoltage | REAL | 电池电压 |
| engineLoad | REAL | 发动机负荷 |
| speed | INTEGER | 车速 |
| ... | ... | 其他 16 个扩展参数 |

---

## ✅ 验证修复

**编译检查：**
```bash
./gradlew build
```

**运行检查：**
1. 安装应用
2. 连接 OBD2 设备
3. 访问 Dashboard 页面
4. 访问 History 页面
5. 检查数据是否正常存储和读取

---

**最后更新：** 2026-04-08  
**修复版本：** v1.0  
**分支：** extended-pids-21
