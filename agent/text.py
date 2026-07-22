from state.schema import MaingraphState
from tools.utils import get_llm
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from tools.docx_tool import (
    set_font_name, set_font_size, set_font_bold, set_font_italic,
    set_paragraph_align, set_line_spacing, set_paragraph_indent,
    set_page_header, set_page_footer, set_page_number,
)
from langchain_core.tools import tool
import json
from typing import List, Dict, Any, Optional


def text_node(state: MaingraphState):
    """正文排版Agent - 负责正文段落、一/二/三级标题、公式、算法、代码片段的格式调整"""
    system_messages = [
        SystemMessage(content="<-- 进入 07 正文 Agent 排版 Node -->")
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
    ]
    tool_lookup = {tool.name: tool for tool in tools}

    llm = get_llm(
        temperature=0.3, timeout=240.0
    )
    llm_with_tools = llm.bind_tools(tools)

    system_prompt = """
    你是一个专业的正文排版大师，负责将排版任务转换为代码参数，以支持后续的工具调用。

    ## 你的职责范围
    - 正文段落的字体、字号、行距、段落缩进
    - 一级标题、二级标题、三级标题的字体、字号、加粗、对齐、段前段后
    - 公式、算法、代码片段的格式设置

    ## 任务说明
    - 你会接收到包含排版要求的任务详情
    - 理解用户的具体排版要求，选择合适的执行工具
    - 将要求转换成工具可以执行的参数格式
    - 你只能通过调用工具来完成任务

    ## 示例输入：
    {{
        "section": "正文",
        "subsection": "正文段落",
        "content": "近年来，深度学习在图像识别领域取得了显著进展...",
        "request": [
          {{"字体": "宋体"}},
          {{"字号": "小四"}},
          {{"行距": "1.5倍"}},
          {{"段落格式": "首行缩进2字符"}}
        ]
    }}

    ## 字号对照（用于 tool call 参数）
    - 三号 ≈ 16pt, 四号 ≈ 14pt, 小四 ≈ 12pt, 五号 ≈ 10.5pt

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
        "text": {
            "agent_result": {
                "status": overall_status,
                "layout_result": task_details
            }
        },
        "agent_done_count": 1,
        "messages": system_messages + [
            AIMessage(
                content=f"【Text Agent】执行完成：{overall_status}，成功 {success_count}/{total_tasks} 项"
            )
        ],
    }
