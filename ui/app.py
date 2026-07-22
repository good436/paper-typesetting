"""
论文排版智能助手 -- Web 界面
设计系统: DESIGN.md (Soft Blush + Rose Gold + 分步页面式)
启动: streamlit run ui/app.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from main import run_formatting_process, app as main_app
import tempfile, uuid, os, base64
from langgraph.types import Command

# ── 背景图片加载 ─────────────────────────────
_BG_DIR = Path(__file__).resolve().parent
_BG_IMAGE = None
for _name in ["背景动图.mp4", "kakarot.jpg"]:
    _candidate = _BG_DIR / _name
    if _candidate.exists():
        _BG_IMAGE = _candidate
        break

st.set_page_config(page_title="论文排版智能助手", page_icon=str(_BG_DIR / "docx_icon.png"), layout="centered", initial_sidebar_state="expanded")

# ── 背景注入 ────────────────────────────────
if _BG_IMAGE and _BG_IMAGE.suffix.lower() == ".mp4":
    _video_b64 = base64.b64encode(_BG_IMAGE.read_bytes()).decode()
    st.markdown(f"""
    <style>
    .bg-video-container {{
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        z-index: -1; pointer-events: none; overflow: hidden;
    }}
    .bg-video-container video {{
        position: absolute; top: 50%; left: 50%;
        min-width: 100%; min-height: 100%;
        transform: translate(-50%, -50%);
        object-fit: cover;
    }}
    </style>
    <div class="bg-video-container">
        <video autoplay loop muted playsinline>
            <source src="data:video/mp4;base64,{_video_b64}" type="video/mp4">
        </video>
    </div>
    """, unsafe_allow_html=True)
elif _BG_IMAGE:
    _img_b64 = base64.b64encode(_BG_IMAGE.read_bytes()).decode()
    _ext = _BG_IMAGE.suffix.lower()
    _mime = "image/gif" if _ext == ".gif" else "image/png" if _ext == ".png" else "image/jpeg"
    st.markdown(f"""
    <style>
    body {{
        background-image: url(data:{_mime};base64,{_img_b64}) !important;
        background-size: cover !important;
        background-position: center center !important;
        background-attachment: fixed !important;
        background-repeat: no-repeat !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# ── 主样式 ──────────────────────────────────
st.markdown("""
<style>
/* ============================================
   Design Tokens :: Soft Blush + Rose Gold
   ============================================ */
:root {
    --bg: #fdf2f4;
    --surface: #ffffff;
    --text: #1f1a1c;
    --text2: #8c7b80;
    --accent: #c97d8b;
    --accent-h: #b06876;
    --border: #f0e4e8;
    --success: #6b9b7a;
    --error: #c4666b;
}

/* ── 全局透明背景，让背景图透出来 ── */
html, body, .stApp, .main, [data-testid="stAppViewContainer"] {
    background: transparent !important;
}

/* ── 主容器居中 ── */
[data-testid="stMain"] .block-container {
    max-width: 680px !important;
    margin: 0 auto !important;
}

/* ============================================
   标题
   ============================================ */
.main-title {
    font-family: 'DM Sans', 'Noto Sans SC', sans-serif;
    font-size: 1.8rem; font-weight: 700;
    color: #000000; text-align: center;
    letter-spacing: -0.01em; margin-bottom: 4px;
    text-shadow: 0 1px 3px rgba(255,255,255,0.8);
}
.subtitle {
    text-align: center; color: #1a1a1a;
    font-size: 0.95rem; margin-bottom: 1.2rem;
    font-weight: 500;
}

/* ============================================
   输入
   ============================================ */
.stTextArea textarea, .stTextInput input {
    background: rgba(255,255,255,0.9) !important;
    border: 1.5px solid #c0b3b8 !important;
    border-radius: 8px !important;
    color: #111111 !important;
    font-size: 1rem !important;
    line-height: 1.6 !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: #c97d8b !important;
    box-shadow: 0 0 0 3px rgba(201,125,139,0.18) !important;
    outline: none !important;
}
.stTextArea textarea::placeholder, .stTextInput input::placeholder {
    color: #a09095 !important;
    font-size: 0.9rem !important;
}

/* ── 文件上传区 ── */
[data-testid="stFileUploader"] section {
    border: 1px solid #e0d4d8 !important;
    border-radius: 8px !important;
    background: rgba(255,255,255,0.75) !important;
    padding: 8px 12px !important;
}
[data-testid="stFileUploader"] section:hover {
    border-color: #c97d8b !important;
}
/* 隐藏上传区多余元素 */
[data-testid="stFileUploader"] small { display: none !important; }

/* ============================================
   按钮
   ============================================ */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important; font-size: 0.92rem !important;
    padding: 9px 22px !important;
    border: none !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease, border-color 0.15s ease !important;
}
button[data-testid="baseButton-primary"] {
    background: #c97d8b !important; color: #fff !important;
}
button[data-testid="baseButton-primary"]:hover {
    background: #b06876 !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(201,125,139,0.25) !important;
}
/* 侧边栏按钮 — 默认描边风格 */
[data-testid="stSidebar"] button {
    background: transparent !important;
    color: #c97d8b !important;
    border: 1.5px solid #c97d8b !important;
    font-weight: 600 !important;
}
[data-testid="stSidebar"] button:hover {
    background: rgba(201,125,139,0.08) !important;
    color: #b06876 !important;
    border-color: #b06876 !important;
}
/* 侧边栏 primary 按钮 — 实心（如有） */
[data-testid="stSidebar"] button[kind="primary"] {
    background: #c97d8b !important;
    color: #ffffff !important;
    border: none !important;
}

/* 重新开始按钮 — 灰色描边，区别于粉色 */
.reset-btn-wrapper button {
    background: transparent !important;
    color: #8c7b80 !important;
    border: 1.5px solid #c0b3b8 !important;
    font-weight: 500 !important;
}
.reset-btn-wrapper button:hover {
    background: rgba(0,0,0,0.03) !important;
    color: #6b6065 !important;
    border-color: #a09095 !important;
}

/* ============================================
   进度条
   ============================================ */
.stProgress > div > div > div { background: #c97d8b !important; }

/* ============================================
   Alert
   ============================================ */
[data-testid="stAlert"] {
    border-radius: 6px !important; border: 1px solid #f0e4e8 !important;
    background: rgba(255,255,255,0.82) !important;
    backdrop-filter: blur(8px) !important;
}
div[data-testid="stNotification"] { background: transparent !important; }

/* ============================================
   侧边栏
   ============================================ */
[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.94) !important;
    border-right: 1px solid rgba(201,125,139,0.2) !important;
}
[data-testid="stSidebar"] * { color: #111111 !important; }

/* ── 侧边栏折叠后的展开按钮 ── */
[data-testid="stExpandSidebarButton"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    background: #c97d8b !important;
    color: #ffffff !important;
    width: 40px !important;
    height: 40px !important;
    min-width: 40px !important;
    min-height: 40px !important;
    border-radius: 10px !important;
    border: none !important;
    z-index: 999999 !important;
    box-shadow: 0 3px 12px rgba(201,125,139,0.40) !important;
    cursor: pointer !important;
    position: fixed !important;
    top: 12px !important;
    left: 12px !important;
}
[data-testid="stExpandSidebarButton"]:hover {
    background: #b06876 !important;
    transform: scale(1.1);
    box-shadow: 0 4px 16px rgba(201,125,139,0.50) !important;
}
[data-testid="stExpandSidebarButton"] svg {
    fill: #ffffff !important;
    color: #ffffff !important;
    stroke: #ffffff !important;
}

/* ── 侧边栏展开后的收起按钮 ── */
[data-testid="stSidebarCollapseButton"] {
    background: transparent !important;
    color: #c97d8b !important;
    border: none !important;
    border-radius: 8px !important;
    cursor: pointer !important;
}
[data-testid="stSidebarCollapseButton"]:hover {
    background: rgba(201,125,139,0.1) !important;
    color: #b06876 !important;
}

/* ── 文件上传按钮 ── */
[data-testid="stFileUploader"] button {
    background: #c97d8b !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    padding: 6px 16px !important;
    cursor: pointer !important;
}
[data-testid="stFileUploader"] button:hover {
    background: #b06876 !important;
}

/* ============================================
   状态标签
   ============================================ */
.status-tag {
    display: inline-block; padding: 2px 10px;
    border-radius: 4px; font-size: 0.74rem; font-weight: 500; margin: 1px 0;
}
.status-tag.info { background: rgba(253,242,244,0.9); color: #5a4a50; font-weight: 600; }
.status-tag.ok   { background: rgba(232,245,233,0.9); color: #3d5c47; font-weight: 600; }
.status-tag.err  { background: rgba(252,228,236,0.9); color: #8b2028; font-weight: 600; }

/* ============================================
   分割线 & 文字
   ============================================ */
.fancy-divider {
    height: 1px; background: linear-gradient(90deg,transparent,rgba(201,125,139,0.3),transparent);
    border: none; margin: 1rem 0;
}
h3, h4 { color: #000000 !important; font-weight: 700; }
p, label, li { color: #000000 !important; font-weight: 500; }
.stCaption { color: #ffffff !important; font-size: 0.85rem; font-weight: 700; text-shadow: 0 1px 3px rgba(0,0,0,0.5); }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
/* Streamlit 一键部署按钮 — 已启用 */
/* 工具栏保留（里面包含侧边栏展开按钮），只隐藏不需要的 */
[data-testid="stToolbarActions"] { display: none !important; }
[data-testid="stMainMenuButton"] { display: none !important; }

/* ── 工具栏透明，只保留侧边栏展开按钮 ── */
[data-testid="stHeader"] {
    background: transparent !important;
}
[data-testid="stToolbar"] {
    background: transparent !important;
}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════
# 会话状态
# ═══════════════════════════════════════════════
for key, val in {
    "messages": [], "user_input": "", "temp_file_path": None,
    "thread_id": None, "process_started": False, "process_completed": False,
    "email_sent": False, "email": "", "final_paper": None,
    "uploaded_file_data": None, "displayed_messages": set(),
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ═══════════════════════════════════════════════
# 侧边栏
# ═══════════════════════════════════════════════
with st.sidebar:
    if "reset_counter" not in st.session_state:
        st.session_state["reset_counter"] = 0

    st.markdown("**🔑 DeepSeek API Key**")
    st.caption("使用你自己的Key，不会存储也不会被他人看到")
    user_api_key = st.text_input(
        "API Key", type="password",
        placeholder="sk-xxxxxxxxxxxxxxxx",
        label_visibility="collapsed",
        key=f"api_key_{st.session_state.reset_counter}",
    )
    st.divider()

    st.markdown("**选择论文文件**")

    # on_change：文件变化时同步更新 session_state
    def _on_upload():
        key = f"file_uploader_{st.session_state.reset_counter}"
        f_obj = st.session_state.get(key)
        if f_obj is not None:
            st.session_state["uploaded_file_data"] = {
                "name": f_obj.name, "size": f_obj.size, "data": f_obj.getvalue()
            }
        else:
            # 用户点了 × 清除文件
            st.session_state["uploaded_file_data"] = None

    # 文件上传器始终显示 — 不切换成卡片，消除 DOM 替换导致的闪屏
    st.file_uploader(
        "选择论文文件", type=["docx"], label_visibility="collapsed",
        key=f"file_uploader_{st.session_state.reset_counter}",
        on_change=_on_upload
    )

    st.divider()

    st.markdown('<div class="reset-btn-wrapper">', unsafe_allow_html=True)
    if st.button("🔄 重新开始", use_container_width=True):
        next_val = st.session_state.get("reset_counter", 0) + 1
        st.session_state.clear()
        st.session_state["reset_counter"] = next_val
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════
# 头部
# ═══════════════════════════════════════════════
st.markdown('<div class="main-title">论文排版·智能助手</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">上传论文文件 · 粘贴排版要求 · 一键自动排版</div>', unsafe_allow_html=True)
st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════
# 页面 1：上传 & 输入
# ═══════════════════════════════════════════════
if not st.session_state["process_started"]:
    st.markdown("#### 排版格式要求")
    st.caption("从期刊官网复制格式要求粘贴进来，或自己描述")

    text_input = st.text_area(
        "排版要求",
        placeholder="把你从期刊官网复制的格式要求粘贴进来，例如：\n\n论文题目用黑体三号加粗居中，英文题目用Times New Roman三号居中。\n作者姓名宋体小四居中，作者单位宋体五号居中。\n摘要宋体小四，1.5倍行距，首行缩进2字符。\n关键词宋体五号，不少于5个。\n正文宋体小四，1.5倍行距，首行缩进2字符。\n一级标题黑体三号加粗居中，二级标题黑体四号加粗左对齐。\n参考文献宋体小五号，悬挂缩进2字符。",
        height=260,
        label_visibility="collapsed",
        key=f"text_input_{st.session_state.reset_counter}",
    )

    st.markdown("")

    _file_data = st.session_state.get("uploaded_file_data")
    btn_label = "开始排版" if _file_data else "请先在左侧上传论文文件"
    if st.button(btn_label, use_container_width=True, type="primary", disabled=not _file_data):
        st.session_state["user_input"] = text_input
        st.session_state["displayed_messages"] = set()
        # 注入用户自己的 API Key（线程隔离，不会泄露给其他用户）
        from config.setting import set_user_api_key
        if user_api_key.strip():
            set_user_api_key(user_api_key.strip())
        if _file_data:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                tmp.write(_file_data["data"])
                st.session_state["temp_file_path"] = tmp.name
        st.session_state["thread_id"] = str(uuid.uuid4())
        st.session_state["process_started"] = True
        st.rerun()

# ═══════════════════════════════════════════════
# 页面 2：排版中
# ═══════════════════════════════════════════════
elif st.session_state["process_started"] and not st.session_state["process_completed"]:
    st.markdown("#### 排版进行中...")
    progress = st.progress(0, text="正在解析需求...")

    phase_pct = {
        "01": 10, "02": 25, "03": 40, "04": 55,
        "05": 65, "06": 75, "07": 85, "08": 90,
        "09": 95, "10": 98, "11": 100,
    }
    current = 0

    try:
        for chunk in run_formatting_process(
            st.session_state["user_input"],
            st.session_state["temp_file_path"],
            st.session_state["thread_id"],
        ):
            if "final_paper" in chunk and chunk["final_paper"]:
                st.session_state["final_paper"] = chunk["final_paper"]

            if "messages" in chunk:
                for msg in chunk["messages"]:
                    if hasattr(msg, 'content'):
                        content = msg.content
                        if content not in st.session_state["displayed_messages"]:
                            st.session_state["displayed_messages"].add(content)
                            st.session_state["messages"].append({"role": "assistant", "content": content})
                            for tag, pct in phase_pct.items():
                                if f"进入 {tag}" in content:
                                    current = pct
                            progress.progress(min(current, 95) / 100, text=content[:100])
                            cls = "ok" if "✅" in content else ("err" if "❌" in content else "info")
                            st.markdown(f'<span class="status-tag {cls}">{content}</span>', unsafe_allow_html=True)

        progress.progress(100, text="排版完成！")
        st.success("排版完成，请在下方接收文件")

    except Exception as e:
        progress.progress(100, text="异常")
        st.error(f"处理失败：{e}")

    st.session_state["process_completed"] = True
    st.rerun()

# ═══════════════════════════════════════════════
# 页面 3：接收文件
# ═══════════════════════════════════════════════
elif st.session_state["process_completed"] and not st.session_state["email_sent"]:
    st.markdown("#### 排版完成，接收文件")

    email = st.text_input("输入邮箱地址（可选）", placeholder="example@163.com", key="email_input")
    st.session_state["email"] = email

    c1, c2 = st.columns(2)
    with c1:
        if st.button("📧 发送到邮箱", use_container_width=True, type="primary"):
            if "@" in email and "." in email:
                st.session_state["email_sent"] = True
                st.rerun()
            else:
                st.error("请输入有效的邮箱地址")
    with c2:
        final_paper = st.session_state.get("final_paper")
        if final_paper and os.path.exists(final_paper):
            with open(final_paper, "rb") as f:
                st.download_button(
                    "📥 下载文件", f.read(),
                    file_name=os.path.basename(final_paper),
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )
        else:
            st.button("📥 下载文件", disabled=True, use_container_width=True)

    st.divider()
    if st.button("跳过，不需要邮件", use_container_width=True):
        st.session_state["email_sent"] = True
        st.rerun()

# ═══════════════════════════════════════════════
# 页面 3.5：发邮件
# ═══════════════════════════════════════════════
elif st.session_state["email_sent"] and st.session_state["email"]:
    st.markdown("#### 正在发送邮件...")
    try:
        config = {"configurable": {"thread_id": st.session_state["thread_id"]}}
        for chunk in main_app.stream(Command(resume=st.session_state["email"]), config=config, stream_mode="values"):
            if "messages" in chunk:
                for msg in chunk["messages"]:
                    if hasattr(msg, 'content'):
                        content = msg.content
                        if content not in st.session_state["displayed_messages"]:
                            st.session_state["displayed_messages"].add(content)
                            if "成功" in content:
                                st.success(content)
                            elif "失败" in content:
                                st.error(content)
                            else:
                                st.info(content)
        st.success("全部完成！")
    except Exception as e:
        st.error(f"发送失败：{e}")
