from state.schema import MaingraphState
from tools.utils import get_llm
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
import json
from typing import List, Dict, Any

# 所有子图Agent的名称列表
ALL_AGENT_NAMES = ["cover", "text", "author", "chart", "fund", "reference", "other"]


def collect_verification_tasks(state: MaingraphState) -> List[Dict[str, Any]]:
    """遍历所有Agent，收集需要验证的任务"""
    verification_tasks = []

    for agent_name in ALL_AGENT_NAMES:
        agent_state = state.get(agent_name)
        if not agent_state:
            continue

        missions = agent_state.get("agent_mission", [])
        results = agent_state.get("agent_result", {}).get("layout_result", [])

        if not missions:
            continue

        # 构建执行结果查找表
        exec_map = {}
        for result in results:
            key = (result.get("section"), result.get("subsection"))
            exec_map[key] = result

        for mission in missions:
            # 跳过系统默认项（无需验证）
            if isinstance(mission.get("request"), dict) and mission["request"].get("source") == "system_default":
                continue

            sec = mission.get("section")
            subsec = mission.get("subsection")
            content = mission.get("content", "")

            exec_result = exec_map.get((sec, subsec), {})

            verification_tasks.append({
                "agent_name": agent_name,
                "section": sec,
                "subsection": subsec,
                "content": content,
                "execution_result": exec_result,
            })

    return verification_tasks


def validator_node(state: MaingraphState):
    system_messages = [
        SystemMessage(content="<-- 进入 08 检验器节点 -->")
    ]

    llm = get_llm(temperature=0.3, timeout=120.0)

    prompt_template = """
请检查以下文档内容的完整性和质量，找出需要改进或缺失的部分：

【文档内容检查】
{task_and_result}

请返回JSON格式，只包含需要改进的问题：
{{
  "issues_found": [
    {{
      "agent_name": "agent名称",
      "section": "章节名称",
      "subsection": "子章节名称",
      "issue_type": "格式问题|内容缺失|质量不足",
      "description": "具体问题描述",
      "suggestion": "改进建议"
    }}
  ],
  "summary": "整体检查摘要"
}}
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个专业文档质量检查员，负责找出文档中需要改进的问题。"),
        ("human", prompt_template)
    ])

    # 遍历所有Agent收集验证任务
    verification_tasks = collect_verification_tasks(state)

    if not verification_tasks:
        return {
            "verification_status": "ok",
            "should_terminate": True,
            "verification_issues": [],
            "messages": system_messages + [
                AIMessage(content="✅ 无需要检查的任务，检验通过")
            ],
        }

    # 统计各Agent任务数
    agent_task_count = {}
    for task in verification_tasks:
        agent_name = task.get("agent_name", "unknown")
        agent_task_count[agent_name] = agent_task_count.get(agent_name, 0) + 1

    stats_msg = " | ".join([f"{k}: {v}项" for k, v in agent_task_count.items()])
    system_messages.append(SystemMessage(content=f"📊 验证任务（{len(verification_tasks)}项）: {stats_msg}"))

    try:
        response = llm.invoke(
            prompt.format(
                task_and_result=json.dumps(verification_tasks, ensure_ascii=False, indent=2)
            )
        )

        content = response.content.strip()
        # 清洗可能的 markdown 代码块包裹
        if content.startswith("```json"):
            content = content[7:].strip()
            if content.endswith("```"):
                content = content[:-3].strip()
        elif content.startswith("```"):
            content = content[3:].strip()
            if content.endswith("```"):
                content = content[:-3].strip()

        result_json = json.loads(content)
        issues_found = result_json.get("issues_found", [])
        summary = result_json.get("summary", "检查完成，发现一些问题需要改进")

        if issues_found:
            system_messages.append(
                SystemMessage(content=f"📋 发现 {len(issues_found)} 个需要改进的问题，将重试失败的Agent")
            )
            for issue in issues_found:
                system_messages.append(
                    SystemMessage(
                        content=f"⚠️ [{issue.get('agent_name', '?')}] {issue.get('section')}-{issue.get('subsection')}: {issue.get('description')}")
                )

            return {
                "verification_status": "again",
                "should_terminate": False,
                "verification_issues": issues_found,
                "overall_summary": summary,
                "messages": system_messages + [
                    AIMessage(content=f"⚠️ 发现 {len(issues_found)} 个问题，回到layout_agent重试")
                ],
            }
        else:
            system_messages.append(
                SystemMessage(content="✅ 未发现需要改进的问题")
            )

        return {
            "verification_status": "ok",
            "should_terminate": True,
            "verification_issues": issues_found,
            "overall_summary": summary,
            "messages": system_messages + [
                AIMessage(content="✅ 检验器检查完成，流程继续")
            ],
        }

    except Exception as e:
        error_message = f"检查过程中发生错误: {str(e)}"
        system_messages.append(SystemMessage(content=f"⚠️ {error_message}"))

        return {
            "verification_status": "ok",
            "should_terminate": True,
            "verification_issues": [{
                "agent_name": "系统",
                "section": "系统",
                "subsection": "检验过程",
                "issue_type": "系统错误",
                "description": error_message,
                "suggestion": "请检查系统日志"
            }],
            "overall_summary": "检查过程遇到错误，但流程继续",
            "messages": system_messages + [
                AIMessage(content="✅ 检验完成（遇到错误但流程继续）")
            ],
        }
