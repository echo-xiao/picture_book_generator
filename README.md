<p align="center">
  <img src="frontend/public/logo.png" alt="StorySprout" width="180" />
</p>

# 🌱 StorySprout

**Turn any classic novel into a character-consistent children's picture book.**

Let a 6-year-old experience *The Great Gatsby* — not a dumbed-down summary, but a real illustrated picture book that preserves the story, characters, and era. The hard part isn't generating images; it's keeping the **same character looking the same** across 40 pages — that's what StorySprout solves.

**Google Cloud Rapid Agent Hackathon** · Track: MongoDB · [Devpost](https://rapid-agent.devpost.com/)

🔗 **Live demo**: https://picture-book-gen-e3mtc46uua-uc.a.run.app

---

## 💡 The Product

| | |
|---|---|
| **Problem** | Classic literature is locked behind dense prose that kids can't read. |
| **Solution** | Upload a classic novel → get a full picture book where every character stays visually consistent across the whole book, in period-accurate clothing, with the story text drawn naturally into the art. |
| **Who it's for** | Parents, educators, early readers — making the classics accessible to children. |
| **Moat** | Cross-page **character consistency** (most AI picture-book tools can't keep a character's face stable) + **MongoDB via MCP** as the consistency data hub. |
| **Status** | Live on Cloud Run · ADK multi-agent pipeline · Gemini 3 on Vertex AI · MongoDB MCP (read + write). |

> 📄 Submission materials (Devpost description + 3-min video script + checklist): see **[SUBMISSION.md](SUBMISSION.md)**

---

## 🏗️ Architecture

One production pipeline, orchestrated with **Google ADK**, powered by **Gemini 3 on Vertex AI**, with **MongoDB (via the official MCP server)** as the consistency data hub — running on **Cloud Run**.

```
            ┌─────────────────────────── Cloud Run (single container) ───────────────────────────┐
            │  Next.js 15 (public :8080)  ──reverse proxy──▶  FastAPI (internal :8000)            │
            │                                                      │                              │
            │                                   ADK SequentialAgent ("storysprout_pipeline")      │
            │                                   ┌──────────┬─────────────┬────────┬────────────┐  │
            │                                   │ Analyzer │ ArtistSetup │ Writer │ IllustrateQA│ │
            │                                   └────┬─────┴──────┬──────┴───┬────┴──────┬─────┘  │
            └────────────────────────────────────────┼────────────┼──────────┼───────────┼────────┘
                                                     │            │          │           │
                       MongoDB Atlas ◀── MCP (stdio) ┘   Gemini 3.5 Flash + Gemini 3.1 Flash Image
                       (consistency hub)                        (Vertex AI, location=global)
```

**The four ADK agents** (`src/agents/adk_pipeline.py`):

| Agent | Role |
|-------|------|
| **Analyzer** | Loads preprocess data (characters, segments, annotations) — **MCP-first** from MongoDB, with pymongo / local-file fallback |
| **ArtistSetup** | Ensures character reference sheets exist; resolves which sheets each page needs |
| **Writer** | Simplifies the original prose into child-friendly page text |
| **IllustrateQA** | Generates each page illustration (feeding character sheets as references), runs the 5-dimension quality check, self-corrects failures, exports PDF |

The agents run in fixed order via ADK `SequentialAgent`, in-process (image generation is too heavy for a remote agent runtime), sharing a `PipelineContext`.

## How It Works

```
Upload a book (.txt, or fetch from a URL)
    ↓
Preprocess (once per book): split chapters → LLM identifies characters/aliases/locations
    → TextTiling segments scenes → LLM annotates each segment
    → character visual identities written to MongoDB via MCP (consistency hub)
    ↓
Generate (per chapter): ADK pipeline — simplify text → build prompts
    → illustrate with character-sheet references → QA each page → self-correct → PDF
    ↓
Edit: interactive editor — characters / scenes / pages tabs, regenerate anything,
    version history, staleness red-flags, live agent activity log
```

## Quick Start (local)

```bash
# 1. Install
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 2. Configure
cp .env.example .env
# Default backend is Vertex AI (uses your gcloud ADC + GCP_PROJECT).
# No GCP project? Set GEMINI_BACKEND=api_key and add GEMINI_API_KEY.

# 3. Start backend
python -m uvicorn src.app:app --port 8000

# 4. Start frontend (another terminal)
cd frontend && npm run dev

# 5. Open http://localhost:3000
```

CLI (what the web endpoints run under the hood):

```bash
python scripts/preprocess_book.py --input data/sample_books/the_great_gatsby.txt
python scripts/generate_chapter.py --book the_great_gatsby --chapter 0 --self-correct
```

## Features

### Interactive Editor (`/editor/{bookId}`)

| Tab | Features |
|-----|----------|
| **Characters** | Reference-sheet gallery, edit visual identity fields, regenerate per character, automatic quality check + self-correct, version history |
| **Scenes** | Major/minor locations extracted by LLM, editable visual details, scene reference image generation, version history |
| **Pages** | Per-page illustration view, edit simplified text / background / characters & actions, regenerate with progress, version carousel |
| **Agents** | Live agent activity log — watch the ADK pipeline stages work in real time |
| **Staleness red-flags** | A page turns red when its illustration is older than a character/scene sheet it depends on |
| **AI Chat** | Describe what you want in natural language → AI auto-fills prompt fields |

### Quality Check (5 dimensions, auto + self-correcting)

1. **Character Consistency** — Do characters match their reference sheets?
2. **Spelling** — Are embedded text words spelled correctly?
3. **Duplicate Characters** — Is any character drawn twice?
4. **Name-Face Mismatch** — Do name labels point to the right person?
5. **Character Count** — Are all expected characters present?

Failed pages are automatically regenerated with corrective feedback (`--self-correct`, also used by the web flow).

### Other Pages

- **Home** (`/`) — Upload books, browse library
- **Book Reader** (`/book/{bookId}`) — Full-screen page-flip reading with thumbnails

## MongoDB MCP Integration (MongoDB Partner Track)

This project integrates **MongoDB's official MCP server** (`mongodb-mcp-server`)
over the Model Context Protocol (stdio). The pipeline talks to MongoDB through
MCP for **both reads and writes** — not a direct driver — satisfying the
hackathon requirement to integrate a partner's MCP server.
(`src/core/mcp_client.py` implements the MCP stdio client; the server is
launched on demand via `npx mongodb-mcp-server`, configured by
`MDB_MCP_CONNECTION_STRING`.)

**Read path** — the Analyzer agent loads all preprocess documents through the
MCP `find` tool, with a pymongo / local-file fallback for resilience.

**Write path — the Character Consistency Hub** — After character reference
sheets are generated, each character's visual identity (reference-sheet path,
visual description, color palette) is written back into the `characters`
collection through the MCP `update-many` tool. This makes MongoDB the
**single source of truth** for cross-page character consistency:

