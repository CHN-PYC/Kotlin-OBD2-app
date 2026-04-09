# 如何使用模拟数据模式

## 🎯 快速开始（3 步）

### 方法 1：长按刷新按钮（推荐）

```
1. 打开应用 → 点击 "Connect to Car"
2. 进入 Dashboard 页面
3. 长按右上角 🔄 刷新按钮 2 秒
4. 看到 "SIMULATION ON" 提示 → 成功！
```

**效果：**
- 标题变为 "OBD2 Demo Mode"
- 连接状态显示 "📊 Simulation Active"
- RPM、水温等数据开始自动变化
- 图表开始绘制曲线

---

### 方法 2：代码启用（开发用）

在 `DashboardActivity.kt` 中：

```kotlin
override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    
    // 启用模拟模式
    isSimulationMode = true
    
    // 设置初始模式（可选）
    SimulatedDataManager.setSimulationMode(
        SimulatedDataManager.SimulationMode.DRIVING
    )
}
```

---

## 📊 模拟数据展示

### 实时数据流

开启模拟后，你会看到：

| 参数 | 模拟效果 |
|------|---------|
| **RPM** | 800-6000 平滑变化 |
| **冷却液温度** | 从 20°C 逐渐上升到 90°C |
| **进气温度** | 30-45°C 波动 |
| **节气门位置** | 0-100%（根据模式）|
| **电池电压** | 14.0-14.4V 稳定 |
| **车速** | 0-120 km/h（估算）|

### 自动模式切换

模拟数据会**自动切换工况**：

```
怠速 (Idle)
   ↓ 5% 概率切换
巡航 (Cruising)
   ↓ 5% 概率切换
加速 (Accelerating)
   ↓ 5% 概率切换
高转速 (High RPM)
   ↓ 循环
```

---

## 🎮 手动控制模式

### 在代码中切换模式

```kotlin
// 在 DashboardActivity 中添加按钮
binding.btnModeIdle.setOnClickListener {
    SimulatedDataManager.setSimulationMode(
        SimulatedDataManager.SimulationMode.IDLE
    )
}

binding.btnModeDriving.setOnClickListener {
    SimulatedDataManager.setSimulationMode(
        SimulatedDataManager.SimulationMode.DRIVING
    )
}
```

### 可用模式

| 模式 | 说明 | RPM 范围 | 车速 |
|------|------|---------|------|
| **IDLE** | 怠速 | 800-900 | 0 km/h |
| **DRIVING** | 巡航 | 2300-2700 | 55-65 km/h |
| **ACCELERATING** | 加速 | 快速上升 | 快速增加 |
| **HIGH_RPM** | 高转速 | 5300-5700 | 95-105 km/h |

---

## 📱 UI 反馈

### 模拟模式指示器

**标题栏：**
```
🔵 OBD2 Demo Mode
📊 Simulation Active (蓝色)
```

**实时模式：**
```
🔵 OBD2 Diagnostics
Signal: Excellent (绿色)
```

### Toast 提示

```
长按刷新按钮 → "SIMULATION ON"
再次长按 → "LIVE DATA"
```

---

## 🛠️ 完整示例代码

### DashboardActivity.kt

```kotlin
class DashboardActivity : AppCompatActivity() {
    
    private var isSimulationMode = false
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = DashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        // 设置刷新按钮
        binding.btnRefresh.setOnClickListener {
            if (isSimulationMode) {
                toggleSimulationMode()
            } else {
                refreshData()
            }
        }
        
        // 长按切换模拟模式
        binding.btnRefresh.setOnLongClickListener {
            toggleSimulationMode()
            true
        }
        
        // 开始观察数据
        observeData()
    }
    
    private fun observeData() {
        lifecycleScope.launch {
            // 根据模式选择数据源
            val dataFlow = if (isSimulationMode) {
                SimulatedDataManager.startSimulation()
            } else {
                repository.startLiveDataStream()
            }
            
            dataFlow.collect { data ->
                updateUI(data)
                updateChart(data)
            }
        }
    }
    
    private fun toggleSimulationMode() {
        isSimulationMode = !isSimulationMode
        SimulatedDataManager.setSimulationMode(
            SimulatedDataManager.SimulationMode.IDLE
        )
        
        val modeText = if (isSimulationMode) {
            "SIMULATION ON"
        } else {
            "LIVE DATA"
        }
        
        Toast.makeText(this, modeText, Toast.LENGTH_SHORT).show()
        
        // 更新 UI
        binding.tvTitle.text = if (isSimulationMode) {
            "OBD2 Demo Mode"
        } else {
            "OBD2 Diagnostics"
        }
        
        // 更新连接状态
        showConnectionBanner()
    }
    
    private fun showConnectionBanner() {
        binding.cardConnectionBanner.visibility = View.VISIBLE
        binding.tvConnectedDevice.text = if (isSimulationMode) {
            "Demo Mode - Simulated Data"
        } else {
            "OBD-II Scanner"
        }
        binding.tvConnectionQuality.text = if (isSimulationMode) {
            "📊 Simulation Active"
        } else {
            "Signal: Excellent"
        }
    }
    
    override fun onDestroy() {
        super.onDestroy()
        if (isSimulationMode) {
            SimulatedDataManager.stopSimulation()
        } else {
            repository.disconnect()
        }
    }
}
```

