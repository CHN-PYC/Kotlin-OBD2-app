# 请求预算、重试与熔断

## 用途与输入输出

输入仍为 VehicleQARequest，输出仍为 VehicleQAResponse。模型服务持续故障时
避免每个请求重复等待；整条请求链路超出预算时返回可解释的规则结果。

## 数据流和算法

```text
QA 路由 -> DeadlineQAService -> WorkflowQAService
        -> CircuitBreakerChatModel -> RetryingChatModel -> 模型 API
```

```text
closed：允许调用，可重试故障达到阈值 -> open
open：冷却期内快速失败；冷却期结束 -> half_open
half_open：只允许一个探测；成功 -> closed；失败/取消 -> open
```

重试解决一次请求的短暂故障；熔断处理多次请求观察到的持续故障；总预算限制
一个请求在多个阶段累计的等待时间。熔断器位于重试外层，3 次尝试都失败算
1 次失败请求。默认阈值 5、冷却 30 秒、总预算 60 秒均为初始配置，应根据
下游延迟和故障率校准，不代表评测得出的最优值。

## 为什么这样实现

用现有 Protocol 装饰模型即可保持节点不变，不需要新增框架。使用 monotonic
计时避免系统时钟跳变。状态判断到探测占位之间没有 await，在同一事件循环中
不会被其他任务插入；这不是跨线程或跨进程锁。epoch 标识阻止旧调用修改
新熔断状态。模型由 lifespan 创建并存入 app.state，不能每个请求重新创建。

## 失败与边界

- 熔断错误为 circuit_open，已有模型失败分支将其转为规则建议。
- 请求超时 trace 包含 request_deadline 和 rule_fallback，HTTP 200 表示
  已返回有效降级结果，不代表模型调用成功。
- 半开探测取消必须释放占位，否则后续请求会永久被拒绝。
- asyncio.timeout 会取消等待中的协程，不能杀死已运行的推理线程或撤销写入。
- 用户取消应继续传播；依赖自身抛出的 TimeoutError 不冒充请求预算耗尽。
- request deadline 从 QA 服务调用开始，不包含请求体上传和依赖组装。
- 当前熔断仅作用于 chat 模型，未实现分布式共享状态。

## 调试与验证

检查 request_deadline、model_generation 的 trace 和 circuit_open 错误码，
再检查 provider 超时、重试次数、总预算之间的关系。单元测试注入时钟推进
冷却，不真实等待 30 秒；并发测试使用 Event 控制旧请求与探测的完成顺序。

测试文件：test_circuit_breaker.py、test_request_deadline.py、
test_chat_model_factory.py。线上应观察请求 p95、降级率、熔断拒绝数量和探测
成功率；本次尚未接入这些指标的监控平台。

## 可替换方案

需要多进程统一配额或集中熔断时可由服务网关承担；需要持久化运行状态或恢复
执行时再评估工作流引擎。Redis 会话历史不能代替执行检查点。
