# 真实 Tokenizer 与候选片段长度

## 目的与状态

用 BGE-M3 对应的 tokenizer 对完整候选 Chunk 计数，再调用已完成的预算函数。
只加载分词器 JSON，不加载模型权重、不调用 Ollama，不产生 Embedding。
输入：候选 Chunk 文件和本地 tokenizer.json。
输出：data/processed/hella_air_mass_sensor.token_report.json。
原 Chunk 文件不变，报告不代表它们已经完成检索质量评测。

## 技术选型

沿用学习计划里的 BGE-M3。它支持多语言，适合后续尝试中文问题检索英文资料。
官方模型卡和配置给出 8192 tokens 的序列长度；1024 是稠密向量维度，
不是 token 上限。本节不生成任何稠密、稀疏或多向量表示。

- [官方模型卡](https://huggingface.co/BAAI/bge-m3)
- [固定版本配置](https://huggingface.co/BAAI/bge-m3/raw/5617a9f61b028005a4858fdac845db406aefb181/tokenizer_config.json)
- [Tokenizers API](https://huggingface.co/docs/tokenizers/api/tokenizer)

使用 tokenizers 库直接加载本地文件，不需要安装模型推理框架。
它比手写分词更准确地复用模型词表和规则；固定版本与 SHA256 避免文件漂移。
来源记录：data/sources/bge_m3_tokenizer.json；文件位于 data/tokenizers/bge-m3/，
已排除 Git 提交。依赖版本由 uv.lock 记录。

## 代码数据流

```text
LocalTokenCounter 加载本地 tokenizer.json
→ no_truncation / no_padding
→ encode(text, add_special_tokens=True)
→ len(encoding.ids)
→ validate_token_budget
→ 写入计数报告
```

关闭截断：保证超长输入按真实长度计数，不能在检查前就被裁掉。
关闭填充：不把为批处理补齐的 padding 当作片段实际长度。
包含特殊 token：单条模型输入除了正文，还可能有起止标记。
Tokenizer 的整数 ID 是词表编号，不是语义向量。

核心调用是 `count_tokens=counter.count_tokens`，这里传方法本身。
预算函数随后执行 `count_tokens(text)`，不会在传参时提前运行方法。

## 参数与实测

本次试验预算为 512 tokens，区别于模型的 8192 上限。
512 只是初始候选片段预算，未证明最优，后续需要检索评测调整。
完整 text 包含标题、安全说明、步骤与换行，实测：

| 主题 | tokens |
|---|---:|
| 原理 | 291 |
| 表现 | 114 |
| 原因 | 135 |
| 检查方法 | 244 |

四个候选片段都满足本次预算，无需仅为长度再次切分。
这只证明本地固定分词器下的长度，不证明召回有效，也不证明服务端使用同一配置。
后续接入 Ollama/API 时必须核对模型、分词、前缀、上下文配置及是否默认截断。

## 失败、调试和验证

找不到 tokenizer 文件直接报错，不用字符数回退冒充 token 数。
文件哈希不匹配时检查脚本停止；坏文件加载错误原样传播。
测试使用微型本地 tokenizer 验证特殊 token、关闭截断/填充、预算注入和缺失文件。
真实 BGE-M3 文件用于手动集成检查，默认测试不依赖网络或模型下载。
超长输入通过预算函数拒绝，不会静默删除末尾的证据。

```powershell
uv run --directory ./server-v2 python -m scripts.check_chunk_tokens
uv run --directory ./server-v2 pytest tests/test_token_budget.py tests/test_token_counter.py -q
```

调试顺序：确认本地路径和版本 → 检查 encode 设置 → 查看 token 数和预算。
可替换方案：实际供应商提供的 tokenizer 或计数接口；预算规则可以复用。
下一步是 Embedding 请求/响应契约，不是继续扩大这批短片段的切分逻辑。
