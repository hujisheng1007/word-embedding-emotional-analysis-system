# 全新电脑部署指南（数据库版）

本文档适用于当前项目在一台全新 Windows 电脑上的完整部署，目标是：

- 能启动前后端
- 后端使用数据库（推荐 MySQL）
- 保留“教育家语料为子集，通用语料为默认”的数据组织

---

## 1. 前置软件

请先安装以下软件：

1. Git（建议最新稳定版）
2. Python 3.12（与当前项目一致）
3. Node.js 20+（建议 LTS）
4. Docker Desktop（用于本地 MySQL，推荐）

安装后，在终端确认：

```powershell
git --version
python --version
node --version
npm --version
docker --version
```

---

## 2. 拉取项目

```powershell
git clone https://github.com/hujisheng1007/word-embedding-emotional-analysis-system.git
cd word-embedding-emotional-analysis-system
```

---

## 3. 后端环境初始化

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..
```

---

## 4. 前端环境初始化

```powershell
cd frontend
npm install
cd ..
```

---

## 5. 配置后端环境变量

复制配置模板：

```powershell
Copy-Item backend\.env.example backend\.env
```

然后编辑 `backend/.env`，至少确认以下项：

```env
DATABASE_ENABLED=true
DATABASE_URL=mysql+pymysql://root:你的密码@127.0.0.1:3306/dachuang_corpus
```

说明：

- 如果你先想本地快速跑通，也可先用 SQLite：
  - `DATABASE_URL=sqlite:///D:/你的路径/data/app.db`
- 生产或长期演示建议使用 MySQL/PostgreSQL。

---

## 6. 启动本地 MySQL（Docker 方案）

### 6.1 启动 Docker Desktop

确保 Docker 引擎可用：

```powershell
docker ps
```

### 6.2 创建 MySQL 容器

```powershell
docker run -d `
  --name dachuang-mysql `
  -e MYSQL_ROOT_PASSWORD=你的密码 `
  -e MYSQL_DATABASE=dachuang_corpus `
  -p 3306:3306 `
  mysql:8.4
```

检查容器状态：

```powershell
docker ps --filter "name=dachuang-mysql"
```

---

## 7. 准备数据库数据

当前项目有两种常用数据导入方式：

1. 从 `data/*.csv` 种子导入数据库（推荐新机器首次执行）
2. 从已有 SQLite 迁移到 MySQL（你已有本地 SQLite 时使用）

### 7.1 CSV 种子导入

```powershell
backend\.venv\Scripts\python scripts\sync_csv_to_database.py
```

### 7.2 SQLite -> MySQL 迁移

```powershell
backend\.venv\Scripts\python scripts\migrate_sqlite_to_mysql.py `
  --target-url "mysql+pymysql://root:你的密码@127.0.0.1:3306/dachuang_corpus" `
  --truncate-target
```

---

## 8. 启动项目

### 方式 A：一键启动（推荐）

```powershell
.\start_dev.ps1
```

### 方式 B：手动分别启动

后端：

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

前端：

```powershell
cd frontend
npm run dev
```

---

## 9. 验证部署

### 9.1 后端健康检查

打开：

- `http://127.0.0.1:8000/health`

### 9.2 数据集接口

打开：

- `http://127.0.0.1:8000/api/datasets`

你应看到：

- `demo-texts`（默认）
- `educator-interviews-analysis`（education 子集）
- `educator-interviews-import`（education 子集）

---

## 10. 常见问题

1. `No module named sqlalchemy`  
说明后端依赖未安装完整，重新执行 `pip install -r backend/requirements.txt`。

2. MySQL 连不上（3306 失败）  
确认 Docker Desktop 已启动，`dachuang-mysql` 容器状态为 `Up`。

3. `Access denied for user`  
检查 `backend/.env` 中 `DATABASE_URL` 的账号密码是否与容器创建参数一致。

4. 前端可开但无数据  
确认后端实际使用的是同一个 `DATABASE_URL`，并执行过 `sync_csv_to_database.py` 或迁移脚本。

---

## 11. 建议的上线前动作

1. 不要使用 root 账号作为应用账号，创建最小权限业务账号。
2. 将数据库密码改为强密码，并避免写入公开仓库。
3. 对 MySQL 容器挂载数据卷，避免重建容器导致数据丢失。
4. 在 README 增加一段“快速部署索引”链接到本文档。
