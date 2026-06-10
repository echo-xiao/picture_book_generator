# Picture Book Generator

Transform any book into a children's picture book with AI-powered analysis, illustration generation, and interactive editing.

**Google Cloud Rapid Agent Hackathon** | Deadline: 2026-06-11 | [Devpost](https://rapid-agent.devpost.com/)

## How It Works

```
Upload a book (.txt/.pdf/.epub)
    ↓
Preprocess: extract text → identify characters → segment into scenes → annotate
    ↓
Generate: simplify text → build prompts → generate illustrations → quality check
    ↓
Edit: interactive editor with AI chat → regenerate → auto quality check → auto fix
    ↓
Export: PDF picture book
```

## Quick Start

```bash
# 1. Install
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 2. Configure
cp .env.example .env
# Add GEMINI_API_KEY (required) and DEEPSEEK_API_KEY (optional, cheaper text tasks)

# 3. Start backend
python -m uvicorn src.app:app --port 8000

# 4. Start frontend (another terminal)
cd frontend && npm run dev

# 5. Open http://localhost:3000
```

## Features

### Interactive Editor (`/editor/{bookId}`)

| Area | Features |
|------|----------|
| **Illustration** | View current illustration, regenerate with progress spinner (30-60s) |
| **Versions** | Thumbnail carousel of current + all history versions, click to switch |
| **Prompt Editing** | Edit simplified text, scene background, characters & actions, summary, sentiment |
| **AI Chat** | Describe what you want in natural language → AI auto-fills prompt fields |
| **Quality Check** | 5-dimension auto scoring after each regeneration |
| **Auto Fix** | Score < 70% → AI automatically fixes prompts based on quality feedback |
| **Character Sheets** | Fuzzy-matched reference images, regenerate per character |
| **URL Persistence** | Chapter/segment position saved in URL across refreshes |
| **Auto Simplify** | Empty simplified text auto-generated when switching segments |

### Quality Check (5 Dimensions)

1. **Character Consistency** — Do characters match their reference sheets?
2. **Spelling** — Are embedded text words spelled correctly?
3. **Duplicate Characters** — Is any character drawn twice?
4. **Name-Face Mismatch** — Do name labels point to the right person?
5. **Character Count** — Are all expected characters present?

### Other Pages

- **Home** (`/`) — Upload books, browse library
- **Book Reader** (`/book/{bookId}`) — Full-screen page-flip reading with thumbnails

## Pipeline

### Phase 1: Preprocess (once per book)

```bash
python scripts/preprocess_book.py --input data/sample_books/a_tale_of_two_cities.txt
```

| Layer | What happens | Output |
|-------|-------------|--------|
| 1 | Extract text, split into chapters | `chapters.json`, `meta.json` |
| 2 | LLM identifies characters, aliases, gender, appearance | `llm_characters.json`, `alias_map.json` |
| 3 | Generate character reference sheets (Gemini Image) | `characters/*.png` |
| 4 | Replace aliases with canonical names in text | `cleaned_chapters.json` |
| 5 | TextTiling segmentation into scenes | `segments_raw.json` |
| 6 | LLM annotates each segment: characters, actions, background, sentiment | `analysis.json` |

### Phase 2: Generate (per chapter, on demand)

```bash
python scripts/generate_chapter.py --book A_TALE_OF_TWO_CITIES --chapter 0
```

| Step | What happens | Tool |
|------|-------------|------|
| 1 | Generate missing character sheets | Gemini Image |
| 2 | Simplify text for children | DeepSeek |
| 3 | Build illustration prompts (single scene enforced) | Template |
| 4 | Generate page illustrations with character sheet references | Gemini 2.5 Flash Image |
| 5 | Quality check each page (5 dimensions) | Gemini Vision |
| 6 | Generate special pages (covers, chapter pages) | Gemini Image |
| 7 | Export PDF (8.5 x 8.5" square format) | ReportLab |

## API Endpoints (27 total)

### Book Management (12)
```
GET    /api/health
POST   /api/generate                          # Create from text
POST   /api/generate/upload                   # Create from file
GET    /api/books                             # List all
GET    /api/books/preprocessed                # List preprocessed
GET    /api/book/{id}                         # Get details
DELETE /api/book/{id}                         # Delete
GET    /api/book/{id}/html                    # HTML version
GET    /api/book/{id}/pdf                     # PDF download
GET    /api/book/{id}/preprocess/progress     # Preprocess progress
GET    /api/book/{id}/preprocess/chapters     # Chapter list
GET    /api/book/{id}/preprocess/characters   # Character list + sheets
```

### Editor (8)
```
GET    /api/book/{id}/preprocess/chapter/{ch}/segments   # Segments
PUT    /api/book/{id}/segment/{seg}                      # Update fields
GET    /api/book/{id}/segment/{seg}/history               # Version history
POST   /api/book/{id}/segment/{seg}/simplify              # Generate simplified text
POST   /api/book/{id}/segment/{seg}/background            # Generate background
POST   /api/book/{id}/segment/{seg}/summarize             # Generate summary
POST   /api/book/{id}/segment/{seg}/chat                  # AI chat
```

### Generation & Quality (7)
```
POST   /api/book/{id}/segment/{seg}/regenerate            # Regenerate illustration
POST   /api/book/{id}/chapter/{ch}/generate               # Generate chapter
GET    /api/book/{id}/chapter/{ch}/progress                # Generation progress
GET    /api/book/{id}/segment/{seg}/quality                # Cached quality result
POST   /api/book/{id}/segment/{seg}/quality                # Run quality check
GET/POST /api/book/{id}/chapter/{ch}/consistency           # Chapter consistency
POST   /api/book/{id}/characters/{name}/regenerate         # Regenerate character sheet
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Text analysis & simplification | DeepSeek |
| Image generation | Gemini 2.5 Flash Image |
| Quality check | Gemini Vision |
| AI Chat assistant | DeepSeek |
| Text segmentation | TextTiling algorithm |
| PDF export | ReportLab |
| Backend | FastAPI + uvicorn |
| Frontend | Next.js 15 + Tailwind CSS |
| Database | MongoDB via official MCP server (read + write) + JSON fallback |
| Partner integration | MongoDB MCP server — Model Context Protocol (stdio) |
| Multi-agent pipeline | Analyzer → Writer → Artist → QA (fixed-order orchestration) |

## Project Structure

```
picture_book_generator/
├── src/                            # Python core library
│   ├── app.py                      # FastAPI setup + router mounting
│   ├── config.py                   # API keys, models, styles
│   ├── llm_client.py               # Unified LLM client (DeepSeek/Gemini)
│   │
│   ├── core/                       # Foundation utilities
│   │   ├── db.py                   # MongoDB data layer (5 collections)
│   │   ├── models.py               # Pydantic data models
│   │   ├── pipeline.py             # Book lifecycle + status management
│   │   ├── state_store.py          # Key-value state for agent
│   │   └── step_logger.py          # Pipeline step logging
│   │
│   ├── routes/                     # API endpoints (27 total)
│   │   ├── books.py                # Book management (12 endpoints)
│   │   ├── editor.py               # Editor & segments (8 endpoints)
│   │   ├── generation.py           # Generation & quality (7 endpoints)
│   │   └── helpers.py              # Shared JSON utilities
│   │
│   ├── agent/                      # AI agent layer
│   │   ├── orchestrator.py         # Gemini Function Calling agent
│   │   ├── mcp_server.py           # 17 MCP tools for agent
│   │   ├── gemini_client.py        # Gemini API wrapper
│   │   ├── text_simplifier.py      # LLM text rewriting for children
│   │   └── illustration_prompter.py # LLM prompt generation
│   │
│   ├── extraction/                 # Text extraction
│   │   ├── text_input.py           # TXT files
│   │   ├── pdf_parser.py           # PDF files
│   │   └── epub_parser.py          # EPUB files
│   │
│   ├── analysis/                   # Text analysis (NLP)
│   │   ├── chapter_split.py        # TextTiling segmentation
│   │   ├── complexity.py           # Reading level assessment
│   │   ├── key_events.py           # Key event extraction
│   │   └── visual_score.py         # Visual concreteness scoring
│   │
│   ├── generation/                 # Image generation
│   │   ├── image_utils.py          # Shared Gemini client + image loading
│   │   ├── illustration.py         # Page illustration generation
│   │   ├── character_sheet.py      # Character reference sheet generation
│   │   ├── gemini_consistency_check.py  # 5-dimension quality check
│   │   └── special_pages.py        # Covers, chapter pages, endings
│   │
│   ├── qa/                         # Quality assurance (agent tools)
│   │   ├── safety_check.py         # Content safety
│   │   ├── readability_check.py    # Reading level
│   │   ├── coverage_check.py       # Story coverage
│   │   └── hallucination_check.py  # Hallucination detection
│   │
│   └── renderer/
│       └── pdf_export.py           # PDF generation (8.5x8.5")
│
├── scripts/                        # CLI entry points
│   ├── preprocess_book.py          # 6-layer preprocess pipeline
│   └── generate_chapter.py         # Chapter generation + quality + PDF
│
├── frontend/src/                   # Next.js frontend
│   ├── app/
│   │   ├── page.tsx                # Home: upload + library
│   │   ├── editor/[bookId]/page.tsx # Interactive editor
│   │   └── book/[bookId]/page.tsx  # Book reader (page-flip)
│   ├── components/
│   │   ├── editor/                 # Editor sub-components
│   │   │   ├── IllustrationPanel.tsx
│   │   │   ├── QualityCheckPanel.tsx
│   │   │   ├── CharacterSheetsPanel.tsx
│   │   │   ├── AIChatPanel.tsx
│   │   │   └── VersionsCarousel.tsx
│   │   ├── BookLibrary.tsx
│   │   ├── UploadForm.tsx
│   │   └── GenerationProgress.tsx
│   ├── lib/api.ts                  # API client (27 endpoints)
│   └── types/index.ts              # TypeScript definitions
│
└── data/                           # Generated output (not in git)
    ├── sample_books/               # Input books (.txt)
    └── generated/{book_id}/
        ├── preprocess/             # 6 layers of cached analysis
        ├── characters/             # Character sheet images
        ├── chapters/ch{N}/
        │   ├── pages/              # Page illustrations
        │   ├── quality/            # Cached quality results
        │   └── history/            # Previous illustration versions
        ├── special/                # Cover + special page images
        └── book.pdf                # Final combined PDF
```

## Key Design Decisions

- **LLM-first analysis** — Character identification, alias resolution, scene annotation all done by LLM (DeepSeek). No spaCy dependency for character work.
- **TextTiling for segmentation** — Algorithmic segmentation is more stable/deterministic than LLM splitting. LLM only annotates, doesn't split.
- **Preprocess once, generate many** — Full book analysis runs once and caches to disk. Chapter generation loads from cache.
- **Single scene per page** — Prompt enforces one moment in time. No multi-panel layouts.
- **Style consistency** — When few character sheets match a scene, other sheets used as style references to prevent drift.
- **Auto-fix feedback loop** — Quality check → AI Chat → fix prompts → regenerate. Fully automated.
- **Dual LLM** — DeepSeek for text tasks (cheap), Gemini for image generation (hackathon requirement). Switchable via `TEXT_LLM` env var.
- **MongoDB MCP as data layer** — Reads (preprocess) and writes (character consistency hub) go through MongoDB's official MCP server. JSON files remain as a resilient fallback.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key (images + vision) |
| `DEEPSEEK_API_KEY` | No | DeepSeek API key (cheaper text tasks) |
| `TEXT_LLM` | No | `"deepseek"` (default) or `"gemini"` |
| `MONGODB_URI` | No | MongoDB connection string |
| `MONGODB_DB` | No | Database name (default: `picture_book_generator`) |

## MongoDB MCP Integration (MongoDB Partner Track)

This project integrates **MongoDB's official MCP server** (`mongodb-mcp-server`)
over the Model Context Protocol (stdio). The pipeline talks to MongoDB through
MCP for **both reads and writes** — not a direct driver — satisfying the
hackathon requirement to integrate a partner's MCP server.
(`src/core/mcp_client.py` implements the MCP stdio client; the server is
launched on demand via `npx mongodb-mcp-server`, configured by
`MDB_MCP_CONNECTION_STRING`.)

**Read path** — `AnalyzerAgent.load_preprocess()` loads all preprocess
documents through the MCP `find` tool, with a pymongo / local-file fallback
for resilience.

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

## MongoDB Collections

| Collection | Contents |
|------------|----------|
| `books` | Book metadata (title, chapters, status) |
| `characters` | Character profiles (name, aliases, gender, appearance, sheet path) |
| `segments` | All segments (text, characters, actions, background, sentiment) |
| `illustrations` | Generation records (segment, prompt, image path, version) |
| `generation_log` | LLM call logs (model, input/output, tokens, duration) |
