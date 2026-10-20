# 项目改动说明（2026-10-19）

## 2026-10-20 续开发状态

V2 多源采集闭环及原清单第 6–10 项已经在提交 `6d7a673` 中完成。新增内容包括采集任务服务与 API、`/collection`、授权字幕/Whisper 作业、人格证据、迁移 `20261020_03`、`/knowledge` 检索评测、33 项后端测试和真实来源端到端报告。用户于 2026-10-20 完成真实 macOS 一键启动和数据迁移验收；当前开发清单为 10/10。远端发布状态仍以 `git status`、`git log` 和远端分支为准。

下文是 2026-10-19 的交接记录；其中“未提交/进行中”的描述是当时状态，不代表当前状态。关于 GitHub 是否已推送，以 `git status`、`git log` 和远端实际分支为准。

本文档记录「教育家人格智能分析系统 2.0」在 2026-10-19 前后由 **Codex** 与 **Claude** 各自完成的改动，便于快速了解「改了什么、谁改的、处于什么状态」。

> 说明：Codex 与 Claude 在同一工作区接力/并行工作。以下按「提交状态」和「作者」拆分。文中「未提交」指尚未进入 git 历史、仍停留在工作区的文件。

---

## 一、Codex 的改动

### 1. 已提交到 GitHub 的改动

**commit `9128f09` — `feat: add cross-platform startup and research library`**
（本地分支 `codex/first-five`，已推送到 GitHub；未合并 `main`）

这是「前五项」的主体，共 29 个文件、约 +2760 行：

| 模块 | 主要文件 | 作用 |
| --- | --- | --- |
| 跨平台启动 | `start_mac.sh`、`.gitattributes`、`README.md` | 新增 macOS 一键启动脚本（依赖检测、固定 5173/8000、就绪后开浏览器、Ctrl+C 清理进程组）；README 补齐两平台部署说明 |
| 数据库迁移 | `alembic.ini`、`alembic/env.py`、`alembic/script.py.mako`、`alembic/versions/20261019_01_research_resources.py` | 引入 Alembic；`20261019_01` 纯新增 6 张研究资源表（`educator_persons` / `research_resources` / `resource_authors` / `resource_files` / `resource_segments` / `resource_import_jobs`），不改旧语料表 |
| 资源库后端 | `backend/app/db/research_models.py`、`backend/app/db/session.py`、`backend/app/api/routes/research_resources.py`、`backend/app/services/research_resource_service.py`、`backend/app/schemas/research_resources.py` | 资源统计/列表/详情/批量导入/任务列表 API；SHA-256 去重、版权/访问级别控制、元数据-only 导入、来源可定位分段 |
| 文件解析 | `backend/app/services/resource_parsers/parsers.py` | 8 类解析：TXT / CSV / DOCX / PDF / XLSX / JSON / SRT / VTT，保留段落/行号/页码/工作表/JSON 路径/时间戳定位 |
| 资源库前端 | `frontend/src/views/resources/ResourceLibraryView.vue`、`frontend/src/api/research.ts`、`frontend/src/types/research.ts`、`frontend/src/router/index.ts`、`frontend/src/App.vue`、`frontend/src/api/client.ts` | 新增 `/resources` 页面（统计、筛选、列表、详情抽屉、批量导入）；前端 API 根地址支持 `VITE_API_BASE_URL` |
| 测试与文档 | `backend/tests/test_research_resources.py`、`test_research_resource_migration.py`、`docs/*` | 迁移保留旧数据测试、资源服务/API 测试、审查报告、数据库设计与进度文档 |

**commit `c824cbc` — `feat: add educator biography analysis demo`**（更早，`main` 基线）

### 2. 未提交、进行中的改动（「采集中心」，对应 P0/P1）

> ⚠️ 以下为 Codex 仍在**并发开发中**的代码，处于半成品状态，尚未接入主程序（`app/main.py` 没有 collection 路由）。内容可能随时变化。

- **`alembic/versions/20261019_02_collection_center.py`**（新增迁移，`down_revision=20261019_01`）
  新增 11 张表：
  - `collection_sources` — 采集源配置（Wikidata/Wikimedia/OpenAlex/Crossref/央视网/教育部），含 terms/robots/许可说明、限流、启停开关
  - `collection_jobs` / `collection_logs` — 采集任务与日志（状态、计数、重试、暂停）
  - `resource_identifiers` — 资源外部标识符（DOI / Wikidata ID 等）
  - `person_external_identities` — 人物外部身份（含置信度、审核状态）
  - `person_facts` — 人物事实（来源 URL/标题/出版方、审核状态、SHA-256 去重）
  - `video_assets` — 视频资产（平台、嵌入/媒体 URL、许可、下载/转写开关）
  - `transcripts` / `transcript_cues` — 转写全文与时间轴分段
  - `personality_analysis_runs` / `personality_evidence` — 人格分析运行与证据（维度、分数、引文、定位、审核状态）

