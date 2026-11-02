import os
import shutil
import asyncio
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import db
import ai_service
import web_search
from event_bus import publish_event
from workers import embedding_worker, cluster_worker
from config import SIMILARITY_THRESHOLD

# Lifespan context manager to manage background worker tasks
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start decoupled in-process workers on app startup
    task_embedding = asyncio.create_task(embedding_worker())
    task_cluster = asyncio.create_task(cluster_worker())
    print("[Startup] Decoupled background workers launched.")

    # Self-healing: resume any pending processing notes across reloads
    try:
        pending = db.supabase.table("notes").select("*").eq("status", "processing").execute().data
        for p in pending:
            fpath = os.path.join(TEMP_DIR, p["filename"])
            if os.path.exists(fpath):
                print(f"[Startup] Resuming processing for pending note: {p['id']} ({p['filename']})")
                await publish_event("note.uploaded", {
                    "note_id": p["id"],
                    "file_path": fpath,
                    "filename": p["filename"]
                })
    except Exception as e:
        print(f"[Startup] Note check error: {e}")

    yield
    # Cleanup on shutdown
    task_embedding.cancel()
    task_cluster.cancel()
    print("[Shutdown] Workers cancelled.")

app = FastAPI(
    title="Class Notes RAG Assistant API",
    description="FastAPI backend for PDF class notes retrieval, topic clustering, and quiz generation.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_uploads")
os.makedirs(TEMP_DIR, exist_ok=True)

import project_manager
from fastapi import Form

# ----------------- Request / Response Models -----------------

class AskRequest(BaseModel):
    project_id: Optional[str] = None
    note_id: Optional[str] = None
    note_ids: Optional[List[str]] = None
    query: str

class ExcerptItem(BaseModel):
    doc_name: str
    chunk_index: int
    content: str
    similarity: float

class AskResponse(BaseModel):
    answer: str
    source: str
    citation: str
    rewritten_query: str
    similarity: float
    excerpts: Optional[List[ExcerptItem]] = None

class QuizRequest(BaseModel):
    project_id: Optional[str] = None
    note_id: Optional[str] = None
    note_ids: Optional[List[str]] = None
    count: Optional[int] = 3

class FlashcardsRequest(BaseModel):
    project_id: Optional[str] = None
    note_id: Optional[str] = None
    note_ids: Optional[List[str]] = None
    count: Optional[int] = 4

class FlashcardItem(BaseModel):
    key_term: str
    front: str
    back: str
    doc_name: Optional[str] = None

class FlashcardsResponse(BaseModel):
    flashcards: List[FlashcardItem]

class CreateProjectRequest(BaseModel):
    name: str

class MCQOption(BaseModel):
    question: str
    options: List[str]
    correct_index: int
    explanation: str

class QuizResponse(BaseModel):
    note_id: str
    quiz: List[MCQOption]

# ----------------- Endpoints -----------------

@app.get("/")
def health_check():
    return {"status": "ok", "app": "Class Notes RAG Assistant"}

@app.get("/projects")
def get_all_projects():
    """List all projects with full document metadata."""
    projects = project_manager.list_projects()
    all_notes = db.supabase.table("notes").select("*").execute().data or []
    all_topics = db.supabase.table("topics").select("*").execute().data or []
    topics_by_note = {}
    for t in all_topics:
        nid = t.get("note_id")
        topics_by_note.setdefault(nid, []).append(t.get("label"))

    notes_by_id = {}
    for n in all_notes:
        nid = n["id"]
        notes_by_id[nid] = {**n, "topics": topics_by_note.get(nid, [])}

    enriched = []
    for p in projects:
        doc_details = [notes_by_id[did] for did in p.get("doc_ids", []) if did in notes_by_id]
        enriched.append({
            **p,
            "documents": doc_details,
            "doc_count": len(doc_details)
        })
    return enriched

