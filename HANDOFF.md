# Handoff Spec: Class Notes RAG Assistant

Build spec for an AI coding agent. Follow this order — each phase should be runnable before moving to the next.

## Stack
- Frontend: Next.js (React), single page, split layout (upload left / chat right)
- Backend: FastAPI
- DB + vectors: Supabase (Postgres + `pgvector` extension)
- LLM: Grok API (embeddings + chat generation + web search)
- Event bus: `asyncio.Queue`, in-process, background worker tasks started on FastAPI startup
- ML: `scikit-learn` KMeans over existing chunk embeddings (topic clustering)

## Environment variables needed
```
SUPABASE_URL=
SUPABASE_KEY=
GROK_API_KEY=
```

## Phase 1 — Data layer (Supabase)
Create tables:
```sql
create extension if not exists vector;

create table notes (
  id uuid primary key default gen_random_uuid(),
  filename text not null,
  status text default 'processing', -- processing | ready | error
  created_at timestamptz default now()
);

create table chunks (
  id uuid primary key default gen_random_uuid(),
  note_id uuid references notes(id),
  content text not null,
  embedding vector(1536), -- match embedding model dimension
  chunk_index int,
  created_at timestamptz default now()
);

create table events (
  id uuid primary key default gen_random_uuid(),
  event_type text not null,
  payload jsonb,
  created_at timestamptz default now()
);

create table topics (
  id uuid primary key default gen_random_uuid(),
  note_id uuid references notes(id),
  label text,
  cluster_id int,
  created_at timestamptz default now()
);
```

## Phase 2 — Backend skeleton (FastAPI)
Endpoints to implement, in this order:

1. `POST /upload` — accept PDF, save temp file, extract text (`pypdf`), insert `notes` row (status=processing), publish `note.uploaded` event to queue, return `{note_id, status: "processing"}` immediately (don't block on embedding).
2. `GET /notes/{id}/status` — poll endpoint, returns current status from `notes` table.
3. `POST /ask` — body `{note_id, query}`. Steps:
   - rewrite query via LLM (fix spelling/intent) before embedding
   - embed rewritten query
   - cosine similarity search against `chunks` where `note_id` matches, top-k=3
   - if top similarity score >= threshold (start at 0.75, tune by testing): generate answer grounded in retrieved chunks, `source: "notes"`
   - else: call Grok web search, generate answer from web results, `source: "web"`
   - return `{answer, source, citation}`
4. `POST /quiz` — body `{note_id, count: 3}`. Retrieve a spread of chunks across topic clusters for that note, prompt LLM to generate MCQs (4 options, correct answer index, one-line explanation each). Return structured JSON, not free text.

## Phase 3 — Background workers (event bus)
```python
event_queue = asyncio.Queue()

async def embedding_worker():
    while True:
        event = await event_queue.get()
        if event["type"] == "note.uploaded":
            # chunk text, call embeddings API per chunk, insert into `chunks`
            # update notes.status = 'ready' when done
            await log_event("embedding.completed", event["payload"])
        event_queue.task_done()

async def cluster_worker():
    while True:
        event = await event_queue.get_cluster_event()  # or filter same queue by type
        if event["type"] == "embedding.completed":
            # fetch all chunk embeddings for note_id, run KMeans (k=3-5),
            # label clusters via LLM (one short label per cluster), write to `topics`
        event_queue.task_done()

@app.on_event("startup")
async def startup():
    asyncio.create_task(embedding_worker())
    asyncio.create_task(cluster_worker())
```
Note: a single queue with type-filtering in each worker is simplest; splitting into two `asyncio.Queue` instances (one per event type) is cleaner if the agent prefers that.

## Phase 4 — Frontend (Next.js)
Single page, two panels:
- **Left (upload):** drag/drop zone, uploaded file list with status badge (Processing/Ready), "Generate Quiz" button (enabled once status=ready)
- **Right (chat):** message thread, input box fixed at bottom, each assistant message shows a small source tag ("from your notes" / "from web"), loading/thinking indicator between send and response
- **Quiz rendering:** inline in the chat panel as a distinct message type (question + 4 options as clickable cards), not a separate route/page
- **Empty state:** before upload, right panel shows placeholder text: "Upload your notes to start asking questions"

Styling direction: Apple-level minimal, typography-first. One sans-serif family (Inter or SF Pro), 2-3 font weights max, generous whitespace, hairline borders (no shadows/boxes), one accent color used only for send button and source tags, no icons beyond upload glyph + send arrow.

## Phase 5 — Demo script (for the live walkthrough)
1. Upload a real PDF of your own notes on screen
2. Show status going Processing → Ready
3. Ask a question that's answered from the notes — point out the citation tag
4. Ask a question NOT in the notes — show it falling back to web search, and say so explicitly
5. Click "Generate Quiz" — show it rendering inline
6. Open a terminal, show the `events` table / log proving each worker reacted independently to the upload event
7. Close with: "Each worker only knows about the event, not about each other — adding a fourth reaction (e.g. spaced-repetition scheduling) means zero changes to the upload endpoint."

## Explicit non-goals (say this if asked, don't build it)
- No auth / multi-user isolation
- No production deployment
- No supervised ML training — clustering is unsupervised and reuses existing RAG embeddings
- No multi-turn conversation memory
