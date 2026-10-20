# 教育家人格智能分析系统 2.0

这是一个面向教育家研究的人格材料管理与分析系统。当前版本保留原有三重人格分析，提供可追溯研究资源库、多源数据采集中心、视频文字稿与审核、人格证据溯源，以及知识检索和科研评测。

## 当前目录结构

```text
.
├─ frontend/                # Vue 3 + Vite 大屏前端
├─ backend/                 # FastAPI 后端与分析服务
├─ alembic/                 # 数据库版本迁移
├─ data/                    # 原始数据、样例数据、处理后数据
├─ models/                  # 小模型与本地大模型目录占位
├─ scripts/                 # 数据处理、启动、导入脚本
├─ docs/                    # 产品说明与接口文档
└─ project_requirements_for_codex.md
```

## 项目总控文档

- 实时规划与进度请查看 [docs/project_status.md](docs/project_status.md)

## 建议开发顺序

1. 先补全后端规则引擎与分析接口。
2. 再把前端大屏页面和接口联调跑通。
3. 最后补批量导入、真实数据样例接入和可视化细节。

## Windows 首次部署

先安装 Git、Python（建议 3.12）和 Node.js 20+（建议 LTS），确认 `git`、`py`、`node`、`npm` 可在 PowerShell 中使用。以下命令使用 Python Launcher 的 `py -3.12`；如果没有安装 Launcher，可改用对应 Python 的 `python` 命令。

首次克隆项目；已有本地仓库时进入现有目录，保留原有文件和配置：

```powershell
git clone https://github.com/hujisheng1007/word-embedding-emotional-analysis-system.git
cd word-embedding-emotional-analysis-system
```

在项目根目录创建后端环境并安装前后端依赖：

```powershell
py -3.12 -m venv backend\.venv
& .\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Set-Location frontend
npm.cmd ci
Set-Location ..
```

首次启用研究资源库时执行数据库迁移。已有 `data/app.db` 时，先把它备份到项目目录之外，再运行：

```powershell
& .\backend\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
```

迁移按 `20261019_01`（资源库）、`20261019_02`（采集中心）和 `20261020_03`（知识检索评测）顺序新增表，不会重建原有 `corpus_datasets`、`corpus_records`。未执行迁移时原人格分析仍可启动，但新增接口会返回明确的 503 初始化提示。

已有可用的 `backend/.venv` 时无需重新创建。如果只有 `.env.example`，复制一份配置；已有 `backend/.env` 时不要覆盖：

```powershell
if (-not (Test-Path -LiteralPath backend\.env)) {
    Copy-Item -LiteralPath backend\.env.example -Destination backend\.env
}
```

启动前按下面的“数据库与环境配置”检查 `backend/.env`。

### Windows 后续一键启动

在项目根目录运行：

```powershell
.\start_dev.ps1
```

也可以双击 `start_dev.bat`。如果 PowerShell 的执行策略阻止 `.ps1`，可以使用这个 `.bat` 入口。

现有 Windows 脚本保持原样，会分别打开前后端 PowerShell 窗口。看到服务启动完成后，打开 `http://127.0.0.1:5173`；后端健康检查为 `http://127.0.0.1:8000/health`。停止时在各服务窗口分别按 `Ctrl+C`。Windows 原脚本不自动打开浏览器；Vite 默认使用 5173，端口被占用时可能自动选择其他端口，因此启动前应保持 5173 和 8000 空闲。

## macOS 首次部署

先安装 Git、Python（建议 3.12）和 Node.js 20+（建议 LTS），在终端确认 `git --version`、`python3 --version`、`node --version` 和 `npm --version` 可用。下列命令中的 `python3` 应指向所需 Python；如果安装的命令名为 `python3.12`，可用它替换。

首次克隆项目；已有仓库时进入现有目录：

```bash
git clone https://github.com/hujisheng1007/word-embedding-emotional-analysis-system.git
cd word-embedding-emotional-analysis-system
```

