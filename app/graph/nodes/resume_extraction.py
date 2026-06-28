from ..state import GraphState
from ...services.pdf_service import extract_text_from_pdf


def resume_extraction_node(state: GraphState):

    extracted_text = extract_text_from_pdf(
        state.resume_file_path
    )

    return {
        "resume_text": extracted_text
    }