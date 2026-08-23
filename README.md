# Codex Grok Build Skill

让 Codex 通过本机 Grok Build CLI 创建、继续、监督并验证编码会话。

## 功能

- 检查 Grok 版本、模型、关键参数、doctor 与活动会话
- 按准确工作目录列出会话，并检查 session ID、事件和上下文
- 创建或继续无头会话，保存 prompt/stdout/stderr/debug 日志
- 在首次配置或升级后运行真实冒烟测试，并删除精确测试会话
- 处理调用超时，报告候选会话与日志，只停止本次脚本启动的进程树
- 监测待处理工具调用、`turn_completed`、文件稳定性和 `/compact`
- 独立检查代码差异、构建、测试、网页和截图

## 安装

将仓库复制到：

```text
%USERPROFILE%\.codex\skills\codex-grok-build
```

## 快速使用

```powershell
python scripts\grok_session.py status --json
python scripts\grok_session.py list --dir C:\path\to\repo --json
python scripts\grok_session.py invoke `
  --dir C:\path\to\repo --prompt-file phase.txt --json
python scripts\grok_session.py smoke-test `
  --dir C:\path\to\safe-dir --json
```

当前版本已在 Windows 与 Grok 1.0.5 上验证。模型和 CLI 参数仍以本机 `grok models` 与 `grok --help` 为准。

普通调用保留会话和日志。`smoke-test` 只删除它本次创建并验证过的准确会话。脚本不会自动提交、推送、发布或修改全局 Grok/Claude 配置。

## 文件

- `SKILL.md`：Codex 使用说明
- `scripts/grok_session.py`：状态、调用、继续、检查与冒烟测试
- `references/defaults.json`：超时、上下文提醒值与测试回复
- `references/operation-protocol.md`：会话、日志、超时与清理说明
- `references/cli-notes.md`：当前 CLI 参数和版本观察
- `evals/evals.json`：行为评测样例

## License

MIT