在项目根目录安装依赖：

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt
cd frontend
npm ci
cd ..
```

首次启用研究资源库时，先把已有 `data/app.db` 备份到项目目录之外，再执行：

```bash
backend/.venv/bin/python -m alembic -c alembic.ini upgrade head
```

用户已于 2026-10-20 在真实 macOS 上完成迁移和启动验收。部署到其他 Mac 时仍应先备份数据库，再运行迁移并核对终端输出。

Windows 与 macOS 的虚拟环境和 `node_modules` 不能直接共用。迁移源码后应在 macOS 上重新创建 `backend/.venv` 并安装依赖，不要拷贝 Windows 的 `.venv`。已有 macOS 可用环境时无需重新创建。

仅在没有配置文件时复制模板：

```bash
if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
fi
```

启动前按下面的“数据库与环境配置”检查 `backend/.env`。

### macOS 后续一键启动

在项目根目录运行（无需设置执行权限）：

```bash
bash ./start_mac.sh
```

也可以先执行 `chmod +x start_mac.sh`，以后使用 `./start_mac.sh`。脚本根据自身位置寻找项目根目录，不依赖终端当前目录；从其他目录启动时，传入脚本所在的实际路径即可。

脚本检测 `backend/.venv/bin/python` 和前端 Node.js 依赖，在同一个终端启动 FastAPI 与 Vite，并固定使用以下地址：

- 前端：`http://127.0.0.1:5173`
- 后端：`http://127.0.0.1:8000`，健康检查：`http://127.0.0.1:8000/health`

两个服务就绪后，脚本自动打开默认浏览器。端口被占用、依赖缺失、服务提前退出，或在 120 秒内没有就绪时，脚本会报错并停止已启动的服务；Vite 不会自动换端口。若浏览器未能自动打开，可手动访问前端地址。

保持启动终端开启，在该终端按 `Ctrl+C` 会停止前后端及其子进程。不要用强制关闭终端代替正常停止。脚本只启动前后端两个服务；可选大模型服务需要另行配置和启动。

## 数据库与环境配置

后端会自动读取 `backend/.env`，已有系统环境变量优先。模板中的 `DATABASE_URL` 带有原开发机的 Windows 绝对路径，复制后必须按本机情况修改，不能直接沿用。

对于项目自带的本地 SQLite，可在 `backend/.env` 中使用以下配置（两个平台的启动脚本均从 `backend` 目录启动后端）：

```dotenv
DATABASE_ENABLED=true
DATABASE_URL=sqlite:///../data/app.db
```

OpenAlex 的当前 API 需要 key。使用 OpenAlex 自动论文检索时，在 `backend/.env` 增加：

```dotenv
OPENALEX_API_KEY=从 OpenAlex 官方申请的 key
```

没有 key 时仍可使用 Crossref 论文元数据检索；系统不会把 key 写入任务日志或数据库。

如果已有数据库，保留并核对原数据库连接 URL，不要替换为新的数据库地址。未设置 `DATABASE_URL` 时，后端默认使用项目 `data/app.db`。原分析模块可直接读取旧表；使用新增研究资源库前必须在项目根目录执行一次 `alembic upgrade head`。不要删除、重建或直接覆盖已有数据库。

提示缺少虚拟环境、Python 包或 Node.js 依赖时，回到对应平台的首次部署步骤安装；前端已有依赖不完整时可在 `frontend` 中重新执行 `npm ci`。

除 Windows 语法与模拟生命周期检查外，用户已于 2026-10-20 在真实 macOS 上完成依赖检测、默认浏览器打开、5173/8000 固定端口和 Ctrl+C 清理验收。

## 研究资源库

启动前后端并完成数据库迁移后，访问 `http://127.0.0.1:5173/resources`。当前支持批量导入：

- TXT：段落定位
- CSV：行号定位，优先识别常见正文列
- DOCX：段落定位
- 文本型 PDF：页码定位；扫描型 PDF 会提示需要 OCR
- XLSX：工作表与行号定位
- JSON：JSON 路径定位
- SRT / VTT：字幕时间戳定位

导入默认采用 `copyright_status=unknown`、`access_level=restricted`，且不保存原文件和全文。只有在界面中明确确认有权保存全文后，后端才会解析和保留文件；保留文件写入 Git 忽略的 `backend/runtime/research_resources/`，文件路径由服务端生成。内容使用 SHA-256 精确去重，每次成功、重复或失败导入都有独立任务记录。

