# VectorStore Errors and Factory

## 异常分类

Qdrant SDK 异常被转换成稳定的应用异常，Agent 和 API 不依赖第三方异常类型。所有异常
记录 `code`、`retryable`、`operation` 和 `collection`，但不包含服务端原始响应正文，
避免泄露内部信息。

```text
timeout / connection / HTTP 429 / HTTP 5xx → retryable = true
HTTP 401、403 / 其他 4xx / unreadable response → retryable = false
```

可重试只表示故障可能是暂态，不等于立即无限重试。后续策略仍需限制次数、退避时间和
总延迟预算。配置不兼容和 payload 损坏使用同一异常体系，但分别标记为 configuration
和 invalid_response，通常应告警或重建索引，而不是重试原请求。

## Factory 与生命周期

`create_vector_store(settings)` 是异步 composition root：memory 分支直接返回固定维度的
MemoryVectorStore；qdrant 分支解析 SecretStr、构造 QdrantVectorStore，并等待
ensure_collection 完成后才返回可用实例。

```text
Settings.vector_store_provider
├─ memory  → MemoryVectorStore
└─ qdrant  → QdrantVectorStore → await ensure_collection
```

VectorStore 契约新增 `aclose()`。Memory 实现不持有外部资源，因此为空操作；Qdrant
只关闭自己创建的客户端。factory 初始化失败时先执行 aclose 再继续抛出原异常，防止
连接池泄漏。注入客户端由注入方管理，不会被 store 擅自关闭。

## 测试与后续

测试覆盖超时、连接、鉴权、限流、4xx、5xx、损坏响应，以及 memory/qdrant 两个 factory
分支。Qdrant 测试使用 SDK 内存模式，不代表远程服务网络与持久化已验证。

下一步是在 FastAPI lifespan 中创建和关闭 VectorStore，并明确 Qdrant 启动失败时采用
fail-fast 还是无知识检索的降级策略；之后才能把它接入 Agent retrieval node。
