# Qdrant Configuration

## 目的与字段

本节只定义配置，不创建客户端或 collection。`vector_store_provider` 决定运行时选择
memory 还是 qdrant；默认 memory 保证未启动外部服务时仍能开发和测试。

`embedding_dimension` 是 Embedding 模型输出维度，也是 MemoryVectorStore 和 Qdrant
collection 的向量维度。默认 1024 对应计划使用的 BGE-M3 dense embedding；换模型时
必须创建匹配维度的新 collection，不能把不同维度写入旧 collection。

`qdrant_url` 是服务地址，`qdrant_collection_name` 是知识索引的逻辑集合名，
`qdrant_timeout_seconds` 限制一次存储请求的等待时间。`qdrant_api_key` 用于远程或云端
鉴权，本地默认空值；SecretStr 只防止 repr 直接泄露，不代替密钥管理。

## 选择和失败

collection 名称带 `v1`，便于 embedding 模型、切分规则或 schema 发生不兼容变化时
构建新版本并切换，而不是直接破坏线上索引。配置层拒绝未知 provider、非正维度、
非法集合名以及非正或无穷超时，让错误在启动阶段出现，而不是首次检索时才暴露。

测试覆盖安全本地默认值、环境变量覆盖、SecretStr 脱敏和非法配置。下一步才安装
qdrant-client，并使用这些字段构造 provider；当前不能宣称 Qdrant 已经接入。
