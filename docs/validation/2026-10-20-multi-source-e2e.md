# 多源采集、人格证据与知识检索端到端验证

验证日期：2026-10-20

运行系统：Windows 11

数据库：隔离 SQLite，`<scratch-dir>\validation.db`

正式数据库：未迁移、未写入；`data/app.db` SHA-256 仍为 `2660C31ACBA99A693EA31BA926BCF60717B9C57FC29ED6511C5F7E364B4664F4`

验证命令：

```powershell
$env:PYTHONPATH='backend'
python scripts/validate_collection_e2e.py `
  --database <scratch-dir>\validation.db `
  --storage <scratch-dir>\storage `
  --report <scratch-dir>\report.json
```

## 验收结果

| 项目 | 真实来源 | 数据库结果 | 前端/API 验证 |
| --- | --- | --- | --- |
| A 人物资料 | Wikidata [Cai Yuanpei / Q19796](http://www.wikidata.org/entity/Q19796)，结构化数据 CC0 | 人物 ID `54fdc4e9-db6c-4ac5-9f13-a136c6576ef7`；外部身份和候选事实为 `pending`，等待人工审核 | `GET /api/collection/people` 返回 200 |
| B 公开视频元数据 | Wikimedia Commons [Montessori explainer video](https://commons.wikimedia.org/wiki/File:EN_simpleshow_foundation_Montessori_explainer_video.webm)，CC BY-SA 4.0 | 视频 ID `f2475b0e-7269-4840-9d9c-582f293df43c`；许可、原始 URL、媒体 URL 与嵌入能力已保存 | `GET /api/collection/videos` 返回 200；页面可使用原始媒体 URL 播放 |
| C 合法字幕 | 同一 Commons 视频的官方 TimedText 德文字幕 | 文字稿 ID `317fb15b-a4eb-4416-a229-9c3a7719fd4d`；54 个时间片；首片 640ms；来源 `official_subtitle`；审核状态 `pending` | 视频详情返回时间片，点击可定位播放器 |
| D 论文元数据 | Crossref DOI [10.5040/9781472541444.ch-004](https://doi.org/10.5040/9781472541444.ch-004) | 论文资源 ID `1db73f79-24d1-4413-8a42-77d7c35944b2`；DOI 去重标识已保存；未保存全文 | 资源列表与详情 API 均返回 200 |
| E 授权书籍 | Project Gutenberg [Democracy and Education, eBook #852](https://www.gutenberg.org/ebooks/852)，页面标注美国公有领域 | 资源 ID `a9cbe8bc-8c00-4502-8a35-cdb64f3935a5`；解析 904 段；人格分析运行 `87f44016-4095-45ba-af4c-8f1ea46a3961`；3 条维度证据 | `GET /api/research-resources/{id}` 返回 200 |
| F 知识检索评测 | 上述公版书籍的合法全文 | 查询最高命中同一书籍，定位 `paragraph:186#1`；Hit@10 = 1.0，MRR = 1.0 | `POST /api/knowledge/search` 返回 200 |

隔离数据库最终包含 3 位人物、3 条研究资源、1 个视频、1 份文字稿和 3 条人格证据。报告字段 `all_passed=true`。

## 自动化检查

- 后端：`33 passed`。
- 前端：`npm run build` 通过。
- Alembic：从旧语料表升级到 `20261020_03`，测试确认旧记录保持不变。
- 安全：测试覆盖受限版权拒绝全文、上传大小与格式、SHA-256 去重、人工来源域名校验、远程转写拒绝回环/内网地址。
- Python 依赖：升级 FastAPI、Starlette、pytest、aiotieba、pypdf、python-multipart 后，`pip-audit -r backend/requirements.txt` 为 `No known vulnerabilities found`。
- 前端依赖：`npm audit fix` 已清除 7 个高危公告；复查剩余 2 个中危均来自 ECharts `<6.1.0` 的同一 Lines-series tooltip XSS 公告。当前代码没有使用 `series.type="lines"`，且 `echarts-wordcloud@2.1.0` 的 peer dependency 只接受 ECharts 5，因此暂不强制跨主版本升级；后续应在词云插件支持 ECharts 6 后升级并复测图表。

## 已知限制

- OpenAlex 在当前规则下需要 API key。未配置 `OPENALEX_API_KEY` 时接口给出明确错误；本次真实论文验收使用无需密钥的 Crossref。
- Whisper 后台任务已实现授权检查、500MB 上限、私网地址拦截、6 小时超时以及模型版本记录；当前机器未安装 Whisper CLI/ffmpeg，因此未声称已完成真实 Whisper 推理。本次 C 使用来源官方字幕满足文字稿验收。
- 央视网与教育部来源当前仅支持人工登记其所属域名的公开页面元数据，不下载媒体或复制正文。自动采集保持关闭，直到来源条款和可用接口被逐项确认。
- 用户提到的 14 本书没有提供可核验的授权清单，本次没有导入或虚构这些书的内容；批量导入能力由公版书籍完成真实验证。
- `start_mac.sh` 仍需在真实 macOS 上验收，本文只记录 Windows 上执行的检查。
- npm 当前仍报告上述 ECharts 中危依赖项；这是已核对调用面的剩余维护项，不应描述为零漏洞。
