from state.schema import MaingraphState
from tools.utils import get_llm
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from tools.docx_tool import (
    set_font_name, set_font_size, set_font_bold, set_font_italic,
    set_paragraph_align, set_line_spacing, set_paragraph_indent,
    set_page_header, set_page_footer, set_page_number,
)
from langchain_core.tools import tool
import json
from typing import List, Dict, Any, Optional


def reference_node(state: MaingraphState):
    """参考文献排版Agent - 负责文献列表的格式化（悬挂缩进、编号格式等）"""
    system_messages = [
        SystemMessage(content="<-- 进入 07 参考文献 Agent 排版 Node -->")
    ]

    layout_check_retrycount = state.get("layout_check_retry", 0)

    tools = [
        set_font_name,
        set_font_size,
        set_font_bold,
        set_font_italic,
        set_paragraph_align,
        set_line_spacing,
        set_paragraph_indent,
        set_page_header, set_page_footer, set_page_number,
    ]
    tool_lookup = {tool.name: tool for tool in tools}

    llm = get_llm(
        temperature=0.3, timeout=240.0
    )
    llm_with_tools = llm.bind_tools(tools)

    system_prompt = """
    你是一个专业的参考文献排版大师，负责将排版任务转换为代码参数，以支持后续的工具调用。

    ## 你的职责范围
    - 参考文献列表的字体和字号
    - 文献条目的行距和段间距
    - 悬挂缩进设置（常用2字符悬挂缩进）
    - 编号格式（如 [1]、[2]...）

    ## 常见参考文献格式规范
    - 字体：宋体（中文）、Times New Roman（英文）
    - 字号：小五号（9pt）或五号（10.5pt）
    - 行距：单倍行距或1.25倍行距
    - 缩进：悬挂缩进2字符（编号突出，正文缩进）
    - 对齐：两端对齐

    ## 字号对照
    - 三号 ≈ 16pt, 四号 ≈ 14pt, 小四 ≈ 12pt, 五号 ≈ 10.5pt, 小五 ≈ 9pt

    ## 输出规则
    - 你只能通过 tool call 执行操作
    - 不要输出思考过程、说明、总结或自然语言解释
    - 输出：直接生成 tool calls
    """

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "请根据以下任务生成对应的格式化指令：\n{mission}"),
        ]
    )

    task_details = []

    for task in state.get("agent_mission", []):
        input_messages = prompt.format_messages(mission=json.dumps(task, ensure_ascii=False))

        try:
            response = llm_with_tools.invoke(input_messages)

            tool_calls = getattr(response, "tool_calls", []) or []
            raw_content = getattr(response, "content", "").strip() if isinstance(getattr(response, "content", ""), str) else ""

            execution_results = []

            for tc in tool_calls:
                if not isinstance(tc, dict):
                    execution_results.append({
                        "tool_call_id": None,
                        "tool_name": "unknown",
                        "args": {},
                        "execution_result": {"status": "error", "error": f"无效 tool_call 类型: {type(tc)}"}
                    })
                    continue

                name = tc.get("name")
                args = tc.get("args", {})

                if name not in tool_lookup:
                    error = f"工具未注册: {name}，可用: {list(tool_lookup.keys())}"
                    execution_results.append({
                        "tool_call_id": tc.get("id"),
                        "tool_name": name,
                        "args": args,
                        "execution_result": {"status": "error", "error": error}
                    })
                else:
                    try:
                        result = tool_lookup[name].invoke(args)
                        execution_results.append({
                            "tool_call_id": tc.get("id"),
                            "tool_name": name,
                            "args": args,
                            "execution_result": {"status": "success", "result": result}
                        })
                    except Exception as e:
                        execution_results.append({
                            "tool_call_id": tc.get("id"),
                            "tool_name": name,
                            "args": args,
                            "execution_result": {"status": "error", "error": str(e)}
                        })

            if not tool_calls:
                status = "failed"
            else:
                success_count = sum(1 for r in execution_results if r["execution_result"]["status"] == "success")
                status = "success" if success_count == len(execution_results) else "partial_success"

            task_detail = {
                "section": task.get("section"),
                "subsection": task.get("subsection"),
                "status": status,
                "raw_model_response": raw_content,
                "tool_calls": tool_calls,
                "tool_execution_results": execution_results,
            }
            task_details.append(task_detail)

        except Exception as e:
            system_messages.append(SystemMessage(content=f"❌ 处理失败: {task.get('subsection')} | {str(e)}"))
            task_details.append({
                "section": task.get("section"),
                "subsection": task.get("subsection"),
                "status": "error",
                "raw_model_response": f"调用异常: {str(e)}",
                "tool_calls": [],
                "tool_execution_results": [],
            })

    success_count = sum(1 for t in task_details if t["status"] == "success")
    total_tasks = len(task_details)
    overall_status = (
        "success"
        if success_count == total_tasks and total_tasks > 0
        else "partial_success" if success_count > 0 else "failed"
    )

    return {
        "reference": {
            "agent_result": {
                "status": overall_status,
                "layout_result": task_details
            }
        },
        "agent_done_count": 1,
        "messages": system_messages + [
            AIMessage(
                content=f"【Reference Agent】执行完成：{overall_status}，成功 {success_count}/{total_tasks} 项"
            )
        ],
    }
