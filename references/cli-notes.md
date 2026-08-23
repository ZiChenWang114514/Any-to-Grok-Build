# Grok Build CLI 速查

始终以本机 `grok --help` 为准。当前机器已验证 `grok 1.0.5 (5115b46bc9)` 支持：

```text
--cwd <dir>                 指定会话所属工作目录
--resume <id>               恢复准确会话；省略参数会选择当前目录最近记录
--prompt-file <path>        从 UTF-8 文件读取单轮提示
--output-format json        返回 text、sessionId、requestId、usage 等字段
--debug --debug-file <path> 写入诊断日志
--model <id>                本次调用的模型
--agent <name-or-file>      本次调用的 agent
--reasoning-effort <level>  本次调用的推理强度
--permission-mode <mode>    本次调用的权限模式
--always-approve            自动批准工具调用
--max-turns <n>             限制无头调用轮次
--no-subagents --no-plan    禁用子 agent 或规划
--disable-web-search        禁用网页搜索和抓取
-p, --single <prompt>       直接发送单轮提示
```

恢复连续协作会话时优先使用准确 `--resume <id>`。`--continue`、省略 ID 的 `--resume`、`--fork-session`、`--worktree` 与 `--restore-code` 都可能改变选择或代码位置，只有任务明确需要时才使用。

常用只读命令：

```powershell
& $grokExe --version
& $grokExe --help
& $grokExe doctor
& $grokExe models
& $grokExe --cwd <owner-cwd> sessions list -n 20
& $grokExe --cwd <owner-cwd> inspect
```

当前显示模型、实际计费模型和会话 agent 名称可能不同。例如：

```text
grok models                  -> grok-4.6
JSON modelUsage              -> grok-4.6-build
summary.json agent_name      -> grok-build-plan
```

记录各来源的实际值，不要写死旧模型 ID。

## 辅助脚本命令

```text
status       检查 CLI、参数、模型、doctor 与活动会话
list         按准确工作目录列出会话
inspect      检查准确 session ID、事件、上下文和活动 PID
wait         比较短时间内的文件与事件状态
invoke       创建或继续无头会话，保存日志并解析 JSON
smoke-test   创建、验证并删除精确测试会话
```

`invoke` 只在显式传入 `--always-approve` 时增加该参数。普通调用不会自动改变用户的全局权限配置。

## `/compact`

将 `/compact` 单独保存为 UTF-8 文件，并通过同一 session ID 调用 `invoke`。命令退出码只能说明客户端结束；压缩结果仍要检查 `compactionCount`、checkpoint、聊天记录变化和后续上下文。

## 1.0.4–1.0.5 观察

- 主回答成功后，stderr 仍可能出现 title generation、proactive bundle、telemetry、plugin collision 或 resident actor warning。结合 JSON 回复、退出码、`turn_completed` 和会话文件判断。
- `error decoding response body` 若只影响标题或后台同步，可记录为后台问题；若模型回复缺失并持续重试，则检查代理与上游响应流。
- Grok/agent 子进程可能注入 `NO_COLOR`。辅助脚本的 `status` 会使用干净显示环境运行 doctor。
- `grok inspect` 可能报告旧 `[privacy]` 配置或 Claude `PowerShell(...)` 权限格式。修改这些全局文件前需要用户明确要求，并保存备份。
- `inspect` 版本行里的 `[unknown]` 可能表示更新通道没有给出稳定版本，不代表会话运行失败。
