# Codex Grok Build Skill

一个让 Codex 通过本机 Grok Build CLI 协作完成编码、阶段审阅、测试核验和上下文维护的 Skill。

## 内容

- `SKILL.md`：主流程与安全要求
- `references/`：会话操作协议与 CLI 速查
- `scripts/grok_session.py`：只读会话状态诊断工具
- `agents/openai.yaml`：Codex Skill 展示信息
- `evals/evals.json`：行为评测样例

## 安装

将整个目录复制到：

```text
%USERPROFILE%\.codex\skills\codex-grok-build
```

安装后，以本机 `grok --help` 和 `grok --version` 为准检查参数。当前版本已验证 Grok 1.0.5 支持 `--resume`、`--prompt-file`、`--output-format plain` 和 `--debug-file`。模型 ID 以 `grok models` 为准，不要写死 `grok-build`。

## 设计原则

- 先读取会话状态、进程、日志和仓库差异，再决定是否恢复会话。
- 使用精确的 session ID 与创建会话时的工作目录。
- 独立运行构建、测试、端到端测试和页面检查。
- 将主回答、退出码、后台同步 warning 与会话事件分别判断。
- 保护既有改动，不批量终止进程，不擅自发布或删除文件。

## 许可证

MIT
