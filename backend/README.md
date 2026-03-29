# Backend

后端负责提供风险分析接口、规则引擎、小模型融合逻辑与大模型解释层。

当前骨架包含：

- FastAPI 应用入口
- 健康检查接口
- 单条分析接口占位
- 批量分析接口占位
- 分析结果数据结构
- 服务层与引擎目录
- 可选小模型融合接口
- 可选本地大模型解释接口

## 当前接口

- `GET /health`
- `POST /api/analyze`
- `POST /api/analyze/batch`

## 模型接入准备

复制环境示例文件并按需填写：

```powershell
Copy-Item .env.example .env
```

当前支持两类可选模型能力：

- 小模型分类服务：通过 `SMALL_MODEL_ENDPOINT` 接入本地分类接口
- 本地大模型解释服务：通过 OpenAI 兼容接口接入 `LLM_BASE_URL`

## 当前项目内置本地 Llama 服务

如果你已经有本地模型权重，可直接在当前项目内启动独立解释服务。

1. 安装额外依赖：

```powershell
cd backend
.\\.venv\\Scripts\\python -m pip install -r requirements-llm.txt
```

2. 复制环境配置：

```powershell
Copy-Item .env.example .env
```

3. 启动本地 LLM 服务：

```powershell
cd ..
.\\start_llm_service.ps1
```

默认地址：

- `http://127.0.0.1:8011/v1/chat/completions`
