# Async VectorStore Pipeline

## 目的与数据流

RetrievalPipeline 依赖 VectorStore 契约，通过
`await vector_store.search(query_vector, k=candidate_k)` 获取第一阶段候选，再执行
rerank 和 final_k 截取。输入是查询文本、查询向量及两级 K，输出是保留 dense score
和 rerank score 的 `RerankedSource`。

## 为什么选择异步接口

MemoryVectorStore 当前没有网络等待，但 Qdrant 实现需要 HTTP/gRPC I/O。提前统一为
async 接口，使流水线不依赖具体存储位置。`await` 会在 I/O 等待期间把执行权交回事件
循环，并不表示搜索本身自动并行，也不会让 CPU 密集型余弦计算自然加速。

## 失败、调试与评测

VectorStore 的超时、连接失败和损坏响应当前继续向上抛；后续在明确的 fallback 层记录
trace 并决定是否降级。调试顺序是检查查询参数校验、VectorStore 调用、候选数量、
reranker 返回和最终排序。测试使用 FakeVectorStore，验证 candidate_k 传递、空召回跳过
rerank、损坏重排结果拒绝，以及流水线不会调用 upsert/delete。

可替换实现包括 MemoryVectorStore、QdrantVectorStore 或其他满足同一契约的存储。
ExactDenseRetriever 保留为同步、可解释的算法基线，不再作为流水线的运行时依赖。
