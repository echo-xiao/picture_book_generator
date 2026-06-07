# Picture Book Generator

Any book → children's picture book. LLM-powered analysis + AI illustrations + interactive editing + PDF output.

Google Cloud Rapid Agent Hackathon entry. Deadline: 2026-06-11.
Hackathon: https://rapid-agent.devpost.com/

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│              6-LAYER PREPROCESS (once per book)                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Layer 1: Extract Text → chapters                               │
│       ↓                                                         │
│  Layer 2: LLM Character ID → characters + aliases + gender      │
│       ↓                                                         │
│  Layer 3: Character Sheets (Gemini Image, on-demand per chapter)│
│       ↓                                                         │
│  Layer 4: Alias Replacement → cleaned text                      │
│       ↓                                                         │
│  Layer 5: TextTiling Segmentation (on cleaned text)             │
│       ↓                                                         │
│  Layer 6: LLM Annotation → characters_in_scene + actions +     │
│           scene_background + sentiment + key_events             │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│              GENERATE (per chapter, on demand)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Generate character sheets (reuse existing)                  │
│  2. LLM simplify text → children's language (DeepSeek)          │
│  3. Build illustration prompts (single scene enforcement)       │
│  4. Gemini Image → page illustrations (with style consistency)  │
│  5. Auto quality check (5 dimensions)                           │
│  6. Auto-fix loop (quality < 70% → AI fixes prompts)            │
│  7. PDF export                                                  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│              INTERACTIVE EDITOR (frontend)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  - View/edit each page: text, characters, actions, background   │
│  - AI Chat assistant for conversational prompt editing          │
│  - Regenerate single pages with progress spinner                │
│  - Auto quality check + auto-fix feedback loop                  │
│  - Version history with thumbnail carousel                      │
│  - Character sheet management with fuzzy matching               │
│  - PDF export                                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Features

### Frontend

#### Home Page (`/`)
- Upload books (TXT/PDF/EPUB)
- Browse book library
- Navigate to Editor or Book Reader

#### Book Reader (`/book/{bookId}`)
- Full-screen page-flip reading experience
- Keyboard navigation (arrow keys, space)
- Bottom thumbnail carousel for quick jumping
- Click any page to jump to Editor

#### Interactive Editor (`/editor/{bookId}`)

**Left Sidebar** — Chapter & segment navigation with character tags

**Col 1 — Illustration (40%)**
- Current illustration display with regenerate button
- Generation progress spinner with time estimate
- Original text display

**Col 2 — Prompt Editing (36%)**
- **Versions carousel**: Current + all history thumbnails, click to switch, highlighted selection
- **Simplified Text**: Editable, auto-generated when empty, manual "Generate" button
- **Scene Background**: Editable, auto/manual generation
- **Characters & Actions**: Add/remove/edit character-action pairs
- **Summary & Sentiment**: Editable summary + sentiment dropdown
- **AI Chat Assistant**: Conversational prompt editing — describe what you want, AI auto-fills fields. Collapsible panel.
- **Save / Save & Regen** buttons

**Col 3 — Quality & Reference (flex)**
- **Quality Check**: 5-dimension scoring (Character Match, Spelling, Duplicates, Name-Face Match, Character Count), per-character breakdown, detailed issues list, manual "Run" button
- **Character Sheets**: Fuzzy-matched character reference images with description, regenerate per character

**Automatic Behaviors**
- Switching segments auto-generates simplified text if empty
- Regenerate completion triggers auto quality check
- Quality score < 70% auto-sends feedback to AI Chat to fix prompts
- URL preserves chapter/segment position across refreshes (`?ch=4&seg=56`)

### Backend API

