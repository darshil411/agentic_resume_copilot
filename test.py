import os
import sys
from dotenv import load_dotenv

# Ensure root directory is in the python path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Load environment variables from your .env file
load_dotenv(os.path.join(ROOT_DIR, ".env"))

from app.utils.llm_factory import get_llm

def test_api_keys():
    providers = ["gemini", "groq", "openrouter"]
    test_prompt = "Hello! Please reply with exactly the words 'API Key is working perfectly!' and nothing else."
    
    print("=" * 60)
    print("Starting LLM API Key Sanity Check...")
    print("=" * 60)
    
    for provider in providers:
        print(f"\n[TESTing] Provider: {provider.upper()}")
        try:
            # Initialize model using your exact factory setup
            llm = get_llm(provider=provider, temperature=0.0)
            
            # Extract configured model name dynamically for debugging clarity
            model_name = getattr(llm, "model", getattr(llm, "model_name", "Unknown Model"))
            print(f" -> Target Model: {model_name}")
            
            # Fire the query
            response = llm.invoke(test_prompt)
            
            print(f" -> Status: SUCCESS ✅")
            print(f" -> Response: \"{response.content.strip()}\"")
            
        except Exception as e:
            print(f" -> Status: FAILED ❌")
            print(f" -> Error Message: {str(e)}")
            
    print("\n" + "=" * 60)
    print("API Key Diagnostics Completed.")
    print("=" * 60)

if __name__ == "__main__":
    test_api_keys()