- **`backend/app/collectors/`**（采集适配器）
  - `base.py` — `Candidate` 数据类 + `HttpAdapter` 基类（User-Agent、429 限流处理、`fetch_subtitle` 接口）
  - `wikidata.py` — Wikidata 教育家人物检索 + 实体事实 + 生卒日期解析（CC0 公有领域）
  - `openalex.py` — OpenAlex 论文元数据检索（DOI、作者、期刊、开放获取状态）
  - `crossref.py` — Crossref 论文元数据检索（DOI、作者、期刊、许可）
  - `wikimedia.py` — Wikimedia Commons 视频检索 + WebVTT 字幕获取（逐文件判断开放许可）
  - `registry.py` — 来源定义清单 + 适配器注册（含央视网/教育部「仅人工登记」的受限来源）

- **`backend/app/db/research_models.py`**（已修改，追加约 216 行）
  为上述 11 张表新增 ORM 模型（`CollectionSource` / `CollectionJob` / `CollectionLog` / `ResourceIdentifier` / `PersonExternalIdentity` / `PersonFact` / `VideoAsset` / `Transcript` / `TranscriptCue` / `PersonalityAnalysisRun` / `PersonalityEvidence`）。

- **`backend/app/schemas/collection.py`**（新增）
  采集中心 Pydantic schema：采集源视图、任务创建/视图、日志、统计、人物事实/人物视图、转写/视频视图、字幕导入、手动登记、人格分析证据视图。

**设计取向**：采集器默认只取**元数据**，开放许可才开放媒体下载/转写入口，未确认许可前不保存正文/摘要，符合「不得抓取未授权版权内容」的约束。

---

## 二、Claude（我）的改动

### 本轮（接手验收）：**没有修改任何项目源代码**

本轮只做了**只读审查与验收**，没有新增、修改或删除任何项目业务代码。具体做了：

- 全面阅读工作区结构、后端/前端代码、迁移、测试与文档。
- 检查 git 状态与未提交改动（识别出 Codex 仍在并发写入）。
- 迁移安全审查：确认 `20261019_01` 为纯新增、不改旧表。
- 在 `data/app.db` 的**副本**上验证迁移：`integrity_check=ok`，旧数据 3 数据集 / 1341 条语料保持不变。
- 运行后端自动化测试：**27 项全部通过**。
- 运行前端生产构建：**通过**。
- 用**隔离临时数据库** + 公有领域材料，实机验证资源库「导入 → 去重 → 检索 → 详情」全链路。
- 全程 `data/app.db` 哈希保持 `2660c31a…` 不变（未改动正式库）。

产生的副作用（均不影响项目代码）：
- 重跑了 `backend/.venv` 虚拟环境创建（目录已被 git 忽略）。
- 临时测试文件已全部清理。

### 上一轮（「更新 GitHub」请求中）对仓库配置的改动

- 生成本机 SSH 密钥 `~/.ssh/id_ed25519` 并写入 `~/.ssh/config`（在仓库之外）。
- 将 `origin` 远程地址从 HTTPS 切换为 SSH：`git@github.com:hujisheng1007/word-embedding-emotional-analysis-system.git`。
- 将本地分支 `codex/first-five` 推送到 GitHub（即上面 commit `9128f09` 的内容）。

---

## 三、当前状态与注意事项

1. **`data/app.db` 尚未执行任何迁移**：正式库仍只有旧的 2 张语料表（3 数据集 / 1341 条语料）。资源库迁移 `01` 与采集中心迁移 `02` 都只在临时副本上验证过，未落地到正式库。
2. **采集中心尚未接入主程序**，且 Codex 仍在持续写入这些文件；在 Codex 停止前，不应在其上进行二次开发，避免互相覆盖。
3. **前五项（1、3、4、5）已在 Windows 上验收通过**；第 2 项「跨平台启动」的 macOS 部分待真机验收。
4. 未提交的采集中心文件里不含任何授权确认前的访谈全文或衍生数据；采集器设计为「元数据优先、开放许可才下载/转写」。
