import re
from state.schema import MaingraphState
from tools.utils import get_llm, read_docx, parse_to_json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, SystemMessage
from config.prompt import paper_parser_system_prompt, paper_parser_paper_sections

# ── 关键词 → 分类映射（不用LLM，零token消耗）──
RULE_MAP = [
    # (关键词列表, section, subsection) — 注意：长关键词必须排在短关键词前面
    (["英文摘要", "abstract"], "首页", "英文摘要"),
    (["英文关键词", "keywords"], "首页", "英文关键词"),
    (["英文题目"], "首页", "英文题目"),
    (["摘要"], "首页", "摘要"),
    (["关键词"], "首页", "关键词"),
    (["分类号", "中图分类号", "CLC"], "首页", "中图分类号"),
    (["参考文献", "references"], "参考文献", "文献列表"),
    (["致谢", "acknowledgment"], "致谢", "致谢"),
    (["作者简介", "作者介绍"], "作者简介", "作者简介"),
    (["作者贡献", "贡献声明"], "作者贡献声明", "作者贡献声明"),
    (["基金项目", "基金", "资助", "fund", "grant"], "课题或基金项目", "课题或基金项目"),
    (["附录", "appendix"], "附录", "附录"),
]

# 一级/二级标题正则（兜底：样式没标heading但文本是标题格式）
HEADING_REGEX = [
    (re.compile(r'^[0-9]+\s+\S'), "一级标题"),     # "1 引言"
    (re.compile(r'^[0-9]+\.[0-9]+\s+\S'), "二级标题"),  # "1.1 背景"
    (re.compile(r'^[0-9]+\.[0-9]+\.[0-9]+\s+\S'), "三级标题"),  # "1.1.1 细节"
]

# 英文标题关键词
ENGLISH_TITLE_KEYWORDS = [
    "research", "study", "analysis", "design", "method", "model",
    "system", "based on", "approach", "algorithm", "network",
    "investigation", "evaluation", "comparison", "survey"
]


def _pre_classify(paragraphs: list) -> tuple:
    """
    规则预分类：先用段落样式和关键词判断，返回 (已分类列表, 需要LLM的编号集合)。
    这一步不消耗任何 token。
    """
    import re
    classified = [None] * len(paragraphs)
    need_llm = set()

    for i, para in enumerate(paragraphs):
        text = para.get("text", "").strip()
        is_heading = para.get("is_heading", False)
        heading_level = para.get("heading_level")
        style = para.get("style", "")

        # 1. 先按样式判断标题
        if is_heading and heading_level == 1:
            # 一级标题 → 正文一级标题，但需要 LLM 确认不是"参考文献""致谢"等
            if any(kw in text for kw in ["参考", "文献", "致谢", "附录", "作者", "基金"]):
                need_llm.add(i)
                continue
            classified[i] = {"section": "正文", "subsection": "一级标题",
                           "content": text, "para_index": i}
            continue

        if is_heading and heading_level == 2:
            classified[i] = {"section": "正文", "subsection": "二级标题",
                           "content": text, "para_index": i}
            continue

        if is_heading and heading_level == 3:
            classified[i] = {"section": "正文", "subsection": "三级标题",
                           "content": text, "para_index": i}
            continue

        # 2. 按关键词匹配
        text_lower = text.lower().replace(" ", "")
        matched = False
        for keywords, section, subsection in RULE_MAP:
            for kw in keywords:
                if kw.lower() in text_lower[:30]:  # 只看前30个字符
                    classified[i] = {"section": section, "subsection": subsection,
                                   "content": text, "para_index": i}
                    matched = True
                    break
            if matched:
                break

        if matched:
            continue

        # 2b. 文本型标题兜底（"1 引言" → 一级标题，即使样式没标 heading）
        for regex, subsection in HEADING_REGEX:
            if regex.match(text):
                classified[i] = {"section": "正文", "subsection": subsection,
                               "content": text, "para_index": i}
                matched = True
                break
        if matched:
            continue

        # 3. 判断英文标题/作者/单位（首页元素）
        if re.match(r'^[ -~\\s]+$', text) and not any('一' <= c <= '鿿' for c in text):  # 纯ASCII/英文(无中文)
            # 判断是英文题目还是英文作者/单位
            words = text.split()
            if len(words) >= 4 and any(kw in text.lower() for kw in ENGLISH_TITLE_KEYWORDS):
                classified[i] = {"section": "首页", "subsection": "英文题目",
                               "content": text, "para_index": i}
                continue
            if re.search(r'[A-Z]{2,}\s+[A-Z][a-z]+', text):  # 大写姓+名模式
                classified[i] = {"section": "首页", "subsection": "英文作者姓名",
                               "content": text, "para_index": i}
                continue
            if "university" in text.lower() or "college" in text.lower() or "institute" in text.lower():
                classified[i] = {"section": "首页", "subsection": "英文作者单位",
                               "content": text, "para_index": i}
                continue

        # 3b. 中文姓名（2-4个汉字，中间可能有空格）——首页位置的短文本
        if i <= 5 and 2 <= len(text) <= 20 and re.match(r'^[一-鿿]{2,4}(\s+[一-鿿]{2,4}){1,5}$', text):
            classified[i] = {"section": "首页", "subsection": "作者姓名",
                           "content": text, "para_index": i}
            continue

        # 3c. 作者单位（含"大学""学院""研究所""医院"等）
        if i <= 8 and len(text) < 100 and re.search(r'(大学|学院|研究所|研究院|医院|中心|实验室|科学院)', text):
            if not any(kw in text for kw in ["摘要","关键词","引言","参考"]):
                classified[i] = {"section": "首页", "subsection": "作者单位",
                               "content": text, "para_index": i}
                continue

        # 3d. 副标题（以 —— 或 - 开头，在前5段内）
        if i <= 5 and (text.startswith('——') or text.startswith('--') or text.startswith('—')):
            classified[i] = {"section": "首页", "subsection": "副题目",
                           "content": text, "para_index": i}
            continue

        # 3e. 题目（首页前3段，中文长文本但不是摘要/关键词/分类号）
        if i <= 3 and len(text) >= 6 and len(text) <= 80:
            not_title = ["摘要", "关键词", "分类号", "引言", "参考文献"]
            if not any(kw in text for kw in not_title):
                has_chinese = any('一' <= c <= '鿿' for c in text)
                if has_chinese and not re.match(r'^\d', text) and not is_heading:
                    classified[i] = {"section": "首页", "subsection": "论文题目",
                                   "content": text, "para_index": i}
                    continue

        # 4. 图/表标题
        if re.match(r'^(图|表|Figure|Table|Fig\.?)\s*\d+', text):
            classified[i] = {"section": "正文", "subsection": "图表",
                           "content": text, "para_index": i}
            continue

        # 5. 公文/算法/代码（开头有特殊标记）
        if text.startswith("```") or text.startswith("算法") or text.startswith("Algorithm"):
            classified[i] = {"section": "正文", "subsection": "代码片段" if text.startswith("```") else "算法",
                           "content": text, "para_index": i}
            continue

        # 6. 都没匹配 → 大概率是正文段落，但也可能漏了 → 标记给LLM
        # 但如果是纯文本段落（非标题、足够长），直接当正文段落
        if len(text) > 15 and not is_heading:
            classified[i] = {"section": "正文", "subsection": "正文段落",
                           "content": text, "para_index": i}
            continue

        # 剩下的真不确定的交给 LLM
        need_llm.add(i)

    return classified, need_llm


