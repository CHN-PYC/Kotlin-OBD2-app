# 候选 Chunk 组装（已实现）

目的：把现有分组和文本组装连接起来，得到带来源的知识单元。
输入：ExtractedArticle、doc_id、source_url。输出：list[KnowledgeChunk]。
模型与 build_section_chunks 已实现；本函数返回内存对象，不自动生成 Chunk 文件。

## 流程和选择理由

```text
去除 doc_id/source_url 首尾空白，空值报错
检查每个正文块的文档标题与 article.title 一致
groups = group_section_blocks(article.blocks)
chunks = []
用 enumerate(groups, start=1) 遍历编号和组：
    text = render_section(group, safety_notes=article.safety_notes)
    创建 KnowledgeChunk，放入 chunks
返回 chunks
```

chunk_id 使用 doc_id:section:编号；section_title 来自 group[0].heading_path[1]。
保留安全说明的结构化字段，同时正文带有安全说明，避免只传 text 时丢失。
KnowledgeChunk 没有 score，因为相关性分数要等具体问题检索时才产生。
没有新增依赖，不重写已测试的分组和渲染逻辑。

## 边界与调试

无主题组返回 []；来源为空或文档标题不一致报错，不创建假来源。
schema 目前只检查 source_url 非空，不验证 URL 可访问或允许抓取。
顺序 ID 在章节插入后会改变，更新文本也不会自动改变编号；暂不支持增量更新。
先看 groups 数量，再看每个 chunk 的编号、章节、安全说明和正文。
测试覆盖正常组装、输入不变、来源空值、空文章、标题不一致及 schema 校验。

```powershell
uv run --directory ./server-v2 pytest tests/test_chunk_builder.py -q
```

unfinished 标记已移除，使用普通回归测试，另补充空标题路径和仅简介的边界测试。
评估：逐组核对来源与正文，不把测试通过等同于召回效果良好。
当前仍为候选 Chunk，未做 token 长度检查、持久化、Embedding 或索引。
后续替换：版本化 ID、长度受限切分、完整来源快照引用，分别单独实现。

## 本次错误与导入排查

- 正确导入：`from app.schemas.knowledge import KnowledgeChunk`，模块文件名小写，类名大小写必须匹配。
- `KnowledgeChunk = {...}` 是给局部变量赋值，遮住了类名，不会创建模型。
- 正确关系：KnowledgeChunk 是类；chunk = KnowledgeChunk(...) 是实例；chunks 是实例列表。
- `chunks.append(chunk)` 需要传入要追加的对象；groups 必须先调用分组函数得到。
- render_section 的 safety_notes 是必填关键字参数；return chunks 必须放在循环外。
- 函数返回类型应为 list[KnowledgeChunk]，不能保留 None 或占位异常。

终端导入已经成功。如果 IDE 仍报错，检查是否使用 server-v2/.venv 的解释器，
以及 server-v2 是否是源码根目录和运行配置工作目录，不要用 noqa 隐藏导入问题。

```powershell
uv run --directory ./server-v2 python -c "from app.schemas.knowledge import KnowledgeChunk; print(KnowledgeChunk.__name__)"
```
