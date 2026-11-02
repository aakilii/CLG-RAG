import os
import sys
import asyncio
import numpy as np
from sklearn.cluster import KMeans

# Set up paths
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

import db
import ai_service
import text_processor

NOTE_ID = "bb79e675-d9a7-490e-bb2d-bad755905102"
PDF_PATH = os.path.abspath(os.path.join(backend_dir, "..", "machine-learning-and-deep-learning-notes.pdf"))

async def reindex():
    print(f"Re-indexing {PDF_PATH} for note {NOTE_ID}...")
    
    # 1. Extract text
    pages = text_processor.extract_text_from_pdf(PDF_PATH)
    print(f"Extracted {len(pages)} pages.")
    
    # 2. Chunk text
    chunks = text_processor.chunk_text(pages)
    print(f"Generated {len(chunks)} semantic chunks.")
    
    # 3. Clean old chunks for this note to ensure fresh indexed knowledge
    db.supabase.table("chunks").delete().eq("note_id", NOTE_ID).execute()
    db.supabase.table("topics").delete().eq("note_id", NOTE_ID).execute()
    print("Cleared existing chunks and topics for clean refresh.")
    
    # 4. Generate embeddings in parallel
    sem = asyncio.Semaphore(8)
    async def embed_item(item):
        async with sem:
            emb = await ai_service.get_embedding(item["content"])
            return {
                "note_id": NOTE_ID,
                "content": item["content"],
                "embedding": emb,
                "chunk_index": item["chunk_index"]
            }
            
    tasks = [embed_item(c) for c in chunks]
    chunks_to_insert = await asyncio.gather(*tasks)
    
    # 5. Insert chunks
    inserted = db.insert_chunks(chunks_to_insert)
    print(f"Inserted {inserted} chunks into Supabase.")
    
    # 6. Run Unsupervised Topic Clustering
    embeddings_matrix = [c["embedding"] for c in chunks_to_insert]
    X = np.array(embeddings_matrix)
    k = 5
    kmeans = KMeans(n_clusters=k, random_state=42, n_init='auto')
    labels = kmeans.fit_predict(X)
    
    for cluster_id in range(k):
        cluster_texts = [
            chunks_to_insert[i]["content"]
            for i, c_id in enumerate(labels)
            if c_id == cluster_id
        ]
        topic_name = ai_service.label_topic_cluster(cluster_texts)
        db.insert_topic(NOTE_ID, topic_name, cluster_id)
        print(f"Clustered Topic {cluster_id + 1}: {topic_name}")
        
    db.update_note_status(NOTE_ID, "ready")
    print("Re-indexing completed successfully!")

if __name__ == "__main__":
    asyncio.run(reindex())
