# 会话生命周期

[README](../../README.zh-CN.md) · [快速开始](./getting-started.md) · [命令手册](./commands.md) · [故障诊断](./troubleshooting.md) · [English](../session-lifecycle.md)

Grok 会话可以跨多个无头调用持续存在。可靠协作依赖三个稳定标识：session ID、创建会话时的工作目录、实际开发仓库。

## 会话存储

```text
%USERPROFILE%\.grok\sessions\<编码后的工作目录>\<session-id>\
```

| 文件 | 主要信息 |
|---|---|
| `summary.json` | 标题、模型、Agent、消息数量和更新时间 |
| `signals.json` | 上下文、压缩次数、工具统计与 telemetry 状态 |
| `updates.jsonl` | 事件、工具状态、回复与 `turn_completed` |
| `chat_history.jsonl` | 对话、推理、工具调用和工具结果 |

会话所属工作目录可能与 Grok 实际修改的仓库不同。监督前应检查会话内容和仓库状态，不能只根据目录名称推断任务。

## 创建阶段

创建新会话前：

1. 确认用户授权的工作目录和任务；
2. 阅读仓库项目指令；
3. 检查 `git status --short` 与已有差异；
4. 将较长阶段说明保存为 UTF-8 文件；
5. 选择只读 `plan` 或已经授权的执行权限。

阶段说明宜包含目标、已确认事实、允许修改的文件、禁止操作、验证命令和需要检查的页面区域。一次安排一项能够清楚验证的任务。

## 运行阶段

调用成功后保存 session ID、原工作目录、日志目录、本次 prompt 文件及调用时间。发送下一阶段前先运行 `inspect`，继续时使用准确 ID 和原工作目录。

## 判断一轮是否完成

完整判断需要组合以下信息：

1. 已出现最终回复或 `turn_completed`；
2. `pending_tool_call_ids` 为空；
3. `updates.jsonl` 与 `chat_history.jsonl` 在短时间内保持稳定；
4. stdout、stderr、debug 没有显示工具仍在执行；
5. 活动进程、子进程和端口状态符合任务预期；
6. 仓库差异与验证结果支持 Grok 的完成说明。

`completion_candidate=true` 与 `stable=true` 只能用于缩小检查范围。Grok 的文字说明、任务清单或退出状态都需要与仓库证据一起判断。

## 上下文读数

即时上下文按以下顺序读取：

1. `signals.json.contextTokensUsed`；
2. `signals.json.contextWindowUsage` 与 `contextWindowTokens`；
3. 最新非 `turn_completed` Agent 或工具事件中的 `_meta.totalTokens`。

不要累计 debug 日志中的 `input_tokens`，也不要将 `turn_completed` 的整轮累计值视为即时上下文。

辅助脚本从 `references/defaults.json` 读取提醒值。如果实际窗口小于该值，脚本会使用窗口的 80% 作为较早提醒值，并在检查结果中说明。

## `/compact`

达到提醒值后：

1. 等待当前阶段完整结束；
2. 创建只包含 `/compact` 的 UTF-8 提示文件；
3. 使用同一 session ID 单独调用 `invoke`；
4. 检查压缩结果；
5. 确认成功后再发送下一阶段。

优先确认 `compactionCount` 增加。若 `signals.json` 没有及时刷新，可以组合检查 debug 中的 compact 命令、checkpoint、聊天记录缩短或替换，以及后续事件中的上下文下降。

## 长任务协作

```text
work/
├── phase-01-inspect.txt
├── phase-02-implement.txt
├── phase-03-fix-tests.txt
└── logs/
    ├── phase-01/
    ├── phase-02/
    └── phase-03/
```

每轮结束后由 Codex 检查准确差异、构建、测试和界面，再根据证据编写下一阶段。不要自动重复超时任务，避免相同修改执行两次。

## 结束协作

- 停止发送新阶段；
- 汇总修改文件、验证结果、已知 warning 和仍需人工决定的事项；
- 检查本阶段启动的临时服务；
- 只处理能够确认属于本阶段的进程；
- 保留正式会话，除非用户明确要求删除。
