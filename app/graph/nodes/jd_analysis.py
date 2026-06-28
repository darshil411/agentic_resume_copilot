from ..state import GraphState
from ...schemas.jd import JDAnalysis
from ...services.llm_service import get_llm
import time

def jd_analysis_node(state: GraphState):

    llm = get_llm()

    structured_llm = llm.with_structured_output(
        JDAnalysis
    )
    time.sleep(5)
    response = structured_llm.invoke(
        f"""
        Analyze the following job description.

        Extract:
        - required skills
        - responsibilities
        - technologies
        - keywords
        - experience requirements

        Job Description:
        {state.job_description_text}
        """
    )

    return {
        "jd_analysis": response
    }