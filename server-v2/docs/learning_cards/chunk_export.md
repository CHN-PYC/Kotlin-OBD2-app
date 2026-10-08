# 候选 Chunk 落盘与核对

目的：在接 Embedding 前检查真实文件链路，保留可人工审阅的中间产物。
输入：data/processed/hella_air_mass_sensor.json。
输出：data/processed/hella_air_mass_sensor.chunks.json。

## 数据流

```text
read_text → json.loads → dict
ExtractedArticle.model_validate → 文章模型
build_section_chunks → list[KnowledgeChunk]
逐个 model_dump(mode="json") → 可序列化的 dict 列表
json.dumps → JSON 字符串
write_text → 文件
```

model_dump 不会写文件；json.dumps 也不会写文件，真正落盘的是 write_text。
model_validate 校验并构造模型对象，不能替代对文章正确性的人工审核。
source 和 extractor_version 保留在文件顶层，记录这一批片段的共同来源。
chunker_version=section-v1；status=candidate_not_token_checked 明确尚未检查 token。

## 技术选择

使用标准库 JSON 和 pathlib，不增加依赖或数据库。目的是便于检查中间结果。
片段生成复用已有函数，不复制分组或渲染算法。本节不调用网络或模型。
同一输入和实现重复运行会覆盖同一个输出文件，不会追加重复条目。

## 失败与验证

空片段、JSON 格式错误、文章校验失败会在写文件之前停止，已有输出保留。
禁止输入与输出指向同一路径，避免覆盖提取结果。
文件读取和写入错误向调用方抛出；当前是本地教学脚本，没有并发写保护、
原子替换或数据库事务，写入中途的磁盘故障仍可能留下不完整文件。
后续多文档处理可以改为 JSONL；线上更新需要版本和原子发布机制。

正常测试覆盖 JSON 往返、来源保留和输入不变；异常测试覆盖坏 JSON、
缺失结构、空正文以及同路径写入。真实文档得到 4 个候选 Chunk：

| 主题 | 字符数（不是 token 数） |
|---|---:|
| 原理 | 1344 |
| 表现 | 550 |
| 原因 | 605 |
| 检查方法 | 1179 |

上述统计含标题和安全说明，仅用于观察长度。每个片段保留 1 条安全说明。
下一步需要根据所选 Embedding 模型的 tokenizer 和输入上限检查 token，
不能用字符数、英语单词数或另一个模型的 tokenizer 代替精确计数。

调试：先检查输入 JSON 能否还原文章，再看分组数，最后逐项核对输出文本。
评估：检查每组是否丢失标题、正文、安全说明和来源；不代表检索评测已完成。

```powershell
uv run --directory ./server-v2 python -m scripts.build_hella_chunks
uv run --directory ./server-v2 pytest tests/test_chunk_export.py -q
```

理解题：model_dump、json.dumps、write_text 分别产生什么？哪一步才写磁盘？