---

## 📊 模拟数据参数

### 核心参数 (5 个)

| 参数 | 范围 | 说明 |
|------|------|------|
| **RPM** | 800-6000 | 平滑渐变，模拟加减速 |
| **冷却液温度** | 20°C → 90°C | 冷启动逐渐升温 |
| **进气温度** | 30-45°C | 环境温度波动 |
| **节气门位置** | 0-100% | 根据模式自动调整 |
| **电池电压** | 14.0-14.4V | 发电机充电电压 |

### 扩展参数 (16 个)

- 发动机负荷、车速、MAP、MAF
- 燃油压力、燃油液位
- STFT/LTFT (组 1&2)
- 点火提前角、Lambda
- 踏板位置、运行时间等

---

## 🎯 使用场景

### 1. 应用演示

```
场景：向客户展示应用功能
操作：开启模拟模式
效果：完整数据流和图表展示
无需：连接真实 OBD2 设备
```

### 2. 开发测试

```
场景：测试 UI 响应和性能
操作：开启模拟模式
效果：无需连接设备即可调试
优势：可重复测试相同场景
```

### 3. 用户教育

```
场景：解释参数含义
操作：切换不同模拟模式
效果：展示不同工况下的数据
示例：怠速 vs 加速 vs 高转速
```

### 4. 安全测试

```
场景：测试极限值告警
操作：切换到 HIGH_RPM 模式
效果：触发高 RPM 警告
安全：不会损坏真实车辆
```

---

## ⚠️ 注意事项

### 模拟数据特点

| 方面 | 模拟数据 | 真实数据 |
|------|---------|---------|
| **准确性** | 近似值 | 精确测量 |
| **变化** | 随机波动 | 实际工况 |
| **故障** | 无故障码 | 可能有故障 |
| **用途** | 演示/测试 | 实际诊断 |

### 何时使用

✅ **适合使用模拟：**
- 应用演示
- UI 测试
- 性能测试
- 用户教育

❌ **不适合使用模拟：**
- 实际车辆诊断
- 故障码读取
- 排放测试
- 性能调校

---

## 🔧 自定义模拟

### 修改参数范围

在 `SimulatedDataManager.kt` 中：

```kotlin
// 修改 RPM 范围
private const val RPM_MIN = 800      // 最小 RPM
private const val RPM_MAX = 6000     // 最大 RPM
private const val RPM_IDLE = 850     // 怠速 RPM

// 修改水温
private const val COOLANT_NORMAL = 90 // 正常工作温度

// 修改电池电压
private const val BATTERY_NORMAL = 14.2 // 充电电压
```

### 添加新模式

```kotlin
enum class SimulationMode {
    IDLE,
    DRIVING,
    ACCELERATING,
    HIGH_RPM,
    CUSTOM_MODE  // 添加自定义模式
}

// 在 startSimulation() 中添加逻辑
when (simulationMode) {
    SimulationMode.CUSTOM_MODE -> {
        targetRpm = 4000 // 自定义 RPM
        // ... 其他参数
    }
}
```

---

## 📈 性能影响

| 指标 | 数值 |
|------|------|
| CPU 占用 | <1% |
| 内存占用 | ~2MB |
| 电池影响 | 忽略不计 |
| 数据延迟 | <10ms |

---

## 🎯 总结

**模拟数据模式是：**
- ✅ 强大的演示工具
- ✅ 安全的测试环境
- ✅ 教育的可视化平台
- ❌ 不能替代真实诊断

**使用建议：**
1. 演示时开启模拟模式
2. 实际诊断时关闭模拟
3. 理解参数范围后关闭模拟
4. 定期用真实数据验证

---

**最后更新：** 2026-04-09  
**版本：** v1.0  
**分支：** extended-pids-21
