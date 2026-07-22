# 论文排版智能助手 — 项目状态文档

> 生成时间: 2026-07-22
> 供下一个上下文窗口恢复工作使用

---

## 一、项目概览

学术论文自动排版工具。用户上传 .docx + 粘贴排版要求 → AI 自动完成格式调整。

- **框架**: LangGraph + LangChain + Streamlit
- **LLM**: DeepSeek (ChatOpenAI 兼容接口)
- **启动**: `streamlit run ui/app.py` (Web) / `python main.py` (命令行)

---

## 二、Agent 分工

| Agent | 负责内容 | 文件 |
|-------|----------|------|
| cover | 首页全部：题目/作者/单位/摘要/关键词/英文版 | agent/cover.py |
| text | 正文段落、各级标题、公式、算法、代码 | agent/text.py |
| reference | 参考文献列表 | agent/reference.py |e
| chart | 图/表标题和编号 | agent/chart.py |
| author | 作者简介、贡献声明 | agent/author.py |
| fund | 课题/基金项目 | agent/fund.py |
| other | 兜底（未匹配的内容） | agent/other.py |

## 三、能调整的格式

| 类别 | 能力 |
|------|------|
| 字体 | 字体名、字号、加粗、斜体、下划线 |
| 段落 | 对齐、行距、首行缩进、悬挂缩进、段前段后 |
| 页面 | 边距、分节符、页码 |
| 页眉页脚 | 页眉文字/格式、页脚文字/格式、页码位置/起始/首页显隐 |
| 检查 | 题目字数、关键词数量、摘要结构/长度、作者姓名/单位格式 |
| 不能做 | 目录(需手动刷新)、脚注/尾注(python-docx不支持)、标注/批注 |

## 四、图结构（当前版本 — 支持失败重试）

```
START → input_check → input_parser → paper_parser → parser_check
    → layout_check → layout_agent → agent_dispatch
    → layout_check → validator
    → (routing_func5) 
        ├── verification_status="again" → layout_check (重试回路)
        └── verification_status="ok"   → assemble → human_editing → send_email → END
```

**重试机制**：
- validator 发现问题 → 返回 `verification_status="again"` + `verification_issues`（含失败的 Agent 名称）
- routing_func5 → layout_check → routing_func4 → layout_agent（重试模式）
- layout_agent 重试模式：只清除失败 Agent 的 `agent_result`，只给失败 Agent 分配 `agent_mission`
- dispatch_node：失败的 Agent 因 `agent_result=None` 重新执行；成功的 Agent 因 `agent_result` 存在被缓存跳过
- 重试后再次验证，最多重试 5 次
- `agent_dispatch` 替代了原来的子图(Send-based subgraph)，逐个调用有任务的 Agent

## 五、当前正在处理的问题（重点）

### 问题：Agent 重复执行（30次→目标6次） ✅ 已修复

**现象**: 6个Agent各被调用5次，共30次LLM调用，实际只需6次（每个一次）。

**排查过程**:
1. 首先怀疑 `routing_func4` 路由死循环 → debug发现只调了2次，逻辑正确 ✅
2. 怀疑子图 Send 机制导致重复 → 用 `dispatch_node` 替换子图（逐个调Agent） ✅
3. 发现 dispatch 后只有 Reference Agent 日志 → `messages` 被后一个覆盖，改为累加 ✅
4. **找到根因**: `agent/layout_agent.py` 每次运行都把 `agent_result` 设为 `None`，dispatch 缓存检查失败

**根因代码** — `agent/layout_agent.py` 原第10-16行:
```python
update = {
    "author": {"agent_mission": None, "agent_result": None},  # ← 每次清空结果!
    "chart":  {"agent_mission": None, "agent_result": None},
    ...
}
```

**已做修改（已验证 ✅）**:
1. `agent/layout_agent.py` — 去掉全部 `"agent_result": None`，只保留 `"agent_mission": None`
2. `agent/dispatch.py` — 加了缓存逻辑（约第40行）：
   ```python
   already_done = bool(agent_data.get("agent_result"))
   if already_done:
       debug_info.append(f'{name}:cached')
       total_done = update_done_count(total_done, 1)
       continue  # 跳过LLM调用
   ```
