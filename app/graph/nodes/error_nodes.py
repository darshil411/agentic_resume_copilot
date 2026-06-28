from typing import Dict, Any
from app.graph.state.global_state import GlobalGraphState

def parsing_error_node(state: GlobalGraphState) -> Dict[str, Any]:
    """
    Handles PDF extraction/parsing errors.
    In a real system, this might notify the user or request a re-upload.
    """
    return {
        "workflow_logs": ["Execution halted at parsing_error_node due to extraction failure."]
    }

def schema_validation_retry_node(state: GlobalGraphState) -> Dict[str, Any]:
    """
    Handles Pydantic validation errors from LLM structured outputs.
    Can be used to trigger a retry loop or prompt the LLM to fix its JSON.
    """
    return {
        "workflow_logs": ["Routing through schema_validation_retry_node to fix structured output."]
    }

def escalation_node(state: GlobalGraphState) -> Dict[str, Any]:
    """
    Final fallback when max retries are exceeded.
    """
    return {
        "workflow_logs": ["Escalated to human support or failed gracefully after max retries."]
    }
