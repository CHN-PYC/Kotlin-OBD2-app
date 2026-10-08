# 这是一份纯注释复习索引，不会被应用导入或执行。
# 这是历史课程笔记，能力状态以当时教学进度为准。
# 当前进度见 task_progress.md 和 remaining_engineering_gaps.md。

# =============================================================================
# 1. 当前端到端链路
# =============================================================================

# Android POST /qa/vehicle
# -> FastAPI 将请求体校验为 VehicleQARequest
# -> Depends(get_vehicle_qa_service) 选择具体 Service
# -> Prompt Builder 构造 ChatRequest
# -> RetryingChatModel 调用 OllamaChatModel
# -> 检查 finish_reason
# -> VehicleAnswerParser 解析并校验 JSON
# -> 成功返回 llm_only；任何已知失败返回规则 baseline

# =============================================================================
# 2. HTTP、JSON 和 API 契约
# =============================================================================

# 问：请求和响应怎么理解？
# 答：请求是客户端发给后端的数据；响应是后端处理后返回给客户端的数据。

# 问：顶层字段是什么？
# 答：最外层 JSON 对象直接拥有的 key。payload 是整个顶层 JSON，不是某一个字段。
# 例如：
# {
#   "session_id": "10001",       # 顶层字段
#   "vehicle_context": {          # 顶层字段，它的 value 是嵌套 JSON
#       "sessionSummary": {...}   # 嵌套字段
#   }
# }

# 问：Header 做什么？
# 答：Header 描述请求元信息。Content-Type: application/json 声明 body 格式；
# Authorization 通常携带身份凭证。出现 api_key 配置不代表鉴权中间件已经实现。

# 问：HTTP 200 是否代表业务成功？
# 答：不一定。200 只表示 HTTP 请求被正常处理。还要检查响应 body、answer_mode、
# agent_trace；模型 Provider 的 200 也不保证内容完整或符合 Schema。

# 问：session_id 为什么用字符串？
# 答：它是标识符而不是参与加减的数值。字符串可以保留前导零，避免超出不同语言的
# 整数精度，也适配 UUID。风险是必须限制长度、字符集并防止被当成权限依据。

# =============================================================================
# 3. Pydantic Schema
# =============================================================================

# Pydantic BaseModel 类似 Java DTO + Bean Validation：定义字段、类型和边界。
# extra="forbid" 会拒绝未知字段，能尽早发现客户端拼写错误或协议漂移。
# strict=True 阻止不安全的隐式类型转换，例如不随意把字符串 "5" 当整数 5。
# str_strip_whitespace=True 会清理字符串首尾空格，但 min_length 仍负责拒绝空文本。

# T | None：值可以是 T 或 None。
# Field(default_factory=list)：每个实例创建自己的列表。
# 不推荐 default=[]：可变默认值的语义不清楚，也容易让人误以为对象间共享列表。
# Enum：约束固定控制值，例如 severity、answer_mode、trace status。
# ClassVar：类级属性，类似 Java static final；例如错误 code 和 retryable。

# fixture 是固定测试样例，不是 Schema 本身。Schema 定义规则，fixture 提供一组数据。

# =============================================================================
# 4. model_dump、model_validate、model_copy
# =============================================================================

# model_dump：Pydantic 对象 -> dict。
# model_dump(mode="json")：把 Enum 等值转换成 JSON 兼容类型。
# model_dump(by_alias=True)：输出 camelCase 别名，适配 Android JSON 契约。
# 重要错误：model_dump 不会原地修改对象，调用后必须接住返回值。

# json.dumps：dict -> JSON str。
# 重要错误：json.dumps 也返回新值；str(dict) 使用单引号等 Python 表示，不是标准 JSON。

# model_validate：不可信 dict/JSON -> 经过校验的 Pydantic 对象。
# 模型输出、HTTP 输入等外部数据都应走 model_validate。

