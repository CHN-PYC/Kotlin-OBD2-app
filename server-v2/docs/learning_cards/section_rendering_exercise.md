# 章节文本渲染（已实现）

目的：将已分组的正文块变成易读文本，为后续候选 Chunk 组装准备正文。
输入：同一章节的 TextBlock 列表、文档级 safety_notes。
输出：保留文档标题、章节标题、子标题、列表和安全说明的字符串。
当前不生成 Chunk ID、来源 metadata、Embedding，也不做长度限制。

## 算法与选择原因

```text
空 blocks → ValueError
检查所有路径至少有两项，且前两项一致；否则 ValueError
lines = 文档标题和章节标题
向 lines 添加带 Safety: 前缀的安全说明
previous_subheading = None
按顺序遍历 blocks：
    当前 subheading = 路径第三项，没有则为 None
    当前 subheading 非空且与上次不同 → 添加子标题
    更新 previous_subheading
    列表项添加 '- ' 前缀；普通段落原样添加
以两个换行符连接 lines，返回结果
```

这是确定性格式转换，不让 LLM 改写原文。原始 block 仍是追溯依据。
当前提取器只产生最多三级标题和平面列表；更深层级或嵌套列表需要扩展设计。
标题重复是补充上下文，不是相邻 Chunk 的 overlap。
Safety 标签只保留信息，不构成强制安全机制，后续流程仍须处理适用范围。

## 失败、调试与验证

索引 blocks[0] 前检查空输入；读取路径第三项前检查长度。
不能把两个章节静默拼成一个 Chunk。不得修改输入列表或对象。
单独观察 lines 和 previous_subheading，定位标题重复或丢失问题。

测试覆盖正常格式、列表、安全说明、无子标题、空输入和混合文档/章节。
函数已实现，未完成标记已移除，使用普通回归测试。
额外验证同名子标题在其他子标题之后再次出现时不会被全局去重。

## 阅读代码的三个重点

1. 第一段循环只校验：不能把不同章节混在一起，也不能缺少文档或章节标题。
2. 第二段循环才组装：previous_subheading 记住上一个子标题，连续相同则不重复写。
3. lines 是字符串列表；最后用 join 转成一个字符串，return 必须放在循环外。

`section_key.copy()` 创建新列表，追加正文不会修改源数据的标题列表。
`f"Safety: {note}"` 是字符串插值，把 note 的内容放到固定前缀后面。

```powershell
uv run --directory ./server-v2 pytest tests/test_section_renderer.py -q
```

评估：对照原始组，检查每段文字顺序、标题归属和安全说明是否保留。
可能替换：更复杂文档可用结构化模板渲染，或直接保留块结构给下游；暂不引入框架。
