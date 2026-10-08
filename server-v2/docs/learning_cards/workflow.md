# 手动 Workflow 学习卡

- 用途：以固定顺序调度节点，在已知失败时选择降级路径。
- 输入：VehicleQARequest 和构造器注入的六个节点。
- 输出：completed 阶段的 VehicleAgentState，其中 final_response 已存在。
- 算法：准备 baseline、构建 Prompt、调用模型；失败直接降级返回；
  否则解析结果，解析失败降级返回，成功则构建响应。
- 选型：固定顺序加两个 if 足以表达当前流程，无循环，暂不需要通用图执行器。
- 失败：已知 Provider 和解析错误由节点转换成 fallback；代码错误继续向上传播。
- 调试：查看 phase、failure_code 与累计 trace；每步必须接住返回的新 State。
- 验证：成功、超时、非法 JSON、截断、同一 Workflow 在失败后执行新请求。
- 替换：未来可迁移到图框架；目前已通过 WorkflowQAService 接入 FastAPI。

## 要点

State 保存数据，Node 执行一步，Workflow 决定执行顺序。
run 中创建状态，避免不同请求共享本次执行数据。
降级分支必须 return，否则后续节点会收到错误阶段。
completed 表示流程结束，业务是否降级看 final_response.answer_mode。
Workflow 每次只调一次模型节点，Provider 装饰器内部仍可能进行多次 HTTP 重试。
