# 宏观数据解读监控

抓取国家统计局「数据解读」栏目（<https://www.stats.gov.cn/sj/sjjd/>）的报告，用正则提取关键指标，再调用 Claude 做单篇解读和月度综合研判，结果存进本地 SQLite，用 Streamlit 仪表盘查看。

## 流程

```text
列表页翻页 ──► 详情页解析 ──► reports 表
                                 │
                 正则提取指标 ──► indicators 表
                                 │
      Claude 单篇解读 / 月度综合 ──► analyses 表 ──► Streamlit 仪表盘
```

| 步骤 | 命令 | 是否联网 / 调用 LLM |
|---|---|---|
| 抓取新报告 | `python run.py --fetch-only` | 联网（stats.gov.cn），每篇间隔 1.5 秒 |
| 提取指标 | `python run.py --extract` | 纯本地，可重复执行 |
| 单篇解读 | `python run.py --analyze` | 调用 Claude，只处理尚未分析的报告 |
| 月度综合研判 | `python run.py --analyze-cross` | 调用 Claude，针对库中最新月份，每次覆盖重算 |

参数可以组合，例如 `python run.py --fetch-only --max-pages 5 --limit 10`。`--limit` 同时限制抓取和单篇解读的篇数，`--max-pages` 限制列表翻页数（默认 20）。抓取遇到一整页都是已知报告时会提前停止。

## 目录

| 路径 | 作用 |
|---|---|
| `scraper/list_page.py` | 列表页翻页，收集新报告 URL |
| `scraper/detail_page.py` | 解析标题、发布日期、正文，按标题关键词归类（PMI、CPI/PPI、投资、工业等） |
| `extractor/indicators.py` | 正则提取指标：指数类水平值及环比百分点、CPI/PPI 环比与同比、各类「同比增长 x%」 |
| `analyzer/prompts.py` | 单篇与综合研判的提示词和 JSON Schema |
| `analyzer/agent.py` | 通过 `claude-agent-sdk` 获取结构化输出；可单独运行，分析最新一篇 |
| `storage/db.py` | SQLite 表结构与读写，数据库固定为仓库根目录的 `data.db` |
| `dashboard/app.py` | Streamlit 仪表盘：指标时间序列、本月综合研判、报告列表与单篇解读 |
| `daily_update.bat` | Windows 定时任务入口，依次执行四个步骤，日志追加到 `update.log` |

## 环境准备

需要 Python 3.10 及以上（代码使用 `X | None` 类型写法）。

```powershell
python -m pip install -r requirements.txt
```

LLM 分析通过 `claude-agent-sdk` 调用本机的 Claude Code CLI，没有单独的 API Key 配置项。运行 `--analyze` / `--analyze-cross` 前，先确认 `claude` 命令可用且已登录。抓取和指标提取不依赖 Claude。

## 运行

```powershell
# 完整更新
python run.py --fetch-only --extract --analyze --analyze-cross

# 打开仪表盘（默认 http://localhost:8501）
streamlit run dashboard/app.py
```

仪表盘侧边栏的「刷新抓取 + 再分析」会在页面内依次执行上面四步，可能需要几分钟。

### 定时更新

`daily_update.bat` 会切到脚本所在目录执行，默认使用 `PATH` 中的 `python`。需要指定解释器时先设置 `PYTHON` 环境变量，例如：

```powershell
setx PYTHON D:\Anaconda\python.exe
```

然后在 Windows 任务计划程序里每天运行一次该脚本。

## 验证

不调用 LLM、不联网的快速检查：

```powershell
python -m py_compile run.py dashboard/app.py analyzer/agent.py analyzer/prompts.py extractor/indicators.py scraper/list_page.py scraper/detail_page.py storage/db.py
python run.py --extract
streamlit run dashboard/app.py --server.headless true
```

项目目前没有自动化测试。

## 数据库现状

仓库里提交了一份 `data.db`（约 730 KB），2026-10-14 核对时内容为：

- `reports`：60 篇，发布时间 2026-02-11 至 2026-06-30；
- `indicators`：252 条。用当前提取规则重跑 `--extract` 得到 235 条，说明部分旧记录来自早期规则；
- `analyses`：仅 3 条单篇解读，没有月度综合研判。

`data.db` 同时是种子数据和运行数据，每次运行都会改动它。若要长期运行，建议决定是否改为不纳入版本管理。

## 已知限制

- 抓取依赖统计局页面结构（`ArticleTitle`、`PubDate` meta 和 `trs_editor_view` 正文容器），页面改版会导致解析失败并跳过。
- 指标提取基于正则，覆盖常见句式，会有漏提和指标名不规范的情况。
- `--analyze-cross` 每次都会强制重算最新月份。
- 分类是按标题关键词匹配，未命中的归为「其他」。
