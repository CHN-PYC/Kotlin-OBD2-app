# 检索命中映射到知识正文

## 目的、输入和输出

输入按排名排列的 `VectorSearchHit(chunk_id, score)` 和知识库 `KnowledgeChunk`
列表，输出同顺序的 `RetrievedSource`。输出带回正文、文档、章节、来源 URL 和
检索分数，可供后续 rerank、Evidence Gate 或 Prompt 使用。
本节不生成向量、不重新评分、不调用 LLM，也不实现 rerank。

## 数据流和算法

```text
遍历 chunks → 建立 chunk_id 到 KnowledgeChunk 的字典
→ 按 hits 原顺序遍历
→ 用 hit.chunk_id 查询字典
→ 合并 hit.score 与 Chunk 内容
→ 创建 RetrievedSource
```

构建字典需要 O(M) 时间和空间，解析 N 个命中约 O(N)；比每个命中都线性扫描
全部 Chunk 的 O(NM) 更清晰。字典只负责快速定位，输出顺序由 hits 决定。

`VectorSearchHit` 只包含搜索层结果；`KnowledgeChunk` 是知识内容；
`RetrievedSource` 是两者合并后的问答证据。向量编号可以作为索引内部位置，
但业务层应通过稳定 chunk_id 找正文，不把数组下标当作永久业务 ID。

## 字段映射

| RetrievedSource 字段 | 来源 |
|---|---|
| chunk_id、doc_id、title、source_url、text、section_title | KnowledgeChunk |
| score | VectorSearchHit |
| topic、pid_tags、page_start、page_end | 当前使用默认值 |

当前 `KnowledgeChunk.safety_notes` 没有对应的 RetrievedSource 独立字段，但
渲染阶段已经把安全说明写入 text。这能避免纯文本下游丢失说明，却不利于结构化
安全策略；后续扩展 metadata 时应显式设计，而不是从 text 反向解析。

## 失败机制

- 知识库出现重复 chunk_id：报错，即使 hits 为空也不能接受损坏的存储状态。
- 命中引用不存在的 chunk_id：报错，说明索引和正文存储版本不一致。
- hits 出现重复 chunk_id：报错，防止 Top-K 被重复证据占据。
- hits 为空且知识库 ID 唯一：返回空列表。

不能静默跳过缺失 ID，否则调用者会误以为 Top-K 完整。也不能按列表下标直接
取 Chunk，因为删除、插入、重建索引后位置可能变化。

## 验证、调试和替换

测试覆盖排名保持、score 和 metadata 映射、空命中、重复知识 ID、缺失 ID、
重复命中、输入不变及可变默认值隔离。当前测试数据为人工数据，不代表 RAG 质量。

```powershell
uv run --offline --directory ./server-v2 pytest tests/test_source_resolver.py -q
```

调试顺序：检查索引版本 → hit.chunk_id → Chunk 存储中的 ID → 输出顺序和字段。
未来可将字典替换为数据库批量查询，但仍应恢复 hit 排名并检查缺失/重复。
下一步先把 `Top-K + resolve` 串成最小检索服务，再决定 rerank 的插入接口。