```
preprocess → write each character's visual identity to MongoDB (via MCP)
                            ↓
generate page N → read that character's sheet + identity from MongoDB (via MCP)
                            ↓
       same canonical reference everywhere → character looks identical book-wide
```

Keeping one character looking the same across an entire book is the hard part
of AI picture books; centralizing the canonical definition in MongoDB (read via
MCP on every page) is what makes it reliable.

**Future work** — aggregation queries over `segments` (character co-occurrence,
scene frequency) to drive richer generation decisions.

### MongoDB Collections

| Collection | Contents |
|------------|----------|
| `books` | Book metadata (title, chapters, status) |
| `characters` | Character profiles + visual identity (the consistency hub) |
| `segments` | All segments (text, characters, actions, background, sentiment) |
| `preprocess_files` | Cached preprocess artifacts (chapters, analysis, locations…) |
| `illustrations` | Generation records (segment, prompt, image path, version) |
| `generation_log` | LLM call logs (model, input/output, tokens, duration) |

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Agent orchestration | **Google ADK** (`SequentialAgent`, 4 custom `BaseAgent` stages) |
| Text analysis & writing | **Gemini 3.5 Flash** on Vertex AI |
| Image generation | **Gemini 3.1 Flash Image** on Vertex AI |
| Quality check | Gemini vision (same models) |
| Data layer | **MongoDB Atlas via the official MCP server** (read + write) + JSON fallback |
| Text segmentation | TextTiling algorithm (deterministic; LLM only annotates) |
| PDF export | ReportLab (8.5 × 8.5″ square format) |
| Backend | FastAPI + uvicorn |
| Frontend | Next.js 15 + Tailwind CSS |
| Deployment | Cloud Run (single container) + Cloud Build CI + GCS volume for generated assets |

## API Surface (selected)

