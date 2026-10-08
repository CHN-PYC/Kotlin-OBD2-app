# 输出预算对照学习卡

- 用途：评估压缩输出能否同时满足延迟、完整性与诊断信息需求。
- 输入：同一车辆样例、同一 qwen3:4b 模型、同一份精简输出 Prompt。
- 变量：num_predict 分别为 128 和 256；temperature=0、think=false、stream=false。
- 输出：耗时、实际 token 数、done_reason、schema_valid、accepted。
- 算法：调用真实 Ollama，使用 GeneratedVehicleAnswer 校验输出。
- 选择理由：在同一 Prompt 下只改变输出上限，观察截断与延迟之间的关系。
- 失败：length 即使有合法 JSON 也拒绝；stop 但 Schema 不合法同样拒绝。
- 调试：先检查 done_reason，再检查 Schema；不能根据 HTTP 200 或较短延迟宣布优化成功。
- 评测：每档一次调用是探索性实验，存在模型缓存、加载和机器负载影响，不能证明普遍提升。
- 可替换：后续比较结构化输出约束、适合硬件的小模型或远程 Provider。

## 验收条件

accepted = done_reason 为 stop 且 Schema 合法。这仍然只表示可进入业务处理，
并非诊断事实通过评审。通过后还需检查数据引用、谨慎表述和可用建议。
正式要求至少包含：不凭单次温度断言零件损坏，建议与已有规则证据相符，
不为了缩短文本而删去重要安全条件。

## 命令

```powershell
uv run --directory .\server-v2 python -m scripts.profile_ollama --case vehicle --compact --tokens 128 --timeout 90
uv run --directory .\server-v2 python -m scripts.profile_ollama --case vehicle --compact --tokens 256 --timeout 90
```

compact 只在本次脚本调用中追加短答指令；正式 Prompt 和服务默认 token 参数不变。
字符长度要求是自然语言提示，不是硬性 token 限制，中文字符数也不等于 token 数。
若两个候选都失败，应记录失败并换优化方向，而不是放宽 Parser 或接受截断答案。

## 实测结果（2026-09-06）

| 输出上限 | 输入 token | 实际输出 token | 输入处理秒 | 生成秒 | 总耗时秒 | 结束原因 | Schema |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 128 | 600 | 128 | 5.393 | 51.750 | 58.792 | length | 不通过 |
| 256 | 600 | 256 | 0.294 | 64.657 | 66.137 | length | 不通过 |

两档 accepted 均为 false。两个请求都带 think=false，但这一开关不保证输出遵守
紧凑 JSON 协议；本次未分析原始内容，不能声称具体失败原因就是思考文本。
256 档输入处理更快，可能受缓存和运行状态影响；单次顺序对照不是严格性能实验。
结论：仅追加精简输出提示并将上限设为 128/256，未使当前样例产生可接受答案。
正式 Prompt、Parser 和服务默认参数未改；下一方向是单独验证输出协议遵循能力，
例如 Provider 原生结构化输出约束，再考虑更换模型，不能把失败结果写成优化收益。
