import asyncio
import os
import db
from event_bus import publish_event, upload_queue, cluster_queue
from workers import embedding_worker, cluster_worker

async def test_pipeline():
    pdf_path = os.path.abspath("../class-notes-rag-architecture.pdf")
    print(f"Testing with PDF: {pdf_path}")

    # 1. Create note in DB
    note = db.create_note("class-notes-rag-architecture.pdf")
    note_id = note["id"]
    print(f"1. Note created: {note_id}, status: {note['status']}")

    # 2. Start workers in background tasks
    task1 = asyncio.create_task(embedding_worker())
    task2 = asyncio.create_task(cluster_worker())

    # 3. Publish note.uploaded event
    await publish_event("note.uploaded", {
        "note_id": note_id,
        "file_path": pdf_path,
        "filename": "class-notes-rag-architecture.pdf"
    })

    # 4. Wait for processing to complete
    print("Waiting for upload_queue and cluster_queue to finish...")
    for _ in range(30):
        await asyncio.sleep(2)
        status_info = db.get_note(note_id)
        topics = db.get_topics_for_note(note_id)
        chunks = db.get_chunks_for_note(note_id)
        print(f"Polling: status={status_info['status']} | chunks={len(chunks)} | topics={len(topics)}")
        if status_info["status"] == "ready" and len(topics) > 0:
            print("Successfully processed note and topics!")
            break

    # 5. Print results
    final_note = db.get_note(note_id)
    final_chunks = db.get_chunks_for_note(note_id)
    final_topics = db.get_topics_for_note(note_id)

    print("\n--- Phase 2 Test Results ---")
    print(f"Note Status: {final_note['status']}")
    print(f"Total Chunks: {len(final_chunks)}")
    print(f"Detected Topics ({len(final_topics)}): {[t['label'] for t in final_topics]}")

    # Cancel background worker loops
    task1.cancel()
    task2.cancel()

if __name__ == "__main__":
    asyncio.run(test_pipeline())
