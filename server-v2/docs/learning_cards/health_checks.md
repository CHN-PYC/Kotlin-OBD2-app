# 存活与就绪检查

## 用途与输入输出

`GET /health`（存活）：无输入，进程能处理请求就返回 `{"status": "ok"}`，不访问
任何依赖，供容器判断是否需要重启。

`GET /health/ready`（就绪）：返回整体状态 ready/degraded 和每个组件的状态
ok / unavailable / not_configured / not_probed，供运维和负载均衡判断依赖是否可用。

## 数据流和算法

```text
readiness -> gather(
    probe(session_memory)  -> Redis PING
    probe(vector_store)    -> Qdrant collection_exists
) + chat/embedding 只读配置
-> 任一 unavailable => degraded，否则 ready
```

每个探测独立 `asyncio.timeout`（默认 2 秒），并发执行，最坏耗时约等于一个
超时而不是全部超时之和。

## 为什么这样实现

- 存活与就绪分开：依赖故障时重启 API 进程无济于事，存活检查不能看依赖。
- 依赖故障时服务仍能返回规则兜底，因此就绪返回 200 + degraded，而不是 503。
  若部署环境要求依赖故障时摘流量，只需在 degraded 时改为 503。
- `HealthProbe` 是独立的可选 Protocol，没有修改 VectorStore/SessionMemoryStore
  契约；没有 ping 的实现（如测试替身）报告 not_probed，而不是假装 ok。
- 模型只检查是否配置，不做真实推理：推理慢、可能计费，且熔断器已覆盖运行时故障。

## 失败与边界

- 探测异常只记录组件名和异常类型，响应中不含错误消息或内部地址。
- 卡住的依赖由单独超时截断，报告 unavailable。
- Qdrant collection 被删除时报告 unavailable；向量维度只在启动时校验。
- 未检查熔断器状态、Embedding 服务可达性和 BM25 语料，这些仍是后续工作。
- 就绪接口目前不需要 API key；暴露的只是组件名和状态。

## 调试与验证

日志搜索 `health_probe_failed component=... type=...`。测试文件：test_health.py，
覆盖默认就绪、探测失败降级且不泄露、探测超时、无 ping 组件、存活不访问依赖、
Redis/Qdrant ping 的错误映射。

## 可替换方案

Kubernetes 可直接把两个路径配置为 liveness/readiness probe；需要更多指标时
可接 Prometheus `/metrics`，健康检查只回答"能否服务"，不替代指标监控。
