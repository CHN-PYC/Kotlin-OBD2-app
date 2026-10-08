# HTML 正文提取

## 目的与边界

把已下载的网页变成保留结构的正文块。本节不做 Chunk、Embedding 或索引，
也不调用 LLM。实现针对当前 HELLA 教程页面模板，并非所有网站通用。

## 输入、输出与流程

- 输入：`data/raw/hella_air_mass_sensor.html` 和来源 JSON。
- 输出：`data/processed/hella_air_mass_sensor.json`，包含来源、标题、安全说明和正文块。
- 每个块包含 `heading_path`、`kind`、`text`，数组顺序就是原始阅读顺序。
- `kind` 区分段落与列表项；目前不建模嵌套列表、表格和多媒体。
- 安全说明属于文档级约束，后续 Chunk 和 Prompt 必须显式继承，当前尚未接入。

```text
校验原始文件 SHA256
→ BeautifulSoup 解析 HTML
→ 定位 main 和文章模块
→ 排除控件，跳过视频模块
→ 更新标题路径，读取段落与列表项
→ 验证非空，生成 JSON
```

## 选择原因与关键代码

Beautiful Soup 负责 HTML 树解析与 CSS 选择器，不负责自动识别知识。
底层用 Python 自带 html.parser，暂不增加 lxml。
标准库 HTMLParser 也能做，但需要自行维护更多嵌套状态；正则不适合完整解析。

参考：[Beautiful Soup 官方文档](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)。

阅读 `app/services/html_extractor.py` 时先理解两处：

1. `extract_hella_article` 决定从哪里读：只选择已检查的文章模块，找不到则失败。
2. `_read_blocks` 决定怎样保留结构：遇到 h2/h3 更新标题路径，遇到 p/li 输出正文块。

遇到新 h2 时，旧 h3 必须清除，否则下一节会错误继承上一节的小标题。
实际网页含有嵌套 p，跳过内部重复块避免提取两次。
当前仅保留检查步骤的顺序和标题，未单独提取网页上的步骤编号。

## 失败、调试与替换

- 标题、正文容器、章节标题缺失或正文为空：ValueError，不退回整页文本。
- 哈希变化：脚本停止，人工确认是否换了来源快照。
- 页面改版可能导致部分漏提而非报错，需要用真实快照回归和人工抽检发现。
- 本次发现 alert-text 同时用于表单反馈，因此安全说明选择器限定在通知模块中。
- 不执行脚本、不请求 iframe，不把原文里的指令当作程序指令执行。
- 后续可为其他站点增加独立提取器；复杂版式再考虑其他解析器或正文提取库。

## 验证与评估

真实快照提取结果：18 个正文块，1 条安全说明，6 个检查步骤按顺序保留。
正常测试覆盖标题路径、列表、实体解码与嵌套段落去重；
边界测试覆盖空输入、结构缺失、空章节，噪声测试覆盖导航、表单反馈与视频。
测试使用自建 HTML，不依赖网络或第三方全文。
这证明当前模板的提取行为，不代表 RAG 召回质量已验证。

运行（仓库根目录）：

```powershell
uv run --directory ./server-v2 python -m scripts.extract_hella
uv run --directory ./server-v2 pytest tests/test_html_extractor.py -q
```

下一节先检查这些正文块如何组合成候选 Chunk，而不是把每个 p 都视为最终 Chunk。
