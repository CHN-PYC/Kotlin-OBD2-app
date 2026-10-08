# 输出节点学习卡

- 用途：把模型结果验收、成功响应、失败降级拆成三个可测试节点。
- 输入：ParseModelOutputNode 接收 model_generated 和 chat_result；
  BuildResponseNode 接收 output_parsed 和 generated_answer；
  RuleFallbackNode 接收 fallback 和 failure_code。三者都要求 baseline_response。
- 输出：解析成功进入 output_parsed，解析失败进入 fallback；两个响应节点进入 completed。
- 算法：先检查 finish_reason，再执行 Parser；成功使用结构化字段，失败保留规则内容。
- 选择理由：复用现有 Parser 和规则服务，控制决策由确定性代码执行。
- 失败：非法 JSON、Schema 错误、非 stop 结束原因进入 fallback；前置条件错误抛 ValueError。
- 调试：检查 failure_code 和累计 trace；State.trace 与最终 response.agent_trace 内容一致。
- 评测：覆盖成功、非法 JSON、缺字段、合法 JSON 但被截断、缺前置数据和重复执行。
- 可替换：将来可以封装到框架节点，当前尚未接入 API 工作流。

## 终止语义

fallback 表示等待降级处理，completed 表示已经产生最终响应。
completed 不等于模型成功，须结合 answer_mode 判断业务结果。
模型生成节点 completed trace 仅表示调用取得结果；随后解析节点仍可能 failed。
Schema 校验只保证结构，不验证诊断事实，confidence 仍为原流程的启发式标签。

## 下一步：Workflow

Workflow 负责调度，节点负责处理数据。先采用固定顺序和显式 if 分支：
准备 baseline -> 构建 Prompt -> 模型调用 -> 失败则降级，否则解析。
解析失败则降级，解析成功则构造响应。此流程无循环，每次只调用一次模型节点。
