# Top-K 向量检索基线

## 目的、输入和输出

输入一个查询向量、若干 `chunk_id + vector` 候选及 K，输出按余弦分数从高到低
排列的 `chunk_id + score`。本节使用人工向量，不调用 Embedding、网络或 FAISS，
也不根据 ID 读取正文。它是后续验证 FAISS 排名的可解释精确基线。

## 流程和算法

```text
校验 K 为正整数
→ 空候选直接返回 []
→ 检查 chunk_id 唯一
→ 查询向量依次与全部知识向量计算 cosine_similarity
→ 构造 VectorSearchHit(chunk_id, score)
→ 按 score 降序稳定排序
→ 返回前 K 条
```

`IndexedVector` 是索引输入；`VectorSearchHit` 是搜索输出。搜索结果不携带正文，
下一阶段再使用 chunk_id 映射到 KnowledgeChunk，保持搜索计算与文档存储分离。
score 约束在 [-1, 1]，它是相似度而不是相关概率或回答置信度。

当前实现是全量精确评分：N 个候选、D 维向量的评分成本约 O(ND)，全部排序
约 O(N log N)，结果列表占用 O(N)。当前只有少量片段，简单且便于审计。
大规模时可以用大小为 K 的堆减少排序工作，或换 FAISS；先保留本实现做基线。

## 边界和失败机制

- K 大于候选数量时返回所有候选；不会补足虚假结果。
- 空知识库返回空列表；此分支不计算查询向量。
- 相同分数保留候选输入顺序，保证测试和调试结果可复现。
- 重复 chunk_id 拒绝，否则后续无法唯一找回正文。
- 非法查询向量、零向量或维度不一致由 cosine_similarity 拒绝，不静默跳过。
- 候选向量由 Pydantic 拒绝空向量和非法数值；当前未检查所有候选维度预先一致。

全量排序后切片 `hits[:k]`：K 超过长度时 Python 自动返回全部，且不报错。
稳定排序只保证同分时沿用输入顺序，不代表这个顺序具有相关性意义。

## 验证、调试和替换

测试覆盖已知排名、分数、同分稳定性、超大 K、空候选、非法 K、重复 ID、
查询非法和输入不变。人工二维向量只验证算法，不能说明语义检索质量。

调试顺序：检查 K → chunk_id 唯一性 → 向量维度 → 每项 score → 最终排序。
后续接真实模型时还要评测 Recall@K、MRR 和 bad case；Top-K 总会返回最相似项，
不保证这些项足以回答问题，因此后面仍需要 Evidence Gate。

```powershell
uv run --offline --directory ./server-v2 pytest tests/test_top_k_search.py -q
```

可替换方案：归一化矩阵的批量内积、堆选 Top-K、FAISS IndexFlatIP 或近似索引。
替换后应使用同一批固定向量，先与该精确基线比较 ID 和分数。
