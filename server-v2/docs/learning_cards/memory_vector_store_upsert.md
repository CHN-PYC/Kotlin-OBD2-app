# MemoryVectorStore

## 目的、输入与输出

`upsert(records)` 将 `VectorRecord` 写入内存字典，key 是稳定的 `chunk_id`。新 ID
表示新增，已有 ID 表示整体覆盖；方法成功时不需要返回值。

```text
VectorRecord[] → 全批校验 → 深拷贝 → dict[chunk_id, VectorRecord].update()
```

## 实现选择

字典按 ID 查询和覆盖的平均复杂度是 O(1)，适合作为小数据精确基线。构造时固定
`dimension`，用于模拟真实向量库 collection 的维度约束。全部记录先写入临时字典，
只有整批通过后才更新正式存储，因此批次中任意一条失败都不会造成部分写入。

保存 `model_copy(deep=True)`，避免调用方在 upsert 后修改原对象，导致存储内容被意外
改变。同一批次出现重复 ID 通常代表 ingestion 错误，因此本实现显式拒绝；不同批次
使用同一 ID 则符合 upsert 的覆盖语义。

## 失败、调试与评测

拒绝非法 dimension、向量维度不一致、全零向量和单批重复 ID。调试时先检查配置维度
是否与 Embedding 模型输出一致，再检查 chunk_id 生成是否稳定。正常测试覆盖新增和
覆盖，边界测试覆盖深拷贝、整批失败不写入和重复 ID。

## Search 与 Delete

`search(query_vector, k)` 先把内部记录转换成 `IndexedVector`，复用现有余弦 Top-K，
再根据命中的 `chunk_id` 找回 `KnowledgeChunk` 并构造 `RetrievedSource`。因此向量算法
不负责保存或返回正文，ID 是索引结果和知识内容之间的连接键。

```text
_records → IndexedVector[] → search_top_k → VectorSearchHit[]
         → KnowledgeChunk[] + hits → resolve_search_hits → RetrievedSource[]
```

`delete(chunk_ids)` 使用 `pop(id, None)`，已存在的记录被删除，不存在的 ID 被忽略，
因此重复请求具有幂等性。所有 ID 在删除前统一校验，避免参数中途出错造成部分删除。

该实现只保存在进程内，重启后数据丢失，也不支持跨进程并发和持久化。后续 Qdrant
实现将替代运行时存储，但保留本实现作为单元测试与精确检索基线。
