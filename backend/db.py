from typing import List, Dict, Any, Optional
from config import supabase, SIMILARITY_THRESHOLD

def create_note(filename: str) -> Dict[str, Any]:
    """Insert a new note record with status 'processing'."""
    res = supabase.table("notes").insert({
        "filename": filename,
        "status": "processing"
    }).execute()
    if res.data and len(res.data) > 0:
        return res.data[0]
    raise RuntimeError("Failed to insert note into Supabase")

def update_note_status(note_id: str, status: str) -> None:
    """Update note status (processing, ready, error)."""
    supabase.table("notes").update({"status": status}).eq("id", note_id).execute()

def get_note(note_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve note metadata by id."""
    res = supabase.table("notes").select("*").eq("id", note_id).execute()
    return res.data[0] if res.data else None

def insert_chunks(chunks_data: List[Dict[str, Any]]) -> int:
    """
    Idempotent bulk insert into Supabase chunks table:
    Checks for existing note_id + chunk_index before inserting.
    Guarantees no duplicate chunks if an embedding worker crashes or restarts mid-batch.
    """
    if not chunks_data:
        return 0
    note_id = chunks_data[0].get("note_id")
    if not note_id:
        supabase.table("chunks").insert(chunks_data).execute()
        return len(chunks_data)

    existing = supabase.table("chunks").select("chunk_index").eq("note_id", note_id).execute().data or []
    existing_indices = {r["chunk_index"] for r in existing}

    new_chunks = [c for c in chunks_data if c.get("chunk_index") not in existing_indices]
    if new_chunks:
        supabase.table("chunks").insert(new_chunks).execute()
        return len(new_chunks)
    return 0

def get_chunks_for_note(note_id: str) -> List[Dict[str, Any]]:
    """Get all chunks for a note, ordered by chunk_index."""
    res = supabase.table("chunks").select("id, note_id, content, embedding, chunk_index").eq("note_id", note_id).order("chunk_index").execute()
    return res.data or []

def insert_event(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Append an event to the events log table."""
    res = supabase.table("events").insert({
        "event_type": event_type,
        "payload": payload
    }).execute()
    return res.data[0] if res.data else {}

def insert_topic(note_id: str, label: str, cluster_id: int) -> Dict[str, Any]:
    """Insert a topic cluster label."""
    res = supabase.table("topics").insert({
        "note_id": note_id,
        "label": label,
        "cluster_id": cluster_id
    }).execute()
    return res.data[0] if res.data else {}

def get_topics_for_note(note_id: str) -> List[Dict[str, Any]]:
    """Get topic cluster labels for a note."""
    res = supabase.table("topics").select("id, label, cluster_id").eq("note_id", note_id).execute()
    return res.data or []

def match_chunks_rpc(note_id: str, query_embedding: List[float], threshold: float = SIMILARITY_THRESHOLD, count: int = 3) -> List[Dict[str, Any]]:
    """Call match_chunks Supabase RPC function for cosine similarity search."""
    params = {
        "query_embedding": query_embedding,
        "match_threshold": threshold,
        "match_count": count,
        "filter_note_id": note_id
    }
    res = supabase.rpc("match_chunks", params).execute()
    return res.data or []

def match_chunks_multi(note_ids: List[str], query_embedding: List[float], threshold: float = SIMILARITY_THRESHOLD, count: int = 3) -> List[Dict[str, Any]]:
    """
    Search chunks across multiple note_ids, ranking all retrieved chunks
    by cosine similarity to support multi-document RAG queries.
    """
    if not note_ids:
        return []
    all_matches = []
    for nid in note_ids:
        try:
            matches = match_chunks_rpc(nid, query_embedding, threshold=0.0, count=count)
            all_matches.extend(matches)
        except Exception as e:
            print(f"Error matching chunks for note {nid}: {e}")
    # Sort descending by similarity
    all_matches.sort(key=lambda x: x.get("similarity", 0.0), reverse=True)
    return all_matches[:count]
