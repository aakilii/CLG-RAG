import asyncio
from typing import Dict, Any
import db

# In-process decoupled event queues
upload_queue: asyncio.Queue = asyncio.Queue()
cluster_queue: asyncio.Queue = asyncio.Queue()

async def publish_event(event_type: str, payload: Dict[str, Any]) -> None:
    """
    Persist event to Supabase events table for audit trail,
    and route to appropriate worker queue.
    """
    try:
        # Write to Supabase events audit table
        db.insert_event(event_type, payload)
        print(f"[EventBus] Logged event to DB: {event_type} | payload: {payload}")
    except Exception as e:
        print(f"[EventBus] Error persisting event {event_type} to DB: {e}")

    # Dispatch to decoupled in-memory worker queues
    if event_type == "note.uploaded":
        await upload_queue.put({"type": event_type, "payload": payload})
    elif event_type == "embedding.completed":
        await cluster_queue.put({"type": event_type, "payload": payload})
