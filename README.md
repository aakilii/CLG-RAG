# Class Notes RAG Assistant

A retrieval-augmented study assistant where students upload PDF class notes, query them with grounded semantic search and citations, fall back to live web search when notes don't cover the query, and generate topic-balanced multiple-choice quizzes.

---

## Architecture Overview

- **Frontend**: Next.js 16 (App Router, React 19) with Apple-minimal, typography-first styling (Inter font, hairline borders, clean layout).
- **Backend API**: FastAPI (`/upload`, `/notes/{id}/status`, `/ask`, `/quiz`, `/events`).
- **Database & Vectors**: Supabase (PostgreSQL + `pgvector` extension) storing `notes`, `chunks`, `events`, and `topics`.
- **Event Bus**: In-process `asyncio.Queue` decoupling upload from indexing.
- **Workers**:
  - `embedding_worker`: Extracts PDF pages, chunks text, generates embeddings, stores vectors in `chunks`, updates status to `ready`.
  - `cluster_worker`: Performs unsupervised `scikit-learn` KMeans clustering on chunk embeddings, labels clusters via LLM, and writes to `topics`.
- **LLM & Search**:
  - Groq (`qwen/qwen3.8-27b`) for instant query rewriting, grounded answering, and structured MCQ generation.
  - Gemini (`models/gemini-embedding-001`, 768 dims) for vector embeddings.
  - Live Web Search fallback when semantic similarity < 0.65 threshold.

---

## Quick Start

### 1. Launch Everything
Double click or run:
```bash
start_all.bat
```
Or run individually:
- **Backend**: `run_backend.bat` (runs on `http://127.0.0.1:8000`)
- **Frontend**: `run_frontend.bat` (runs on `http://localhost:3000`)

---

## Live Demo Script (Phase 5 Walkthrough)

1. **Upload Notes**: Drag and drop `class-notes-rag-architecture.pdf` into the upload zone.
2. **Real-time Status**: Observe the badge transition from `Processing...` (amber) to `Ready` (green) with detected topic tags displayed below the note.
3. **In-Notes Question**:
   - Query: *"What is the role of the event bus and asyncio.Queue?"*
   - Observe: Answer generated with the `"from your notes"` tag and chunk citations.
4. **Out-of-Domain Question (Web Fallback)**:
   - Query: *"What is the James Webb Space Telescope?"*
   - Observe: Similarity score drops below threshold, triggers live web search fallback with the `"from web"` tag, explicit disclosure note, and live citations.
5. **Interactive Inline Quiz**:
   - Click the **"Generate Quiz"** button.
   - Observe: 3 topic-balanced multiple-choice questions rendered inline in chat as clickable cards. Clicking reveals immediate feedback (green for correct, red for incorrect) and a 1-line explanation.
6. **Audit Log Inspection**:
   - Visit `http://127.0.0.1:8000/events` to inspect the decoupled event logs proving each worker reacted independently.
