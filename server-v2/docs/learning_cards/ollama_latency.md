# Ollama 超时定位学习卡

- 用途：区分模型加载、输入处理、输出生成的耗时，避免只盲目增加 timeout。
- 输入：tiny 短请求或已有 vehicle 样例；显式输出 token 上限和请求超时。
- 输出：load_duration、prompt_eval_duration、eval_duration、实际 token 数及速度。
- 算法：读取 Ollama 原始响应中的纳秒计时，除以 1e9 转秒；
  tokens_per_second = eval_count / eval_duration_seconds。
- 选择原因：先测极短输入和输出，再比较连续请求，观察加载与稳定生成的区别。
- 失败：超时不能获得完整统计；length 表示人为限制下的截断，不能算诊断成功。
- 调试：结合 /api/ps 的内存和显存占用判断是否完整放入 GPU。
- 评测：本轮是小样本诊断，不是吞吐 benchmark，不足以推断并发性能或 P95。
- 可替换：资源允许时比较更小模型、远程模型或硬件加速；任何选择都需同一测试集验证。

## 实测记录

2026-09-06：MX450 独显 2 GiB。/api/ps 报模型 size=3584224768 字节，
size_vram=1332018688 字节，context_length=4096。模型未完整驻留显存。

tiny 请求，num_predict=16，think=false，stream=false，temperature=0：

| 指标 | 第一次 | 紧接着第二次 |
| --- | --- | --- |
| load 秒 | 10.150 | 0.474 |
| prompt_eval 秒 | 3.436 | 0.271 |
| eval 秒 | 8.858 | 3.536 |
| 实际输出 token | 16 | 16 |
| token/秒 | 1.81 | 4.52 |
| 客户端总秒数 | 27.797 | 5.139 |
| done_reason | length | length |

第二次更快表明加载和预热有影响；不据此声称首次一定是完全冷启动。
若以第二次速度粗略外推，生成满 512 token 约需 113 秒，不含输入处理和排队。
512 是输出上限，不代表每次必定生成 512；速度也可能随负载和上下文变化。
tiny 请求即使只要求回复 OK 也生成至上限，说明这次不能假设模型会严格短答。
本轮没有修改生产 timeout 或 num_predict；先记录实际性能，再进行参数对照实验。

车辆输入对照：542 个输入 token，输入处理 8.341 秒；生成 16 token 花 3.614 秒，
速度 4.43 token/秒，加载 0.229 秒，客户端总计 12.750 秒，结束原因为 length。
这说明完整输入还增加了约 8 秒处理时间；在这次配置下，生成速度仍是重要约束。
前次完整请求的超时没有返回计时明细，以上结果只能解释可能的性能瓶颈，
不能重建那一次超时请求的每个阶段耗时。

## 命令

```powershell
uv run --directory .\server-v2 python -m scripts.profile_ollama --case tiny --tokens 16 --timeout 60
uv run --directory .\server-v2 python -m scripts.profile_ollama --case vehicle --tokens 16 --timeout 60
```

脚本直连 Ollama，复用 Prompt Builder 的车辆输入，不经过 FastAPI；
用于拆解性能，完整业务联调继续使用 smoke_vehicle_qa.py。
不打印模型原始文本或密钥；本轮参数仅对脚本此次调用生效。
