# Embedding 输入输出契约

## 目的、输入与输出

定义可替换 Embedding 服务的共同接口，沿用 ChatModel 的 Protocol 模式。
输入：EmbeddingRequest.texts，按顺序排列的非空文本列表。
输出：EmbeddingResult，包含 provider、model 和二维 vectors 列表。
约定 vectors[i] 对应 texts[i]，但仅凭 schema 无法验证语义对应关系。
本节没有真实模型、HTTP 请求、向量持久化或索引。

## 类型选择

Annotated[T, Field(...)] 是给类型 T 附加 Pydantic 校验约束。
texts 外层 min_length=1 保证至少一条文本，EmbeddingText 保证每个元素
都是非空字符串；field_validator 额外排除仅空白的内容，保留原始文本不裁剪。
文本必须与上一阶段 token 检查的文本一致。

vectors 的外层是批次，内层是单个文本的向量。例如两条文本的二维测试向量
形如 [[0.1, 0.2], [0.3, 0.4]]；这里不是实际 BGE-M3 输出维度。
VectorValue 拒绝 NaN、正负无穷以及字符串、布尔值，防止无效数值进入检索。
非空列表检查不等于维度校验，也不保证向量已经归一化。

Protocol 类似 Java 接口：只规定能力，不规定 HTTP 协议、服务地址或模型实现。
async embed 是因为后续需要等待服务响应；async 本身不会自动产生并行调用。
无 temperature、对话 role、输出文本或 answer_mode，这些不是此接口的职责。

## 验证与边界

正常测试使用 FakeEmbeddingModel 验证接口、批次顺序和类型。
失败测试覆盖空批次、空文本、非字符串、空向量、NaN、Infinity 等。
Fake 的数值只是测试数据，不具备语义，不能用来证明真实检索质量。

本节未实现的检查：

- 向量条数是否等于请求文本条数。
- 每条向量是否具有期望维度，各条维度是否一致。
- 是否为全零向量，以及后续相似度计算需要的归一化。
- 返回的模型身份与实际所用模型版本是否匹配。
- token 上限、批次大小、超时、重试和远程服务错误映射。

调试先看 texts 数量和内容，再看 vectors 的条数及内层长度，不要把
token ID 列表误当成返回向量。实际模型的顺序保证要在 provider 适配中测试。
评估目前只覆盖契约行为，不评估模型效果；下一节补跨请求的响应校验。
可替换为不同 provider 的实现，不需要调用者依赖具体 HTTP 格式。

```powershell
uv run --directory ./server-v2 pytest tests/test_embedding_contract.py -q
```
