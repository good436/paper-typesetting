# Design System — 论文排版智能助手

## Product Context
- **What this is:** 学术论文自动排版工具，用户上传 .docx + 粘贴排版要求 → AI 自动完成格式调整
- **Who it's for:** 需要投稿期刊的学者和研究人员（面向外部用户）
- **Space/industry:** 学术工具 / 在线排版服务
- **Project type:** Web 工具应用（Streamlit 前端 + LangGraph 后端）

## Aesthetic Direction
- **Direction:** Soft Editorial — 柔和但有分量，温暖的学术感
- **Decoration level:** intentional — 背景图处理为纹理（8-12%透明度+模糊），不抢眼
- **Mood:** 让人放松的粉色暖调，降低投稿焦虑，同时保持专业工具的可信度
- **Memorable thing:** "专业精致" — 用户第一眼觉得这是一个精心打磨过的正经工具

## Layout
- **Approach:** 分步页面式（三步：上传 → 排版中 → 下载），每页独立不滚屏
- **Max content width:** 680px 居中
- **Border radius:** sm:6px, md:10px, lg:14px

## Typography
- **Display/Title:** DM Sans 700 — 几何现代感，与柔和的粉色形成对比
- **Body:** Noto Sans SC 400/500 — 中文阅读舒适
- **UI/Labels:** Noto Sans SC 500 + DM Sans 500
- **Code/Data:** JetBrains Mono 400
- **Loading:** Google Fonts CDN
- **Scale:** 标题 1.5rem, 正文 0.9rem, 小字 0.78rem, 日志 0.74rem

## Color
- **Approach:** balanced — 粉色为主调，玫瑰金强调，灰调做层次
- **Page background:** #fdf2f4 (Soft Blush — 极淡樱花粉)
- **Card/Surface:** #ffffff
- **Primary text:** #1f1a1c (Charcoal — 深炭灰)
- **Secondary text:** #8c7b80 (Warm Gray-Pink)
- **Accent:** #c97d8b (Rose Gold / Dusty Rose — 干枯玫瑰)
- **Accent hover:** #b06876
- **Border:** #f0e4e8 (Whisper Pink)
- **Success:** #6b9b7a (Sage Green)
- **Error:** #c4666b (Warm Red)
- **Warning:** #d49b6a (Warm Amber)
- **Info:** #8b9dc3 (Dusty Blue)

## Spacing
- **Base unit:** 4px
- **Density:** comfortable (舒适密度)
- **Scale:** xs(4) sm(8) md(16) lg(24) xl(32) 2xl(48)

## Motion
- **Approach:** intentional — 只做有意义的过渡
- **Easing:** enter(ease-out) exit(ease-in) move(ease-in-out)
- **Duration:** micro(80-120ms) short(150-200ms) medium(250-350ms)
- **Button hover:** translateY(-1px) + shadow spread
- **Progress bar:** smooth width transition 0.5s ease
- **Page switch:** fade transition between steps

## Background Image
- **Usage:** 全屏固定背景，不透明度 8-12% + blur 滤镜
- **Position:** center center, cover
- **Purpose:** 远看是暖色纹理，近看隐约能辨认——作为彩蛋而非主角
- **Source:** ui/kakarot.jpg (用户自定义图片)

## Decisions Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-07-21 | 粉色基调设计系统 | 用户偏好淡粉色，参考 erdock.cn；学术工具中粉色极少见，差异化强；低饱和度保留专业感 |
| 2026-07-21 | 分步页面式布局 | 用户不想要一页滚到底；三步页面式（上传→排版→下载）更清晰 |
| 2026-07-21 | 背景图做纹理处理 | 保留用户个性化但不抢功能焦点 |
