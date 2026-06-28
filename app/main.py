import os
import sys
from dotenv import load_dotenv

# Ensure root directory is in path and load env variables BEFORE importing anything else
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

env_path = os.path.join(ROOT_DIR, ".env")
load_dotenv(dotenv_path=env_path)

from fastapi import FastAPI
from app.api.routes import router

# Initialize FastAPI App
app = FastAPI(
    title="AI Resume Copilot API",
    description="Backend orchestration system using LangGraph and FastAPI.",
    version="1.0.0"
)

# Register API routes
app.include_router(router, prefix="/api/v1")

@app.get("/")
def health_check():
    return {"status": "healthy", "service": "AI Resume Copilot backend"}

if __name__ == "__main__":
    import uvicorn
    # Run the server locally on port 8000
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)