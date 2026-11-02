import asyncio
import sys
import os
import numpy as np

# Ensure backend modules can be imported
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

import db
import ai_service
from config import SIMILARITY_THRESHOLD

EVAL_BENCHMARK = [
    {
        "id": "EVAL-01",
        "query": "What is the difference between supervised and unsupervised learning?",
        "target_doc": "machine-learning-and-deep-learning-notes.pdf",
        "expected_keywords": ["labeled", "unlabeled", "clustering", "classification"],
        "is_in_domain": True
    },
    {
        "id": "EVAL-02",
        "query": "How does backpropagation compute gradients for neural network weight updates?",
        "target_doc": "machine-learning-and-deep-learning-notes.pdf",
        "expected_keywords": ["chain rule", "gradient", "weights", "loss"],
        "is_in_domain": True
    },
    {
        "id": "EVAL-03",
        "query": "Explain the bias-variance tradeoff and underfitting versus overfitting",
        "target_doc": "machine-learning-and-deep-learning-notes.pdf",
        "expected_keywords": ["bias", "variance", "overfitting", "underfitting"],
        "is_in_domain": True
    },
    {
        "id": "EVAL-04",
        "query": "What is the Global Interpreter Lock (GIL) and why does Python use it?",
        "target_doc": "computer-science-and-programming-fundamentals.pdf",
        "expected_keywords": ["gil", "mutex", "thread", "interpreter"],
        "is_in_domain": True
    },
    {
        "id": "EVAL-05",
        "query": "How does RAII and std::unique_ptr manage heap memory in modern C++?",
        "target_doc": "computer-science-and-programming-fundamentals.pdf",
        "expected_keywords": ["raii", "unique_ptr", "destructor", "smart pointer"],
        "is_in_domain": True
    },
    {
        "id": "EVAL-06",
        "query": "Explain the JVM runtime data areas including Heap and Metaspace",
        "target_doc": "computer-science-and-programming-fundamentals.pdf",
        "expected_keywords": ["jvm", "heap", "metaspace", "stack"],
        "is_in_domain": True
    },
    {
        "id": "EVAL-07",
        "query": "How does the JavaScript event loop prioritize the microtask queue over macrotasks?",
        "target_doc": "computer-science-and-programming-fundamentals.pdf",
        "expected_keywords": ["microtask", "call stack", "event loop", "promise"],
        "is_in_domain": True
    },
    {
        "id": "EVAL-08",
        "query": "What are the 4 Coffman conditions required for an operating system deadlock?",
        "target_doc": "computer-science-and-programming-fundamentals.pdf",
        "expected_keywords": ["coffman", "mutual exclusion", "hold and wait", "circular wait"],
        "is_in_domain": True
    },
    {
        "id": "EVAL-09",
        "query": "How does the TCP 3-way handshake establish a reliable connection?",
        "target_doc": "computer-science-and-programming-fundamentals.pdf",
        "expected_keywords": ["syn", "ack", "handshake", "connection"],
        "is_in_domain": True
    },
    {
        "id": "EVAL-10",
        "query": "Who won the FIFA World Cup soccer championship in 1998 in Paris?",
        "target_doc": None,
        "expected_keywords": [],
        "is_in_domain": False  # Negative control test
    }
]

async def run_evaluation():
    print("=" * 80)
    print("  RAG RETRIEVAL & THRESHOLD EVALUATION BENCHMARK")
    print(f"  Target Threshold: {SIMILARITY_THRESHOLD:.2f} | Eval Cases: {len(EVAL_BENCHMARK)}")
    print("=" * 80)

    # Fetch notes in DB
    all_notes = db.supabase.table("notes").select("id, filename").execute().data or []
    note_ids = [n["id"] for n in all_notes]
    filename_map = {n["id"]: n["filename"] for n in all_notes}

    if not note_ids:
        print("[ERROR] No notes indexed in database. Run seed_cs_memory.py first.")
        return

    in_domain_scores = []
    out_of_domain_scores = []
    correct_retrievals = 0
    total_in_domain = sum(1 for item in EVAL_BENCHMARK if item["is_in_domain"])

    print(f"{'ID':<8} | {'Type':<12} | {'Top Score':<10} | {'Decision':<14} | {'Status':<8} | {'Query'}")
    print("-" * 80)

    for item in EVAL_BENCHMARK:
        qid = item["id"]
        raw_query = item["query"]
        is_in_domain = item["is_in_domain"]

        # Step 1: Rewrite query
        rewritten = ai_service.rewrite_query(raw_query)

        # Step 2: Embed query
        emb = await ai_service.get_embedding(rewritten)

        # Step 3: Vector retrieval across notes
        matches = db.match_chunks_multi(note_ids=note_ids, query_embedding=emb, threshold=0.0, count=3)

        top_score = matches[0]["similarity"] if matches else 0.0
        top_content = (matches[0]["content"] if matches else "").lower()

        if is_in_domain:
            in_domain_scores.append(top_score)
            # Evaluate hit: score >= threshold AND at least one expected keyword present
            has_keywords = any(kw.lower() in top_content for kw in item["expected_keywords"])
            above_threshold = top_score >= SIMILARITY_THRESHOLD
            passed = above_threshold and has_keywords
            if passed:
                correct_retrievals += 1

            status_str = "PASS" if passed else "FAIL"
            decision_str = "GROUNDED" if above_threshold else "LOW_CONF"
            print(f"{qid:<8} | {'In-Domain':<12} | {top_score:<10.4f} | {decision_str:<14} | {status_str:<8} | {raw_query[:35]}...")
        else:
            out_of_domain_scores.append(top_score)
            # Negative control: must be BELOW threshold
            passed = top_score < SIMILARITY_THRESHOLD
            status_str = "PASS" if passed else "FALSE_POS"
            decision_str = "REJECTED" if passed else "FALSE_GROUND"
            print(f"{qid:<8} | {'Negative':<12} | {top_score:<10.4f} | {decision_str:<14} | {status_str:<8} | {raw_query[:35]}...")

    print("=" * 80)
    print("  EMPIRICAL EVALUATION RESULTS & THRESHOLD ANALYSIS")
    print("=" * 80)

    mean_in = np.mean(in_domain_scores) if in_domain_scores else 0.0
    min_in = np.min(in_domain_scores) if in_domain_scores else 0.0
    max_in = np.max(in_domain_scores) if in_domain_scores else 0.0
    mean_out = np.mean(out_of_domain_scores) if out_of_domain_scores else 0.0

    precision_at_k = (correct_retrievals / total_in_domain) * 100 if total_in_domain > 0 else 0.0

    print(f"  • Precision@1 on In-Domain Queries: {precision_at_k:.1f}% ({correct_retrievals}/{total_in_domain})")
    print(f"  • In-Domain Cosine Similarity:       Mean={mean_in:.4f} | Min={min_in:.4f} | Max={max_in:.4f}")
    print(f"  • Out-of-Domain Negative Score:     Mean={mean_out:.4f}")
    print(f"  • Safety Margin (Min In - Mean Out): {min_in - mean_out:.4f}")
    print(f"  • Tested SIMILARITY_THRESHOLD:       {SIMILARITY_THRESHOLD:.2f}")

    if min_in > SIMILARITY_THRESHOLD > mean_out:
        print(f"  [VERIFICATION PASSED] The threshold {SIMILARITY_THRESHOLD:.2f} cleanly separates in-domain material ({min_in:.2f}+) from off-topic queries ({mean_out:.2f}).")
    else:
        print(f"  [OBSERVATION] Consider adjusting threshold toward {(min_in + mean_out) / 2:.2f}")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_evaluation())
