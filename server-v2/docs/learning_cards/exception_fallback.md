# 意外异常兜底

## 用途与输入输出

输入为 VehicleQARequest，输出为 VehicleQAResponse。工作流中出现未预料的异常
（节点 bug、状态未完成、第三方库错误）时，返回规则兜底结果而不是 HTTP 500，
Android 端始终收到符合契约的响应。

## 数据流和算法

```text
QA 路由 -> ExceptionFallbackQAService -> DeadlineQAService -> WorkflowQAService
```

```text
try: 返回内层结果（正常时不改动）
except Exception: 记录异常类型 -> 规则兜底 -> trace 前插 unexpected_error
```

DeadlineQAService 只处理"请求总预算耗尽"；工作流节点自己处理"已知外部依赖
失败"（检索、模型、解析）；本层只处理"没人预料到的错误"。三者各管一种失败，
trace 中 request_deadline、unexpected_error、节点失败步骤可以区分原因。

## 为什么这样实现

用包装器组合已有 VehicleQAService Protocol，不修改工作流和超时类。放在最外层，
可以接住 DeadlineQAService 重新抛出的依赖 TimeoutError。相比 FastAPI 全局
exception handler，本层能返回业务契约内的诊断结果，而不只是错误 JSON。

## 失败与边界

- 只捕获 Exception；asyncio.CancelledError 属于 BaseException，继续传播。
- 日志和响应都不包含异常消息，避免泄露用户问题或内部地址。
- 规则兜底本身失败时不再捕获，由 FastAPI 返回 500，避免嵌套兜底。
- 兜底结果不写入会话记忆，与超时兜底一致。
- 宽泛捕获会掩盖 bug：HTTP 200 不代表系统健康，必须监控 unexpected_error 数量。

## 调试与验证

日志搜索 qa_unexpected_error type=...，按类型名定位后在本地复现；响应 trace
以 unexpected_error 开头。测试文件：test_exception_fallback.py，覆盖正常透传、
异常兜底且不泄露消息、取消传播、兜底失败不吞掉、API 返回 200。

## 可替换方案

需要统一错误格式时可增加 FastAPI 全局 exception handler 作为第二道防线；
接入请求 ID 后应在日志中带上它，便于从客户端反馈定位到具体异常。
