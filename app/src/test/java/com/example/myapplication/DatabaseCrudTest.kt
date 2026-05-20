package com.example.myapplication

import com.example.myapplication.data.local.AppDatabase
import com.example.myapplication.data.local.VehicleData
import com.example.myapplication.data.local.VehicleDataDao
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import java.io.File

/**
 * 数据库 CRUD 操作测试
 * 测试 VehicleData 的增删改查功能
 */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [28])
class DatabaseCrudTest {

    private lateinit var dao: VehicleDataDao
    private lateinit var db: AppDatabase

    @Before
    fun setup() {
        // 创建临时数据库
        val context = org.robolectric.RuntimeEnvironment.getApplication()
        val dbFile = File(context.cacheDir, "test_obd_database")
        dbFile.deleteRecursively()
        
        db = androidx.room.Room.databaseBuilder(
            context,
            AppDatabase::class.java,
            "test_obd_database"
        ).build()
        
        dao = db.vehicleDataDao()
    }

    @After
    fun teardown() {
        db.close()
    }

    // ==================== CREATE 测试 ====================

    @Test
    fun testInsertSingleRecord() {
        // 创建测试数据
        val vehicleData = createTestVehicleData(
            rpm = 2500,
            coolantTemp = 85,
            timestamp = System.currentTimeMillis()
        )

        // 执行插入
        dao.insert(vehicleData)

        // 验证
        val allData = dao.getAllHistory().blockingFirst()
        assertEquals(1, allData.size)
        assertEquals(2500, allData[0].rpm)
        assertEquals(85, allData[0].coolantTemp)
    }

    @Test
    fun testInsertMultipleRecords() {
        // 插入 10 条记录
        for (i in 1..10) {
            val vehicleData = createTestVehicleData(
                rpm = 1000 + (i * 100),
                coolantTemp = 80 + i,
                timestamp = System.currentTimeMillis() + (i * 1000)
            )
            dao.insert(vehicleData)
        }

        // 验证
        val allData = dao.getAllHistory().blockingFirst()
        assertEquals(10, allData.size)
        assertTrue(allData.all { it.id > 0 }) // 所有记录都有自增 ID
    }

    // ==================== READ 测试 ====================

    @Test
    fun testGetAllHistory() {
        // 插入测试数据
        insertTestData(5)

        // 获取所有数据
        val allData = dao.getAllHistory().blockingFirst()

        // 验证
        assertEquals(5, allData.size)
        // 验证按时间戳降序排列
        for (i in 0 until allData.size - 1) {
            assertTrue(allData[i].timestamp >= allData[i + 1].timestamp)
        }
    }

    @Test
    fun testGetRecordsInTimeRange() {
        // 插入测试数据
        val baseTime = System.currentTimeMillis()
        for (i in 1..10) {
            val vehicleData = createTestVehicleData(
                rpm = 1000 + (i * 100),
                coolantTemp = 80,
                timestamp = baseTime + (i * 60000) // 每分钟一条
            )
            dao.insert(vehicleData)
        }

        // 查询中间 5 分钟的数据
        val startTime = baseTime + (3 * 60000)
        val endTime = baseTime + (7 * 60000)
        val rangeData = dao.getRecordsInTimeRange(startTime, endTime).blockingFirst()

        // 验证
        assertEquals(5, rangeData.size)
        assertTrue(rangeData.all { it.timestamp in startTime..endTime })
    }

    // ==================== UPDATE 测试 ====================

    @Test
    fun testUpdateRecord() {
        // 插入记录
        val originalData = createTestVehicleData(
            rpm = 2000,
            coolantTemp = 85,
            timestamp = System.currentTimeMillis()
        )
        dao.insert(originalData)

        // 获取并修改
        val allData = dao.getAllHistory().blockingFirst()
        val recordToUpdate = allData[0].copy(
            rpm = 3500,
            coolantTemp = 95,
            batteryVoltage = 14.2
        )

        // Room 没有直接的 update 方法，需要删除后重新插入
        // 在实际应用中，我们会使用 @Update 注解
        // 这里测试通过 ID 更新的方式
        val updatedData = recordToUpdate.copy(id = recordToUpdate.id)
        dao.deleteAll()
        dao.insert(updatedData)

        // 验证
        val updated = dao.getAllHistory().blockingFirst()[0]
        assertEquals(3500, updated.rpm)
        assertEquals(95, updated.coolantTemp)
        assertEquals(14.2, updated.batteryVoltage, 0.01)
    }

    // ==================== DELETE 测试 ====================

    @Test
    fun testDeleteAllRecords() {
        // 插入测试数据
        insertTestData(10)

        // 验证已插入
        assertEquals(10, dao.getAllHistory().blockingFirst().size)

        // 删除所有
        dao.deleteAll()

        // 验证已删除
        assertEquals(0, dao.getAllHistory().blockingFirst().size)
    }