# model_copy(update={...})：复制一个现有模型并替换部分可信内部字段。
# 它类似 Kotlin data class.copy，不修改原对象。
# 重要风险：update 默认不重新校验，所以不能把未经校验的模型原始输出直接放进去。

# =============================================================================
# 5. async、await、Callable 和 client
# =============================================================================

# async def 返回协程。调用 async 方法而不 await，拿到的是 coroutine，不是最终结果。
# await 会挂起当前协程等待 I/O，同时让事件循环处理其他任务；不是阻塞整个服务线程。

# Callable[[float], Awaitable[None]] 表示：
# 接收一个 float，返回可等待对象且最终无返回值的函数。
# retry.py 注入 sleep 是为了测试等待策略时不真的休眠。

# FastAPI TestClient：模拟客户端 -> FastAPI。
# httpx2.AsyncClient：FastAPI -> Ollama 等外部 HTTP 服务。
# 二者都叫 Client，但方向和职责不同。

# async with client_factory() as client 管理资源生命周期。
# 重要错误：如果 try/yield 缩进到 async with 外，client 在应用运行前已经关闭。
# @asynccontextmanager 中 yield 前是 startup，yield 后是 shutdown。

# 谁创建 client 谁关闭：
# - OllamaChatModel 自己创建 client -> 自己 aclose。
# - FastAPI lifespan 注入共享 client -> lifespan 统一关闭。

# =============================================================================
# 6. Protocol、Factory 和依赖注入
# =============================================================================

# ChatModel Protocol 类似 Java interface：只规定 generate、provider_name、model_name。
# OllamaChatModel 是实现；RetryingChatModel 是装饰器；调用方只依赖 ChatModel。

# Factory 负责“对象怎么组装”：
# Settings -> OllamaChatModel -> RetryingChatModel -> ChatModel。
# Protocol 负责“对象怎么使用”。二者不是同一职责。

# FastAPI Depends 类似构造器/容器注入：
# app.state 中有模型 -> 创建 LLMVehicleQAService；
# app.state.chat_model 为 None -> 返回 RuleFallbackQAService。

# FastAPI Request 是框架请求上下文，可访问 request.app.state。
# VehicleQARequest 是业务请求体。名字相似，但不是一个对象。

# app.state：应用级共享基础设施，例如 HTTP client 和 ChatModel。
# Agent State：一次 Agent 执行中的 question、结果、路由等，尚未实现。
# Session Memory：跨请求的用户会话数据，尚未实现。

# =============================================================================
# 7. Provider 错误、重试和 fallback
# =============================================================================

# 可重试：timeout、connection_error、server_error。
# 不可重试：not_configured、invalid_response、request_error。
# 原因：暂态网络/5xx 可能恢复；错误配置、4xx、错误 Schema 重试通常不会自行修复。

# 指数退避：base * 2 ** (attempt - 1)，例如 0.1、0.2、0.4 秒。
# max_attempts 包含第一次调用，不是“失败后再重试 N 次”。
# Retry 层只负责是否再次调用 Provider，不决定业务答案。

# fallback 是主路径不可用时的替代策略，不等于简单 catch Exception。
# 当前项目的 fallback：返回规则诊断和保守建议，并降低 confidence、记录 trace。
# 不捕获所有 Exception：代码 bug 应暴露给测试和监控，不能伪装成模型故障。

# =============================================================================
# 8. Prompt Builder
# =============================================================================

# System 消息定义稳定角色、证据约束、安全边界和输出协议。
# User 消息承载本次 question、vehicleContext 和 ruleSummary。
# 不把 session_id、top_k 喂给模型：它们是流程控制字段，不是诊断证据。

# temperature=0：尽量降低随机性，适合诊断和可复现测试；不代表绝对确定。
# max_output_tokens=512：限制延迟和成本；过小会出现 finish_reason=length。
# ensure_ascii=False：保留中文；separators=(",", ":")：减少无意义空格和 token。

