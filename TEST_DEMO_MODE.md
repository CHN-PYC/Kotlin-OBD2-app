# Try Demo Mode 功能测试指南

## 📋 功能说明

**Try Demo Mode** 卡片允许用户无需 OBD2 设备即可体验 Dashboard 功能。

---

## 🎯 测试步骤

### 步骤 1：从 GitHub 拉取最新代码

```bash
# 克隆或更新仓库
git clone https://github.com/CHN-PYC/Kotlin-OBD2-app.git
cd Kotlin-OBD2-app
git checkout extended-pids-21
git pull origin extended-pids-21
```

### 步骤 2：编译项目

```bash
# 清理并编译
./gradlew clean
./gradlew assembleDebug

# APK 位置
app/build/outputs/apk/debug/app-debug.apk
```

### 步骤 3：安装到设备

```bash
# 通过 ADB 安装
adb install -r app/build/outputs/apk/debug/app-debug.apk

# 或者手动传输 APK 到手机安装
```

### 步骤 4：测试 Try Demo Mode

```
1. 打开应用
2. 在主页看到三张卡片：
   - Connect to Car
   - Try Demo Mode ← 点击这个
   - View History

3. 点击 "Try Demo Mode" 卡片
4. 应该跳转到 Dashboard
5. 看到提示："🎉 Demo Mode Enabled"
6. 数据开始自动更新
7. RPM 图表开始绘制
```

---

## ✅ 预期行为

### 主页 (MainActivity)

```
┌─────────────────────────────────┐
│  OBD2 Monitor        12:34     │
├─────────────────────────────────┤
│                                 │
│  [🔵 Connect to Car]           │
│  Connect to your vehicle's...  │
│                                 │
│  [📊 Try Demo Mode] ← 点击这个  │
│  Explore the app with...       │
│  (no device needed)            │
│                                 │
│  [📜 View History]             │
│  Review past trip data...      │
│                                 │
└─────────────────────────────────┘
```

### Dashboard (Demo Mode)

```
┌─────────────────────────────────┐
│ ℹ️  🔄  📤  OBD2 Demo Mode     │
│ 📊 Simulation Active (蓝色)     │
├─────────────────────────────────┤
│                                 │
│  [RPM]     [Coolant]           │
│  2,450     85 °C               │
│  Normal    Normal              │
│                                 │
│  [Battery] [Intake]            │
│  14.2 V    35 °C               │
│  Normal    Normal              │
│                                 │
│  RPM History Chart              │
│  ╱╲╱╲╱╲╱╲                      │
│                                 │
│  Session Stats                  │
│  Avg: 2,400  Max: 3,800  02:34 │
│                                 │
└─────────────────────────────────┘
```

---

## 🔍 代码实现

### MainActivity.kt

```kotlin
// Demo Mode Card 点击处理
binding.cardDemoMode.setOnClickListener {
    // Launch Dashboard with simulation mode enabled
    val intent = Intent(
        this, 
        com.example.myapplication.ui.dashboard.DashboardActivity::class.java
    )
    intent.putExtra("simulation_mode", true)
    startActivity(intent)
    overridePendingTransition(R.anim.slide_in_right, R.anim.slide_out_left)
}
```

### DashboardActivity.kt

```kotlin
override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    try {
        binding = DashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Check if launched in simulation mode from MainActivity
        isSimulationMode = intent.getBooleanExtra("simulation_mode", false)
        
        // ... 其他初始化
        
        // If launched in simulation mode, show confirmation
        if (isSimulationMode) {
            Toast.makeText(this, "🎉 Demo Mode Enabled", Toast.LENGTH_SHORT).show()
        }
    } catch (e: Exception) {
        e.printStackTrace()
        Toast.makeText(this, "Error: ${e.message}", Toast.LENGTH_LONG).show()
        finish()
    }
}

// 数据观察
private fun observeData() {
    lifecycleScope.launch {
        val dataFlow = if (isSimulationMode) {
            SimulatedDataManager.startSimulation()
        } else {
            repository.startLiveDataStream()
        }
        
        dataFlow.collect { data ->
            updateUI(data)
            updateChart(data)
            updateSessionStats(data)
        }
    }
}
```

---

## 🐛 常见问题排查

### 问题 1：点击卡片没反应

**检查：**
```bash
# 查看 Logcat 日志
adb logcat | grep -i "dashboard\|demo"
```

**可能原因：**
- cardDemoMode 未正确初始化
- Intent 创建失败
- DashboardActivity 未在 Manifest 中注册

**解决：**
```xml
<!-- AndroidManifest.xml -->
<activity android:name=".ui.dashboard.DashboardActivity" />
```

### 问题 2：Dashboard 闪退

**检查：**
```bash
adb logcat | grep -i "crash\|exception"
```

**可能原因：**
- ViewBinding 初始化失败
- SimulatedDataManager 未找到
- 资源文件缺失

**解决：**
```kotlin
// 添加 try-catch
try {
    binding = DashboardBinding.inflate(layoutInflater)
    setContentView(binding.root)
} catch (e: Exception) {
    e.printStackTrace()
    Toast.makeText(this, "Error: ${e.message}", Toast.LENGTH_LONG).show()
    finish()
}
```

### 问题 3：数据不更新

**检查：**
```bash
adb logcat | grep -i "simulation\|data"
```

**可能原因：**
- isSimulationMode 未正确设置
- SimulatedDataManager.startSimulation() 未调用
- Flow collect 未执行

**解决：**
```kotlin
// 确认 simulation_mode extra 被正确传递
isSimulationMode = intent.getBooleanExtra("simulation_mode", false)
Log.d("Dashboard", "Simulation mode: $isSimulationMode")
```

---

## 📊 模拟数据特性

### 数据更新频率

```
500ms (每秒 2 次)
```

### 参数范围

| 参数 | 范围 | 说明 |
|------|------|------|
| **RPM** | 800-6000 | 平滑变化 |
| **冷却液** | 20°C → 90°C | 冷启动升温 |
| **进气温度** | 30-45°C | 环境波动 |
| **节气门** | 0-100% | 根据模式 |
| **电池电压** | 14.0-14.4V | 稳定 |

### 自动模式切换

```
怠速 (Idle)
   ↓ 5% 概率
巡航 (Cruising)
   ↓ 5% 概率
加速 (Accelerating)
   ↓ 5% 概率
高转速 (High RPM)
   ↓ 循环
```

---

## 🎯 测试检查清单

- [ ] 主页显示 "Try Demo Mode" 卡片
- [ ] 点击卡片跳转到 Dashboard
- [ ] 显示 "🎉 Demo Mode Enabled" 提示
- [ ] 标题显示 "OBD2 Demo Mode"
- [ ] 连接状态显示 "📊 Simulation Active"（蓝色）
- [ ] RPM 数据开始更新
- [ ] 图表开始绘制曲线
- [ ] 会话统计开始计时
- [ ] 状态指示器显示 "Normal"（绿色）
- [ ] 点击 ℹ️ 按钮可以关闭模拟模式
- [ ] 底部导航可以切换页面

---

## 📱 截图位置

测试时建议截图以下页面：
1. 主页（显示 Try Demo Mode 卡片）
2. Dashboard（Demo Mode 启用状态）
3. RPM 图表（数据流动）
4. 会话统计

---

## 🚀 下一步

测试通过后：
1. 提交测试反馈
2. 可以添加更多模拟模式
3. 优化数据生成算法
4. 添加教程提示

---

**最后更新：** 2026-04-09  
**版本：** v1.0  
**分支：** extended-pids-21
