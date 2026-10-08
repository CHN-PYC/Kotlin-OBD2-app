# Rerank 插入位置与管线

## 当前状态

本节实现了 rerank 契约、PassThrough 基线和 RetrievalPipeline，但没有下载或调用
真实重排模型。它用于讲清流程和验证边界，不能宣称项目已经提升了排序质量。

## 输入、输出与数据流

```text
query_vector → await VectorStore.search 召回 candidate_k 条 RetrievedSource
query_text + 候选正文 → Reranker 返回全部候选的 chunk_id + rerank_score
校验 ID 集合与候选完全一致 → 按 rerank_score 降序稳定排序 → 取 final_k
→ RerankedSource
```

为什么需要 query_text：Cross-Encoder 类 reranker 通常直接联合读取问题和候选正文，
而第一阶段 Dense Retriever 使用预先生成的文档向量与查询向量，更适合大范围召回。
`candidate_k >= final_k > 0`，否则重排阶段没有额外候选可筛选。

## 两种分数

`RerankedSource.source.score` 保留第一阶段余弦召回分数；`rerank_score` 保存第二阶段
分数。二者来自不同算法，量纲可能完全不同，不能直接相加，也不能统一解释成概率。
PassThroughReranker 只是复制召回顺序和分数，用于关闭真实 rerank 时保持统一流程。

Reranker 只返回 ID 和分数，正文从原候选映射回来。这样模型不能在重排过程中修改
证据文本。管线要求每个候选恰好返回一次，拒绝缺失、重复或未知 ID；排序由管线
统一执行，不假设 provider 已经正确排序。同分沿用 provider 返回顺序。

## 技术选择和复杂度

Reranker 使用 Protocol，后续本地模型或远程 API 都能替换；方法定义为 async，
因为真实实现可能等待模型服务。`async` 不代表候选会自动并行处理，批量方式由具体
实现决定。流水线依赖 VectorStore 契约，并使用 `await search()`，因此当前内存实现
和未来 Qdrant 网络实现可以替换。ExactDenseRetriever 继续作为同步精确算法基线。

当前管线未实现超时、重试、批次限制或 rerank fallback。真实 reranker 失败时可考虑
显式降级到 Dense 排名，并记录模式与 trace；不能悄悄吞掉异常。

## 验证与后续评测

测试覆盖 candidate_k/final_k 传递、重排顺序、两种分数、PassThrough、空召回、
非法参数和损坏的 rerank 返回。FakeReverse 只是证明顺序能变化，不代表算法有效。

```powershell
uv run --offline --directory ./server-v2 pytest tests/test_retrieval_pipeline.py -q
```

真实模型是否值得接入，应比较 rerank 前后的 MRR、nDCG@K、Recall@K、延迟和成本。
Recall@candidate_k 决定正确证据是否进入候选；reranker 无法找回第一阶段漏掉的证据。
下一步可以先定义一小批检索评测样例，再决定使用哪种 reranker，而不是只看模型榜单。
