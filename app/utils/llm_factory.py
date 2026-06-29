import os
from dotenv import load_dotenv # pyright: ignore[reportMissingImports]
from langchain_google_genai import ChatGoogleGenerativeAI # pyright: ignore[reportMissingImports]
from langchain_groq import ChatGroq # pyright: ignore[reportMissingImports]
from langchain_openai import ChatOpenAI # pyright: ignore[reportMissingImports]


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(ROOT_DIR, ".env"), override=False)


def _get_env_or_fallback(primary: str, fallback: str) -> str:
    value = os.getenv(primary, "").strip()
    if value:
        return value
    return os.getenv(fallback, "").strip()


def get_llm(provider: str = "gemini", model: str = None, temperature: float = 0.0):
    """
    Returns a LangChain chat model for the given provider.

    Provider defaults (as of mid-2026):
      - gemini    → gemini-1.5-flash   (stable, free tier available)
      - groq      → llama-3.1-8b-instant  (fast free tier on Groq)
      - openrouter→ mistralai/mistral-7b-instruct:free
    """
    provider = provider.lower()

    if provider == "gemini":
        api_key = _get_env_or_fallback("GEMINI_API_KEY", "GOOGLE_API_KEY")
        if api_key:
            os.environ["GEMINI_API_KEY"] = api_key
            os.environ["GOOGLE_API_KEY"] = api_key
        model_name = model or "gemini-2.5-flash"
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            api_key=api_key,
        )

    elif provider == "groq":
        api_key = _get_env_or_fallback("GROQ_API_KEY", "GROQ_API_KEY")
        if api_key:
            os.environ["GROQ_API_KEY"] = api_key
        model_name = model or "llama-3.1-8b-instant"
        return ChatGroq(
            model_name=model_name,
            temperature=temperature,
            groq_api_key=api_key,
        )

    elif provider == "openrouter":
        api_key = _get_env_or_fallback("OPENROUTER_API_KEY", "OPENROUTER_API_KEY")
        if api_key:
            os.environ["OPENROUTER_API_KEY"] = api_key
        model_name = model or "openrouter/free"
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )

    else:
        raise ValueError(f"Unsupported provider: {provider!r}")