# 重要错误：System Prompt 曾只写 "provided evidence" 来通过测试。
# 测试通过不等于业务需求完成，安全约束必须表达完整语义。

# =============================================================================
# 9. 结构化输出 Parser
# =============================================================================

# ChatResult.content 是不可信字符串。
# HTTP 200 -> 只表示 Provider 响应。
# finish_reason=stop -> 只表示正常结束。
# json.loads + GeneratedVehicleAnswer.model_validate 通过 -> 才能进入业务对象。

# Prompt 和 Schema 字段名必须完全一致。
# 重要错误：recommendation 与 recommendations 不一致，被 extra="forbid" 正确发现。
# 标准 JSON 的 key 使用双引号；Python 单引号只是源码字符串定界符。

# raise InvalidModelResponseError(...) from exc：
# 对外给出统一错误；通过 __cause__ 保留 JSONDecodeError/ValidationError 供调试。
# Parser 负责识别错误；QA Service 负责决定是否 fallback。

# =============================================================================
# 10. LLM QA Service
# =============================================================================

# baseline = await fallback.answer(request)：先准备一个合法、确定性的备用响应。
# baseline 被创建不等于已经 fallback；只有失败分支 return baseline 才发生降级。

# 正常顺序：
# 1. build prompt
# 2. await model.generate
# 3. 检查 finish_reason == "stop"
# 4. parser.parse
# 5. model_copy 生成成功响应

# 重要错误：忘记 await 后访问 result.content，实际 result 是 coroutine。
# 重要错误：model_copy 返回值未 return，导致分支没有返回响应。
# 重要错误：finish_reason 曾拼成 finich_reason。
# 重要错误：失败时把 answer 更新为 None，但响应 Schema 要求非空答案；fallback 应保留规则答案。
# 重要错误：Parser 调用了但未捕获 InvalidModelResponseError，导致异常穿透到 API。

# finish_reason="length" 表示截断。即使文本非空甚至碰巧是合法 JSON，也应丢弃。
# 模型成功且有规则证据 -> 当前 confidence=medium；没有规则证据 -> low。
# 当前没有检索，所以 answer_mode=llm_only，不能声称 llm_rag，sources 仍为空。

# agent_trace 是执行事实记录：
# - prompt_build completed
# - model_generation completed/failed
# - model_output_parse completed/failed
# - rule_fallback fallback
# 它不是完整 Agent State，也不应保存密钥或无限大的原始上下文。

# =============================================================================
# 11. 测试与调试顺序
# =============================================================================

# 单元测试：测试单个 Schema、Parser、Provider、Retry 或 Service。
# 集成测试：用 TestClient + MockTransport 验证 FastAPI 到 Provider 的整条接线。
# TestClient 必须用 with，才能执行 FastAPI lifespan。
# MockTransport 不会请求真实 Ollama，适合稳定测试成功、4xx、5xx、timeout 和坏 JSON。

# 推荐定位顺序：
# 1. 看失败测试名称。
# 2. 看最内层原始异常，而不只看最终 fallback。
# 3. 判断是 HTTP、Provider Schema、生成 Schema 还是业务路由阶段。
# 4. 查看 answer_mode 和 agent_trace。
# 5. 单测通过后再跑 ruff、mypy、全量 pytest。

# =============================================================================
# 12. 尚未实现，不能在面试中说成已有功能
# =============================================================================

# Agent State 已定义；显式 Node/Route 工作流尚未实现。
# v2 已接入 chunk、Embedding、Qdrant、BM25+RRF 混合检索和可选 rerank；PDF OCR 仍是后续项。
# Evidence Gate、Query Rewrite、RAG Eval、短期/长期 Memory、Redis Session：尚未接入 v2。
# 当前 answer_mode=llm_only；只有真正加入检索证据后才能使用 llm_rag。

# =============================================================================
# 13. Agent State
# =============================================================================

