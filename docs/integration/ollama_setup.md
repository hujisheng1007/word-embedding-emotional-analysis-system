# Ollama 接入说明

## 1. 官方安装信息

根据 Ollama 官方 Windows 文档：

- Windows 10 22H2 或更高版本可用
- 安装后 Ollama 会在后台运行
- 默认 API 地址为 `http://localhost:11434`

官方页面：

- https://docs.ollama.com/windows
- https://ollama.com/download/windows

## 2. Windows 最简单安装方式

官方推荐的最简单方式是使用 `OllamaSetup.exe` 安装器。

你也可以使用官方 PowerShell 安装命令：

```powershell
irm https://ollama.com/install.ps1 | iex
```

安装完成后，重新打开 PowerShell，检查：

```powershell
ollama --version
```

## 3. 下载模型

如果你要接项目里的 `Ollama / Qwen2.5 7B` 档案，推荐直接拉这个模型：

```powershell
ollama pull qwen2.5:7b-instruct
```

官方模型页：

- https://ollama.com/library/qwen2.5:7b-instruct

如果你机器内存压力较大，也可以先试更小版本：

```powershell
ollama pull qwen2.5:3b
```

如果你还想在项目里保留一个本地 DeepSeek 选项，推荐再拉一个：

```powershell
ollama pull deepseek-r1:8b
```

当前项目已经支持以下两个本地 Ollama 档案：

- `Ollama / Qwen2.5 7B`
- `Ollama / DeepSeek-R1 8B`

## 4. 验证服务是否正常

安装并拉取模型后，运行：

```powershell
ollama run qwen2.5:7b-instruct
```

或者直接测试本地 API：

```powershell
Invoke-WebRequest -Method POST `
  -Uri http://localhost:11434/api/chat `
  -Body '{"model":"qwen2.5:7b-instruct","messages":[{"role":"user","content":"你好"}]}' `
  -ContentType "application/json"
```

## 5. 在当前项目里怎么用

当前项目网页已经内置了 `Ollama / Qwen2.5 7B` 模型档案。

安装完 Ollama 后：

1. 启动项目
2. 打开网页
3. 在顶部“强模型档案”中选择 `Ollama / Qwen2.5 7B`
4. 点击“切换强模型”

如果本地 `11434` 服务正常、模型已下载，系统就会开始使用 Ollama 进行更强研判。

## 6. 常见问题

### 没有足够磁盘空间

官方文档说明可以通过设置用户环境变量 `OLLAMA_MODELS` 改模型存储目录。

### 想改模型存储路径

在 Windows 用户环境变量中新增：

```text
OLLAMA_MODELS=D:\OllamaModels
```

然后重启 Ollama。

### 安装后项目里切换无效

先确认：

```powershell
ollama --version
ollama list
```

并确认 `qwen2.5:7b-instruct` 已存在。
如果你要使用 `Ollama / DeepSeek-R1 8B`，请同时确认 `deepseek-r1:8b` 已存在。
