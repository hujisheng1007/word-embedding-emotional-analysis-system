# 校园风险文本识别与可视化分析平台

这是基于需求文档搭建的第一版项目骨架，目标是尽快跑通一个适合答辩展示的 Web Demo。

## 当前目录结构

```text
.
├─ frontend/                # Vue 3 + Vite 大屏前端
├─ backend/                 # FastAPI 后端与分析服务
├─ data/                    # 原始数据、样例数据、处理后数据
├─ models/                  # 小模型与本地大模型目录占位
├─ scripts/                 # 数据处理、启动、导入脚本
├─ docs/                    # 产品说明与接口文档
└─ project_requirements_for_codex.md
```

## 项目总控文档

- 实时规划与进度请查看 [docs/project_status.md](d:/大创/docs/project_status.md)

## 建议开发顺序

1. 先补全后端规则引擎与分析接口。
2. 再把前端大屏页面和接口联调跑通。
3. 最后补批量导入、真实数据样例接入和可视化细节。

## 启动准备

### 后端

```powershell
cd backend
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 前端

```powershell
cd frontend
npm install
npm run dev
```
