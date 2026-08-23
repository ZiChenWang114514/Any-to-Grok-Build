# 实现说明

[README](../README.md) · [快速开始](./getting-started.md) · [命令手册](./commands.md) · [会话生命周期](./session-lifecycle.md)

## 设计目标

这个 Skill 将 Grok Build 视为本机外部编码协作者。辅助脚本提供一致命令和可检查结果，Codex 负责理解任务、监督执行并独立验证仓库。

- 会话选择可复查；
- 工作目录保持一致；
- 调用日志可以检查；
- 超时处理范围明确；
- 上下文读数来源清楚；
- 测试会话可以准确清理；
- 全局配置和正式会话不会被普通命令修改。

## 组件

| 组件 | 职责 |
|---|---|
| `SKILL.md` | Codex 何时使用该 Skill，以及完整操作要求 |
| `scripts/grok_session.py` | 诊断、发现、检查、等待、调用与冒烟测试 |
| `references/defaults.json` | 超时、上下文提醒值和测试回复 |
| `references/operation-protocol.md` | Skill 执行过程中的详细解释 |
| `references/cli-notes.md` | 当前 Grok CLI 参数和版本观察 |
| `evals/evals.json` | 典型请求与预期行为 |
| `docs/` | 面向安装者和维护者的使用文档 |

## 状态来源

```text
grok --help / models / doctor
             │
             ├── installation status
             │
~/.grok/active_sessions.json
             ├── active PID and cwd
             │
~/.grok/sessions/<cwd>/<id>/
             ├── summary.json
             ├── signals.json
             ├── updates.jsonl
             └── chat_history.jsonl
```

一个来源不足以完整描述会话。例如，进程仍然存在可能表示工具还在执行，也可能是临时开发服务没有关闭；`turn_completed` 已出现也需要检查待处理工具和仓库结果。

## 子命令职责

- `status`：检查本机 CLI 和会话基础设施。
- `list`：根据解码后的所属目录查找会话。
- `inspect`：聚合单个会话的状态、事件、上下文和 PID。
- `wait`：比较两次状态文件快照，并重新检查事件。
- `invoke`：调用 Grok，解析 JSON 结果并保存日志。
- `smoke-test`：以最小功能创建真实会话，验证后准确删除。

## 进程处理

辅助脚本为每次 `invoke` 创建独立进程组。调用超时后，它只处理该次调用启动的进程树：Windows 使用准确 PID 调用 `taskkill /T`，其他系统使用独立进程组信号。用户已有 Grok、Node、浏览器或开发服务不在自动处理范围内。

## 网络与日志

Grok 子进程继承当前代理配置。辅助脚本只清理可能干扰嵌套诊断的显示变量和 `GROK_AGENT`，并保证 loopback 地址包含在 `NO_PROXY` 中。它不修改 Clash、系统代理或 Grok 全局配置。

未指定 `--log-dir` 时，普通调用创建唯一临时目录并保留；冒烟测试成功后删除自己的默认临时目录。指定目录时，脚本保留日志，并拒绝覆盖已有标准日志文件。

## 兼容性验证

Grok CLI 更新后依次执行：

1. `python -m py_compile scripts/grok_session.py`；
2. Skill 结构校验；
3. `status --json`；
4. `smoke-test --json`；
5. 创建并继续同一测试会话；
6. 检查准确会话是否能够删除。
