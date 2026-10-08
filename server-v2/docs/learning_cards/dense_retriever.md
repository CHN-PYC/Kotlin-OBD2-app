# 最小 Dense Retriever 封装

## 目的、输入和输出

`ExactDenseRetriever` 把精确 Top-K 搜索和 Chunk 正文映射封装成一个入口。
初始化输入是 `IndexedVector` 与 `KnowledgeChunk` 列表；查询输入是查询向量和 K；
输出是已排序的 `RetrievedSource`。本节不负责生成 Embedding、rerank、
Evidence Gate、Prompt 或 FAISS 索引。

## 数据流和职责

```text
初始化：检查 IDs 一一对应、唯一，检查向量维度一致且非零
      → 深拷贝为一个一致的内存快照

查询：query_vector
      → search_top_k（余弦评分、排序、截断）
      → resolve_search_hits（根据 chunk_id 找正文）
      → list[RetrievedSource]
```

Retriever 是检索能力的封装，不等于向量索引，也不调用 LLM。
当前实现名称带 `Exact`，明确它全量比较候选，是教学和评测基线。
后续 FAISS Retriever 可以实现相同的输入输出行为，但无需现在提前引入 Protocol。

## 为什么初始化时检查一致性

如果向量 IDs 为 `{a,b}`，正文 IDs 为 `{a,c}`，只有查询命中 b 时才报错会使故障
具有偶然性。初始化时比较集合可以立即发现索引和正文版本不一致。
同时拒绝重复 ID、不同向量维度和全零向量，不等第一次线上查询才发现损坏。
集合比较不关心两个输入列表的顺序，因为关联依赖稳定 chunk_id，而非数组位置。

## 快照与复杂度

构造时深拷贝模型，外部修改列表、向量或 Chunk 正文不会悄悄改变当前 Retriever。
代价是初始化需要 O(ND) 时间和空间。检索仍为 O(ND + N log N)，每次将内部
元组转成浅列表以复用已测试函数；不会再次复制向量内容。
生产系统可用不可变数据、版本化存储或数据库快照替代这种内存深拷贝。

## 失败机制和验证

- IDs 不一致或重复、维度不一致、全零索引向量：构造阶段 ValueError。
- K 非法、查询零向量或维度错误：查询阶段 ValueError。
- 空向量集合和空 Chunk 集合是一致的空索引，合法查询返回空列表。
- 不捕获底层异常并返回空列表，否则无法区分“没有结果”和“索引损坏”。

测试覆盖完整排名和正文映射、输入顺序不同、快照隔离、空索引、ID 完整性、
维度、零向量、非法 K 和查询维度。人工二维向量不代表语义检索质量。

```powershell
uv run --offline --directory ./server-v2 pytest tests/test_dense_retriever.py -q
```

调试顺序：先检查索引与 Chunk 版本/ID，再看维度，最后看单项 score 和映射。
下一步可以定义 rerank 接口位置：接收 query_text 与本 Retriever 的较大候选集，
输出重排后的较小集合；是否启用仍要由真实评测证明。
