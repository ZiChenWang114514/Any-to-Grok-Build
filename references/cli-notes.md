# Grok Build CLI 速查

以本机 `grok --help` 的输出为准。当前机器已验证 `grok 1.0.4 (d846eb93d9)` 仍支持以下常用参数；后续更新仍需重新检查：

```text
--cwd <dir>                 指定会话所属工作目录
--resume <id>               精确恢复指定会话
--prompt-file <path>        从文件读取单轮提示
--output-format plain       以文本写入 stdout
--debug --debug-file <path> 写入诊断日志
--reasoning-effort <level>  设置新会话或明确需要覆盖时的推理强度
--fork-session              恢复时建立新会话副本
--worktree                  新建 Git worktree
-p, --single <PROMPT>       无交互单轮请求，适合做兼容性冒烟测试
```

除非用户明确要求，不要将 `--fork-session`、`--worktree` 或 `--restore-code` 用在恢复协作会话中。它们会改变会话或代码所在位置，妨碍连续审阅。

常用诊断命令：

```powershell
& $grokExe --version
& $grokExe --help
& $grokExe doctor
& $grokExe --cwd <session-owner-cwd> sessions list -n 20
& $grokExe --cwd <session-owner-cwd> inspect
```

对现有会话发送 `/compact`：将该字符串保存为 UTF-8 文件，按正常 `--resume` 命令发送。压缩完成的判断依照操作协议，不能只依据命令退出码。

1.0.4 及更新版本可能在主回答成功后额外输出 session title、proactive bundle 或 telemetry 的后台同步 warning。主回答、退出码和 debug 中的会话事件应分别判断；`error decoding response body` 若只出现在后台同步且主回答完整，可记录为非阻断 warning；若出现在模型响应重试并最终没有主回答，则检查本地代理、Clash 路由和响应流。
