import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI


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
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        model_name = model or "gemini-1.5-flash"
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            google_api_key=api_key,
        )

    elif provider == "groq":
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        # llama-3.1-8b-instant is the current stable free-tier model on Groq
        model_name = model or "llama-3.1-8b-instant"
        return ChatGroq(
            model_name=model_name,
            temperature=temperature,
            groq_api_key=api_key,
        )

    elif provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        model_name = model or "mistralai/mistral-7b-instruct:free"
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )

    else:
        raise ValueError(f"Unsupported provider: {provider!r}")