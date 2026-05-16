package com.example.myapplication.ui.dashboard

import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.RectF
import android.util.AttributeSet
import android.view.View
import androidx.core.content.ContextCompat
import com.example.myapplication.R
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin

class MetricGaugeView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {

    private val arcRect = RectF()
    private val zoneRect = RectF()
    private val startAngle = 150f
    private val sweepAngle = 240f
    private val gaugeStroke = dp(14f)
    private val zoneStroke = dp(6f)

    private val backgroundArcPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeWidth = gaugeStroke
        color = ContextCompat.getColor(context, R.color.card_border)
    }

    private val safeZonePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeWidth = zoneStroke
        color = ContextCompat.getColor(context, R.color.success)
        alpha = 210
    }

    private val warningZonePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeWidth = zoneStroke
        color = ContextCompat.getColor(context, R.color.warning)
        alpha = 220
    }

    private val dangerZonePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeWidth = zoneStroke
        color = ContextCompat.getColor(context, R.color.error)
        alpha = 230
    }

    private val progressArcPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeWidth = gaugeStroke
        color = ContextCompat.getColor(context, R.color.accent)
    }

    private val majorTickPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeWidth = dp(2.4f)
        color = ContextCompat.getColor(context, R.color.text_secondary)
    }

    private val minorTickPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeWidth = dp(1.3f)
        color = ContextCompat.getColor(context, R.color.text_hint)
        alpha = 170
    }

    private val titlePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = ContextCompat.getColor(context, R.color.text_secondary)
        textAlign = Paint.Align.CENTER
        textSize = sp(12f)
        isFakeBoldText = true
    }

    private val valuePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = ContextCompat.getColor(context, R.color.text_primary)
        textAlign = Paint.Align.CENTER
        textSize = sp(28f)
        isFakeBoldText = true
    }

    private val unitPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = ContextCompat.getColor(context, R.color.text_secondary)
        textAlign = Paint.Align.CENTER
        textSize = sp(12f)
    }

    private val statusPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = ContextCompat.getColor(context, R.color.success)
        textAlign = Paint.Align.CENTER
        textSize = sp(12f)
        isFakeBoldText = true
    }

    private val tickLabelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = ContextCompat.getColor(context, R.color.text_hint)
        textAlign = Paint.Align.CENTER
        textSize = sp(10f)
    }

    private val needlePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeWidth = dp(4f)
        color = ContextCompat.getColor(context, R.color.text_primary)
    }

    private val needleTailPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeWidth = dp(3f)
        color = ContextCompat.getColor(context, R.color.text_secondary)
        alpha = 180
    }

    private val hubPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
        color = ContextCompat.getColor(context, R.color.text_primary)
    }

    private val hubInnerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
        color = ContextCompat.getColor(context, R.color.card_background)
    }

    var title: String = "Metric"
        private set
    var unit: String = ""
        private set
    var maxValue: Float = 100f
        private set
    var value: Float = 0f
        private set
    var statusText: String = "Ready"
        private set
    private var majorTickStep: Float = 25f
    private var warningThreshold: Float = 70f
    private var dangerThreshold: Float = 90f

    fun configure(
        title: String,
        maxValue: Float,
        unit: String,
        majorTickStep: Float = maxValue / 4f,
        warningThreshold: Float = maxValue * 0.7f,
        dangerThreshold: Float = maxValue * 0.88f
    ) {
        this.title = title
        this.maxValue = maxValue.coerceAtLeast(1f)
        this.unit = unit
        this.majorTickStep = majorTickStep.coerceAtLeast(1f)
        this.warningThreshold = warningThreshold.coerceIn(0f, this.maxValue)
        this.dangerThreshold = dangerThreshold.coerceIn(this.warningThreshold, this.maxValue)
        invalidate()
    }

    fun setMetricValue(value: Float) {
        this.value = value.coerceIn(0f, maxValue)
        invalidate()
    }

    fun setStatus(text: String, color: Int) {
        statusText = text
        progressArcPaint.color = color
        statusPaint.color = color
        invalidate()
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val desiredHeight = dp(190f).toInt()
        val resolvedHeight = resolveSize(desiredHeight, heightMeasureSpec)
        setMeasuredDimension(MeasureSpec.getSize(widthMeasureSpec), resolvedHeight)
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)

        val contentWidth = width.toFloat() - paddingLeft - paddingRight
        val contentHeight = height.toFloat() - paddingTop - paddingBottom
        val cx = paddingLeft + contentWidth / 2f
        val cy = paddingTop + contentHeight * 0.76f
        val radius = min(contentWidth * 0.34f, contentHeight * 0.44f)

        arcRect.set(cx - radius, cy - radius, cx + radius, cy + radius)
        zoneRect.set(
            arcRect.left - dp(5f),
            arcRect.top - dp(5f),
            arcRect.right + dp(5f),
            arcRect.bottom + dp(5f)
        )

        canvas.drawText(title.uppercase(), cx, paddingTop + dp(20f), titlePaint)
        canvas.drawArc(arcRect, startAngle, sweepAngle, false, backgroundArcPaint)
        drawZones(canvas)
        drawTicks(canvas, cx, cy, radius)

        val ratio = (value / maxValue).coerceIn(0f, 1f)
        canvas.drawArc(arcRect, startAngle, sweepAngle * ratio, false, progressArcPaint)
        drawNeedle(canvas, cx, cy, radius, ratio)

        canvas.drawText(formatValue(value), cx, cy - dp(10f), valuePaint)
        canvas.drawText(unit, cx, cy + dp(16f), unitPaint)
        canvas.drawText(statusText, cx, cy + dp(38f), statusPaint)
        canvas.drawCircle(cx, cy, dp(8f), hubPaint)
        canvas.drawCircle(cx, cy, dp(4f), hubInnerPaint)
    }

    private fun drawZones(canvas: Canvas) {
        val safeRatio = (warningThreshold / maxValue).coerceIn(0f, 1f)
        val warningRatio = ((dangerThreshold - warningThreshold) / maxValue).coerceIn(0f, 1f)
        val dangerRatio = ((maxValue - dangerThreshold) / maxValue).coerceIn(0f, 1f)

        if (safeRatio > 0f) {
            canvas.drawArc(zoneRect, startAngle, sweepAngle * safeRatio, false, safeZonePaint)
        }
        if (warningRatio > 0f) {
            canvas.drawArc(
                zoneRect,
                startAngle + sweepAngle * safeRatio,
                sweepAngle * warningRatio,
                false,
                warningZonePaint
            )
        }
        if (dangerRatio > 0f) {
            canvas.drawArc(
                zoneRect,
                startAngle + sweepAngle * (safeRatio + warningRatio),
                sweepAngle * dangerRatio,
                false,
                dangerZonePaint
            )
        }
    }

    private fun drawTicks(canvas: Canvas, cx: Float, cy: Float, radius: Float) {
        val minorSegments = 24
        for (index in 0..minorSegments) {
            val ratio = index / minorSegments.toFloat()
            val angle = Math.toRadians((startAngle + sweepAngle * ratio).toDouble())
            val isMajor = index % 4 == 0
            val tickOuter = radius + if (isMajor) dp(8f) else dp(4f)
            val tickInner = radius - if (isMajor) dp(14f) else dp(8f)
            val outerX = cx + cos(angle).toFloat() * tickOuter
            val outerY = cy + sin(angle).toFloat() * tickOuter
            val innerX = cx + cos(angle).toFloat() * tickInner
            val innerY = cy + sin(angle).toFloat() * tickInner
            canvas.drawLine(innerX, innerY, outerX, outerY, if (isMajor) majorTickPaint else minorTickPaint)
        }

        var labelValue = 0f
        while (labelValue <= maxValue + 0.01f) {
            val ratio = (labelValue / maxValue).coerceIn(0f, 1f)
            val angle = Math.toRadians((startAngle + sweepAngle * ratio).toDouble())
            val labelRadius = radius - dp(28f)
            val x = cx + cos(angle).toFloat() * labelRadius
            val y = cy + sin(angle).toFloat() * labelRadius + dp(4f)
            canvas.drawText(formatTickLabel(labelValue), x, y, tickLabelPaint)
            labelValue += majorTickStep
        }
    }

    private fun drawNeedle(canvas: Canvas, cx: Float, cy: Float, radius: Float, ratio: Float) {
        val angle = Math.toRadians((startAngle + sweepAngle * ratio).toDouble())
        val needleLength = radius - dp(18f)
        val frontX = cx + cos(angle).toFloat() * needleLength
        val frontY = cy + sin(angle).toFloat() * needleLength
        val tailX = cx - cos(angle).toFloat() * dp(20f)
        val tailY = cy - sin(angle).toFloat() * dp(20f)
        canvas.drawLine(cx, cy, tailX, tailY, needleTailPaint)
        canvas.drawLine(cx, cy, frontX, frontY, needlePaint)
    }

    private fun formatValue(value: Float): String {
        return value.toInt().toString()
    }

    private fun formatTickLabel(value: Float): String {
        return if (maxValue >= 1000f && majorTickStep >= 1000f) {
            (value / 1000f).toInt().toString()
        } else {
            value.toInt().toString()
        }
    }

    private fun dp(value: Float): Float = value * resources.displayMetrics.density
    private fun sp(value: Float): Float = value * resources.displayMetrics.scaledDensity
}
