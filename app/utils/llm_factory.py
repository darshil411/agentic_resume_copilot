import os
import random
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq

def get_gemini_key():
    keys = []
    # Search for keys like GEMINI_API_KEY, GEMINI_API_KEY_1, GEMINI_API_KEY_2, etc.
    for key, value in os.environ.items():
        if key.startswith("GEMINI_API_KEY") and value:
            keys.append(value)
    if not keys:
        raise ValueError("No Gemini API keys found in environment variables.")
    return random.choice(keys)

def get_groq_key():
    keys = []
    for key, value in os.environ.items():
        if key.startswith("GROQ_API_KEY") and value:
            keys.append(value)
    if not keys:
        raise ValueError("No Groq API keys found in environment variables.")
    return random.choice(keys)

def get_openrouter_key():
    keys = []
    for key, value in os.environ.items():
        if key.startswith("OPENROUTER_API_KEY") and value:
            keys.append(value)
    if not keys:
        raise ValueError("No OpenRouter API keys found in environment variables.")
    return random.choice(keys)

def get_llm(provider: str = "gemini", model: str = None, temperature: float = 0.0):
    """
    Returns a configured LLM instance based on the provider.
    Rotates API keys randomly to prevent exhaustion.
    """
    if provider.lower() == "gemini":
        api_key = get_gemini_key()
        model_name = model or "gemini-1.5-flash"
        return ChatGoogleGenerativeAI(model=model_name, temperature=temperature, google_api_key=api_key)
        
    elif provider.lower() == "groq":
        api_key = get_groq_key()
        model_name = model or "llama3-8b-8192"
        return ChatGroq(model_name=model_name, temperature=temperature, groq_api_key=api_key)
        
    elif provider.lower() == "openrouter":
        api_key = get_openrouter_key()
        model_name = model or "meta-llama/llama-3-8b-instruct:free"
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")
