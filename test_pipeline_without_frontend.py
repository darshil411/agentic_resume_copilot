import os
import tempfile
from pathlib import Path

import fitz

from app.api.routes import app_graph


TEST_JOB_DESCRIPTION = """
We are hiring a Senior Python Backend Engineer with FastAPI, LangGraph, and AI integrations experience.
Requirements: Python, FastAPI, LangGraph, APIs, async programming, deployment, testing, and strong backend systems knowledge.
"""


def create_sample_resume_pdf(path: str) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Jane Doe\nSenior Python Engineer\nFastAPI, Python, LangGraph, APIs, Docker")
    doc.save(path)
    doc.close()


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "sample_resume.pdf")
        create_sample_resume_pdf(pdf_path)
        print(f"Created sample resume: {pdf_path}")

        initial_state = {
            "resume_file_path": pdf_path,
            "job_description_text": TEST_JOB_DESCRIPTION,
            "workflow_logs": [],
            "errors": [],
            "current_section": "summary",
        }

        print("Starting graph invocation...")
        result = app_graph.invoke(initial_state, config={"configurable": {"thread_id": "pipeline-test"}})
        print("Graph completed.")
        print("Final state keys:", sorted(result.keys()))
        print("Errors:", result.get("errors", []))
        print("Workflow logs:", result.get("workflow_logs", [])[:10])
        print("Original resume:", result.get("original_resume"))
        print("Optimized resume:", result.get("optimized_resume"))
