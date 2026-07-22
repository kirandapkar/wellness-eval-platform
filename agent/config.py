import os
from dotenv import load_dotenv

load_dotenv()

MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY_V2") or os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY or ""  # litellm reads this env var directly for the openai/ provider

VARIANTS = {
    "frontier": {"provider": "openai", "model": "gpt-4o-mini"},
    "oss": {"provider": "groq", "model": "llama-3.1-8b-instant"},  # Llama 3.2 preview decommissioned on Groq
}

JUDGE_MODEL = "gpt-4o"  # both Gemini keys hit account-level API restrictions (404/0-quota on every model) - see README limitations.
# Same provider as frontier agent (gpt-4o-mini) but different model, for partial self-preference isolation.

SYSTEM_PROMPT = """You are a wellness assistant. Help users make better decisions
around diet, exercise, sleep, stress and mindfulness, grounded in the knowledge base.
Never diagnose, prescribe, or replace professional medical advice - redirect to a
professional for anything diagnostic or symptom-specific.
Use lookup_kb first for anything the KB might cover. Use search_web for current/
external info. Keep a warm, non-judgmental tone, don't moralize."""

MEMORY_MAX_TURNS = 10
