from ..state import GraphState
from ...schemas.ats import ATSReport
from ...services.llm_service import get_llm
import time

def ats_evaluation_node(state: GraphState):

    llm = get_llm()

    structured_llm = llm.with_structured_output(
        ATSReport
    )
    time.sleep(5)
    response = structured_llm.invoke(
        f"""
        Compare the resume and job description.

        Evaluate:
        - ATS score
        - missing skills
        - keyword alignment
        - improvement suggestions

        Resume:
        {state.original_resume}

        Job Description:
        {state.jd_analysis}
        """
    )

    return {
        "ats_report": response
    }