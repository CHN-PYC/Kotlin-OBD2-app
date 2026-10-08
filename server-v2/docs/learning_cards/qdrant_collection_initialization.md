# Qdrant Collection Initialization

## 目的与输入输出

QdrantVectorStore 构造函数接收 URL、collection 名称、向量维度、超时、可选 API key
和可注入客户端。构造阶段只保存配置；`ensure_collection()` 才执行异步网络操作。

```text
collection 不存在 → create_collection(size, COSINE)
collection 已存在 → get_collection → 校验向量模式、维度和距离
```

方法成功时无返回值；不兼容时抛出 `QdrantCollectionConfigurationError`。它不删除或
重建已有 collection，避免启动程序时意外破坏数据。

## 技术选择

使用 AsyncQdrantClient 是因为 FastAPI 和 VectorStore 契约均为异步 I/O。选择 COSINE
与当前内存精确检索的余弦相似度保持一致。单个 unnamed dense vector 是第一阶段最小
结构；混合检索需要 named dense/sparse vectors，将在后续版本显式迁移 collection。

客户端可从外部注入，单元测试使用 fake 验证参数而不依赖真实服务。只有类自己创建
客户端时，`aclose()` 才负责关闭，遵循“谁创建资源，谁释放资源”。

## 失败与调试

构造阶段拒绝空 collection 名、非正维度和超时。已有 collection 的维度、距离或向量
模式不匹配时快速失败。网络超时、鉴权失败、并发创建竞争和 SDK 异常映射尚未实现；
当前不能宣称完成了 Qdrant 读写或真实服务集成。

调试时依次检查 URL/端口、服务健康状态、鉴权、collection 是否存在、向量维度和距离。
下一步实现 Point ID、payload 映射和 upsert。
