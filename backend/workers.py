import asyncio
import numpy as np
from sklearn.cluster import KMeans
from typing import Dict, Any, List

import db
import ai_service
import text_processor
from event_bus import upload_queue, cluster_queue, publish_event

async def embedding_worker():
    """
    Decoupled background worker that consumes note.uploaded events:
    1. Extracts PDF text
    2. Chunks text with page metadata
    3. Generates vector embeddings
    4. Inserts into Supabase chunks table
    5. Updates note status to 'ready'
    6. Publishes embedding.completed event
    """
    print("[Worker] embedding_worker started...")
    while True:
        try:
            event = await upload_queue.get()
            payload = event.get("payload", {})
            note_id = payload.get("note_id")
            file_path = payload.get("file_path")
            filename = payload.get("filename")

            print(f"[Worker] Processing upload for note_id: {note_id} ({filename})")

            # 1. Extract text
            pages = text_processor.extract_text_from_pdf(file_path)
            if not pages:
                print(f"[Worker] Warning: No text extracted from {filename}")
                db.update_note_status(note_id, "error")
                await publish_event("embedding.failed", {"note_id": note_id, "error": "No text extracted"})
                upload_queue.task_done()
                continue

            # 2. Semantic-aware Chunking (paragraph & heading boundaries first)
            chunks = text_processor.chunk_text(pages)
            print(f"[Worker] Extracted {len(pages)} pages into {len(chunks)} semantic chunks.")

            # 3. Generate embeddings in parallel (semaphore=10)
            sem = asyncio.Semaphore(10)
            async def embed_with_limit(text):
                async with sem:
                    return await ai_service.get_embedding(text)

            tasks = [embed_with_limit(item["content"]) for item in chunks]
            embeddings = await asyncio.gather(*tasks)

            chunks_to_insert = []
            for item, emb in zip(chunks, embeddings):
                chunks_to_insert.append({
                    "note_id": note_id,
                    "content": item["content"],
                    "embedding": emb,
                    "chunk_index": item["chunk_index"]
                })

            # 4. Idempotent Insert into Supabase (skips duplicates on crash/restart)
            inserted_count = db.insert_chunks(chunks_to_insert)
            print(f"[Worker] Inserted {inserted_count} new chunks into Supabase (total: {len(chunks_to_insert)}).")

            # 5. Update note status to 'ready'
            db.update_note_status(note_id, "ready")
            print(f"[Worker] Note {note_id} status updated to 'ready'.")

            # 6. Publish completion event
            await publish_event("embedding.completed", {
                "note_id": note_id,
                "chunk_count": len(chunks_to_insert)
            })

            upload_queue.task_done()
        except asyncio.CancelledError:
            print("[Worker] embedding_worker cancelled, exiting.")
            break
        except Exception as e:
            print(f"[Worker] Error in embedding_worker: {e}")
            if 'note_id' in locals() and note_id:
                db.update_note_status(note_id, "error")
                await publish_event("embedding.failed", {"note_id": note_id, "error": str(e)})
            upload_queue.task_done()

async def cluster_worker():
    """
    Decoupled background worker that consumes embedding.completed events:
    1. Fetches all chunk embeddings for note_id
    2. Runs unsupervised scikit-learn KMeans topic clustering
    3. Uses LLM to label each cluster
    4. Writes topic labels to Supabase topics table
    """
    print("[Worker] cluster_worker started...")
    while True:
        try:
            event = await cluster_queue.get()
            payload = event.get("payload", {})
            note_id = payload.get("note_id")

            print(f"[Worker] Running topic clustering for note_id: {note_id}")

            # 1. Fetch chunks
            chunks = db.get_chunks_for_note(note_id)
            if not chunks:
                print(f"[Worker] No chunks found for note {note_id}")
                cluster_queue.task_done()
                continue

            # If very few chunks, assign 1 general topic
            if len(chunks) < 3:
                label = ai_service.label_topic_cluster([c["content"] for c in chunks])
                db.insert_topic(note_id, label, 0)
                await publish_event("clustering.completed", {"note_id": note_id, "clusters": 1, "topics": [label]})
                cluster_queue.task_done()
                continue

            # 2. Extract embedding matrix
            embeddings_matrix = []
            for c in chunks:
                emb = c.get("embedding")
                if isinstance(emb, str):
                    import json
                    emb = json.loads(emb)
                embeddings_matrix.append(emb)

            X = np.array(embeddings_matrix)

            # Determine k (between 2 and 5)
            k = min(5, max(2, len(chunks) // 2))
            k = min(k, len(chunks))

            print(f"[Worker] Fitting KMeans with k={k} on {len(chunks)} chunk embeddings...")
            kmeans = KMeans(n_clusters=k, random_state=42, n_init='auto')
            cluster_assignments = kmeans.fit_predict(X)

            # 3. Label each cluster using LLM
            detected_topics = []
            for cluster_idx in range(k):
                cluster_chunks = [chunks[i]["content"] for i in range(len(chunks)) if cluster_assignments[i] == cluster_idx]
                if not cluster_chunks:
                    continue
                topic_label = ai_service.label_topic_cluster(cluster_chunks)
                db.insert_topic(note_id, topic_label, cluster_idx)
                detected_topics.append(topic_label)
                print(f"[Worker] Cluster {cluster_idx}: '{topic_label}' ({len(cluster_chunks)} chunks)")

            # 4. Log completion
            await publish_event("clustering.completed", {
                "note_id": note_id,
                "clusters": len(detected_topics),
                "topics": detected_topics
            })

            cluster_queue.task_done()
        except asyncio.CancelledError:
            print("[Worker] cluster_worker cancelled, exiting.")
            break
        except Exception as e:
            print(f"[Worker] Error in cluster_worker: {e}")
            cluster_queue.task_done()
