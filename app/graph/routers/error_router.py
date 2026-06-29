from app.graph.state.global_state import GlobalGraphState

def route_on_errors(state: GlobalGraphState) -> str:
    """
    Deterministic Router: Inspects the global errors list to decide if we need to 
    divert to an explicit error handling node before continuing the main flow.
    """
    # FIX: Use Pydantic dot-notation for the state object
    errors = state.errors
    
    if not errors:
        return "continue"
        
    latest_error = errors[-1].lower()
    
    if "schemavalidationerror" in latest_error:
        return "schema_validation_retry_node"
    elif "extraction" in latest_error:
        return "parsing_error_node"
    
    # Default fallback for unknown errors
    return "escalation_node"