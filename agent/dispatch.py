"""
Agent 顺序分发器 — 替代 LangGraph Send 机制，避免子图内重复执行
"""
from state.schema import MaingraphState
from langchain_core.messages import AIMessage, SystemMessage
from agent.author import author_node
from agent.chart import chart_node
from agent.cover import cover_node
from agent.fund import fund_node
from agent.reference import reference_node
from agent.text import text_node
from agent.other import other_node

AGENTS = {
    "cover": cover_node,
    "text": text_node,
    "author": author_node,
    "chart": chart_node,
    "fund": fund_node,
    "reference": reference_node,
    "other": other_node,
}


def dispatch_node(state: MaingraphState):
    """逐个调用所有 Agent，只传给各自的任务数据。只执行一次。"""
    # 已经执行过 → 直接返回（防御性检查）
    if state.get("_dispatch_done"):
        return {}

    from state.schema import update_done_count, update_state2
    merged = {}
    total_done = 0
    all_messages = []
    debug_info = []
    for name, func in AGENTS.items():
        agent_data = state.get(name) or {}
        if isinstance(agent_data, dict):
            mission = agent_data.get("agent_mission")
            agent_result = agent_data.get("agent_result")
            already_done = bool(agent_result)
        else:
            mission = None
            agent_result = None
            already_done = False
        if not mission:
            debug_info.append(f'{name}:skip')
            continue
        if already_done:
            debug_info.append(f'{name}:cached')
            total_done = update_done_count(total_done, 1)
            continue
        debug_info.append(f'{name}:run({len(mission)})')
        task_state = dict(state)
        task_state["agent_mission"] = mission
        result = func(task_state)
        if not result:
            continue
        for key, val in result.items():
            if key == "agent_done_count":
                total_done = update_done_count(total_done, val)
            elif key == "messages":
                if val:
                    all_messages.extend(val if isinstance(val, list) else [val])
            elif key in ("cover", "text", "author", "chart", "fund", "reference", "other"):
                merged[key] = update_state2(merged.get(key, {}), val)
            else:
                merged[key] = val
    merged["agent_done_count"] = total_done
    merged["_dispatch_done"] = True
    msg_text = '<-- dispatch: ' + ' '.join(debug_info) + ' -->'
    merged["messages"] = [SystemMessage(content=msg_text)] + all_messages + [
        AIMessage(content=f'执行了 {total_done} 个Agent')]
    return merged
