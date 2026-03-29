# DeepSeek 接入说明

## 1. 你需要准备什么

接入 DeepSeek 只需要一项核心信息：

- `DEEPSEEK_API_KEY`

当前项目已经内置了 `DeepSeek Chat` 的模型档案，默认参数如下：

```env
FOUNDATION_MODEL_BASE_URL=https://api.deepseek.com/v1
FOUNDATION_MODEL_NAME=deepseek-chat
```

也就是说，你通常不需要自己改地址和模型名，只需要把 API Key 配好。

## 2. 如何填写 `.env`

在 [backend/.env.example](/d:/大创/backend/.env.example) 的基础上，确保有这一行：

```env
DEEPSEEK_API_KEY=你的_deepseek_api_key
```

如果你希望把“当前环境配置”也直接设置为 DeepSeek，可同时填写：

```env
FOUNDATION_MODEL_ENABLED=true
FOUNDATION_MODEL_BASE_URL=https://api.deepseek.com/v1
FOUNDATION_MODEL_NAME=deepseek-chat
FOUNDATION_MODEL_API_KEY=你的_deepseek_api_key
```

## 3. 网页里怎么切换

项目启动后，在网页顶部的“强模型档案”切换区：

1. 选择 `DeepSeek Chat`
2. 点击“切换强模型”

如果 `DEEPSEEK_API_KEY` 已配置，系统就会启用 DeepSeek 作为更强的研判模型。

## 4. 如果你没有看到 Key

官方文档明确说明：使用 DeepSeek API 前，需要先创建 API key。  
参考文档：

- https://api-docs.deepseek.com/zh-cn/
- https://api-docs.deepseek.com/zh-cn/api/deepseek-api

常见流程通常是：

1. 登录 DeepSeek 开放平台
2. 进入 API Keys 页面
3. 创建新的 API Key
4. 复制后立即保存

常见入口通常是：

- `https://platform.deepseek.com/`
- `https://platform.deepseek.com/api_keys`

如果页面改版，优先在登录后的左侧菜单里找 `API Keys`、`API 密钥`、`开放平台` 这类入口。

## 5. 调试建议

- 如果报 `401`，通常是 API Key 错误或没填
- 如果报 `402`，通常是账户余额不足
- 如果切换后仍显示未启用，先重启后端再刷新页面