3. `graph/routes.py` — `routing_func4` 简化，`done_count >= carry_count` 优先判

**验证结果 (2026-07-22)**:
- dispatch_node 实际只调用 **1次**（通过 dispatch 内部计数器确认）
- routing_func4 第一次路由到 layout_agent，dispatch 完成后正确路由到 validator
- 之前测试中看到的 "30次" 是假阳性：`messages` 字段使用 `add` 累加器，Agent 完成消息在后续 state chunk 中被重复统计
- **修复生效，6个Agent各执行1次，共6次LLM调用 ✅**

**注意**: 之前的验证命令 (`grep 'Agent】'`) 计数方式有问题，会重复统计累积的 messages。正确方式是看 dispatch_node 内部的 `_DISPATCH_CALL_COUNT` 计数器或 dispatch debug 消息的首次出现。

## 五-B、被手动中断的两部分工作 ✅ 已完成

### 中断1：dispatch_node 缓存逻辑
已确认修复生效。dispatch 只调用1次，6个Agent各执行1次。

### 中断2：要求我"总结一份文档"
已生成并更新 PROJECT_STATUS.md（本文档）。

## 六、已解决的历史问题

| 问题 | 修复 | 文件 |
|------|------|------|
| `stream=True` 导致 model_dump 错误 | 默认改为 `stream=False` | tools/utils.py |
| `layout_check_retry` 并发写冲突 | 只让 layout_agent 更新 | agent/layout_agent.py |
| text.py 系统提示花括号未转义 | `{`→`{{` `}`→`}}` | agent/text.py |
| assembly_log 变量未定义就使用 | 调换声明顺序 | agent/assemble.py |
| 前端流水线重复解析（Send循环） | routing_func1检查解析状态 | graph/routes.py |
| paper_parser LLM分类不准 | 规则优先+分批LLM兜底 | agent/paper_parser.py |
| zhipu_llm 残留引用 | 全局替换为 get_llm | 全部 agent/*.py |

## 七、关键文件

| 文件 | 作用 |
|------|------|
| main.py | 入口，run_formatting_process() |
| graph/builder.py | 图结构定义 |
| graph/routes.py | 4个路由函数 |
| state/schema.py | 状态定义 MaingraphState |
| agent/dispatch.py | Agent分发器（替代子图） |
| agent/paper_parser.py | 论文结构解析（规则+LLM） |
| agent/assemble.py | 文档组装+页眉页脚应用 |
| tools/docx_tool.py | 所有Word操作工具 |
| tools/utils.py | get_llm()、read_docx()等 |
| config/setting.py | API Key/模型配置 |
| config/prompt.py | 所有 Prompt 模板 |
| ui/app.py | Streamlit 前端 |

## 八、环境配置

`.env` 文件需要：
```
DEEPSEEK_API_KEY=你的Key
DEEPSEEK_MODEL=deepseek-v4-pro
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
EMAIL_HOST=smtp.163.com
EMAIL_PORT=465
EMAIL_USER=你的邮箱
EMAIL_PASS=你的密码
```

## 九、测试方式

```bash
# 快速测试
python -c "
from main import run_formatting_process
for chunk in run_formatting_process('排版要求...', 'data/input/测试论文.docx', 'test-id'):
    pass
"

# 完整Web界面
streamlit run ui/app.py
```

## 十、下一步

1. ~~验证 Agent 执行次数是否降到 6~~ ✅ 已验证，修复生效
2. ~~如果没降到，在 dispatch_node 加 print 调试~~ ✅ 不需要，已确认
3. 可能需要在 state schema 里加 `_dispatch_done` 字段确保持久化（当前路由逻辑已确保 dispatch 不会重复调用，此字段为防御性保护）
4. ~~清理临时文件: `run_test.py`, `run_full_test.py`, `design-preview.html`~~ ✅ 已不存在（之前已清理）
5. ~~跑一次完整的 23 条要求 + 综合论文测试~~ ✅ main.py 两端测试均通过
6. 后续优化：如果验证失败需要重试时，需要让 routing_func4 能重新回到 layout_agent（当前直接 validator→assemble，无重试回路）
