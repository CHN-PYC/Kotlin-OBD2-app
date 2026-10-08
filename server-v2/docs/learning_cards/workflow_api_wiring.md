# Workflow 接入 API 学习卡

- 用途：让 POST /qa/vehicle 真正执行显式节点流程。
- 输入：VehicleQARequest，依赖函数组装六个节点和 WorkFlow。
- 输出：WorkflowQAService 从最终 State 提取 VehicleQAResponse。
- 算法：await workflow.run(request)，检查 completed 和非空 final_response，返回响应。
- 选择理由：适配器保持 VehicleQAService 的 answer 协议，HTTP 路由不需要认识内部 State。
- 失败机制：无模型配置直接选规则服务；Provider/解析错误由工作流降级；
  未完成或缺少最终响应抛 RuntimeError，暴露编程错误。
- 调试：成功 trace 应包含 prepare_baseline 到 build_response；
  降级路径保留先前记录并以 rule_fallback 结束。
- 验证：MockTransport 模拟成功、超时、非法 JSON、截断；检查重试次数、trace 和关闭资源。
- 可替换：将来替换 WorkFlow 的实现，保留适配器的 answer 协议。

## 依赖与生命周期

app.state 中保存共享模型，依赖函数按请求组装轻量节点。
每次 WorkFlow.run 创建独立 State。模型实例和 HTTP client 不写入 State。
适配器位于 workflow_qa_service.py：nodes.py 已依赖 qa_service.py 中的协议，
若在后者中直接导入 Workflow，会产生循环导入。

## 当前行为

已配置模型：路由 -> WorkflowQAService -> WorkFlow -> Nodes -> final_response。
未配置模型：路由 -> RuleFallbackQAService。
原 LLMVehicleQAService 保留作为前期参考与已有单测对象，API 不再选择它。
成功答案仍为 llm_only，未引入知识检索。
测试使用模拟 Provider，本节未实测本机 Ollama 的回答质量。
