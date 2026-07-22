from state.schema import MaingraphState
from config.prompt import input_check_prompt
from langchain_core.prompts import ChatPromptTemplate
from tools.utils import str_to_bool, get_llm
from langchain_core.messages import AIMessage, SystemMessage
import traceback


def input_check_node(state: MaingraphState):
    # 已判断过 → 直接返回
    if state.get("task_judgement") is not None:
        return {"messages": [SystemMessage(content="<-- 01 检查用户输入Node -->"),
                            AIMessage(content="输入检查已完成，跳过")]}
    llm = get_llm(temperature=0.1)
    input_text = state.get("user_input", [])
    input_paper = state.get("paper_file", [])

    # 快速预判：如果用户输入明显是关于排版/论文格式的，跳过LLM调用
    quick_check_text = "".join(input_text) if isinstance(input_text, list) else str(input_text)
    obvious_keywords = ["排版", "格式", "字体", "字号", "行距", "论文", "题目", "摘要", "关键词",
                        "参考文献", "作者", "期刊", "投稿", "宋体", "黑体", "对齐", "缩进", "加粗"]
    if any(kw in quick_check_text for kw in obvious_keywords):
        if not input_paper:
            return {
                "task_judgement": True,
                "paper_file": None,
                "messages": [
                    SystemMessage(content="<-- 进入 01 检查用户输入Node -->"),
                    AIMessage(content="用户未上传论文文件！请上传~"),
                ],
            }
        return {
            "task_judgement": True,
            "messages": [
                SystemMessage(content="<-- 进入 01 检查用户输入Node -->"),
                AIMessage(content="符合期刊论文自动排版 agent 任务范围！"),
            ],
        }

    template = ChatPromptTemplate.from_messages(
        [("system", input_check_prompt), ("human", "{input}")]
    )

    try:
        response = llm.invoke(template.format_messages(input=input_text))
        raw_result = response.content.strip()
        print(f"[DEBUG] input_check LLM 原始返回: {raw_result}")
        task_judgement = str_to_bool(raw_result)
    except Exception as e:
        print(f"[ERROR] input_check 失败: {e}")
        traceback.print_exc()
        # 出错时不要直接拒绝，让用户重试或交给后续节点处理
        return {
            "task_judgement": True,  # 放行，让后续节点判断
            "messages": [
                SystemMessage(content="<-- 进入 01 检查用户输入Node -->"),
                AIMessage(content=f"输入检查遇到问题({str(e)[:50]})，但任务将继续处理..."),
            ],
        }

    if task_judgement is False:
        return {
            "task_judgement": False,
            "messages": [
                SystemMessage(content="<-- 进入 01 检查用户输入Node -->"),
                AIMessage(content="用户需求超出 agent 任务范围！请提供论文排版相关的需求。"),
            ],
        }

    if task_judgement is True and not input_paper:
        return {
            "task_judgement": True,
            "paper_file": None,
            "messages": [
                SystemMessage(content="<-- 进入 01 检查用户输入Node -->"),
                AIMessage(content="用户未上传论文文件！请上传~"),
            ],
        }

    return {
        "task_judgement": True,
        "messages": [
            SystemMessage(content="<-- 进入 01 检查用户输入Node -->"),
            AIMessage(content="符合期刊论文自动排版 agent 任务范围！"),
        ],
    }
