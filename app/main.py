import os
import sys
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Ensure root directory is in python path and load .env before any other imports
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Load environment variables from .env file (must happen before llm_factory imports)
load_dotenv(os.path.join(ROOT_DIR, ".env"))

from app.api.routes import router

# 1. Initialize FastAPI Application
app = FastAPI(
    title="AI Resume Tailoring & Interview Copilot API",
    description="Backend orchestration system using LangGraph and FastAPI",
    version="2.0.0"
)

# 2. Configure CORS Middleware (Crucial Connection Layer)
# This explicitly signals the browser to permit cross-origin JavaScript requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],             # Allows requests from any frontend address (local file, Live Server, etc.)
    allow_credentials=True,
    allow_methods=["*"],             # Allows GET, POST, OPTIONS, etc.
    allow_headers=["*"],             # Allows headers like Content-Type
)

# 3. Include Workflow Routes
app.include_router(router)

if __name__ == "__main__":
    # Start the application server
    # FIX: Restrict reload to the 'app' directory so uploads/checkpoints don't trigger server restarts!
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True, reload_dirs=["app"])