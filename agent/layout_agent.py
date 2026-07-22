from state.schema import MaingraphState
from typing import  Dict
from langchain_core.messages import AIMessage, SystemMessage
from tools.utils import clean_dict
from config.prompt import layout_agent_rules
def layout_agent_node(state: MaingraphState):
    all_mission = state.get("request_group", [])
    rules = layout_agent_rules
    is_retry = state.get("verification_status") == "again"

    # 重试模式：从验证结果中找出哪些Agent失败了
    failed_agents = set()
    if is_retry:
        verification_issues = state.get("verification_issues", [])
        for issue in verification_issues:
            agent_name = issue.get("agent_name")
            if agent_name:
                failed_agents.add(agent_name)

    update: Dict[str, Dict] = {
        "author": {"agent_mission": None},
        "chart": {"agent_mission": None},
        "cover": {"agent_mission": None},
        "fund": {"agent_mission": None},
        "reference": {"agent_mission": None},
        "text": {"agent_mission": None},
        "other": {"agent_mission": None},
    }

    # 重试模式：只分配失败Agent的任务，其余Agent保持不变（已有成功结果）
    for mission in all_mission:
        section = mission.get("section")
        subsection = mission.get("subsection")
        target_key = None

        if subsection:
            for key, keywords in rules.items():
                if subsection in keywords:
                    target_key = key
                    break
        elif section:
            for key, keywords in rules.items():
                if section in keywords:
                    target_key = key
                    break

        if target_key is None:
            target_key = "other"

        # 重试模式：只处理失败的Agent
        if is_retry and target_key not in failed_agents:
            continue

        if update[target_key]["agent_mission"] is None:
            update[target_key]["agent_mission"] = []
        update[target_key]["agent_mission"].append(mission)

    # 重试模式：清除失败Agent的agent_result，让dispatch重新执行它们
    if is_retry:
        for agent_name in failed_agents:
            if update[agent_name]["agent_mission"] is not None:
                # 有任务要重试 → 清除旧结果
                update[agent_name]["agent_result"] = None

    filter_update = clean_dict(update)

    retry = state.get("layout_check_retry", 0)
    return {
        **filter_update,
        "agent_carry_count": len(filter_update),
        "agent_done_count": 0,
        "layout_check_retry": retry + 1,
        "verification_status": None,  # 重置，让下一轮验证重新判断
        "messages": [
            SystemMessage(content="<-- 进入 06 子图agent分发器 -->"),
            AIMessage(content=f"{'🔄 重试模式：' + ','.join(failed_agents) + ' 重新执行' if is_retry else '✅ layout agent 任务分发完成！'}")
        ],
    }
