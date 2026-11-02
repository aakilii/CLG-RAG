import json
from typing import List, Dict, Any, Optional
import httpx
from openai import OpenAI
from config import groq_client, GROQ_CHAT_MODEL, EMBEDDING_MODEL, EMBEDDING_DIM, GEMINI_API_KEY

async def get_embedding(text: str) -> List[float]:
    """Generate 768-dim vector embedding using Gemini embedding API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/{EMBEDDING_MODEL}:embedContent?key={GEMINI_API_KEY}"
    payload = {
        "model": EMBEDDING_MODEL,
        "content": {"parts": [{"text": text[:3000]}]},
        "outputDimensionality": EMBEDDING_DIM
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        values = data.get("embedding", {}).get("values", [])
        if not values:
            raise ValueError("No embedding returned from Gemini API")
        return values

async def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a list of texts."""
    embeddings = []
    for text in texts:
        emb = await get_embedding(text)
        embeddings.append(emb)
    return embeddings

def rewrite_query(query: str) -> str:
    """
    Rewrite student query to fix typos and clarify intent for semantic retrieval.
    Preserves all key domain terminology.
    """
    system_prompt = (
        "You are an AI search query optimizer for student notes. "
        "Correct any spelling errors, typos, or grammatical mistakes, while preserving the key academic terms, concepts, and question intent. "
        "Do NOT reduce the question to arbitrary keywords. Return ONLY the clarified query without quotes or explanation."
    )
    try:
        completion = groq_client.chat.completions.create(
            model=GROQ_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            max_tokens=60,
            temperature=0.0
        )
        rewritten = completion.choices[0].message.content.strip()
        # Fallback if empty or quoted
        rewritten = rewritten.strip('"\'')
        return rewritten if rewritten else query
    except Exception as e:
        print(f"Error in rewrite_query: {e}")
        return query