#### Book Management
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/generate` | POST | Create book from text |
| `/api/generate/upload` | POST | Create book from file upload |
| `/api/books` | GET | List all books |
| `/api/books/preprocessed` | GET | List preprocessed books |
| `/api/book/{id}` | GET | Get book details |
| `/api/book/{id}` | DELETE | Delete book |
| `/api/book/{id}/html` | GET | HTML version |
| `/api/book/{id}/pdf` | GET | PDF download |
| `/api/book/{id}/preprocess/progress` | GET | Preprocessing progress |

#### Editor & Segments
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/book/{id}/preprocess/chapters` | GET | Chapter list with segment counts |
| `/api/book/{id}/preprocess/characters` | GET | Character list + sheet URLs |
| `/api/book/{id}/preprocess/chapter/{ch}/segments` | GET | Segments for a chapter |
| `/api/book/{id}/segment/{seg}` | PUT | Update segment fields |
| `/api/book/{id}/segment/{seg}/history` | GET | Illustration version history |
| `/api/book/{id}/segment/{seg}/simplify` | POST | Generate simplified text |
| `/api/book/{id}/segment/{seg}/background` | POST | Generate scene background |
| `/api/book/{id}/segment/{seg}/summarize` | POST | Generate summary + sentiment |
| `/api/book/{id}/segment/{seg}/chat` | POST | AI chat for prompt editing |

#### Generation & Quality
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/book/{id}/segment/{seg}/regenerate` | POST | Regenerate illustration |
| `/api/book/{id}/chapter/{ch}/generate` | POST | Generate entire chapter |
| `/api/book/{id}/chapter/{ch}/progress` | GET | Chapter generation progress |
| `/api/book/{id}/segment/{seg}/quality` | GET | Get cached quality result |
| `/api/book/{id}/segment/{seg}/quality` | POST | Run quality check |
| `/api/book/{id}/chapter/{ch}/consistency` | GET/POST | Chapter consistency check |
| `/api/book/{id}/characters/{name}/regenerate` | POST | Regenerate character sheet |

### Pipeline

#### Phase 1: Preprocess (`scripts/preprocess_book.py`)
1. **Extract text** — TXT/PDF/EPUB → chapters
2. **LLM Character ID** — Identify characters, aliases, gender, appearance
3. **Character Sheets** — Gemini Image reference sheets (on-demand)
4. **Alias Replacement** — Normalize character names in text
5. **TextTiling Segmentation** — Split into scene segments
6. **LLM Annotation** — Per-segment: characters, actions, background, sentiment

#### Phase 2: Generate (`scripts/generate_chapter.py`)
1. **Character sheets** — Generate missing sheets
2. **Simplify text** — DeepSeek rewrites for children
3. **Build prompts** — Template with single-scene enforcement
4. **Generate illustrations** — Gemini 2.5 Flash Image with character sheet references + style fallback
5. **Quality check** — Gemini Vision 5-dimension scoring
6. **Special pages** — Covers, chapter pages, endings
7. **PDF export** — ReportLab 8.5x8.5" square format

#### Quality Check (5 Dimensions)
1. **Character Consistency** — Do characters match their reference sheets?
2. **Spelling** — Are embedded text words spelled correctly?
3. **Duplicate Characters** — Is any character drawn twice?
4. **Name-Face Mismatch** — Do name labels point to the right person?
5. **Character Count** — Are all expected characters present?

### Key Design Decisions

- **LLM-first analysis**: Character ID, aliases, annotation all by LLM. No spaCy dependency.
- **TextTiling for segmentation**: Algorithmic segmentation is more stable than LLM splitting.
- **Preprocess once, generate many**: Full analysis cached to disk, chapters generated on demand.
- **Single scene per page**: Prompt enforces one moment in time, no multi-panel layouts.
- **Fuzzy character matching**: Name parts (length > 3) match across sheets and scene characters.
- **Style consistency fallback**: When few character sheets match, others used as style references.
- **Auto-fix feedback loop**: Quality check → AI Chat → fix prompts → regenerate.
- **Dual LLM**: DeepSeek for text (cheap), Gemini for images (hackathon requirement).

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Text Analysis | DeepSeek (switchable to Gemini) |
| Text Segmentation | TextTiling algorithm |
| Text Simplification | DeepSeek |
| Image Generation | Gemini 2.5 Flash Image |
| Character Sheets | Gemini 2.5 Flash Image |
| Quality Check | Gemini Vision |
| AI Chat Assistant | DeepSeek |
| PDF Export | ReportLab |
| Data Storage | JSON files + MongoDB (optional) |
| Backend | FastAPI + uvicorn |
| Frontend | Next.js 15 + Tailwind CSS |
| Agent Orchestrator | Gemini Function Calling |

## Project Structure

```
src/
├── app.py                      # FastAPI app setup + router mounting
├── routes/
│   ├── books.py                # Book management endpoints (12)
│   ├── editor.py               # Editor/segment endpoints (8)
│   ├── generation.py           # Generation & quality endpoints (7)
│   └── helpers.py              # Shared utilities (_load_json, _save_json)
├── llm_client.py               # Unified LLM client (DeepSeek/Gemini)
├── config.py                   # Models, styles, API keys
├── analysis/
│   ├── chapter_split.py        # TextTiling segmentation
│   ├── character_extract.py    # spaCy NER character extraction
│   ├── character_persona.py    # Character persona analysis
│   ├── coreference.py          # Coreference utilities
│   ├── sentiment_curve.py      # Sentiment analysis
│   ├── key_events.py           # Key event detection
│   ├── complexity.py           # Text complexity analysis
│   └── visual_score.py         # Visual scoring
├── generation/
│   ├── character_sheet.py      # Character reference sheet generation
│   ├── illustration.py         # Page illustration generation
│   ├── gemini_consistency_check.py  # Gemini Vision quality check
│   ├── consistency_check.py    # CLIP-based consistency (optional)
│   └── special_pages.py        # Cover, chapter, ending pages
├── agent/
│   ├── gemini_client.py        # Gemini API wrapper
│   ├── text_simplifier.py      # LLM text rewriting
│   ├── illustration_prompter.py # Prompt generation
│   └── scene_selector.py       # NLP scene scoring
├── agent_orchestrator.py       # Gemini Function Calling agent
├── mcp_server.py               # 17 MCP tools for the agent
├── qa/                         # Quality assurance modules
├── renderer/
│   ├── pdf_export.py           # PDF generation
│   ├── layout_engine.py        # Page layout
│   └── text_overlay.py         # Text rendering
├── pipeline.py                 # MongoDB integration + status
├── models.py                   # Pydantic data models
├── db.py                       # Database utilities
├── state_store.py              # State management
└── step_logger.py              # Pipeline step logging

