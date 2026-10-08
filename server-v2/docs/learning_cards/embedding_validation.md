# Embedding 返回值校验

本节以读懂参考实现为主，暂不要求学习者手写代码。

## 目的、输入和输出

避免数量、维度错误的向量进入后续索引。输入是已通过 Pydantic 基础校验的
EmbeddingRequest、EmbeddingResult，以及期望维度 expected_dimension。
成功返回原 result，不归一化、不裁剪、不补向量；失败抛出异常。
函数已实现但尚未接入真实 provider，没有调用模型或写入索引。

## 数据流与规则

```text
预期维度必须为正数（本地配置错误用 ValueError）
→ 返回向量条数等于请求文本条数
→ 每条向量长度等于预期维度
→ 每条向量不是全零
→ 返回原结果
```

后三种错误沿用 InvalidModelResponseError，code=invalid_response、retryable=False。
格式或契约错误通常不会因为立即重试而改善，本节不新增重试策略。
expected_dimension 来自所选模型与实际输出配置，不从响应第一条向量推断：
如果错误模型返回了统一的错误维度，内部维度一致仍不足以通过。

## 为什么分两层校验

EmbeddingResult 负责基础格式：列表非空、数字有限等。
validate_embedding_result 负责本次调用关系：输入几条、期望几维。
result 自身不知道请求有多少条，所以不能只靠字段校验解决。
普通循环即可完成，不增加框架。维度和数量检查开销小，非零检查最坏需要
扫描所有分量；检查过程不复制完整向量，不额外增加归一化工作。

## 全零向量与边界

[0.0, 1.0] 可以接受，[0.0, 0.0] 不接受。
这是为后续余弦检索设置的规则：全零向量的范数为零，无法定义余弦相似度。
通过本函数不代表范数已经归一化，也不证明向量语义有效。
期望维度参数按类型契约传入整数；完整服务配置校验由后续 Settings 负责。

## 验证与调试

测试覆盖正常结果、保持原值、缺失或多余向量、维度不一致、统一错误维度、
全零向量与非法维度参数。采用二维测试向量是为了便于阅读，不代表 BGE-M3 维度。
调试顺序：len(request.texts) → len(result.vectors) → 每条 len(vector)。
不要把异常修成零向量 fallback，不要用 zip 默认截断来掩盖数量不一致。

```powershell
uv run --directory ./server-v2 pytest tests/test_embedding_validation.py -q
```

尚不能发现的错误：顺序错乱但数量和维度都对、错误模型却维度相同、语义召回差。
后续 provider 必须保证请求响应顺序与模型配置，召回质量需要检索评测。
可替换方式：在未来批处理服务中统一调用这段校验，无需每个 provider 重写。
下一步才是 Ollama Embedding 请求与响应适配。