def generate_grounded_answer(query: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate an answer grounded strictly in retrieved excerpts across one or more documents.
    Source: 'notes'
    """
    context_blocks = []
    citations = []
    for i, chunk in enumerate(chunks):
        content = chunk.get("content", "").strip()
        doc_name = chunk.get("doc_name", "Notes")
        context_blocks.append(f"--- Excerpt [{i+1}] from '{doc_name}' ---\n{content}")
        preview = (content[:110] + "...") if len(content) > 110 else content
        citations.append(f"[{doc_name}] \"{preview}\"")

    context_str = "\n\n".join(context_blocks)
    system_prompt = (
        "You are an academic study assistant. Answer the student's question clearly, thoroughly, and accurately "
        "based strictly on the provided course material excerpts below. "
        "Explain key terms, mechanics, and principles step-by-step. "
        "Whenever mathematical equations, Big-O notations, or loss functions appear, format them in standard LaTeX math notation using $...$ for inline formulas and $$...$$ for block equations (e.g. $O(n \\log n)$, $\\sigma(z) = \\frac{1}{1 + e^{-z}}$). "
        "If the student is asking to compare, contrast, or analyze trade-offs between concepts or documents, synthesize the information into a clear Markdown comparison table followed by key trade-offs. "
        "If multiple documents are provided in the excerpts, synthesize the information across them. "
        "Maintain a helpful, natural, and scholarly tone without referencing system prompts or technical backend mechanics."
    )
    user_prompt = f"Course Excerpts:\n{context_str}\n\nStudent Question: {query}"

    completion = groq_client.chat.completions.create(
        model=GROQ_CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,
        max_tokens=900
    )
    answer = completion.choices[0].message.content.strip()
    return {
        "answer": answer,
        "source": "notes",
        "citation": " | ".join(citations[:2])
    }

def generate_web_answer(query: str, web_results: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Generate an answer synthesized from reference material.
    Never states or specifies that it is from the web.
    """
    context_blocks = []
    citations = []
    for item in web_results:
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        url = item.get("url", "")
        context_blocks.append(f"Subject: {title}\nDetails: {snippet}")
        citations.append(f"{title}")

    context_str = "\n\n".join(context_blocks)
    system_prompt = (
        "You are an academic study assistant. Provide a comprehensive, clear, and scholarly answer "
        "addressing the student's question based on the reference concepts below. "
        "Explain principles thoroughly and naturally. "
        "Never say or indicate that this comes from a web search or the internet, and never state that notes were missing. "
        "Answer with direct academic authority."
    )
    user_prompt = f"Reference Concepts:\n{context_str}\n\nStudent Question: {query}"

    completion = groq_client.chat.completions.create(
        model=GROQ_CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.25,
        max_tokens=900
    )
    answer = completion.choices[0].message.content.strip()
    return {
        "answer": answer,
        "source": "reference",
        "citation": " | ".join(citations[:2]) if citations else ""
    }

def label_topic_cluster(sample_texts: List[str]) -> str:
    """
    Given sample text chunks from an unsupervised KMeans cluster,
    use Groq to generate a concise 2-4 word topic label.
    """
    combined_samples = "\n---\n".join([t[:250] for t in sample_texts[:4]])
    prompt = (
        "Analyze these excerpts from a student's study notes belonging to the same cluster:\n"
        f"{combined_samples}\n\n"
        "Provide a concise, descriptive academic topic label (2 to 4 words maximum, e.g. 'Binary Search Trees', 'Thermodynamic Cycles', 'Cellular Respiration'). "
        "Return ONLY the topic label with no punctuation, intro, or quotation marks."
    )
    try:
        completion = groq_client.chat.completions.create(
            model=GROQ_CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=25,
            temperature=0.1
        )
        label = completion.choices[0].message.content.strip().strip('"\'')
        return label if label else "General Notes"
    except Exception as e:
        print(f"Error labeling topic cluster: {e}")
        return "Topic Cluster"

def generate_mcq_quiz(chunks: List[Dict[str, Any]], count: int = 3) -> List[Dict[str, Any]]:
    """
    Generate N multiple-choice questions grounded in the provided chunks spread across topic clusters.
    Returns structured JSON: list of {question, options: [4], correct_index: int, explanation: str}.
    """
    chunks_text = "\n---\n".join([f"Excerpt: {c.get('content', '')[:400]}" for c in chunks[:8]])
    system_prompt = (
        "You are an expert professor creating an exam quiz from student class notes. "
        f"Generate exactly {count} high-quality multiple choice questions grounded strictly in the provided notes excerpts. "
        "Each question must have exactly 4 options (A, B, C, D), a correct option index (0, 1, 2, or 3), "
        "and a concise one-line explanation justifying the correct answer based on the notes.\n\n"
        "You MUST respond ONLY with a valid JSON array of objects. Do not include markdown code block backticks (like ```json), "
        "do not include preamble or postscript. Example format:\n"
        "[\n"
        "  {\n"
        '    "question": "What is the time complexity of binary search?",\n'
        '    "options": ["O(1)", "O(log n)", "O(n)", "O(n^2)"],\n'
        '    "correct_index": 1,\n'
        '    "explanation": "Binary search divides the search space in half each step, yielding logarithmic time."\n'
        "  }\n"
        "]"
    )
    user_prompt = f"Study Notes Content:\n{chunks_text}"

    completion = groq_client.chat.completions.create(
        model=GROQ_CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,
        max_tokens=1500
    )
    raw_content = completion.choices[0].message.content.strip()
    # Strip markdown codeblocks if model included them
    if raw_content.startswith("```"):
        lines = raw_content.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw_content = "\n".join(lines).strip()

    try:
        quiz_data = json.loads(raw_content)
        if isinstance(quiz_data, list):
            return quiz_data[:count]
    except Exception as e:
        print(f"Failed to parse quiz JSON: {e}, raw was: {raw_content[:200]}")
    
    # Fallback structure if parsing failed
    return [
        {
            "question": "Review Question on Notes",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_index": 0,
            "explanation": "Based on the provided notes review."
        }
    ]

def generate_flashcards(chunks: List[Dict[str, Any]], count: int = 4) -> List[Dict[str, Any]]:
    """
    Generate Active Recall Flashcard deck from study notes:
    - Front: High-yield concept prompt / challenge
    - Back: Precise breakdown, core mechanics, and key takeaway
    """
    chunks_text = "\n---\n".join([f"[{c.get('doc_name', 'Notes')}] {c.get('content', '')[:400]}" for c in chunks[:8]])
    system_prompt = (
        "You are an academic learning science expert designing high-yield active recall flashcards. "
        f"Generate exactly {count} distinct study flashcards strictly derived from the provided course notes. "
        "Each card must contain:\n"
        "- 'key_term': The core subject/concept (e.g. 'Global Interpreter Lock', 'Backpropagation')\n"
        "- 'front': A probing conceptual question or active recall challenge (not simple trivia)\n"
        "- 'back': A clear, structured explanation with the core principle and key takeaway\n\n"
        "Return ONLY a valid JSON array of objects without markdown backticks or commentary:\n"
        "[\n"
        "  {\n"
        '    "key_term": "Concept Name",\n'
        '    "front": "What fundamental problem does X solve, and how does it work?",\n'
        '    "back": "X solves... Mechanism: 1. ... 2. ... Key takeaway: ..."\n'
        "  }\n"
        "]"
    )
    user_prompt = f"Course Excerpts:\n{chunks_text}"

    completion = groq_client.chat.completions.create(
        model=GROQ_CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,
        max_tokens=1500
    )
    raw_content = completion.choices[0].message.content.strip()
    if raw_content.startswith("```"):
        lines = raw_content.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw_content = "\n".join(lines).strip()

    try:
        cards = json.loads(raw_content)
        if isinstance(cards, list):
            return cards[:count]
    except Exception as e:
        print(f"Failed to parse flashcards JSON: {e}, raw was: {raw_content[:200]}")

    return [
        {
            "key_term": "Active Recall Review",
            "front": "Summarize the core concepts covered in this section of your notes.",
            "back": "Review the primary definitions and algorithms in the uploaded documents."
        }
    ]
