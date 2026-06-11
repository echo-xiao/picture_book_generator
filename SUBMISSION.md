# 🌱 StorySprout — Devpost Submission Kit

> **Tagline:** Turn any classic novel into a character-consistent children's picture book.
> **Hackathon:** Google Cloud Rapid Agent Hackathon · **Track:** MongoDB · **Deadline:** 2026-06-11 14:00 PT

---

## ✅ 提交清单(Devpost 必填项)

| # | 必填项 | 内容 | 状态 |
|---|--------|------|------|
| 1 | **Hosted Project URL** | https://picture-book-gen-e3mtc46uua-uc.a.run.app | ✅ 在线 |
| 2 | **Code Repository** | https://github.com/echo-xiao/picture_book_generator | ✅ 公开,已同步到最新 |
| 3 | **Open-source License** | AGPL-3.0(repo 根目录 LICENSE,GitHub About 区可见) | ✅ 已加 |
| 4 | **Track** | MongoDB | ✅ 已选 |
| 5 | **Text Description** | ⬇️ 见下方,直接复制 | ✅ 可贴 |
| 6 | **~3 min Demo Video** | ⬇️ 脚本见下,需上传 YouTube/Vimeo(公开) | ❌ **待录** |

**还差的就一件:按脚本录 3 分钟视频 → 传 YouTube/Vimeo → 把链接填进 Devpost。**

---

## 📝 项目描述(复制粘贴到 Devpost 的 description)

### Inspiration
Classic literature is locked behind dense prose that kids can't access. We wanted to let a 6-year-old experience *The Great Gatsby* or *A Tale of Two Cities* — not a dumbed-down summary, but a real illustrated picture book that preserves the story, characters, and era. The hard part isn't generating images; it's keeping the **same character looking the same** across 40 pages.

### What it does
Paste a classic novel, upload a .txt, or fetch one straight from Project Gutenberg → StorySprout extracts characters, segments scenes, rewrites each scene into child-friendly narration, and generates illustrations where **the same character looks identical on every page**, in period-accurate clothing, with the story text drawn naturally into the art (clouds, scrolls, speech bubbles). Every page then passes a vision QA gate before it ships. Output is a full square-format PDF picture book, plus an interactive editor to refine any character, scene, or page.

### How we built it
- **Multi-agent pipeline**: four specialized agents collaborate in sequence — **Analyzer** (NLP + character/scene extraction) → **Writer** (child-level rewriting) → **Artist** (illustration generation) → **QA** (Gemini-vision quality check). The QA agent isn't report-only: it scores five dimensions per page (character match vs. reference sheets, spelling in embedded text, duplicate characters, name–face mismatch, missing/extra characters) and **triggers a bounded self-correction loop** — a failing page is regenerated with the QA feedback and only the better image is kept.
- **Character & scene consistency**: each character gets a reference sheet + a canonical "visual identity" stored in **MongoDB as the single source of truth**; every page generation receives the same reference images. Location reference sheets and the book cover are fed in as style anchors, so backgrounds and art style stay coherent across the whole book.
- **MongoDB MCP integration (partner track)**: the pipeline talks to MongoDB through MongoDB's **official MCP server** (Model Context Protocol, over stdio) for both reads (preprocess data) and writes (the character consistency hub) — not a direct driver.
- **Gemini 3 on Vertex AI (Agent Platform)**: every model call runs on **Gemini 3.5 Flash** (text) and **Gemini 3.1 Flash Image** (illustrations) through **Vertex AI / Agent Platform**; the product is served on **Cloud Run** with a GCS-backed asset store.
- **Google Agent Builder — ADK**: the four-agent pipeline is orchestrated by a **Google Agent Development Kit (ADK) `SequentialAgent`**, running in-process on Cloud Run so the Artist stage generates real illustrations. The **MongoDB MCP server** is wired in as a tool for character / consistency data.

### Challenges we ran into
Cross-page character consistency was the core challenge — naive per-page generation makes a character's face drift every page. We solved it by centralizing each character's canonical visual identity in MongoDB and feeding reference sheets into every generation. The second challenge was trust: a generated page can *look* fine while the embedded text or characters are wrong, so we made the QA agent an actual gate (score → feedback → regenerate → keep the better image) instead of a report.

### Accomplishments that we're proud of
A real, working end-to-end pipeline that keeps characters consistent across an entire book; a QA agent that gates and self-corrects every page instead of just scoring it; a genuine (read + write) MongoDB MCP integration; the full book pipeline orchestrated by **Google's Agent Development Kit (ADK)**; and text embedded *inside* the illustrations rather than overlaid.

### What we learned
How to architect a deterministic multi-agent pipeline, how MCP standardizes AI-to-data access, and how much of "AI picture books" is really a *consistency* problem, not an image-quality problem.

### What's next
Configurable age bands and output languages, aggregation-driven scene analysis over MongoDB, cross-book character libraries, and narrated/animated output.

