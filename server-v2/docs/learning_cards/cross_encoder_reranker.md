# Cross-Encoder Reranker 核心适配层

## 目的与数据流

第一阶段向量检索快速召回候选；本模块将每条候选转换为
`(query_text, document_text)`，批量交给 Cross-Encoder，再按输入位置把分数绑定回
`chunk_id`。它不会拼接 query 向量和文档向量，也不允许模型改写证据正文。

```text
query + candidate texts
→ RerankPair[]
→ CrossEncoderModel.score_pairs()
→ scores[]
→ RerankHit(chunk_id, score)[]
```

## 为什么这样设计

`CrossEncoderModel` 是类似 Java interface 的 Protocol。业务层只依赖“批量为文本对评分”
的能力，因此后续可以使用 sentence-transformers、本地推理服务或远程 API，而不修改
RetrievalPipeline。批量输入能减少模型调用开销，但批次过大会增加显存和延迟。

结果按位置对应输入，因此数量必须完全一致。分数只要求是有限浮点数，不限制在
`0..1`：很多 reranker 输出的是未归一化 logit，不能直接解释为概率。

## 失败、调试与评测

空查询在调用模型前拒绝；空候选直接返回；分数数量不一致、NaN 或无穷值都视为损坏
响应。provider 的超时和连接异常应继续向上抛，由后续显式 fallback 节点决定是否降级
为向量排序，不能在本层静默吞掉。

调试时记录模型名、候选数、耗时以及脱敏后的 chunk_id。效果需要对比 rerank 前后的
MRR、nDCG@K 和 Precision@K，同时观察 P95 延迟；不能只凭模型名称判断效果。

当前只完成模型无关的适配层和假模型测试，尚未安装或运行真实 Cross-Encoder。
