# 故障诊断

[README](../README.md) · [快速开始](./getting-started.md) · [命令手册](./commands.md) · [会话生命周期](./session-lifecycle.md)

先运行统一状态检查：

```powershell
$helper = "$env:USERPROFILE\.codex\skills\codex-grok-build\scripts\grok_session.py"
python $helper status --json
```

## Grok 启动超时

典型提示包括 `startup timed out` 或长时间停在 account settings。依次检查：

1. `grok --version` 是否能够立即返回；
2. `grok models` 是否能够读取账号和模型；
3. `grok doctor` 是否报告认证或网络问题；
4. PowerShell 中的 `HTTP_PROXY`、`HTTPS_PROXY`、`ALL_PROXY` 与 `NO_PROXY`；
5. 本地代理进程和对应端口是否存在；
6. Grok 实际访问路径是否经过预期代理。

辅助脚本保留代理变量，并向 `NO_PROXY` 加入 `127.0.0.1`、`localhost` 与 `::1`。不要在诊断输出中展示代理密码或认证令牌。

## doctor 报颜色问题

父 Agent 可能注入 `NO_COLOR` 或其他颜色变量，使嵌套 `grok doctor` 产生误报。优先查看辅助脚本的 doctor 结果，或在干净 PowerShell 中重新运行。

## 找不到会话

常见原因包括原工作目录不同、session ID 错误、会话已经删除，或 `GROK_HOME` 指向其他位置。

```powershell
python $helper list --dir "C:\original\cwd" --json
```

不要使用省略 ID 的 `--resume` 猜测会话。

## 工作目录不匹配

`invoke --session-id` 会核验会话所属目录。出现不匹配时，读取 `inspect` 的 `session_owner_cwd`，确认该目录是否仍然存在，并检查会话内的实际任务。

## 调用超时

辅助脚本超时后会停止它本次启动的进程树，并在错误 JSON 中返回启动 PID、新会话候选 ID、stdout/stderr 尾部和日志目录。

超时后先检查候选会话、仓库差异和日志。模型可能已经完成部分修改，自动重新发送相同 prompt 会造成重复编辑。

## 主回复成功但 stderr 有 warning

Grok 1.0.4–1.0.5 可能在主回复完成后报告 session title generation、proactive bundle、telemetry、plugin collision 或 resident session actor warning。

如果 JSON 回复完整、退出状态为 0、`turn_completed` 已出现且工具调用已经结束，可以将其记录为后台 warning。若模型回复缺失、持续重试或退出状态非零，再检查网络、代理和上游响应。

## `error decoding response body`

- 只影响标题或后台同步时，主任务可能已经成功；
- 发生在模型主体响应并导致重试耗尽时，通常需要检查网络链路；
- 同时检查 stdout、stderr、debug 和会话事件，避免仅根据一行日志判断。

## `grok.exe` 仍在运行

会话可能启动 Vite、浏览器或其他长期服务，使 Grok 进程继续存在。检查活动索引中的准确 PID、父子进程关系、监听端口、启动时间和服务来源。

只停止能够确认属于本阶段的进程。不要按名称统一终止所有 `grok.exe`、Node 或浏览器进程。

## 日志检查

每次 `invoke` 生成 `stdout.log`、`stderr.log` 和 `debug.log`；使用 `--prompt` 或 `smoke-test` 时还会生成 `prompt.txt`。

公开问题报告前应清理用户名、绝对路径、session/request ID、认证令牌、代理凭据、私有仓库信息和未公开 prompt。

## 全局配置 warning

`grok inspect` 可能报告旧配置键或 Claude 权限格式。先确认 warning 是否影响当前调用。修改 `~/.grok/config.toml`、Claude 权限或代理配置前，应获得用户明确授权并保存可识别的备份。
