# VehicleRepository 修复

## ✅ 已修复的问题

### 问题 1: 缺少 List 导入
**症状：** `Unresolved reference: List`  
**原因：** `Flow<List<VehicleData>>` 返回类型需要导入 `java.util.List`  
**修复：**
```kotlin
// ✅ 已添加
import java.util.List
```

### 问题 2: 缺少断开连接方法
**症状：** 应用关闭时蓝牙连接未释放  
**原因：** 没有调用 `bluetoothManager.close()`  
**修复：**
```kotlin
/**
 * 断开蓝牙连接
 */
fun disconnect() {
    bluetoothManager.close()
}
```

---

## 📋 VehicleRepository 完整结构

### 依赖注入
```kotlin
class VehicleRepository(
    private val bluetoothManager: ObdBluetoothManager,  // 蓝牙通信
    private val dao: VehicleDataDao                      // 数据库访问
)
```

### 公共方法

| 方法 | 返回类型 | 说明 |
|------|---------|------|
| `connectToDevice(device)` | `Boolean` | 连接 OBD2 设备 |
| `requestVehicleData()` | `VehicleData?` | 采集一次完整数据 |
| `startLiveDataStream()` | `Flow<VehicleData>` | 实时数据流 (500ms) |
| `getHistory()` | `Flow<List<VehicleData>>` | 获取历史记录 |
| `getHistoryByTimeRange()` | `Flow<List<VehicleData>>` | 时间范围查询 |
| `cleanOldData()` | `Unit` | 清理 30 天前数据 |
| `disconnect()` | `Unit` | 断开蓝牙连接 ✅ |

---

## 🔍 数据采集流程

```
startLiveDataStream() (每 500ms)
    ↓
requestVehicleData()
    ↓
[核心参数 5 个]
  1. RPM (010C)
  2. Coolant Temp (0105)
  3. Intake Temp (010F)
  4. Throttle Pos (0111)
  5. Battery Voltage (0142)
    ↓
[扩展参数 16 个]
  6. Engine Load (0104)
  7. Speed (010D)
  8. MAP (010B)
  9. MAF (0110)
  10. Fuel Pressure (010A)
  11. Fuel Level (012F)
  12. STFT Bank 1 (0106)
  13. LTFT Bank 1 (0107)
  14. STFT Bank 2 (0108)
  15. LTFT Bank 2 (0109)
  16. Timing Advance (010E)
  17. Lambda (0124)
  18. Accelerator Pedal (012C)
  19. Run Time (011F)
  20. Warm-ups (0131)
  21. Time Since DTC (0133)
    ↓
VehicleData (21 字段)
    ↓
emit() → UI 更新
insert() → 数据库存储
```

---

## 🛠️ 错误处理

### 核心参数失败
```kotlin
val rpm = ObdDecoder.parse(rpmResponse, ObdCommand.RPM)?.toInt() 
    ?: return@withContext null  // 立即返回 null
```

### 扩展参数失败
```kotlin
val engineLoad = ObdDecoder.parse(loadResponse, ObdCommand.ENGINE_LOAD) 
    ?: 0.0  // 使用默认值
```

---

## 📊 性能优化

### 1. 协程调度
```kotlin
suspend fun requestVehicleData(): VehicleData? = withContext(Dispatchers.IO) {
    // 所有蓝牙和数据库操作在 IO 线程
}
```

### 2. Flow 背压处理
```kotlin
fun startLiveDataStream(): Flow<VehicleData> = flow {
    while (true) {
        val data = requestVehicleData()
        if (data != null) {
            emit(data)
            dao.insert(data)
        }
        delay(500)  // 控制采样频率
    }
}
```

### 3. 连接管理
```kotlin
// 应用关闭时调用
fun disconnect() {
    bluetoothManager.close()  // 释放蓝牙资源
}
```

---

## 🔗 与其他层的关系

```
UI Layer (Activity/Fragment)
    ↓ observes
Repository Layer (VehicleRepository)
    ↓ uses
├── Bluetooth Layer (ObdBluetoothManager)
└── Data Layer (VehicleDataDao)
        ↓
    Room Database
```

---

## 🐛 常见问题

### Q1: 数据不更新
**原因：** Flow 未正确观察  
**解决：**
```kotlin
lifecycleScope.launch {
    repository.startLiveDataStream().collect { data ->
        updateUI(data)
    }
}
```

### Q2: 蓝牙连接失败
**原因：** 权限未授予或设备未配对  
**解决：**
```kotlin
val connected = repository.connectToDevice(device)
if (!connected) {
    // 显示错误提示
}
```

### Q3: 数据库写入慢
**原因：** 在主线程写入  
**解决：** Room 自动在 IO 线程执行，无需额外处理

---

## ✅ 测试方法

### 单元测试
```kotlin
@Test
fun testRequestVehicleData() = runBlocking {
    val data = repository.requestVehicleData()
    assertNotNull(data)
    assertTrue(data.rpm > 0)
}
```

### 集成测试
```kotlin
@Test
fun testLiveDataStream() = runBlocking {
    var count = 0
    repository.startLiveDataStream().take(10).collect {
        count++
    }
    assertEquals(10, count)
}
```

---

## 📦 提交信息

**Commit:** `4d0cdee`  
**分支:** `extended-pids-21`  
**状态:** ✅ 已推送到 GitHub

---

**最后更新：** 2026-04-08  
**修复版本：** v1.0
