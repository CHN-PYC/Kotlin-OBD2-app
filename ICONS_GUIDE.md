# 图标和按钮设计指南

## 🎨 应用图标

### 自适应图标 (Android 8.0+)

**位置：** `res/mipmap-anydpi-v26/`

```
ic_launcher.xml          → 标准图标
ic_launcher_round.xml    → 圆形图标
```

### 设计理念

```
┌─────────────────────────────┐
│        OBD2 图标             │
│  ┌──────────────────────┐   │
│  │   🔵 青色圆形背景     │   │
│  │   ⬜ 白色 OBD2 接口    │   │
│  │   📶 信号波纹         │   │
│  └──────────────────────┘   │
└─────────────────────────────┘
```

**元素说明：**
- **青色圆形** (#00BCD4) - 代表连接和科技
- **OBD2 接口** - 16 针诊断接口简化图形
- **信号波纹** - 代表无线连接和数据传输
- **深色背景** - 符合应用的深色主题

---

## 🔘 按钮样式系统

### 1️⃣ Primary Button (主要按钮)

**用途：** 主要操作（提交、确认、连接）

```xml
<style name="Widget.OBD2.Button.Primary">
    - 青色背景 (@color/accent)
    - 白色文字
    - 涟漪效果
    - 12dp 圆角
</style>
```

**使用示例：**
```xml
<Button
    style="@style/Widget.OBD2.Button.Primary"
    android:text="Connect" />
```

**视觉效果：**
```
┌─────────────────────────┐
│      Connect            │ ← 青色背景，白色文字
└─────────────────────────┘
     ↘ 点击涟漪效果
```

---

### 2️⃣ Secondary Button (次要按钮)

**用途：** 次要操作（取消、返回、更多选项）

```xml
<style name="Widget.OBD2.Button.Secondary">
    - 卡片背景 (@color/card_background)
    - 青色边框 (2dp)
    - 青色文字
    - 涟漪效果
</style>
```

**使用示例：**
```xml
<Button
    style="@style/Widget.OBD2.Button.Secondary"
    android:text="Cancel" />
```

**视觉效果：**
```
┌─────────────────────────┐
│      Cancel             │ ← 深色背景，青色边框
└─────────────────────────┘
```

---

### 3️⃣ Outline Button (轮廓按钮)

**用途：** 低优先级操作（跳过、稍后）

```xml
<style name="Widget.OBD2.Button.Outline">
    - 透明背景
    - 灰色边框 (2dp)
    - 灰色文字
</style>
```

**视觉效果：**
```
┌─────────────────────────┐
│      Skip               │ ← 仅边框，无背景
└─────────────────────────┘
```

---

### 4️⃣ Icon Button (图标按钮)

**用途：** 工具栏操作（刷新、导出、设置）

```xml
<style name="Widget.OBD2.Button.Icon">
    - 圆形 (48dp)
    - 卡片背景
    - 涟漪效果
    - 图标居中
</style>
```

**使用示例：**
```xml
<ImageButton
    style="@style/Widget.OBD2.Button.Icon"
    android:src="@drawable/ic_refresh" />
```

**视觉效果：**
```
┌──────┐
│  🔄  │ ← 圆形，图标居中
└──────┘
```

---

### 5️⃣ FAB (Floating Action Button)

**用途：** 页面主要操作（添加、扫描）

```xml
<style name="Widget.OBD2.Button.FAB">
    - 圆形 (56dp)
    - 青色背景
    - 阴影 (6dp)
    - 悬浮效果
</style>
```

**视觉效果：**
```
    ┌──────┐
    │  +   │ ← 悬浮，带阴影
    └──────┘
     阴影效果
```

---

### 6️⃣ Disabled Button (禁用按钮)

**用途：** 不可用状态

```xml
<style name="Widget.OBD2.Button.Disabled">
    - 灰色背景 (@color/text_hint)
    - 无交互
    - 半透明
</style>
```

**视觉效果：**
```
┌─────────────────────────┐
│      Connect (50%)      │ ← 灰色，半透明
└─────────────────────────┘
```

---

## 📐 尺寸规范

### 按钮尺寸

| 类型 | 高度 | 左右内边距 | 圆角 |
|------|------|-----------|------|
| Primary | 48dp | 24dp | 12dp |
| Secondary | 48dp | 24dp | 12dp |
| Outline | 48dp | 24dp | 12dp |
| Icon | 48dp | 12dp | 24dp (圆形) |
| FAB | 56dp | - | 28dp (圆形) |

### 文字大小

| 类型 | 大小 | 字重 |
|------|------|------|
| Button | 14sp | Bold |
| Title | 20sp | Bold |
| Subtitle | 14sp | Regular |
| Caption | 12sp | Regular |
| Metric | 28sp | Bold, Light |
| Status | 11sp | Bold |

---

## 🎨 颜色系统

### 按钮颜色状态

| 状态 | 背景色 | 文字色 |
|------|--------|--------|
| Normal | @color/accent | @color/white |
| Pressed | @color/accent_dark | @color/white |
| Disabled | @color/text_hint (50%) | @color/white (50%) |

### 语义颜色

| 含义 | 颜色 | 用途 |
|------|------|------|
| Success | #4CAF50 | 正常状态，连接成功 |
| Warning | #FFA726 | 警告状态 |
| Error | #EF5350 | 错误状态，危险 |
| Info | #42A5F5 | 信息提示 |

---

## 🎬 动画效果

### 涟漪效果 (Ripple)

所有按钮都包含 Material Design 涟漪效果：

```xml
<ripple android:color="@color/accent_dark">
    <item>
        <shape>...</shape>
    </item>
</ripple>
```

**效果：** 点击时从触摸点扩散的波纹

### 状态变化

```kotlin
// 按钮点击动画
button.setOnClickListener {
    val fadeIn = AnimationUtils.loadAnimation(context, R.anim.fade_in)
    button.startAnimation(fadeIn)
    // 执行操作
}
```

---

## 📱 使用示例

### MainActivity 按钮

```xml
<!-- 主要操作卡片 -->
<androidx.cardview.widget.CardView
    android:id="@+id/cardConnect"
    style="@style/Widget.OBD2.Card.Elevated"
    android:clickable="true"
    android:focusable="true"
    android:foreground="?attr/selectableItemBackground">
    
    <LinearLayout>
        <ImageView
            android:background="@drawable/badge_background" />
        <TextView style="@style/Widget.OBD2.Text.Title" />
    </LinearLayout>
</androidx.cardview.widget.CardView>
```

### Dashboard 工具栏按钮

```xml
<ImageButton
    android:id="@+id/btnRefresh"
    style="@style/Widget.OBD2.Button.Icon"
    android:src="@drawable/ic_refresh"
    app:tint="@color/accent" />
```

### 连接按钮

```xml
<Button
    android:id="@+id/btnConnect"
    style="@style/Widget.OBD2.Button.Primary"
    android:text="Connect to Device"
    android:layout_width="match_parent"
    android:layout_height="56dp" />
```

---

## ✅ 设计原则

1. **一致性** - 所有按钮使用统一的圆角 (12dp) 和高度 (48dp)
2. **层次性** - Primary > Secondary > Outline 的视觉层次
3. **反馈性** - 所有可点击元素都有涟漪效果
4. **可达性** - 最小点击区域 48x48dp
5. **美观性** - Material Design 3 规范，深色主题优化

---

## 📦 资源文件清单

### Drawable (8 个)
```
btn_primary.xml       - 主要按钮背景
btn_secondary.xml     - 次要按钮背景
btn_outline.xml       - 轮廓按钮背景
btn_icon.xml          - 图标按钮背景
btn_fab.xml           - 悬浮按钮背景
btn_disabled.xml      - 禁用按钮背景
ic_launcher_foreground.xml - 应用图标前景
ic_launcher_background.xml - 应用图标背景
```

### Mipmap (2 个)
```
mipmap-anydpi-v26/ic_launcher.xml         - 自适应图标
mipmap-anydpi-v26/ic_launcher_round.xml   - 圆形自适应图标
```

### Styles (1 个)
```
values/styles.xml - 完整的按钮和文本样式定义
```

---

**最后更新：** 2026-04-09  
**版本：** v2.0  
**分支：** extended-pids-21
