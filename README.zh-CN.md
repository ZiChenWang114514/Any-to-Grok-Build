<p align="center">
  <img src="./assets/readme/hero.zh-CN.svg" width="100%" alt="Codex Grok Build 会话控制——可检查的本机 Grok CLI 协作流程">
</p>

<p align="center">
  <a href="./README.md">English</a> · <strong>简体中文</strong>
</p>

<p align="center">
  <a href="./docs/zh-CN/getting-started.md">快速开始</a> ·
  <a href="./docs/zh-CN/commands.md">命令手册</a> ·
  <a href="./docs/zh-CN/session-lifecycle.md">会话生命周期</a> ·
  <a href="./docs/zh-CN/troubleshooting.md">故障诊断</a> ·
  <a href="./SKILL.md">Skill 说明</a>
</p>

# Codex Grok Build Session

让 Codex 通过本机 Grok Build CLI 创建、继续、监督并验证编码会话。它将工作目录、session ID、事件、上下文和日志组织成可检查的协作流程，同时保留 Grok 原生会话。

> 适用于 Windows、PowerShell、Codex Skills 与本机 Grok Build CLI。当前实现已经在 Grok 1.0.5 上完成真实调用测试；运行时仍以本机 `grok --help` 和 `grok models` 为准。

## 它解决什么问题

直接启动外部编码 Agent 很容易遇到四类麻烦：继续了错误会话、工作目录不一致、进程退出但工具仍在执行、上下文读数判断错误。这个 Skill 为 Codex 提供一套可复查的操作方式：

- 根据准确工作目录查找会话，并核验 session ID 的归属。
- 创建或继续无头 Grok 会话，保存 prompt、stdout、stderr 与 debug 日志。
- 结合 `turn_completed`、待处理工具调用、文件稳定性、进程和端口判断执行状态。
- 从 `signals.json` 与最新事件读取上下文，达到提醒值后单独执行 `/compact`。
- 在 Grok 更新后运行真实冒烟测试，并删除本次创建的测试会话。
- Grok 完成实现后，由 Codex 独立检查差异、构建、测试、网页和截图。

## 工作方式

<p align="center">
  <img src="./assets/readme/session-workflow.svg" width="100%" alt="Four-stage workflow: diagnose, invoke, observe, and verify a Grok Build session">
</p>

1. **Diagnose**：检查 CLI、模型、doctor、会话目录与活动 PID。
2. **Invoke**：在用户指定目录创建会话，或使用准确 ID 继续已有会话。
3. **Observe**：读取状态文件、事件、上下文和日志，判断是否需要继续或压缩。
4. **Verify**：检查实际代码差异并运行项目自己的验证命令。

## 五分钟开始使用

### 1. 安装

需要 Python 3.10+、已经安装并登录的 Grok Build CLI，以及支持 Skills 的 Codex。

```powershell
git clone https://github.com/ZiChenWang114514/codex-grok-build-skill.git `
  "$env:USERPROFILE\.codex\skills\codex-grok-build"
```

如果目标目录已经存在，请先检查其中的本地修改，再选择更新方式。

### 2. 检查环境

```powershell
python "$env:USERPROFILE\.codex\skills\codex-grok-build\scripts\grok_session.py" `
  status --json
```

成功结果会报告 Grok 版本、默认模型、可用模型、关键参数、doctor 结果、会话目录和活动会话。

### 3. 运行兼容性测试

首次安装或 Grok 更新后，可以在安全目录中创建一次短会话：

```powershell
python "$env:USERPROFILE\.codex\skills\codex-grok-build\scripts\grok_session.py" `
  smoke-test --dir "C:\path\to\safe-dir" --json
```

测试会禁用工具、子 Agent、规划与网页搜索。精确回复和实际模型通过检查后，本次测试会话与默认临时日志会被删除。

### 4. 创建编码会话

将较长任务保存为 UTF-8 文本：

```powershell
python "$env:USERPROFILE\.codex\skills\codex-grok-build\scripts\grok_session.py" `
  invoke --dir "C:\path\to\repo" `
  --prompt-file "C:\path\to\phase.txt" --json
```

返回结果包含 `session_id`、实际模型、回复、停止原因与日志目录。继续同一会话时，必须使用它原来的工作目录：

```powershell
python "$env:USERPROFILE\.codex\skills\codex-grok-build\scripts\grok_session.py" `
  invoke --dir "C:\path\to\repo" `
  --session-id "<session-id>" `
  --prompt-file "C:\path\to\next-phase.txt" --json
```

## 命令一览

| 命令 | 用途 | 是否改变会话 |
|---|---|:---:|
| `status` | 检查安装、模型、doctor 与活动会话 | 否 |
| `list` | 按工作目录列出会话 | 否 |
| `inspect` | 检查一个 session ID 的事件、上下文和 PID | 否 |
| `wait` | 比较短时间内的会话文件与事件状态 | 否 |
| `invoke` | 创建或继续 Grok 无头会话 | 是 |
| `smoke-test` | 创建、验证并删除一次测试会话 | 是，随后自动清理 |

完整参数和返回字段见 [命令手册](./docs/zh-CN/commands.md)。

## 安全行为

- 普通调用保留 Grok 会话与日志，便于后续检查。
- 指定日志目录中已有调用日志时，脚本会拒绝覆盖。
- 超时后只停止本次脚本启动的进程树，并报告候选会话和日志。
- 脚本不会自行提交、推送、发布、部署或修改全局 Grok/Claude 配置。
- `--always-approve` 只在调用者明确传入时生效。
- 登录信息、代理凭据和认证令牌不应写入 prompt、仓库或公开日志。

## 文档

| 文档 | 内容 |
|---|---|
| [快速开始](./docs/zh-CN/getting-started.md) | 安装、首次检查、创建和继续会话 |
| [命令手册](./docs/zh-CN/commands.md) | 全部子命令、常用参数、输出和退出状态 |
| [会话生命周期](./docs/zh-CN/session-lifecycle.md) | 会话定位、完成判断、上下文与长任务协作 |
| [故障诊断](./docs/zh-CN/troubleshooting.md) | 启动、网络、超时、warning、进程和日志检查 |
| [实现说明](./docs/zh-CN/design.md) | 数据来源、辅助脚本职责与安全设计 |

## 仓库结构

```text
.
├── SKILL.md                         # Codex 执行说明
├── scripts/grok_session.py          # 会话辅助脚本
├── references/                      # Skill 执行参考与默认值
├── docs/                            # 英文文档
│   └── zh-CN/                       # 中文文档
├── assets/readme/                   # README SVG 视觉素材
├── agents/openai.yaml               # Skill 展示信息
└── evals/evals.json                 # 行为评测样例
```

## 兼容性

- **操作系统**：目前以 Windows PowerShell 为主要验证环境。
- **Python**：需要 3.10 或更高版本。
- **Grok CLI**：已验证 1.0.5；不同版本的模型名、参数和会话文件可能变化。
- **模型选择**：脚本读取 `grok models`，不会把旧模型 ID 固定在代码中。

发现版本差异时，请附上 `status --json`、`grok --version` 和已经清理敏感信息的相关日志。

## 许可证

[MIT](./LICENSE) © 2026 ZiChenWang114514
