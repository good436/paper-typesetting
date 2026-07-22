from state.schema import MaingraphState
from langgraph.types import Send  # 子图 subrouting_func1 仍使用
from langgraph.constants import END


def routing_func1(state: MaingraphState):
    if state["task_judgement"] == "again":
        return "input_check"
    if state["task_judgement"] is False or not state["paper_file"]:
        return END
    return "input_parser"

def routing_func2(state: MaingraphState):
    if state["user_input_parser"]['status'] == "failed":
        return "input_parser"
    if state["input_parser_retry"] >= 3:
        raise ValueError("❌ 用户输入解析陷入循环！")
    return "paper_parser"
def routing_func3(state: MaingraphState):
    if state["paper_file_parser"]["status"] == "failed":
        return "paper_parser"
    if state["paper_parser_retry"] >= 3:
        raise ValueError("❌ 文章解析陷入循环！")
    if state["paper_file_parser"]["status"] == "success":
        return "parser_check"


# def routing_func4(state: MaingraphState):
#     if state["layout_check_retry"] == 0 and not state.get("verification_status") and state['should_terminate'] is False:
#         return "layout_agent"
#
#     if state["agent_carry_count"] == state["agent_done_count"] and state['should_terminate'] is False:
#         return "validator"
#     if state["layout_check_retry"] != 0 and state["verification_status"] == "again":
#         return "layout_agent"
#     MAX_LAYOUT_RETRY = 3
#     if state["layout_check_retry"] >= MAX_LAYOUT_RETRY:
#         raise ValueError("❌ 出现循环错误！")
#     if  state["verification_status"] == "ok" and state['should_terminate'] is True:
#         return "assemble"
#     raise ValueError("❌ 有问题！")
def routing_func4(state: MaingraphState):
    """layout_check 之后的路由：
    - 验证通过 → assemble（组装文档）
    - 验证失败 → layout_agent（只重试失败的Agent）
    - Agent全部完成 → validator（去验证）
    - 首次进入 → layout_agent（去执行Agent）
    """
    vstatus = state.get("verification_status")

    # 验证通过 → 组装
    if vstatus == "ok" and state.get("should_terminate"):
        return "assemble"

    # 验证失败需要重试 → 回去重新执行（layout_agent会只重试失败的Agent）
    if vstatus == "again":
        retry = state.get("layout_check_retry", 0)
        if retry >= 5:
            raise ValueError("❌ 排版重试次数超限(5次)，请检查验证失败的项！")
        return "layout_agent"

    # Agent全部完成 → 去验证
    done_count = state.get("agent_done_count", 0)
    carry_count = state.get("agent_carry_count")
    if carry_count is not None and carry_count > 0 and done_count >= carry_count:
        return "validator"

    # 首次进入 → 去执行Agent
    return "layout_agent"


def routing_func5(state: MaingraphState):
    """validator 之后的路由：验证失败→回到layout_check重试，验证通过→组装"""
    if state.get("verification_status") == "again":
        return "layout_check"
    return "assemble"

def subrouting_func1(state: MaingraphState):
    sends = []
    agent_fields = ["cover", "chart", "author", "fund", "reference", "text","other"]
    for agent_name in agent_fields:
        agent_status = state.get(agent_name, {})
        agent_mission = agent_status.get("agent_mission")
        if agent_mission is not None and len(agent_mission) > 0:
            packet = {
                "agent_mission": agent_mission
            }
            sends.append(Send(agent_name, packet))
    return sends