# VehicleAgentState 只描述一次 Agent 执行，不是 FastAPI 全局资源或跨请求记忆。
# app.state：全应用共享的 client/model。
# VehicleAgentState：单次执行的输入、中间结果、阶段、失败原因和最终响应。
# Session Memory：跨请求保存的会话信息，目前尚未实现。

# phase 表示当前执行位置；字段保存该位置产生的数据。
# baseline_response 必须是 VehicleQAResponse，因为它是规则服务已经生成的备用响应。
# 重要错误：曾把 RECEIVED 的值写成 approved，也曾把 baseline 写成 Request 类型；
# 原有测试只检查默认 None，没有覆盖枚举真实值和非空 baseline，因此仍然显示通过。

# 使用 model_copy(update=...) 创建新快照，旧 state 保持不变。
# trace 使用 [*state.trace, new_step] 创建新列表，避免修改旧快照中的执行历史。
# State 中不放 ChatModel/AsyncClient，它们是依赖；也不放无限历史，它不是 Memory。

# 14. 两种星号与第一个 Node
# def f(*, fallback): 中的 * 要求命名传参：f(fallback=service)。
# [*state.trace, step] 展开历史元素并创建新列表；[state.trace, step] 会嵌套列表。
# state.trace.append(step) 修改旧列表，不适合保留历史快照。
# 新列表只浅复制容器，旧 AgentTraceStep 对象仍共享，不能原地修改旧记录。
# PrepareBaselineNode: received -> baseline_prepared，准备 baseline 并追加 completed trace。
# 预备规则响应不等于发生业务降级；此时 final_response 仍为空。
# 节点目前独立实现与测试，API 仍执行已有 QA Service。

# 15. BuildPromptNode
# 前置条件既检查 phase=baseline_prepared，也检查 baseline_response 非空。
# phase 是标签，不保证对应数据存在；model_copy(update=...) 不重新校验更新值。
# Prompt Builder 构造消息；BuildPromptNode 检查执行条件、保存产物并追加 trace。
# build 没有异步 I/O，run 使用普通 def；不是所有 Node 都必须 async。
# __init__ -> None 表示初始化不返回业务结果。
# received -> PrepareBaselineNode -> baseline_prepared -> BuildPromptNode -> prompt_built。
# 两个节点当前独立测试，尚未替换 FastAPI 中的 QA Service 执行链路。

# 16. 输出节点与终止条件
# ParseModelOutputNode: model_generated -> output_parsed 或 fallback。
# BuildResponseNode: output_parsed -> completed，生成 llm_only 响应。
# RuleFallbackNode: fallback -> completed，生成 llm_call_failed 响应。
# fallback 是等待降级处理的阶段；completed 说明已有 final_response，不等于模型成功。
# State 保存数据，Node 处理一步，Workflow 根据 phase 决定下一步。
# 新节点复用旧 Service 的策略；尚未接入 API，工作流调度是下一步练习。

# 17. 手动 Workflow 已实现
# WorkFlow.run 每次创建新 State，依次准备 baseline、Prompt、调用模型、解析、构造响应。
# 两处 if phase=FALLBACK 都直接 return fallback_node.run(state)，终止成功路径。
# state = node.run(state) 必须接住新快照，不能丢弃返回值。
# 同一个 Workflow 可顺序处理多个请求；当前执行 State 不能存在共享 self 字段中。
# 模型节点每次调度一次，重试装饰器可能在内部发送多次 HTTP 请求。
# 当前 Workflow 已独立测试，但 FastAPI 仍调用原 QA Service，接线尚未迁移。

