from copy import deepcopy

from ..state import GraphState


def commit_changes_node(state: GraphState):

    updated_resume = deepcopy(
        state.original_resume
    )

    updated_resume.projects = (
        state.proposed_changes["projects"]
    )

    return {
        "optimized_resume": updated_resume
    }