### Built With
`Gemini 3.5 Flash` · `Gemini 3.1 Flash Image` · `Vertex AI (Agent Platform)` · `Google ADK (Agent Development Kit)` · `Google Cloud Run` · `MongoDB` · `MongoDB MCP Server` · `FastAPI` · `Next.js` · `Python` · `TypeScript`

---

## 🎬 3-Minute Demo Video Script

> 旁白用英文(rules 要求英文或英文字幕);画面是拍摄指导。控制在 3 分钟内。

**[0:00–0:15] Hook**
- 📺 翻开《The Great Gatsby》原著(密密麻麻的字)
- 🎙️ *"Classic novels are locked behind dense prose kids can't read. What if any child could experience The Great Gatsby — as a real picture book?"*

**[0:15–0:35] Solution**
- 📺 StorySprout 首页
- 🎙️ *"Meet StorySprout — it turns any classic novel into a character-consistent children's picture book, powered by Gemini 3 on Vertex AI, Google's Agent Development Kit, and MongoDB."*

**[0:35–1:30] Live Demo(必须拍到项目运行)**
- 📺 选 The Great Gatsby → 进 editor → 翻几页绘本
- 🎙️ *"Paste a classic or pull one from Project Gutenberg, and StorySprout extracts characters, rewrites each scene for kids, and illustrates it. Notice Gatsby looks identical on every page — with the story text drawn right into the art. Cross-page character consistency is the hard part of AI picture books, and that's what we nailed."*
- ⭐ **重点:停在同一角色(Gatsby)的不同页,展示长相一致 + 文字嵌在插画里**

**[1:30–2:10] Tech: Multi-agent + QA gate**
- 📺 editor 的角色面板/角色 sheet → 点一页的 quality check 结果(五维分数)
- 🎙️ *"Four specialized agents collaborate — Analyzer, Writer, Artist, and QA. Each character's visual identity is stored as a single source of truth, so every page references the same definition. And the QA agent is a real gate: it vision-checks five dimensions on every page and automatically regenerates the ones that fail."*

**[2:10–2:45] MongoDB MCP(partner track,必须展示!)**
- 📺 终端跑 MCP(显示 "5/5 docs via MongoDB MCP server") + MongoDB Atlas/Compass 看 characters 数据
- 🎙️ *"StorySprout reads and writes through MongoDB's official MCP server. The character consistency hub lives in MongoDB, accessed via the Model Context Protocol — both reads and writes."*

**[2:45–3:00] Close**
- 📺 成品 PDF 绘本翻页 + logo
- 🎙️ *"StorySprout — making the classics accessible to every child. Built with Gemini, Google Cloud, and MongoDB."*

**录制要点:**
1. ⭐ 一定要拍到**角色一致性**(同角色翻页)—— 你的护城河
2. ⭐ 一定要展示 **MongoDB MCP**(终端 5/5 + Atlas 数据)—— partner track 评分点
3. ⭐ 新卖点:点开一页的 **quality check 五维分数** —— "QA agent 是真闸门"比"有 QA"有说服力
4. 控制在 3 分钟内(超了只看前 3 分钟)

---

## 🚀 提交步骤

1. 打开 https://rapid-agent.devpost.com/ → 点 **"Join hackathon"** 报名
2. 录视频 → 传 **YouTube 或 Vimeo**(设为公开)
3. 点 **"Submit project"** 填表:
   - Hosted URL / Repo URL(见上方清单)
   - 粘贴上方**项目描述**
   - 填**视频链接**
   - 选 **MongoDB** track
4. **6/11 下午 2pm PT 前**点提交(可先存草稿反复改)

---

## 🔧 演示前自查(录视频前确认 demo 能跑)

- [ ] Cloud Build `5e39ea2` 部署完成(`gcloud builds list --limit=1` 显示 SUCCESS)
- [ ] 打开 https://picture-book-gen-e3mtc46uua-uc.a.run.app/editor/the_great_gatsby — characters 有 116 个、pages 有插图
- [ ] 点开任意一页的 quality check,五维分数正常显示(视频新卖点)
- [ ] 终端能跑出 "5/5 docs via MongoDB MCP server"(MCP 演示)
- [ ] MongoDB Atlas 能看到 characters/segments 数据
- [ ] 注意:本次部署起章节生成开启了 self-correct,低分页会自动重试一次,生成时间略长——录"点 Gen 实时生成"片段时留余量

---

## ⚠️ 材料与代码一致性说明(本次更新)

- ❌ 删除了 "CLIP check" 的说法 —— 该代码路径从未被调用,已清理;真实机制是 **Gemini 视觉 QA 五维检查 + 有界自我修正**,且本次部署起在 web 流程中真实生效
- ❌ 删除了 ".pdf/.epub 上传" 的说法 —— 输入方式为粘贴文本 / .txt 上传 / Gutenberg URL 抓取
- ✅ 新增了可以诚实宣称的卖点:QA 真闸门(self-correct)、场景 sheet + 封面风格锚定进了主 pipeline、页面显示文字与画进图里的文字一致