scripts/
├── preprocess_book.py          # 6-layer preprocess pipeline
├── generate_chapter.py         # Chapter generation + quality check + PDF
├── check_and_fix.py            # QA verification + regeneration
├── run_pipeline.py             # End-to-end pipeline runner
└── resolve_names.py            # Coreference resolution utility

frontend/src/
├── app/
│   ├── page.tsx                # Home: upload + library
│   ├── editor/[bookId]/page.tsx # Interactive page editor
│   └── book/[bookId]/page.tsx  # Book reader (page-flip)
├── components/
│   ├── BookLibrary.tsx         # Library listing
│   ├── UploadForm.tsx          # File upload
│   ├── GenerationProgress.tsx  # Progress tracking
│   └── editor/                 # Editor sub-components
├── lib/api.ts                  # API client (30+ endpoints)
└── types/index.ts              # TypeScript definitions
```

## Usage

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Set up environment
cp .env.example .env
# Edit .env: add GEMINI_API_KEY and optionally DEEPSEEK_API_KEY

# Start backend
python -m uvicorn src.app:app --port 8000

# Start frontend (in another terminal)
cd frontend && npm run dev

# Open http://localhost:3000
```

### CLI: Preprocess a book

```bash
python scripts/preprocess_book.py --input data/sample_books/a_tale_of_two_cities.txt
```

### CLI: Generate a chapter

```bash
# Generate chapter 0
python scripts/generate_chapter.py --book A_TALE_OF_TWO_CITIES --chapter 0

# Generate multiple chapters
python scripts/generate_chapter.py --book A_TALE_OF_TWO_CITIES --chapter 0,4

# Generate specific pages only
python scripts/generate_chapter.py --book A_TALE_OF_TWO_CITIES --chapter 4 --pages 1,2,3
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| GEMINI_API_KEY | (required) | Google Gemini API key |
| DEEPSEEK_API_KEY | (optional) | DeepSeek API key (cheaper text tasks) |
| TEXT_LLM | "deepseek" | Text LLM provider: "deepseek" or "gemini" |
| MONGODB_URI | mongodb://localhost:27017 | MongoDB connection string |

## Sample Books

- A Tale of Two Cities (Charles Dickens) — primary demo, 45 chapters
- The Great Gatsby (F. Scott Fitzgerald)
- Frankenstein (Mary Shelley)
- Pride and Prejudice (Jane Austen)
- Don Quixote (Cervantes)
- The Odyssey (Homer)
- The Prince (Machiavelli)