当前公开仓库中的具名教师访谈材料包含姓名、性别、教龄、学科及逐段回答。确认知情同意、公开范围和二次研究授权并完成去标识化前，不要继续提交或推送这些全文及衍生数据。仓库中的传记 DOCX、理论论文 PDF 等材料也需要补齐逐项版权和来源记录。

## 多源数据采集中心

完成迁移并启动服务后，访问 `http://127.0.0.1:5173/collection`。页面包含来源管理、教育家姓名/关键词检索、任务状态与日志、成功/重复/失败统计、人物事实审核、视频播放、文字稿和时间戳定位。

当前来源能力：

| 来源 | 实际能力 | 主要限制 |
| --- | --- | --- |
| Wikidata | 教育家候选人物、外部身份、生卒日期与来源描述 | 结构化数据为 CC0；候选身份和事实默认待人工审核 |
| Wikimedia Commons | 开放许可教育视频发现、逐文件许可读取、官方 TimedText 字幕 | 只为确认开放许可的文件提供媒体/转写入口 |
| Crossref | 论文与期刊元数据、作者、期刊、DOI、许可链接 | 默认不保存受出版方版权保护的摘要或全文 |
| OpenAlex | 论文、作者、期刊、开放获取状态 | 需要 `OPENALEX_API_KEY`；全文许可逐条判断 |
| 央视网 / 教育部网站 | 人工登记公开页面元数据和原始链接 | 自动采集关闭；不绕过反爬、登录、播放限制或复制正文 |

定期增量采集默认关闭。来源已有一次可复用查询后，可通过 `PATCH /api/collection/sources/{source_id}/schedule` 设置分钟间隔；设为 `0` 即关闭。后台调度器每分钟检查到期来源。任务支持条目边界暂停与恢复，远程失败和重复项写入独立日志。

视频处理优先获取来源官方字幕。只有数据库同时记录 `download_allowed=true` 和 `transcription_allowed=true` 时，才可创建 Whisper 后台转写任务；该任务要求系统已安装 `openai-whisper` CLI 和 ffmpeg，并记录模型名与版本。远程媒体限制为 HTTPS、公开网络地址、500MB 以内和 6 小时任务超时。

## 三重人格证据与知识检索

资源详情或采集中心可触发三重人格分析。结果写入独立分析运行和证据表，保存自然人格、职业人格和道德人格的维度分数、原文引证、资源 ID，以及段落或时间戳定位；推断默认标记为待审核。

访问 `http://127.0.0.1:5173/knowledge` 可在已授权正文和文字稿中检索。每条命中都显示原始来源和定位信息。评测区接受带期望资源 ID 的案例集，保存 Hit@K、MRR 和逐题排序结果，方便复现实验。

真实来源 A–F 验证方法与结果见 [多源采集端到端验证](docs/validation/2026-10-20-multi-source-e2e.md)。Windows 检查为后端 `33 passed`、前端生产构建通过；用户另在真实 macOS 上完成一键启动和迁移数据展示验收。真实 Whisper 推理仍未执行。

## 模型接入

后端已经预留了模型接入层，配置示例见：

- [backend/.env.example](backend/.env.example)

当前支持两类可选能力：

- 小模型分类融合
- 本地大模型解释增强

当前项目还提供了一个独立本地 Llama 服务启动脚本：

- [start_llm_service.ps1](start_llm_service.ps1)
- [start_llm_service.bat](start_llm_service.bat)

如果 `backend/.env` 中设置了 `LLM_ENABLED=true`，那么运行 Windows 的 [start_dev.ps1](start_dev.ps1) 时会自动一并拉起本地 Llama 服务。macOS 的 `start_mac.sh` 不启动该独立服务；在 macOS 上启用模型能力前，需要单独准备兼容的模型服务并配置对应地址和模型路径。

## Deployment Guide

- New machine setup (database-first): [docs/deployment/new_machine_setup.md](docs/deployment/new_machine_setup.md)
