"""
LLM Factory — Centralized provider routing with automatic Gemini fallback.

Provider → Task Assignment:
  openrouter (gpt-4o-mini) → resume_structuring_node, jd_analysis_node, ats_evaluation_node
  cerebras  (llama3.1-8b)  → optimize_section_node  (HITL resume optimization)
  groq      (llama-3.1-8b) → interview_prep_node, outreach_node
  gemini    (gemini-2.5-flash, with key rotation) → universal fallback for all above

Usage:
  from app.utils.llm_factory import get_llm
  llm = get_llm("cerebras")                        # plain call
  llm = get_llm("openrouter", model="openai/gpt-4o-mini").with_structured_output(MySchema)

All providers return an object that supports .with_structured_output() and .invoke().
On any failure (rate limit, timeout, API error) the caller should catch and use
get_llm("gemini") as the fallback — see individual node implementations.
"""

import os
import logging
from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]
from langchain_google_genai import ChatGoogleGenerativeAI  # pyright: ignore[reportMissingImports]
from langchain_groq import ChatGroq  # pyright: ignore[reportMissingImports]
from langchain_openai import ChatOpenAI  # pyright: ignore[reportMissingImports]

logger = logging.getLogger(__name__)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(ROOT_DIR, ".env"), override=False)


# ---------------------------------------------------------------------------
# Gemini key rotation helpers
# ---------------------------------------------------------------------------

def _get_gemini_keys() -> list[str]:
    """
    Returns all valid Gemini API keys in rotation order:
    GEMINI_API_KEY → GEMINI_API_KEY_2 → GEMINI_API_KEY_3
    Filters out empty strings and YOUR_* placeholder values.
    """
    candidates = [
        os.getenv("GEMINI_API_KEY", "").strip(),
        os.getenv("GOOGLE_API_KEY", "").strip(),
        os.getenv("GEMINI_API_KEY_2", "").strip(),
        os.getenv("GEMINI_API_KEY_3", "").strip(),
    ]
    seen: set[str] = set()
    keys: list[str] = []
    for k in candidates:
        if k and k not in seen and not k.startswith("YOUR_"):
            seen.add(k)
            keys.append(k)
    return keys


def _get_env(key: str) -> str:
    return os.getenv(key, "").strip()


# ---------------------------------------------------------------------------
# _GeminiWithRotation — quota-aware Gemini proxy (used as universal fallback)
# ---------------------------------------------------------------------------

class _GeminiWithRotation:
    """
    Gemini proxy that auto-rotates through up to 3 API keys on 429 errors.
    Fully compatible with .with_structured_output() chaining.
    """

    def __init__(self, model: str = None, temperature: float = 0.0):
        self._model = model or "gemini-2.5-flash"
        self._temperature = temperature
        self._keys = _get_gemini_keys()
        self._structured_schema = None
        if not self._keys:
            raise ValueError(
                "No valid Gemini API key found. Set GEMINI_API_KEY in .env"
            )

    def with_structured_output(self, schema):
        clone = _GeminiWithRotation(self._model, self._temperature)
        clone._structured_schema = schema
        return clone

    def _build(self, key: str):
        llm = ChatGoogleGenerativeAI(
            model=self._model,
            temperature=self._temperature,
            api_key=key,
        )
        if self._structured_schema is not None:
            return llm.with_structured_output(self._structured_schema)
        return llm

    def invoke(self, *args, **kwargs):
        last_exc = None
        for idx, key in enumerate(self._keys):
            try:
                result = self._build(key).invoke(*args, **kwargs)
                if idx > 0:
                    logger.info(f"[Gemini] Succeeded with key slot {idx + 1}")
                return result
            except Exception as exc:
                err = str(exc).lower()
                is_quota = any(x in err for x in ("resource_exhausted", "429", "quota"))
                if is_quota and idx < len(self._keys) - 1:
                    logger.warning(
                        f"[Gemini] Key {idx + 1}/{len(self._keys)} quota exhausted, trying next..."
                    )
                    last_exc = exc
                    continue
                raise  # non-quota error or last key → bubble up immediately

        raise RuntimeError(
            f"All {len(self._keys)} Gemini key(s) quota-exhausted. Last: {last_exc}"
        )


# ---------------------------------------------------------------------------
# Main factory
# ---------------------------------------------------------------------------

def get_llm(provider: str = "gemini", model: str = None, temperature: float = 0.0):
    """
    Returns a LangChain-compatible LLM for the given provider.

    Supported providers
    -------------------
    openrouter  OpenRouter API (default model: openai/gpt-4o-mini)
                env: OPENROUTER_API_KEY
    cerebras    Cerebras cloud API (default model: llama3.1-8b)
                env: CEREBRAS_API_KEY
    groq        Groq cloud API (default model: llama-3.1-8b-instant)
                env: GROQ_API_KEY
    gemini      Google Gemini with automatic key rotation on 429
                env: GEMINI_API_KEY, GEMINI_API_KEY_2, GEMINI_API_KEY_3

    All objects support .with_structured_output(Schema) and .invoke(messages).
    """
    provider = provider.lower()

    # ── OpenRouter ────────────────────────────────────────────────────────
    if provider == "openrouter":
        api_key = _get_env("OPENROUTER_API_KEY")
        model_name = model or "openai/gpt-4o-mini"
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=api_key or "NO_KEY",
            base_url="https://openrouter.ai/api/v1",
        )

    # ── Cerebras ──────────────────────────────────────────────────────────
    elif provider == "cerebras":
        api_key = _get_env("CEREBRAS_API_KEY")
        # Available models on this account: gpt-oss-120b, gemma-4-31b, zai-glm-4.7
        model_name = model or "gpt-oss-120b"
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=api_key or "NO_KEY",
            base_url="https://api.cerebras.ai/v1",
        )

    # ── Groq ──────────────────────────────────────────────────────────────
    elif provider == "groq":
        api_key = _get_env("GROQ_API_KEY")
        model_name = model or "llama-3.1-8b-instant"
        return ChatGroq(
            model_name=model_name,
            temperature=temperature,
            groq_api_key=api_key,
        )

    # ── Gemini (with key rotation) ────────────────────────────────────────
    elif provider == "gemini":
        return _GeminiWithRotation(model=model, temperature=temperature)

    else:
        raise ValueError(f"Unsupported provider: {provider!r}")