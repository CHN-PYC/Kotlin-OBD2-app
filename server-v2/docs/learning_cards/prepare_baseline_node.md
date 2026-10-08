# PrepareBaselineNode 学习卡

- 用途：为一次执行预先准备合法的规则备用响应。
- 输入：阶段为 received 的 VehicleAgentState，以及注入的 VehicleQAService。
- 输出：新 State，阶段为 baseline_prepared，保存 baseline_response 并追加 trace。
- 算法：检查阶段，await fallback.answer(state.request)，model_copy 返回新快照。
- 选择原因：复用已有规则服务；由确定性代码安排固定步骤。
- 失败：阶段错误抛 ValueError；规则服务自身异常向上传播，不能伪装为模型失败。
- 调试：比较输入和输出的 phase、baseline_response、trace。
- 评测：正常路径能生成备用响应；错误阶段被拒绝；旧 State 不应被修改。
- 可替换：将来可迁移为工作流框架节点，目前尚未接入 API 的执行流程。

## 两种星号

`def __init__(self, *, fallback)` 中的星号要求使用命名参数：
`PrepareBaselineNode(fallback=service)`。

`[*state.trace, step]` 中的星号展开旧列表元素，并构造新列表。
省略星号会得到嵌套列表；使用 `state.trace.append(step)` 会修改旧状态。
新列表中的旧记录对象仍然共享引用，这不是深复制或强制不可变。
