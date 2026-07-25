import os
import sys
from dotenv import load_dotenv # pyright: ignore[reportMissingImports]
from fastapi import FastAPI # pyright: ignore[reportMissingImports]
from fastapi.middleware.cors import CORSMiddleware # pyright: ignore[reportMissingImports]
import uvicorn # pyright: ignore[reportMissingImports]

# Ensure required directories exist to prevent file crashes on platforms like Render
os.makedirs("data/uploads", exist_ok=True)
os.makedirs("data", exist_ok=True)

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
# Read the domain from the environment, default to localhost for local testing
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Include Workflow Routes
app.include_router(router)

if __name__ == "__main__":
    # Start the application server
    # FIX: Restrict reload to the 'app' directory so uploads/checkpoints don't trigger server restarts!
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True, reload_dirs=["app"])