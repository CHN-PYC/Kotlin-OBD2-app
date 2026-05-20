# 调试指南 - 应用闪退问题

## ✅ 已修复的闪退问题

### 问题 1: 权限前访问蓝牙 (Android 12+)
**症状：** 应用启动立即闪退  
**原因：** 在请求权限之前就访问了 `BluetoothAdapter`  
**修复：**
```kotlin
// ❌ 错误：在 onCreate 中直接访问
val bluetoothAdapter = getSystemService(BLUETOOTH_SERVICE) as BluetoothManager

// ✅ 正确：权限授予后才访问
private fun initializeBluetooth() {
    if (checkPermissions()) {
        bluetoothAdapter = getSystemService(...)
    }
}
```

### 问题 2: 数据库初始化失败
**症状：** 应用启动时崩溃  
**原因：** Room 数据库初始化可能失败  
**修复：** 添加 try-catch 包裹初始化代码

---

## 🔍 如果仍然闪退，请查看日志

### 方法 1: 使用 adb 查看日志
```bash
# 连接手机后运行
adb logcat -s com.example.myapplication

# 或者查看所有日志
adb logcat | grep -i "obd2\|myapplication\|crash"
```

### 方法 2: Android Studio Logcat
1. 打开 Android Studio
2. View → Tool Windows → Logcat
3. 过滤：`com.example.myapplication`
4. 级别：Error

### 方法 3: 手机开发者选项
1. 设置 → 开发者选项
2. 开启"USB 调试"
3. 连接电脑后使用 adb

---

## 📋 常见闪退原因

### 1. 权限问题 ⭐ 最常见
```xml
<!-- 确保 AndroidManifest.xml 包含 -->
<uses-permission android:name="android.permission.BLUETOOTH_SCAN" />
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
```

**检查：**
```bash
adb shell dumpsys package com.example.myapplication | grep permission
```

### 2. 蓝牙硬件不支持
```kotlin
// 代码已添加检查
if (bluetoothAdapter == null) {
    binding.tvStatus.text = "Bluetooth not supported"
}
```

### 3. Room 数据库问题
**症状：** `IllegalStateException: Room cannot find implementation`  
**解决：**
```bash
# 清理并重新编译
./gradlew clean
./gradlew build
```

### 4. ViewBinding 未启用
**症状：** `Cannot resolve symbol 'ActivityMainBinding'`  
**检查 build.gradle.kts：**
```kotlin
android {
    buildFeatures {
        viewBinding = true  // 必须启用
    }
}
```

### 5. 主题/样式问题
**症状：** `Resources$NotFoundException`  
**检查：**
- `res/values/themes.xml` 存在
- `res/values/colors.xml` 包含所有引用颜色

---

## 🛠️ 调试步骤

### 步骤 1: 检查应用是否安装
```bash
adb shell pm list packages | grep myapplication
```

### 步骤 2: 查看崩溃日志
```bash
adb logcat -d > crash_log.txt
```

### 步骤 3: 清除应用数据
```bash
adb shell pm clear com.example.myapplication
```

### 步骤 4: 重新安装
```bash
./gradlew uninstallDebug
./gradlew installDebug
```

### 步骤 5: 启动应用并监控
```bash
adb shell am start -n com.example.myapplication/.MainActivity
adb logcat -s com.example.myapplication
```

---

## 📱 手机设置要求

### Android 版本要求
- **最低：** Android 7.0 (API 24)
- **推荐：** Android 12+ (API 31+)

### 必须授予的权限
1. 蓝牙扫描
2. 蓝牙连接
3. 位置信息（Android 11 及以下）

### 开发者选项
```
设置 → 关于手机 → 版本号 (点击 7 次)
设置 → 开发者选项 → USB 调试 (开启)
```

---

## 🐛 已知问题

### 问题：连接蓝牙设备时闪退
**原因：** 未配对设备  
**解决：** 先在系统设置中配对 OBD2 适配器

### 问题：访问历史页面闪退
**原因：** 数据库为空  
**解决：** 已添加空状态处理，应该不再崩溃

---

## 📞 获取帮助

如果问题仍未解决，请提供：
1. 手机型号和 Android 版本
2. 完整的 logcat 日志
3. 闪退前的操作步骤

---

**最后更新：** 2026-04-08  
**版本：** v1.0  
**分支：** extended-pids-21
