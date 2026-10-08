# Qdrant VectorStore Operations

## 数据映射

每个 VectorRecord 被映射成一个 Qdrant Point：向量用于相似度计算，KnowledgeChunk 的
JSON 作为 payload，point ID 是根据 `chunk_id` 生成的确定性 UUID5。

```text
PointStruct(
  id = uuid5("vehicle-agent/chunk/{chunk_id}"),
  vector = embedding,
  payload = KnowledgeChunk JSON
)
```

UUID5 不是随机值；相同 chunk_id 始终得到相同 ID。因此重复 upsert 会覆盖同一个 point，
delete 也能根据业务 ID 重新计算 point ID。原始 chunk_id 仍保存在 payload，便于业务
追踪，不能只依赖 UUID。

## Upsert、Search 与 Delete

upsert 在发送前校验单批重复 ID、维度、有限数值和全零向量，再调用 Qdrant
`upsert(..., wait=True)`。空批次不发送请求。

search 校验 k 和查询向量，调用 `query_points`，要求返回 payload、不返回原向量。响应
按 Qdrant 排名顺序转换为 RetrievedSource，并校验 payload schema、重复 chunk_id 以及
point ID 与 chunk_id 是否匹配。score 是 Qdrant 的余弦相关性分数，不是概率。

delete 先校验整个 ID 批次，再去重并转换为 PointIdsList。未知 ID 被忽略，因而删除操作
具有幂等性。`wait=True` 表示写操作返回前等待服务端确认应用，而不是只接收请求。

## 失败、调试与评测

输入错误在网络调用前失败；损坏 payload 抛出 QdrantPayloadError。Qdrant 网络超时、
连接、鉴权、限流、4xx、5xx 和损坏响应已经映射为稳定的 VectorStoreProviderError
子类，供 Agent trace 和 fallback 判断。方法要求调用方先执行 ensure_collection。

测试使用 AsyncQdrantClient 的内存模式，实际执行 collection 创建、写入、查询、覆盖和
删除，不需要 Docker。上线前仍需针对真实服务测试连接、持久化、并发和重启恢复。
