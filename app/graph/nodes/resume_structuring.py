from ..state import GraphState
from ...schemas.resume import StructuredResume
from ...services.llm_service import get_llm
from ...prompts.resume_prompts import STRUCTURE_RESUME_PROMPT
import time

def resume_structuring_node(state: GraphState):

    llm = get_llm()
    structured_llm = llm.with_structured_output(
        StructuredResume
    )
    time.sleep(5)
    response = structured_llm.invoke(
        f"""
        {STRUCTURE_RESUME_PROMPT}

        Resume Text:
        {state.resume_text}
        """
    )

    return {
        "original_resume": response
    }