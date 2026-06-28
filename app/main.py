import os
import sys
from dotenv import load_dotenv

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# FIX: Load environment variables BEFORE importing the graph or running anything
env_path = os.path.join(ROOT_DIR, ".env")
load_dotenv(dotenv_path=env_path)

from app.graph.builder import graph

# Dynamically build the absolute path to the data folder inside your project root
RESUME_PATH = os.path.join(ROOT_DIR, "data", "resume.pdf")

initial_state = {
    "resume_file_path": RESUME_PATH,
    "job_description_text": """
    Looking for Python backend engineer with FastAPI,
    LangGraph, AI workflow experience and vector DB knowledge.
    """
}

result = graph.invoke(initial_state)

print(result)