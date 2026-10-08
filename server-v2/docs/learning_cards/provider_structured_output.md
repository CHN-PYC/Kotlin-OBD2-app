# Provider 原生结构化输出学习卡

- 用途：向 Ollama 提交输出 Schema，降低只靠 Prompt 时的格式不确定性。
- 输入：现有车辆 Prompt，以及 GeneratedVehicleAnswer.model_json_schema()。
- 输出：请求 payload.format 保存 JSON Schema；响应继续用应用 Schema 校验。
- 算法：实验启用 --structured 时加入 format，其余 Prompt 和 token 上限保持一致。
- 选择理由：Schema 从 Pydantic 自动生成，避免手写两份字段定义发生漂移。
- 失败：Provider 可能不接受请求或内部加载失败；输出仍可能超时、截断或语义错误。
- 调试：区分 HTTP 错误、非 stop、Schema 校验错误；HTTP 500 不能归因于业务 Parser。
- 验证：模拟成功请求检查 Schema 实际写入 payload，未启用时不写；真实请求观察服务能力。
- 可替换：修复 Provider 运行环境或使用支持结构化输出的其他模型服务。

## 三种方法的区别

model_dump()：从模型实例导出实际数据。
model_json_schema()：从模型类导出字段、类型、必填和长度限制等规则。
model_validate()：对实际数据执行应用端校验。

本项目 Schema 只有 answer 必填；findings 和 recommendations 有默认值，允许省略。
Prompt 要求三个字段不等于 Schema 强制三个字段必填；不能声称当前 Schema 已强制这一点。

## 2026-09-07 实验结果

命令：

```powershell
uv run --directory .\server-v2 python -m scripts.profile_ollama --case vehicle --compact --structured --tokens 256 --timeout 90
```

起初 Ollama 未启动。启动后 /api/tags 返回 200，qwen3:4b 可见。
结构化请求返回 HTTP 500，Provider 报：
`failed to load model vocabulary required for format`。
这是格式约束所需词表加载失败，尚未进入应用 Parser；不能据此断言模型不支持 JSON，
也不能确认根因一定是版本或文件损坏。下一步应检查 Provider 版本、模型加载与兼容性。
本轮没有结构化生成成功样例，不能计算相对之前的成功率或延迟提升。
本轮只改变实验脚本，正式 OllamaChatModel 尚未传 format。

## 官方依据

https://docs.ollama.com/capabilities/structured-outputs

官方支持 format="json" 或 format=JSON Schema；后者可描述具体字段结构。
官方示例使用 Pydantic model_json_schema()，并继续校验返回内容。
