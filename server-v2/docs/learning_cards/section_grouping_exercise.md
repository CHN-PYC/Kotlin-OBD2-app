# 主题分组练习（已实现）

目的：按连续的二级主题组织正文块，为后续 Chunk 构建准备候选单元。
输入：TextBlock 列表。输出：列表的列表，每个内层列表对应一个连续主题。

本节只写 group_section_blocks，不做最终 Chunk 文本、长度限制、ID 或 Embedding。
简介只含文档标题，暂时跳过；它仍保存在提取结果中，不是删除原始数据。
文档级 safety_notes 本节不处理，后续构建 Chunk 时必须显式保留。

## 算法与理由

```text
groups = 空列表
previous_key = 无
依次读取每个 block：
    heading_path 为空 → ValueError
    只有文档标题 → 跳过
    key = heading_path 的前两项
    key 与 previous_key 不同 → 新建一个组，更新 previous_key
    将 block 追加到最后一个组
返回 groups
```

顺序扫描适合保留章节和步骤次序。不要用全局字典将所有同名章节合并。
本节每个主题不设 overlap；超长主题的二次切分留到后续。
不需要新依赖。按块数计是一次线性遍历，输出分组占用线性空间。

## 验证与调试

测试涵盖正常分组、输入不变、重复章节名、不同文档名、空输入、简介和缺失路径。
分组函数已实现，测试的 xfail 标记已移除，按普通测试验证。

```powershell
uv run --directory ./server-v2 pytest tests/test_section_grouper.py -q
```

调试时看 key、previous_key、groups 的组数。检查是否遗漏新建第一组，
以及是否错误使用完整 heading_path 导致每个 h3 步骤各自分组。

当前 HELLA 快照预期得到 4 个候选组，块数依次为 2、3、5、7；简介 1 块跳过。
候选分组不代表最终切分效果最优。
后续可替换为长度受限的分段策略，但先验证这个确定性基线。

## 本次错误记录

- `groups: list[list[TextBlock]] = []`：冒号是类型标注，等号是赋值。
- `not block.heading_path` 检查空列表；`is None` 不能识别 `[]`。
- 跳过简介用 `continue`，`break` 会结束整个循环。
- `return groups` 放在循环外，否则处理一个正文块就提前返回。
- `previous_key` 在循环外初始化，比较后更新，这部分原本已经写对。