```
POST   /api/generate, /api/generate/upload, /api/fetch-url   # create a book
GET    /api/books, /api/books/preprocessed                   # library
GET    /api/book/{id}/preprocess/{chapters|characters|locations|progress}
PUT    /api/book/{id}/preprocess/characters/{name}           # edit character identity
PUT    /api/book/{id}/preprocess/scenes/{name}               # edit location profile
POST   /api/book/{id}/chapter/{ch}/generate                  # run the ADK pipeline
GET    /api/book/{id}/chapter/{ch}/{progress|agent-log|stale-pages|consistency}
POST   /api/book/{id}/segment/{seg}/{regenerate|quality|simplify|background|chat}
POST   /api/book/{id}/characters/{name}/{regenerate|quality} # sheets + auto QC
POST   /api/book/{id}/scenes/{name}/regenerate               # scene reference images
POST   /api/book/{id}/special/{page_type}/regenerate         # covers, chapter pages
```

## Project Structure

```
picture_book_generator/
├── src/
│   ├── app.py                  # FastAPI setup + router mounting
│   ├── config.py               # Models, backends, styles, BYOK gate
│   ├── gemini_backend.py       # Vertex-AI / API-key client factory (+ per-request BYOK)
│   ├── agents/                 # ★ ADK pipeline
│   │   ├── adk_pipeline.py     #   SequentialAgent + 4 BaseAgent stages
│   │   ├── analyzer.py / writer.py / artist.py / qa.py
│   │   └── agent_log.py        #   live activity log for the editor
│   ├── core/                   # db.py (MongoDB), mcp_client.py (MCP stdio), models
│   ├── preprocessing/          # 6-layer preprocess pipeline
│   ├── analysis/               # TextTiling segmentation, complexity scoring
│   ├── generation/             # illustration, character/scene sheets, QC, special pages
│   ├── extraction/             # text input parsing
│   ├── renderer/               # PDF export
│   └── routes/                 # books / editor / generation endpoints
├── scripts/                    # preprocess_book.py, generate_chapter.py (CLI)
├── frontend/src/               # Next.js app (editor, reader, library)
├── cloudbuild.yaml             # git push main → build + deploy to Cloud Run
└── data/                       # generated output (GCS volume in production)
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_BACKEND` | `vertex` | `vertex` (ADC / service account) or `api_key` (AI Studio) |
| `GCP_PROJECT` | `picture-book-gen` | GCP project for Vertex AI |
| `GCP_LOCATION` | `global` | Vertex location (Gemini 3 requires `global`) |
| `GEMINI_MODEL` | `gemini-3.5-flash` | Text/vision model |
| `GEMINI_IMAGE_MODEL` | `gemini-3.1-flash-image` | Image model |
| `GEMINI_API_KEY` | — | Only needed when `GEMINI_BACKEND=api_key` |
| `REQUIRE_USER_KEY` | `false` | When `true`, generation endpoints require the caller to bring their own Gemini key (BYOK) — public deployments can't bill the project key |
| `MONGODB_URI` / `MDB_MCP_CONNECTION_STRING` | — | MongoDB Atlas connection (driver fallback / MCP server) |
| `MONGODB_DB` | `picture_book_generator` | Database name |
| `APP_ENV` | `test` | `production` = Gemini for everything; `test` = cheaper third-party models for local iteration |

## Key Design Decisions

- **One real pipeline, agent-orchestrated** — the ADK `SequentialAgent` *is* the production path (no demo-only agent), running in-process because image generation is too heavy to ship to a remote agent runtime.
- **MongoDB MCP as the consistency hub** — character visual identity lives in one canonical place, read via MCP on every page generation.
- **LLM-first analysis, algorithmic segmentation** — LLM identifies characters/aliases/locations; TextTiling does the splitting (deterministic), LLM only annotates.
- **Preprocess once, generate many** — full-book analysis is cached (MongoDB + files); chapter generation loads from cache.
- **Every page gets art, QA gates it** — all segments are illustrated (no filtering); a 5-dimension vision check with self-correction keeps quality up.
- **BYOK-ready** — a per-request user API key (HTTP header) always beats the server key, so the public demo can run without billing the project.

---

## License

This project is **open source** under the **[GNU AGPL-3.0](LICENSE)**.

You are free to use, study, modify, and redistribute it, including running it
as a network service — provided derivative works and hosted modifications are
also published under AGPL-3.0. For commercial licensing outside the AGPL terms,
contact the author.

Built for the **Google Cloud Rapid Agent Hackathon 2026** (MongoDB track) with
Google ADK · Gemini 3 on Vertex AI · MongoDB MCP.
