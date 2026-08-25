# 快速开始

[README](../../README.zh-CN.md) · [命令手册](./commands.md) · [会话生命周期](./session-lifecycle.md) · [故障诊断](./troubleshooting.md) · [English](../getting-started.md)

本页完成一次完整路径：安装 Skill、检查 Grok、运行兼容性测试、创建会话并继续同一会话。

## 前置条件

- Windows PowerShell；
- Python 3.10 或更高版本；
- 已经安装并登录的 Grok Build CLI；
- 支持 Skills 的 Codex；
- 一个允许 Grok 读取或修改的工作目录。

```powershell
python --version
& "$env:USERPROFILE\.grok\bin\grok.exe" --version
& "$env:USERPROFILE\.grok\bin\grok.exe" models
```

## 安装 Skill

```powershell
git clone https://github.com/ZiChenWang114514/codex-grok-build-skill.git `
  "$env:USERPROFILE\.codex\skills\codex-grok-build"
```

重新打开 Codex 任务后，可以用 `$codex-grok-build` 明确调用该 Skill。如果本机已有同名目录，先运行 `git status --short` 检查本地修改。

## 第一次状态检查

```powershell
$skill = "$env:USERPROFILE\.codex\skills\codex-grok-build"
python "$skill\scripts\grok_session.py" status --json
```

重点查看：

- `ok` 是否为 `true`；
- `required_flag_support` 是否全部为 `true`；
- `available_models` 与 `default_model`；
- `doctor.ok` 与具体问题；
- `sessions_root_exists`；
- `active_sessions` 中 PID 是否仍然存在。

`status` 会保留网络代理变量，同时移除可能影响嵌套 doctor 的颜色变量和 `GROK_AGENT`。

## 兼容性冒烟测试

首次安装、Grok 升级或辅助脚本更新后运行：

```powershell
python "$skill\scripts\grok_session.py" smoke-test `
  --dir "C:\path\to\safe-dir" --json
```

成功结果应包含：

```json
{
  "ok": true,
  "reply": "GROK_SESSION_OK",
  "test_session_deleted": true,
  "test_logs_deleted": true
}
```

测试使用空工具列表，并禁用子 Agent、规划和网页搜索。脚本只删除本次返回 ID 对应的测试会话。指定 `--log-dir` 后，日志会保留以供检查。

## 创建第一个会话

将较长任务保存为 UTF-8 文件，例如 `phase-01.txt`：

```text
检查当前仓库状态和项目指令。只分析现状，报告建议修改的文件和验证命令，不要修改文件。
```

```powershell
python "$skill\scripts\grok_session.py" invoke `
  --dir "C:\path\to\repo" `
  --prompt-file "C:\path\to\phase-01.txt" `
  --permission-mode plan --json
```

保存返回的 `session_id` 和 `log_dir`。普通调用会保留会话及日志。

## 继续准确会话

```powershell
python "$skill\scripts\grok_session.py" invoke `
  --dir "C:\path\to\repo" `
  --session-id "<session-id>" `
  --prompt-file "C:\path\to\phase-02.txt" --json
```

如果目录与会话记录不一致，脚本会拒绝继续。这样可以避免在其他仓库中恢复同名或最近使用的会话。

## 允许执行工具

当用户已经授权 Grok 在指定目录中实施任务，可以明确传入 `--always-approve`。这个参数只影响本次调用。若仍处于分析阶段，使用 `--permission-mode plan`。

## 下一步

- [命令手册](./commands.md)：全部参数和返回字段。
- [会话生命周期](./session-lifecycle.md)：监督与上下文维护。
- [故障诊断](./troubleshooting.md)：启动、网络和超时问题。
