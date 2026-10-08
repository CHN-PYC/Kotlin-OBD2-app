# Minimal RAG Closed Loop

## 离线写库

KnowledgeIngestionService 按 batch_size 切分 KnowledgeChunk，调用 EmbeddingModel 后再次
校验向量数量、维度和全零向量，再按位置构造 VectorRecord 并 upsert。当前每个批次
单独提交；如果后续批次失败，前面批次已经写入，但确定性 chunk ID 允许安全重跑。

```text
chunks JSON → EmbeddingRequest → validate → VectorRecord → VectorStore.upsert
```

`scripts/ingest_knowledge.py` 是离线入口，不暴露无鉴权的管理 API。它不会下载模型；
Ollama 未安装指定模型时会明确失败。当前示例知识文件是本地学习产物且被 Git 忽略。

## 在线问答

配置了 embedding 模型后，QueryRetrievalService 对 question 生成一个查询向量，按
`top_k * candidate_multiplier` 召回候选，经过 RetrievalPipeline 和 PassThroughReranker
得到最终证据。PassThrough 不是实际 Cross-Encoder，当前不会提升排序质量。

```text
prepare baseline
→ query embedding
→ VectorStore search
→ rerank baseline
→ evidence gate
→ prompt with retrievedEvidence
→ LLM
→ response with sources and trace
```

EvidenceGate 当前要求至少一条证据的 dense cosine score 达到
`evidence_min_dense_score=0.35`。这是未经业务评测的保守初始值，必须通过标注问题集分析
误放行和误拒绝后调整。门控失败不会调用 ChatModel，而是返回规则诊断，并使用
`insufficient_retrieval_evidence` answer mode。

Embedding 或 VectorStore 的分类异常会写入 retrieval_tool trace 并走规则 fallback；代码
错误不会被宽泛捕获。正常模型回答在响应中标记 `llm_rag` 并携带来源。

## Qdrant 本地开发

compose.yaml 固定 Qdrant v1.18.1，端口只绑定 127.0.0.1，并使用 Docker named volume，
避免 Windows bind mount 的已知持久化问题。当前 Docker 引擎未运行且镜像未缓存，因此
尚未进行真实服务 smoke test；单元测试使用 Qdrant SDK 内存模式。

真实闭环还需启动 Qdrant、确认 Ollama 已有 bge-m3、配置 .env、执行 ingestion，再启动
FastAPI。模型质量、混合检索、真实 rerank、索引版本迁移和 RAG 评测不属于本最小闭环。
