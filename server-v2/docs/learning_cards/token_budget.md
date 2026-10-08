# Token 预算检查（已实现）

## 目的、输入与输出

在 Embedding 请求前检查输入长度，避免自动截断导致证据丢失。
输入：待发送文本、对应模型的计数函数、正整数预算。
输出：符合预算时返回 token 数，否则 ValueError；计数器异常原样传播。
预算函数已完成，测试已移除 xfail 标记。真实 tokenizer 适配与检查脚本见
`real_tokenizer.md`。原始 Chunk 导出脚本保持不变。

## 算法与选择

```text
空白文本或预算 <= 0 → ValueError
count = count_tokens(原始 text)
count < 0 或 count > max_tokens → ValueError
返回 count
```

预算相等可接受。校验用 text.strip() 判断空白，但不能把 strip 后的文本
偷偷交给计数器；计数文本应与实际发送文本一致。
不按字符数估计，不因超长而静默裁剪，超长后的结构化二次切分另做一节。

Callable[[str], int] 表示“接收字符串、返回整数的可调用对象”。
把计数功能作为参数传入，就是函数级依赖注入；测试无需下载模型。
传入 count_tokens=my_counter，不是 count_tokens=my_counter(text)。
前者传函数，后者提前调用并传入整数，违反参数约定。

## 模型与预算边界

当前选用 BGE-M3 tokenizer 做本地长度实验，尚未接入 Embedding 推理服务。
不能用聊天模型 tokenizer 替代它；实际接服务时仍需核对：

- 计数时关闭截断，否则计数结果可能掩盖原文超长。
- 必须考虑该模型实际输入的特殊 token、指令或前缀。
- 本地预处理必须与服务端匹配，否则本地计数只是近似检查。
- 模型输入上限是硬约束，检索 Chunk 的目标长度是效果调优参数，两者不同。
- 多个 Chunk 的批量请求还可能有服务级总量约束，本节仅检查单条输入。

## 验证与调试

测试计数器固定返回数字，只验证预算规则，不代表任何真实分词算法。
正常测试覆盖预算内和恰好等于预算；失败测试覆盖超长、空输入、非法预算、
计数器负数结果和计数器故障，并验证原始文本只被计数一次。
预算函数使用 8 项普通测试，不再使用待完成标记。

```powershell
uv run --directory ./server-v2 pytest tests/test_token_budget.py -q
```

调试查看实际 text、count 和 max_tokens；本地测试不要只看字符数。
评估时还要对照实际 Embedding 服务的输入限制和超长行为，不能仅凭单元测试
就声称真实的四个候选 Chunk 已满足 token 预算。
可能替换：真实 tokenizer 或服务端计数接口，预算校验规则无需重写。
