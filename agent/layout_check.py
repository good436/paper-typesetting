from state.schema import MaingraphState
from langchain_core.messages import AIMessage, SystemMessage


def layout_check_node(state: MaingraphState):
    system_messages = [
        SystemMessage(content="<-- 进入 05 排版智能中枢Node -->")
    ]
    verification_status = state.get("verification_status")

    if verification_status == "ok" and state.get("should_terminate"):
        return {
            "messages": system_messages + [SystemMessage(content="验证通过，assemble节点！")],
        }

    if verification_status == "again":
        system_messages.append(SystemMessage(content=">>>>>>   再次进入 05 排版智能中枢Node"))
        return {
            "messages": system_messages + [AIMessage(content="需要补漏，交给layout_agent！")],
        }

    # 首次进入，不做任何重置，让 routing_func4 决定下一步
    return {
        "messages": system_messages + [AIMessage(content="首次执行，交给layout_agent！")],
    }
