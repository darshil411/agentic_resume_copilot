from typing import Dict, Any
import asyncio
from app.graph.state.global_state import GlobalGraphState
from app.graph.nodes.interview_nodes import generate_interview_prep_node
from app.graph.nodes.outreach_nodes import generate_outreach_templates_node

# In-process store for background job results
# Structure: { thread_id: { "interview": {...}, "outreach": {...} } }
_bg_results: Dict[str, Dict[str, Any]] = {}

def init_bg_slot(thread_id: str):
    """Initializes the background result slot for a new thread."""
    _bg_results[thread_id] = {
        "interview": {"status": "PROCESSING", "data": None},
        "outreach": {"status": "PROCESSING", "data": None}
    }

def run_interview_worker_sync(thread_id: str, original_resume: Any, jd_analysis: Any):
    """Runs the interview prep generation synchronously (meant for ThreadPoolExecutor)."""
    # Initialize if missing (e.g. tests or direct calls)
    if thread_id not in _bg_results:
        init_bg_slot(thread_id)
        
    try:
        # Create a mock state to pass to the pure node function
        state = GlobalGraphState(
            original_resume=original_resume,
            jd_analysis=jd_analysis
        )
        result = generate_interview_prep_node(state)
        
        if "errors" in result and result["errors"]:
            _bg_results[thread_id]["interview"] = {"status": "FAILED", "data": result}
        else:
            _bg_results[thread_id]["interview"] = {"status": "COMPLETED", "data": result}
            
    except Exception as e:
        _bg_results[thread_id]["interview"] = {"status": "FAILED", "error": str(e)}

def run_outreach_worker_sync(thread_id: str, original_resume: Any, jd_analysis: Any):
    """Runs the outreach generation synchronously (meant for ThreadPoolExecutor)."""
    if thread_id not in _bg_results:
        init_bg_slot(thread_id)
        
    try:
        state = GlobalGraphState(
            original_resume=original_resume,
            jd_analysis=jd_analysis
        )
        result = generate_outreach_templates_node(state)
        
        if "errors" in result and result["errors"]:
            _bg_results[thread_id]["outreach"] = {"status": "FAILED", "data": result}
        else:
            _bg_results[thread_id]["outreach"] = {"status": "COMPLETED", "data": result}
            
    except Exception as e:
        _bg_results[thread_id]["outreach"] = {"status": "FAILED", "error": str(e)}

def get_interview_result(thread_id: str) -> Dict[str, Any]:
    """Retrieves the interview result for a thread."""
    slot = _bg_results.get(thread_id, {}).get("interview", {"status": "PROCESSING"})
    return slot

def get_outreach_result(thread_id: str) -> Dict[str, Any]:
    """Retrieves the outreach result for a thread."""
    slot = _bg_results.get(thread_id, {}).get("outreach", {"status": "PROCESSING"})
    return slot