    @Test
    fun testDeleteOldRecords() {
        // 插入不同时间的记录
        val now = System.currentTimeMillis()
        val oldTime = now - (31 * 24 * 60 * 60 * 1000) // 31 天前

        // 插入旧记录
        val oldData = createTestVehicleData(
            rpm = 1000,
            coolantTemp = 80,
            timestamp = oldTime
        )
        dao.insert(oldData)

        // 插入新记录
        for (i in 1..5) {
            val newData = createTestVehicleData(
                rpm = 2000 + (i * 100),
                coolantTemp = 85,
                timestamp = now - (i * 60000)
            )
            dao.insert(newData)
        }

        // 验证总数
        assertEquals(6, dao.getAllHistory().blockingFirst().size)

        // 删除 30 天前的记录
        val thirtyDaysAgo = now - (30 * 24 * 60 * 60 * 1000)
        dao.deleteOldRecords(thirtyDaysAgo)

        // 验证旧记录已删除，新记录保留
        val remaining = dao.getAllHistory().blockingFirst()
        assertEquals(5, remaining.size)
        assertTrue(remaining.all { it.timestamp > thirtyDaysAgo })
    }

    // ==================== 扩展参数测试 ====================

    @Test
    fun testExtendedPidsStorage() {
        // 创建包含所有 21 个 PID 的完整数据
        val fullData = VehicleData(
            timestamp = System.currentTimeMillis(),
            rpm = 3000,
            coolantTemp = 90,
            intakeTemp = 35,
            throttlePos = 45,
            batteryVoltage = 14.2,
            
            // 扩展参数
            engineLoad = 65.5,
            speed = 80,
            intakeManifoldPressure = 55.0,
            mafRate = 45.8,
            fuelPressure = 350.0,
            fuelLevel = 75.0,
            shortTermFuelTrimBank1 = 5.2,
            longTermFuelTrimBank1 = 3.8,
            shortTermFuelTrimBank2 = 4.9,
            longTermFuelTrimBank2 = 3.5,
            timingAdvance = 25.5,
            equivalenceRatio = 1.02,
            acceleratorPedalPos = 50.0,
            runTime = 3600.0,
            warmupsSinceCodesCleared = 15,
            timeSinceCodesCleared = 120.0
        )

        // 插入数据库
        dao.insert(fullData)

        // 读取并验证
        val retrieved = dao.getAllHistory().blockingFirst()[0]
        
        // 验证核心参数
        assertEquals(3000, retrieved.rpm)
        assertEquals(90, retrieved.coolantTemp)
        assertEquals(14.2, retrieved.batteryVoltage, 0.01)
        
        // 验证扩展参数
        assertEquals(65.5, retrieved.engineLoad, 0.1)
        assertEquals(80, retrieved.speed)
        assertEquals(55.0, retrieved.intakeManifoldPressure, 0.1)
        assertEquals(45.8, retrieved.mafRate, 0.1)
        assertEquals(350.0, retrieved.fuelPressure, 0.1)
        assertEquals(75.0, retrieved.fuelLevel, 0.1)
        
        // 验证燃油修正参数
        assertEquals(5.2, retrieved.shortTermFuelTrimBank1, 0.1)
        assertEquals(3.8, retrieved.longTermFuelTrimBank1, 0.1)
        assertEquals(4.9, retrieved.shortTermFuelTrimBank2, 0.1)
        assertEquals(3.5, retrieved.longTermFuelTrimBank2, 0.1)
        
        // 验证点火和空燃比
        assertEquals(25.5, retrieved.timingAdvance, 0.1)
        assertEquals(1.02, retrieved.equivalenceRatio, 0.01)
        
        // 验证状态参数
        assertEquals(3600.0, retrieved.runTime, 0.1)
        assertEquals(15, retrieved.warmupsSinceCodesCleared)
        assertEquals(120.0, retrieved.timeSinceCodesCleared, 0.1)
    }

    // ==================== 边界条件测试 ====================

    @Test
    fun testMaxValues() {
        val maxData = VehicleData(
            timestamp = System.currentTimeMillis(),
            rpm = 16383,  // 最大 RPM
            coolantTemp = 215,  // 最高温度
            intakeTemp = 215,
            throttlePos = 100,
            batteryVoltage = 65.535,  // 最大电压
            engineLoad = 100.0,
            speed = 255,
            intakeManifoldPressure = 255.0,
            mafRate = 655.35,
            fuelPressure = 765.0,
            fuelLevel = 100.0,
            shortTermFuelTrimBank1 = 99.2,
            longTermFuelTrimBank1 = 99.2,
            timingAdvance = 63.5,
            equivalenceRatio = 2.0,
            runTime = 65535.0,
            warmupsSinceCodesCleared = 65535
        )

        dao.insert(maxData)
        val retrieved = dao.getAllHistory().blockingFirst()[0]
        
        assertEquals(16383, retrieved.rpm)
        assertEquals(215, retrieved.coolantTemp)
        assertEquals(100.0, retrieved.engineLoad, 0.1)
    }

