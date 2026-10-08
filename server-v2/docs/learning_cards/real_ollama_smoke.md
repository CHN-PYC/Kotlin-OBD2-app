# 真实 Ollama 联调学习卡

- 用途：验证本机模型能否通过完整 API 契约和节点流程生成答案。
- 输入：已有 vehicle_qa_request.json 样例；显式指定模型和单次超时。
- 输出：非敏感配置、可用模型、HTTP 状态、耗时、响应和 trace。
- 算法：检查 /api/tags，TestClient 调用 /qa/vehicle，实际向 Ollama 发 HTTP 请求。
- 选择理由：入站使用进程内 TestClient，出站不使用 MockTransport，避免同时调试端口与模型。
- 失败：进程存在但未监听；环境代理干扰回环请求；模型超时、截断、非法 JSON。
- 调试：依次检查模型列表、model_generation、model_output_parse 和最终 answer_mode。
- 评测：一次 smoke 只能证明该样例的运行结果，不能作为质量或性能评测结论。
- 可替换：后续可用独立 Uvicorn 和 Android 真机验证入站网络及端到端超时。

## 执行方式

在项目根目录运行：

```powershell
uv run --directory .\server-v2 python -m scripts.smoke_vehicle_qa --model qwen3:4b --timeout 60
```

脚本设置 max_attempts=1，便于观察单次失败，避免冷启动时反复调用模型。
timeout 是 HTTP 客户端超时设置，不是整个业务链路的统一截止时间。
只覆盖本次 Settings，不写 .env，不打印 API Key。
脚本 trust_env=False，显式直连；正式应用仍沿用现有 client 配置。
HTTP 200 但 answer_mode=llm_call_failed 是成功降级，不是 LLM 成功。
脚本 LLM 成功返回 0，降级返回 2；运行器可能将非零状态统一显示为失败。

## 本轮发现

最初模型列表接口不可用，API 返回规则保底结果，trace 记录 server_error。
启动 ollama serve 后，直连 /api/tags 返回 200，确认模型 qwen3:4b，Q4_K_M。
服务就绪与生成就绪是两步；后者必须用真实生成请求确认。

直连后的完整样例：约 60.12 秒返回 HTTP 200，answer_mode=llm_call_failed，
confidence=low；model_generation failed，错误码 timeout，随后 rule_fallback。
Parser 未执行。本次验证了真实超时降级，没有验证成功生成；不能从此结果判断
是冷启动、推理速度还是其他服务内部原因，后续需查 Ollama 日志和负载。
