# VectorStore FastAPI Lifespan

## 目的与流程

FastAPI lifespan 是进程级资源的所有者。启动时调用异步 VectorStore factory，把已经
初始化的实例放入 `app.state.vector_store`；关闭时执行 `aclose()`。路由或 Agent 节点
后续只读取这个共享实例，不应为每次请求重新建立 Qdrant 客户端。

```text
startup → HTTP client → VectorStore factory → ChatModel → yield
shutdown ← close HTTP client ← VectorStore.aclose ← return from yield
```

## 失败策略

当前采用 fail-fast：配置为 Qdrant 且 collection 初始化失败时，异常发生在 yield 前，
应用不开始接收请求。这样不会把存储故障伪装成“检索到零条证据”。LLM 未配置仍允许
启动，因为已有明确的规则诊断 fallback；两者的业务含义不同。

未来若要求诊断 API 在 Qdrant 故障时继续工作，应设计显式 degraded 状态、健康检查、
trace 和无 RAG 的保守回答，而不是在 factory 中静默换成空 MemoryVectorStore。

## 生命周期与测试

VectorStore 每个应用进程创建一次并共享连接池，避免逐请求建连。`try/finally` 保证
正常关闭和请求期间异常都能释放资源；factory 自身负责初始化失败时清理尚未返回的
实例。

测试验证资源只在 startup 后可见、运行期间未关闭、shutdown 后关闭，以及 factory
失败会阻止应用启动并仍关闭共享 HTTP client。当前还没有 RetrievalNode 使用该实例。