@app.post("/projects")
def create_project_endpoint(req: CreateProjectRequest):
    """Create a new project (e.g. Project 1, Project 2, Project 3)."""
    return project_manager.create_project(req.name)

@app.delete("/projects/{project_id}")
def delete_project_endpoint(project_id: str):
    """
    Deletes a project workspace.
    NOTE: All documents and vector embeddings in Supabase permanently remain intact!
    """
    success = project_manager.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "project_deleted", "project_id": project_id, "knowledge_permanently_preserved": True}

@app.delete("/projects/{project_id}/docs/{note_id}")
def remove_doc_from_project_endpoint(project_id: str, note_id: str):
    """
    Removes document from this project workspace.
    PERMANENT STORAGE: The document and its vector embeddings are strictly
    preserved in the database so the knowledge base benefits other sessions.
    """
    removed = project_manager.remove_doc_from_project(project_id, note_id)
    return {
        "status": "removed_from_project",
        "permanently_preserved_in_db": True,
        "note_id": note_id
    }

@app.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_pdf(file: UploadFile = File(...), project_id: Optional[str] = Form(None)):
    """
    Accepts PDF, saves temporarily, creates note record with status 'processing',
    links to project, and permanently indexes into Supabase pgvector.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Save to disk temporarily
    file_path = os.path.join(TEMP_DIR, f"{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 1. Insert notes row (permanently stored in DB)
    note = db.create_note(filename=file.filename)
    note_id = note["id"]

    # 2. Attach to designated project
    if project_id:
        project_manager.add_doc_to_project(project_id, note_id)
    else:
        # Default: attach to first project
        projs = project_manager.list_projects()
        if projs:
            project_manager.add_doc_to_project(projs[0]["id"], note_id)

    # 3. Publish event to decoupled queue
    await publish_event("note.uploaded", {
        "note_id": note_id,
        "file_path": file_path,
        "filename": file.filename
    })

    return {
        "note_id": note_id,
        "filename": file.filename,
        "status": "processing",
        "project_id": project_id
    }

@app.get("/notes")
def list_notes():
    """List all uploaded notes with status and creation timestamps."""
    res = db.supabase.table("notes").select("*").order("created_at", desc=True).execute()
    return res.data or []

@app.delete("/notes/{note_id}")
def delete_note(note_id: str):
    """
    Remove note from active projects while strictly preserving
    all chunks, vector embeddings, and topics in Supabase permanently.
    """
    projects = project_manager.list_projects()
    for p in projects:
        project_manager.remove_doc_from_project(p["id"], note_id)
    return {
        "status": "removed_from_active_view",
        "permanently_preserved_in_db": True,
        "note_id": note_id
    }

@app.delete("/notes")
def clear_all_notes():
    """
    Clears document linkages from projects while permanently
    preserving records and vector embeddings in Supabase.
    """
    projects = project_manager.list_projects()
    for p in projects:
        p["doc_ids"] = []
    project_manager._save_projects_data(projects)
    return {"status": "cleared_from_active_projects", "permanently_preserved_in_db": True}

@app.get("/notes/{note_id}/status")
def get_note_status(note_id: str):
    """
    Poll endpoint returning current note status, chunk count, and detected topic clusters.
    """
    note = db.get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    topics = db.get_topics_for_note(note_id)
    chunks = db.supabase.table("chunks").select("id", count="exact").eq("note_id", note_id).execute()

    return {
        "id": note["id"],
        "filename": note["filename"],
        "status": note["status"],
        "created_at": note.get("created_at"),
        "chunk_count": chunks.count or 0,
        "topics": [t["label"] for t in topics]
    }

@app.post("/ask", response_model=AskResponse)
async def ask_question(req: AskRequest):
    """
    Multi-Document RAG Query Endpoint:
    Queries across one or all active uploaded documents in the session.
    """
    # 1. Resolve target document IDs
    if req.note_ids and len(req.note_ids) > 0:
        target_ids = req.note_ids
    elif req.note_id:
        target_ids = [req.note_id]
    elif req.project_id:
        proj = project_manager.get_project(req.project_id)
        target_ids = proj.get("doc_ids", []) if proj else []
    else:
        ready_notes = db.supabase.table("notes").select("id, filename").eq("status", "ready").execute().data or []
        target_ids = [n["id"] for n in ready_notes]

    if not target_ids:
        return AskResponse(
            answer="This project doesn't have any uploaded documents yet. Upload your PDF notes above to start asking questions!",
            source="notes",
            citation="No documents in project",
            rewritten_query=req.query,
            similarity=0.0
        )

    # Map note_id to filename for multi-doc citations
    notes_meta = db.supabase.table("notes").select("id, filename").in_("id", target_ids).execute().data or []
    filename_map = {n["id"]: n["filename"] for n in notes_meta}
    doc_names = list(filename_map.values())

    raw_lower = req.query.strip().lower()

    # Friendly greeting handler
    greetings = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening", "howdy", "sup", "yo"}
    if raw_lower in greetings or raw_lower.rstrip("!?.") in greetings:
        all_topics = []
        for nid in target_ids:
            all_topics.extend([t["label"] for t in db.get_topics_for_note(nid)])
        all_topics = list(dict.fromkeys(all_topics)) # deduplicate
        topic_str = ", ".join(all_topics[:6]) if all_topics else "uploaded course material"
        doc_count_str = f"{len(target_ids)} documents" if len(target_ids) > 1 else f"'{doc_names[0]}'"

        return AskResponse(
            answer=(
                f"Hello! I'm your Study Assistant. Your active study library includes **{doc_count_str}**, "
                f"covering topics such as: **{topic_str}**.\n\n"
                "Ask me anything across your notes, or click **'Generate Quiz'** to test yourself!"
            ),
            source="notes",
            citation=f"Active Documents: {', '.join(doc_names)}",
            rewritten_query=req.query,
            similarity=1.0
        )

    # Meta-queries about document status / library content
    meta_phrases = [
        "is there anything in ur data",
        "is there anything in your data",
        "what is in your data",
        "what do you have",
        "what are the topics",
        "what is this document",
        "what is this about",
        "summarize my notes",
        "summarize the notes",
        "what can you do"
    ]
    if any(p in raw_lower for p in meta_phrases):
        all_topics = []
        total_chunks = 0
        doc_summaries = []
        for nid in target_ids:
            fname = filename_map.get(nid, "Document")
            chunks = db.get_chunks_for_note(nid)
            topics = db.get_topics_for_note(nid)
            total_chunks += len(chunks)
            all_topics.extend([t["label"] for t in topics])
            doc_summaries.append(f"• **{fname}** ({len(chunks)} sections)")

        all_topics = list(dict.fromkeys(all_topics))
        topic_bullets = "\n".join([f"  - {t}" for t in all_topics]) if all_topics else "  - General Overview"
        docs_list = "\n".join(doc_summaries)

        return AskResponse(
            answer=(
                f"Your study workspace has **{len(target_ids)} document(s)** indexed with a total of **{total_chunks} sections**:\n\n"
                f"{docs_list}\n\n"
                f"**Key Topics Covered:**\n{topic_bullets}\n\n"
                "You can ask any question grounded across all your notes, or click **'Generate Quiz'** to practice!"
            ),
            source="notes",
            citation=f"Indexed: {', '.join(doc_names)} ({total_chunks} sections)",
            rewritten_query=req.query,
            similarity=1.0
        )

    # Guard: check if any chunks are indexed across target documents
    total_existing_chunks = 0
    for tid in target_ids:
        c_count = db.supabase.table("chunks").select("id", count="exact").eq("note_id", tid).execute().count or 0
        total_existing_chunks += c_count

    if total_existing_chunks == 0:
        return AskResponse(
            answer="Your documents are still being processed and indexed into vector memory. Please wait a few moments and try your question again.",
            source="notes",
            citation="Indexing in progress",
            rewritten_query=req.query,
            similarity=0.0
        )

    # Step 1: Query rewrite via Groq
    rewritten_query = ai_service.rewrite_query(req.query)

    # Step 2: Embed rewritten query
    query_emb = await ai_service.get_embedding(rewritten_query)

    # Step 3: Cosine similarity search across all target documents
    matched_chunks = db.match_chunks_multi(
        note_ids=target_ids,
        query_embedding=query_emb,
        threshold=0.0,
        count=4
    )

    # Attach document filename to each chunk for accurate multi-doc citation
    for c in matched_chunks:
        c["doc_name"] = filename_map.get(c.get("note_id"), "Notes")

    top_similarity = matched_chunks[0]["similarity"] if matched_chunks else 0.0

    # --- Server-Side Retrieval Logging (Debuggable from logs, not vibes) ---
    chunk_score_logs = [
        f"[chunk={c.get('chunk_index')} doc='{c.get('doc_name')}' score={c.get('similarity', 0.0):.4f}]"
        for c in matched_chunks
    ]
    print(
        f"[RAG Retrieval Log] query='{req.query}' | rewritten='{rewritten_query}' | "
        f"target_docs={len(target_ids)} | top_score={top_similarity:.4f} | "
        f"threshold={SIMILARITY_THRESHOLD} | chunks={', '.join(chunk_score_logs) if chunk_score_logs else 'none'}"
    )

    # Step 4: Router decision
    if matched_chunks and top_similarity >= SIMILARITY_THRESHOLD:
        print(f"[RAG Router] DECISION: GROUNDED_NOTES (top_score {top_similarity:.4f} >= threshold {SIMILARITY_THRESHOLD})")
        res = ai_service.generate_grounded_answer(req.query, matched_chunks)
        excerpts = [
            ExcerptItem(
                doc_name=c.get("doc_name", "Notes"),
                chunk_index=c.get("chunk_index", 0),
                content=c.get("content", ""),
                similarity=float(c.get("similarity", 0.0))
            )
            for c in matched_chunks
        ]
        return AskResponse(
            answer=res["answer"],
            source="notes",
            citation=res["citation"],
            rewritten_query=rewritten_query,
            similarity=float(top_similarity),
            excerpts=excerpts
        )
    else:
        # LOW CONFIDENCE IN NOTES
        print(f"[RAG Router] DECISION: LOW_CONFIDENCE_IN_NOTES (top_score {top_similarity:.4f} < threshold {SIMILARITY_THRESHOLD})")

        search_results = []
        try:
            search_results = web_search.search_web(rewritten_query, max_results=3)
        except Exception as search_err:
            print(f"[RAG Fallback Error] Reference search failed/timed out: {search_err}")
            search_results = []

        if not search_results:
            # Genuine low-confidence answer path & graceful fallback failure state
            print("[RAG Router] DECISION: LOW_CONFIDENCE_SYSTEM_STATE (No notes match and no reference fallback available)")
            return AskResponse(
                answer=(
                    f"I'm not confident this topic is covered in your active notes. "
                    f"The highest similarity section scored below the confidence threshold ({top_similarity:.2f} < {SIMILARITY_THRESHOLD}).\n\n"
                    "To get an accurate answer, consider uploading notes that cover this subject or rephrasing your question with specific terms from your course material."
                ),
                source="notes",
                citation=f"Low confidence (score: {top_similarity:.2f})",
                rewritten_query=rewritten_query,
                similarity=float(top_similarity)
            )

        res = ai_service.generate_web_answer(req.query, search_results)
        return AskResponse(
            answer=res["answer"],
            source="reference",
            citation=res["citation"],
            rewritten_query=rewritten_query,
            similarity=float(top_similarity)
        )

@app.post("/quiz", response_model=QuizResponse)
async def generate_quiz(req: QuizRequest):
    """
    Multi-Document Quiz Generation:
    Retrieves chunks across all active documents in the library and generates
    balanced MCQs testing knowledge across the student's materials.
    """
    if req.note_ids and len(req.note_ids) > 0:
        target_ids = req.note_ids
    elif req.note_id:
        target_ids = [req.note_id]
    elif req.project_id:
        proj = project_manager.get_project(req.project_id)
        target_ids = proj.get("doc_ids", []) if proj else []
    else:
        ready_notes = db.supabase.table("notes").select("id").eq("status", "ready").execute().data or []
        target_ids = [n["id"] for n in ready_notes]

    if not target_ids:
        raise HTTPException(status_code=400, detail="This project has no documents available for quiz generation. Please upload notes first.")

    all_chunks = []
    for nid in target_ids:
        chunks = db.get_chunks_for_note(nid)
        all_chunks.extend(chunks)

    if not all_chunks:
        raise HTTPException(status_code=400, detail="No chunks found across selected notes.")

    # Spread selection across chunks
    count = req.count or 3
    step = max(1, len(all_chunks) // min(8, len(all_chunks)))
    selected_chunks = all_chunks[::step][:8]

    # Generate structured MCQs
    quiz_items = ai_service.generate_mcq_quiz(selected_chunks, count=count)

    formatted_quiz = []
    for item in quiz_items:
        formatted_quiz.append(MCQOption(
            question=item.get("question", "Question"),
            options=item.get("options", ["A", "B", "C", "D"]),
            correct_index=int(item.get("correct_index", 0)),
            explanation=item.get("explanation", "")
        ))

    return QuizResponse(
        note_id=target_ids[0] if target_ids else "",
        quiz=formatted_quiz
    )

@app.post("/flashcards", response_model=FlashcardsResponse)
async def generate_flashcards_endpoint(req: FlashcardsRequest):
    """
    Generate high-yield Active Recall flashcards across active project documents.
    """
    if req.note_ids and len(req.note_ids) > 0:
        target_ids = req.note_ids
    elif req.note_id:
        target_ids = [req.note_id]
    elif req.project_id:
        proj = project_manager.get_project(req.project_id)
        target_ids = proj.get("doc_ids", []) if proj else []
    else:
        ready_notes = db.supabase.table("notes").select("id").eq("status", "ready").execute().data or []
        target_ids = [n["id"] for n in ready_notes]

    if not target_ids:
        raise HTTPException(status_code=400, detail="This project has no documents available for flashcards. Please upload notes first.")

    all_chunks = []
    notes_meta = db.supabase.table("notes").select("id, filename").in_("id", target_ids).execute().data or []
    filename_map = {n["id"]: n["filename"] for n in notes_meta}

    for nid in target_ids:
        chunks = db.get_chunks_for_note(nid)
        for c in chunks:
            c["doc_name"] = filename_map.get(nid, "Notes")
        all_chunks.extend(chunks)

    if not all_chunks:
        raise HTTPException(status_code=400, detail="No chunks found across selected notes.")

    count = req.count or 4
    step = max(1, len(all_chunks) // min(8, len(all_chunks)))
    selected_chunks = all_chunks[::step][:8]

    cards_data = ai_service.generate_flashcards(selected_chunks, count=count)
    cards = [
        FlashcardItem(
            key_term=c.get("key_term", "Concept"),
            front=c.get("front", "Question"),
            back=c.get("back", "Answer"),
            doc_name=c.get("doc_name", filename_map.get(target_ids[0], "Notes"))
        )
        for c in cards_data
    ]
    return FlashcardsResponse(flashcards=cards)

@app.get("/events")
def get_events_log():
    """Returns recent events from the events audit table for demonstration."""
    res = db.supabase.table("events").select("*").order("created_at", desc=True).limit(20).execute()
    return res.data or []