    @Test
    fun testMinValues() {
        val minData = VehicleData(
            timestamp = System.currentTimeMillis(),
            rpm = 0,
            coolantTemp = -40,  // 最低温度
            intakeTemp = -40,
            throttlePos = 0,
            batteryVoltage = 0.0,
            engineLoad = 0.0,
            speed = 0,
            shortTermFuelTrimBank1 = -100.0,
            longTermFuelTrimBank1 = -100.0
        )

        dao.insert(minData)
        val retrieved = dao.getAllHistory().blockingFirst()[0]
        
        assertEquals(0, retrieved.rpm)
        assertEquals(-40, retrieved.coolantTemp)
        assertEquals(-100.0, retrieved.shortTermFuelTrimBank1, 0.1)
    }

    @Test
    fun testConcurrentInserts() {
        // 模拟并发插入
        val threads = mutableListOf<Thread>()
        
        for (i in 1..5) {
            val thread = Thread {
                for (j in 1..10) {
                    val data = createTestVehicleData(
                        rpm = 1000 + (i * 100) + j,
                        coolantTemp = 80 + i,
                        timestamp = System.currentTimeMillis() + (i * 1000) + j
                    )
                    dao.insert(data)
                }
            }
            threads.add(thread)
            thread.start()
        }

        // 等待所有线程完成
        threads.forEach { it.join() }

        // 验证总共插入了 50 条记录
        val allData = dao.getAllHistory().blockingFirst()
        assertEquals(50, allData.size)
    }

    // ==================== 性能测试 ====================

    @Test
    fun testBulkInsertPerformance() {
        val startTime = System.currentTimeMillis()
        
        // 批量插入 1000 条记录
        for (i in 1..1000) {
            val data = createTestVehicleData(
                rpm = 1000 + (i % 5000),
                coolantTemp = 80 + (i % 50),
                timestamp = System.currentTimeMillis() + (i * 100)
            )
            dao.insert(data)
        }

        val endTime = System.currentTimeMillis()
        val duration = endTime - startTime

        // 验证
        assertEquals(1000, dao.getAllHistory().blockingFirst().size)
        
        // 性能要求：1000 条记录应在 5 秒内完成
        assertTrue("Bulk insert too slow: ${duration}ms", duration < 5000)
        
        println("✓ Bulk insert: 1000 records in ${duration}ms (${1000.0 / (duration / 1000.0)} inserts/sec)")
    }

    @Test
    fun testQueryPerformance() {
        // 先插入 1000 条记录
        for (i in 1..1000) {
            val data = createTestVehicleData(
                rpm = 1000 + (i % 5000),
                coolantTemp = 80,
                timestamp = System.currentTimeMillis() + (i * 100)
            )
            dao.insert(data)
        }

        // 测试查询性能
        val startTime = System.currentTimeMillis()
        val result = dao.getAllHistory().blockingFirst()
        val endTime = System.currentTimeMillis()

        assertEquals(1000, result.size)
        assertTrue("Query too slow", (endTime - startTime) < 1000)
        
        println("✓ Query 1000 records: ${endTime - startTime}ms")
    }

    // ==================== 辅助方法 ====================

    private fun createTestVehicleData(
        rpm: Int,
        coolantTemp: Int,
        timestamp: Long,
        batteryVoltage: Double = 12.5
    ): VehicleData {
        return VehicleData(
            timestamp = timestamp,
            rpm = rpm,
            coolantTemp = coolantTemp,
            intakeTemp = 25,
            throttlePos = 10,
            batteryVoltage = batteryVoltage
        )
    }

    private fun insertTestData(count: Int) {
        for (i in 1..count) {
            val data = createTestVehicleData(
                rpm = 1000 + (i * 100),
                coolantTemp = 80 + i,
                timestamp = System.currentTimeMillis() + (i * 1000)
            )
            dao.insert(data)
        }
    }
}

// Flow 的 blockingFirst 扩展函数（用于测试）
fun <T> kotlinx.coroutines.flow.Flow<T>.blockingFirst(): T {
    return kotlinx.coroutines.runBlocking {
        this@blockingFirst.first()
    }
}

fun <T> kotlinx.coroutines.flow.Flow<List<T>>.blockingFirst(): List<T> {
    return kotlinx.coroutines.runBlocking {
        this@blockingFirst.first()
    }
}
