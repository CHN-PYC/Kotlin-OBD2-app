# 远程模型 Provider 学习卡

- 用途：通过配置在本地 Ollama 与远程 Chat Completions 服务间切换。
- 输入：统一 ChatRequest，以及服务端配置的 URL、模型名称、SecretStr 密钥。
- 输出：统一 ChatResult，保留真实 finish_reason；工作流继续检查截断和生成 Schema。
- 算法：将消息映射为 HTTP JSON，携带 Bearer Header，解析 choices[0].message 与 usage。
- 选择理由：复用现有 httpx2、Pydantic、ChatModel Protocol 和重试装饰器，无新增 SDK。
- 失败：缺配置抛 ModelNotConfiguredError；4xx 不重试；429 为 rate_limited；
  5xx、网络和超时按现有次数与指数退避重试；坏响应进入 invalid_response。
- 调试：配置选择 -> Factory -> 远程 HTTP 状态 -> finish_reason -> Parser -> trace。
- 评测：模拟服务验证 URL、Header、字段映射、重试、生命周期和 API；
  尚未使用真实远程密钥调用，不能宣称远程推理成功或质量提升。
- 可替换：若服务商仅支持 Responses API、专有 token 字段或思考参数，可另写适配器。

## 配置

在 server-v2/.env 中配置（不要提交真实密钥）：

```dotenv
VEHICLE_AGENT_MODEL_PROVIDER=openai_compatible
VEHICLE_AGENT_LLM_BASE_URL=https://YOUR_PROVIDER_API/v1
VEHICLE_AGENT_LLM_MODEL=YOUR_MODEL_ID
VEHICLE_AGENT_LLM_API_KEY=YOUR_SERVER_SIDE_KEY
VEHICLE_AGENT_LLM_JSON_MODE=false
VEHICLE_AGENT_MODEL_TIMEOUT_SECONDS=60
VEHICLE_AGENT_MODEL_MAX_ATTEMPTS=3
```

BASE_URL 填服务商文档给出的 API 前缀，代码追加 /chat/completions。
有的地址需要 /v1，有的不需要；不要填成完整 /chat/completions 地址。
本示例的地址和模型是占位符，必须按实际供应商替换。
llm_api_key 用于后端访问模型，api_key 是预留的入站凭证配置，二者不能混用。

只有确认目标模型支持 response_format={"type":"json_object"} 时才启用 JSON_MODE。
现有 Prompt 已要求 JSON，但服务商要求可能不同；不支持该选项时保持 false。
JSON mode 不等于严格 JSON Schema，更不等于事实正确，Parser 和 Evidence 校验仍有必要。
本实现发送 max_tokens、temperature 和 stream=false；不声称支持所有“兼容”模型。
未请求 Tool Calling；空 content/refusal 等响应被拒绝，不会作为成功答案。

## 运行

从项目根目录启动（端口被占用时改用空闲端口）：

```powershell
uv run --directory .\server-v2 uvicorn app.main:app --host 127.0.0.1 --port 8001
```

打开 http://127.0.0.1:8001/docs，向 POST /qa/vehicle 提交 tests/fixtures 中的请求样例。
预期成功 answer_mode=llm_only，trace 包含 prepare_baseline、prompt_build、
model_generation、model_output_parse、build_response。
修改 .env 后需要重启服务，已有 Settings 缓存与共享 Client 不会自动刷新。

## 生命周期与限制

FastAPI lifespan 注入共享 client，Provider 不关闭外部 client，也不向共享 client
全局写入 Authorization，密钥只在本次请求 Header 中使用。禁止自动跟随重定向。
独立创建 Provider 时自有 client 由 aclose 关闭，与 Ollama 的所有权规则一致。
异常文本不包含原始服务商响应或密钥；不要将底层 HTTP 对象完整记录到日志。
429 当前沿用有限指数退避，尚未实现 Retry-After、抖动或跨请求限流。
usage 缺失时沿用现有 ChatResult 整数契约填 0，这表示缺少统计，不能当作免费调用。
协议身份 provider_name=openai_compatible，具体服务商由所配置的地址决定。
本次未写入真实 .env，也没有将用户数据发送到未经指定的远程服务。

## 参考

https://api-docs.deepseek.com/api/create-chat-completion/

此文档作为兼容协议的一份具体参考；使用其他服务时须核对其实际 API 能力。
