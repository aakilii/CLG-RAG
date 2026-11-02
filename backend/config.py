import os
from dotenv import load_dotenv
from supabase import create_client, Client
from openai import OpenAI
import httpx

# Load .env
load_dotenv()

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in environment variables.")

# Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Groq Client (OpenAI SDK Compatible)
groq_client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
    default_headers={"User-Agent": "Mozilla/5.0"}
)

GROQ_CHAT_MODEL = "qwen/qwen3.8-27b"
EMBEDDING_MODEL = "models/gemini-embedding-001"
EMBEDDING_DIM = 768
SIMILARITY_THRESHOLD = 0.55

# --- Defensible RAG Chunking Configuration ---
# 500 tokens (~400-450 words / ~1800-2000 chars):
# 1. Matches Gemini embedding attention window (peak retrieval fidelity at 250-500 tokens).
# 2. Preserves full theorem/algorithm/definition paragraphs without truncation.
# 50 tokens (~40-45 words / ~200 chars overlap):
# Ensures cross-boundary continuity for definitions spanning adjacent split points.
CHUNK_TARGET_WORDS = 420
CHUNK_OVERLAP_WORDS = 45
CHUNK_TARGET_CHARS = 1800
CHUNK_OVERLAP_CHARS = 200
