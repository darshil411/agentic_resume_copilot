import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

def get_llm(provider: str = "gemini", model: str = None, temperature: float = 0.0):
    if provider.lower() == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        # 2026 Default: gemini-3.5-flash (older versions will 404)
        model_name = model or "gemini-3.5-flash"
        return ChatGoogleGenerativeAI(model=model_name, temperature=temperature, google_api_key=api_key)
        
    elif provider.lower() == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        # 2026 Default: Llama 3 models are deprecated on Groq. 
        model_name = model or "openai/gpt-oss-120b"
        return ChatGroq(model_name=model_name, temperature=temperature, groq_api_key=api_key)
        
    elif provider.lower() == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        # 2026 Default: Reliable free endpoint
        model_name = model or "openai/gpt-oss-20b:free"
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")
    