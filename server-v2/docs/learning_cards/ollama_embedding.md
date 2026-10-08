# Ollama Embedding 适配器

## 目的与当前状态

把通用 EmbeddingModel 接口接到 Ollama HTTP 服务。
本节已实现适配器、模拟 HTTP 测试和独立 smoke 脚本，未接入 FastAPI lifespan、
配置工厂、入库任务或向量索引，也未自动下载模型。
2026-09-09 探测本机默认地址 127.0.0.1:11434 时无法连接，因此未验证真实推理成功。

## 输入输出与流程

```text
EmbeddingRequest.texts
→ POST /api/embed，JSON 字段为 model、input、truncate=false
→ 检查 HTTP 状态
→ 解析 model 和 embeddings
→ 转为 EmbeddingResult.vectors
→ 校验返回模型名、条数、维度、非零
→ 返回原顺序向量
```

协议来源：[Ollama 官方 embed API](https://docs.ollama.com/api/embed)。
原生响应还可能有耗时和 token 计数，本节仅提取业务需要的字段，未记录用量。
服务端默认允许截断，因此显式设置 truncate=false；超长时报错，不能丢失证据。
expected_dimension 仅校验预期维度，并没有发送 dimensions 请求模型降维。

## 为什么这样实现

复用项目中的 httpx2.AsyncClient 和 ModelProviderError 异常类型，不新增 SDK。
直接 HTTP 适配便于观察真实协议；以后也可以用 SDK 替换这一层。
embed 负责解析和校验，_send 负责 HTTP 与传输错误映射。
不复用 RetryingChatModel：它调用的是 generate，不能当作 embed 的重试器。
目前每次 embed 只发送一次请求，没有自动重试或模型切换 fallback。

客户端由外部传入时，创建者负责关闭；适配器自己创建时，由 aclose 关闭。
关闭重定向，避免输入文本被转发到未预期地址。
错误消息不包含远程原始响应正文；__cause__ 保留调试原因，但不能不加审核地
将异常堆栈或请求对象记录到对外日志中。

## 参数与身份

模型、地址、预期维度和超时通过构造参数传入，不复用聊天模型名称。
独立 smoke 默认 bge-m3、1024 维、60 秒超时，给本地冷启动留出试验空间；
这不是生产延迟目标，也不能保证所有硬件都能在该时间内完成。
未带 tag 的名字按 :latest 比较，例如 bge-m3 与 bge-m3:latest 视为相同。
该比较不能保证权重版本一致，后续需要记录模型 digest；本地 tokenizer 与
Ollama 的模型版本和运行配置仍需对齐，不能只靠模型名称证明分词完全一致。

## 失败机制

| 失败 | 异常 |
|---|---|
| 未配置模型 | ModelNotConfiguredError |
| 超时 | ModelTimeoutError |
| 连接或读取故障 | ModelConnectionError |
| 429 | ModelRateLimitError |
| 5xx | ModelServerError |
| 其他非成功状态（包括模型不存在、超长输入等 4xx） | ModelRequestError |
| 非法 JSON、错误模型名、数量/维度/非零校验失败 | InvalidModelResponseError |

retryable 标记只表示错误类别，不代表本适配器已经实现重试。
没有用全零向量伪装降级成功，也没有静默改用另一 Embedding 模型。

## 验证、调试与评估

测试不读取 .env，不调用真实 Ollama；正常测试核对路径、顺序、原文、truncate
和返回映射，失败测试覆盖 HTTP、网络、非法返回值、配置与客户端资源归属。
二维向量只是可读的测试数据，不能用于评价 BGE-M3 召回质量。
调试顺序：服务可达 → 模型已安装 → 请求参数 → 返回数量/维度 → 后续检索效果。

Ollama 启动且已有 bge-m3 模型后，从仓库根目录执行：

```powershell
uv run --directory ./server-v2 python -m scripts.smoke_ollama_embedding
```

脚本读取四个候选 Chunk，输出各自向量维度及请求总耗时；向量只在内存中。
服务端 truncate=false 是本次实际请求的超长防线，脚本尚未串入本地 512-token
目标预算检查。后续入库流水线再统一连接各阶段。
评估仍需真实连接验证、模型版本核对及领域检索数据，不能用模拟测试替代。
