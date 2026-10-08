# BuildPromptNode 学习卡

- 用途：将已有 Prompt Builder 接到显式状态流程中。
- 输入：phase=baseline_prepared 且 baseline_response 非空的 VehicleAgentState。
- 输出：新快照，phase=prompt_built，保存 chat_request 并追加 prompt_build completed。
- 算法：检查阶段和必要数据，调用 builder.build(state.request)，model_copy 更新快照。
- 选择原因：复用 Prompt Builder 的消息构建能力，由 Node 管理执行条件和状态更新。
- 失败：错误阶段或缺少 baseline 时抛 ValueError；这是流程错误，不伪装成模型故障。
- 调试：先检查 phase 和 baseline，再比较 chat_request 与 trace；确认旧快照未被修改。
- 评测：测试正常构建、跳过前置节点、重复执行、缺少 baseline，以及历史 trace 保留。
- 可替换：将来可包装为工作流框架节点；当前 API 仍使用已有 QA Service。

## 关键语法

run 使用普通 def：Prompt Builder 只进行内存数据转换，没有需要 await 的异步调用。
__init__ 标注 -> None：构造器初始化实例，不返回业务结果。
model_copy 是浅复制，[*state.trace, step] 创建新列表；旧记录对象仍共享引用。
检查 phase 并不能替代检查字段，因为 model_copy(update=...) 不重新校验更新值。
