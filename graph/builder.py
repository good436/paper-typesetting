from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import InMemorySaver
from state.schema import MaingraphState
from agent import (input_parser_node, paper_parser_node, validator_node,
                   layout_agent_node, input_check_node, parser_check_node,
                   layout_check_node, assemble_node, human_editing_node,
                   send_email_node)
from agent.dispatch import dispatch_node
from langgraph.constants import END, START
from graph.routes import (routing_func1, routing_func2, routing_func3, routing_func4, routing_func5)


def create_formatting_graph():
    builder = StateGraph(MaingraphState)

    builder.add_node("input_check", input_check_node)
    builder.add_node("input_parser", input_parser_node)
    builder.add_node("paper_parser", paper_parser_node)
    builder.add_node("parser_check", parser_check_node)
    builder.add_node("layout_check", layout_check_node)
    builder.add_node("layout_agent", layout_agent_node)
    builder.add_node("agent_dispatch", dispatch_node)
    builder.add_node("validator", validator_node)
    builder.add_node("assemble", assemble_node)
    builder.add_node("human_editing", human_editing_node)
    builder.add_node("send_email", send_email_node)

    # 边
    builder.add_edge(START, "input_check")
    builder.add_conditional_edges("input_check", routing_func1, ["input_parser","input_check",END])
    builder.add_conditional_edges("input_parser", routing_func2, ["paper_parser","input_parser"])
    builder.add_conditional_edges("paper_parser", routing_func3, ["parser_check","paper_parser"])
    builder.add_edge("parser_check", "layout_check")
    builder.add_conditional_edges("layout_check", routing_func4, ["layout_agent","validator","assemble",END])
    builder.add_edge("layout_agent", "agent_dispatch")
    builder.add_edge("agent_dispatch", "layout_check")
    builder.add_conditional_edges("validator", routing_func5, ["layout_check", "assemble"])
    builder.add_edge("assemble", "human_editing")
    builder.add_edge("human_editing", "send_email")
    builder.add_edge("send_email", END)

    checkpointer = InMemorySaver()
    graph = builder.compile(checkpointer=checkpointer)
    return graph
