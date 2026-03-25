package com.example.myapplication.utils

import com.example.myapplication.data.model.ObdCommand

object ObdDecoder {

    /**
     * 清洗原始响应：去除空格、换行、提示符等
     */
    fun cleanResponse(raw: String): String {
        return raw
            .replace(">", "")
            .replace("\r", "")
            .replace("\n", "")
            .replace(" ", "")
            .trim()
    }

    /**
     * 解析响应
     * @param response 原始响应字符串（如 "41 0C 1A F0"）
     * @param command 对应的 OBD 命令
     * @return 解析后的物理值，失败返回 null
     */
    fun parse(response: String, command: ObdCommand): Double? {
        val cleaned = cleanResponse(response)
        // 验证响应头：应为 "41" + PID
        val expectedHeader = "41" + command.pid.substring(2) // 去除模式 "01"
        if (!cleaned.startsWith(expectedHeader)) {
            return null
        }
        // 提取数据字节
        val dataPart = cleaned.substring(4) // 去掉前4字符（41+pid）
        if (dataPart.length < command.responseBytes * 2) {
            return null
        }
        val bytes = mutableListOf<Int>()
        for (i in 0 until command.responseBytes) {
            val hex = dataPart.substring(i * 2, i * 2 + 2)
            bytes.add(hex.toIntOrNull(16) ?: return null)
        }
        return command.formula(bytes)
    }
}