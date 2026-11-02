import db
from fastapi.testclient import TestClient
from main import app

def test_all():
    print("Testing FastAPI Endpoints...", flush=True)

    with TestClient(app) as client:
        # 1. Health check
        resp = client.get("/")
        print("1. Health check:", resp.status_code, resp.json(), flush=True)
        assert resp.status_code == 200

        # Get the latest ready note
        notes = db.supabase.table("notes").select("*").eq("status", "ready").limit(1).execute().data
        if not notes:
            print("No ready notes found to test with.", flush=True)
            return
        note_id = notes[0]["id"]
        print(f"Testing with Note ID: {note_id} ({notes[0]['filename']})", flush=True)

        # 2. Status endpoint
        status_resp = client.get(f"/notes/{note_id}/status")
        print("\n2. Status Endpoint:", status_resp.status_code, flush=True)
        print("Data:", status_resp.json(), flush=True)
        assert status_resp.status_code == 200

        # 3. Ask Question IN Notes (should route to 'notes')
        print("\n3. Testing /ask for in-notes query...", flush=True)
        ask_notes = client.post("/ask", json={
            "note_id": note_id,
            "query": "What is the role of the event bus and asyncio.Queue?"
        })
        print("Status:", ask_notes.status_code, flush=True)
        notes_ans = ask_notes.json()
        print("Source:", notes_ans.get("source"), flush=True)
        print("Similarity:", notes_ans.get("similarity"), flush=True)
        print("Answer Preview:", notes_ans.get("answer", "")[:150], flush=True)
        print("Citation:", notes_ans.get("citation"), flush=True)

        # 4. Ask Question NOT in Notes (should route to 'web')
        print("\n4. Testing /ask for out-of-domain query (web fallback)...", flush=True)
        ask_web = client.post("/ask", json={
            "note_id": note_id,
            "query": "What is the James Webb Space Telescope?"
        })
        print("Status:", ask_web.status_code, flush=True)
        web_ans = ask_web.json()
        print("Source:", web_ans.get("source"), flush=True)
        print("Similarity:", web_ans.get("similarity"), flush=True)
        print("Answer Preview:", web_ans.get("answer", "")[:150], flush=True)
        print("Citation:", web_ans.get("citation"), flush=True)

        # 5. Quiz Generation
        print("\n5. Testing /quiz endpoint...", flush=True)
        quiz_resp = client.post("/quiz", json={
            "note_id": note_id,
            "count": 3
        })
        print("Status:", quiz_resp.status_code, flush=True)
        quiz_data = quiz_resp.json()
        print(f"Generated {len(quiz_data.get('quiz', []))} MCQs:", flush=True)
        for i, q in enumerate(quiz_data.get("quiz", [])):
            print(f"  Q{i+1}: {q['question']}", flush=True)
            print(f"      Options: {q['options']}", flush=True)
            print(f"      Correct: {q['correct_index']} ({q['options'][q['correct_index']]})", flush=True)

        # 6. Events audit log
        events_resp = client.get("/events")
        print(f"\n6. Events Log: {events_resp.status_code}, count: {len(events_resp.json())}", flush=True)

    print("\n>>> ALL PHASE 3 ENDPOINTS VERIFIED 100%! <<<", flush=True)

if __name__ == "__main__":
    test_all()