# 18. 接线更新：API 现已执行 Workflow
# 已配置模型时 Depends 组装六个节点和 WorkFlow，返回 WorkflowQAService。
# 适配器 await workflow.run(request)，检查 completed 和 final_response 后返回响应。
# 缺少最终响应是流程代码错误，不是 Provider 故障，应抛 RuntimeError。
# 未配置模型继续选择 RuleFallbackQAService，旧 LLMVehicleQAService 仅保留作学习参考。
# 以上第 17 节“尚未接入”的记录是当时的阶段说明，以本节为准。
# 适配器单独放文件，避免 qa_service -> workflow -> nodes -> qa_service 循环导入。

# 19. 真实模型联调
# scripts/smoke_vehicle_qa.py：入站 TestClient，出站真实 Ollama，不使用 MockTransport。
# 本轮 qwen3:4b 可在 /api/tags 查到，但完整生成请求 60 秒超时并触发规则降级。
# HTTP 200 不等于 llm_only；先看 answer_mode，再看 trace 失败节点。
# model_generation timeout 时 Parser 尚未运行，不能说是 JSON 格式错误。
# 服务列表可读不等于模型能及时生成；timeout 根因需要日志和性能数据继续定位。

# 20. 超时定位实测
# MX450 2GB 显存，qwen3:4b 未完全驻留 GPU。
# 短输入两次测量：加载 10.150 -> 0.474 秒，生成速度 1.81 -> 4.52 token/秒。
# 车辆输入 542 token，prompt_eval 8.341 秒，生成速度 4.43 token/秒。
# 加载、输入处理和逐 token 生成都影响延迟；排队和网络也可能产生额外开销。
# num_predict 是上限；实际生成满 512 token 才能用 512 / 实测速度估算输出时间。
# length 是截断，速度测试完成不代表诊断成功；不能为通过测试而接受半截答案。
# profile_ollama.py 拆解性能；smoke_vehicle_qa.py 验证完整 API 和 fallback。

# 21. 精简输出与 token 预算对照
# 同一车辆输入、精简 Prompt（600 输入 token），分别测试 128/256 输出上限。
# 实测约 58.79/66.14 秒，均输出至上限 length，Schema 均不通过。
# 降低上限只限制生成长度，不保证模型更简洁或更快给出完整答案。
# 增加上限也不保证模型遵循 JSON 协议；本轮两个候选均未被接受。
# accepted 要同时满足 stop 和 Schema 合法，然后才评审业务内容。
# 顺序实验受缓存/负载影响，不能拿单次耗时直接宣称优化百分比。

# 22. Provider 原生结构化输出
# model_dump 导出数据；model_json_schema 导出字段规则；model_validate 校验实际数据。
# Ollama payload["format"] = GeneratedVehicleAnswer.model_json_schema()。
# format="json" 指定 JSON，传 Schema 才能描述具体字段；仍保留 stop 与应用校验。
# 当前 findings/recommendations 有默认值，Schema 中并非必填，不能混淆 Prompt 和 Schema。
# 本轮真实请求 HTTP 500：failed to load model vocabulary required for format。
# 是 Provider 词表加载错误，未进入业务 Parser；不等于已证实模型不支持此功能。
# 新能力只在 profile_ollama.py 的 --structured 实验中启用，正式服务尚未采用。

# 23. 远程 Chat Completions Provider
# 配置 model_provider=ollama/openai_compatible，Factory 选择实现，再包装统一重试。
# Workflow 继续依赖 ChatModel.generate，不需要知道底层是 Ollama 还是远程 HTTP。
# OpenAICompatibleChatModel: 请求消息 -> Bearer 鉴权 -> choices/message -> ChatResult。
# llm_api_key 是调用模型的出站密钥，与 Android 访问后端的入站 api_key 分开。
# JSON_MODE 是可选服务商能力，不支持时不能默认发送，开启后仍需 Parser。
# 401/403 属于请求错误，不重试；429 单独标记 rate_limited 并有限重试。
# Client 谁创建谁关闭；共享 Client 的 Authorization 只在请求级设置。
# 已用 MockTransport 验证远程 API 接线；实际远程请求还需要用户配置地址、模型与密钥。
