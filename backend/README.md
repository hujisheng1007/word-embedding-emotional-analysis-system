# Backend

后端负责提供风险分析接口、规则引擎、小模型融合逻辑与大模型解释层。

当前骨架包含：

- FastAPI 应用入口
- 健康检查接口
- 单条分析接口占位
- 批量分析接口占位
- 分析结果数据结构
- 服务层与引擎目录

## 当前接口

- `GET /health`
- `POST /api/analyze`
- `POST /api/analyze/batch`