def _llm_classify(llm, paragraphs: list, indices: set, classified: list) -> list:
    """对不确定的段落用 LLM 分类，分批处理避免超长输入"""
    if not indices:
        return classified

    # 每次最多 30 段凑一批
    batch = []
    for i in sorted(indices):
        batch.append(paragraphs[i])
        if len(batch) >= 30:
            _llm_batch(llm, batch, classified)
            batch = []
    if batch:
        _llm_batch(llm, batch, classified)

    return classified


def _llm_batch(llm, batch: list, classified: list):
    """LLM 处理一批不确定的段落"""
    system_prompt = paper_parser_system_prompt.format(paper_sections=paper_parser_paper_sections)
    template = ChatPromptTemplate.from_messages(
        [("system", system_prompt), ("human", "{input}")]
    )
    try:
        response = llm.invoke(template.format_messages(input=batch))
        raw_content = response.content
        result_json = parse_to_json(raw_content)
        if result_json and "result" in result_json:
            for item in result_json["result"]:
                idx = item.get("para_index")
                if idx is not None and 0 <= idx < len(classified):
                    classified[idx] = item
    except Exception:
        # LLM 分类失败 → 这些段落标为正文段落，不丢内容
        for para in batch:
            idx = para.get("index", len(classified))
            if 0 <= idx < len(classified) and classified[idx] is None:
                classified[idx] = {
                    "section": "正文", "subsection": "正文段落",
                    "content": para.get("text", ""), "para_index": idx
                }


def paper_parser_node(state: MaingraphState):
    # 已成功解析过 → 直接返回，不重复调 LLM
    if (state.get("paper_file_parser") or {}).get("status") == "success":
        return {"messages": [AIMessage(content="论文解析已完成，跳过")]}

    retry_count = state.get("paper_parser_retry")
    llm = get_llm(temperature=0.1, timeout=120.0)
    paper_input = state.get("paper_file")

    try:
        paragraphs = read_docx(paper_input)
    except Exception as e:
        return {
            "paper_file_parser": {
                "status": "failed",
                "data": {},
                "error": f"❌ 文件读取失败，原因：{str(e)}",
            },
            "messages": [AIMessage(content=f"❌ 文章读取失败，原因：{str(e)}")],
        }

    if not paragraphs:
        return {
            "paper_file_parser": {"status": "success", "data": {"result": []}},
            "messages": [SystemMessage(content="<-- 进入 03 解析论文Node -->"),
                        AIMessage(content="⚠️ 论文无有效段落")],
            "paper_parser_retry": 0
        }

    # 1. 规则预分类（零 token 消耗）
    classified, need_llm = _pre_classify(paragraphs)

    # 2. LLM 补充分类不确定的段落
    classified = _llm_classify(llm, paragraphs, need_llm, classified)

    # 3. 兜底：所有 None 段落标为正文（不丢内容）
    result = []
    for i, item in enumerate(classified):
        if item is None:
            text = paragraphs[i].get("text", "") if i < len(paragraphs) else ""
            result.append({
                "section": "正文", "subsection": "正文段落",
                "content": text, "para_index": i
            })
        else:
            result.append(item)

    return {
        "paper_file_parser": {"status": "success", "data": {"result": result}},
        "messages": [SystemMessage(content="<-- 进入 03 解析论文Node -->"),
                     AIMessage(content=f"✅ 已成功解析论文结构（{len(paragraphs)}段, LLM处理{len(need_llm)}段），正在准备排版...")],
        "paper_parser_retry": 0
    }
