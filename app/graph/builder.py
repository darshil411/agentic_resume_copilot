from langgraph.graph import StateGraph, END # pyright: ignore[reportMissingImports]

from .state import GraphState

from .nodes.resume_extraction import (
    resume_extraction_node
)

from .nodes.resume_structuring import (
    resume_structuring_node
)

from .nodes.jd_analysis import (
    jd_analysis_node
)

from .nodes.ats_evaluation import (
    ats_evaluation_node
)

from .nodes.optimize_projects import (
    optimize_projects_node
)

from .nodes.commit_changes import (
    commit_changes_node
)

from .routers import (
    approval_router
)


builder = StateGraph(GraphState)


builder.add_node(
    "resume_extraction_node",
    resume_extraction_node
)

builder.add_node(
    "resume_structuring_node",
    resume_structuring_node
)

builder.add_node(
    "jd_analysis_node",
    jd_analysis_node
)

builder.add_node(
    "ats_evaluation_node",
    ats_evaluation_node
)

builder.add_node(
    "optimize_projects_node",
    optimize_projects_node
)

builder.add_node(
    "commit_changes_node",
    commit_changes_node
)


builder.set_entry_point(
    "resume_extraction_node"
)


builder.add_edge(
    "resume_extraction_node",
    "resume_structuring_node"
)

builder.add_edge(
    "resume_structuring_node",
    "jd_analysis_node"
)

builder.add_edge(
    "jd_analysis_node",
    "ats_evaluation_node"
)

builder.add_edge(
    "ats_evaluation_node",
    "optimize_projects_node"
)


builder.add_conditional_edges(
    "optimize_projects_node",
    approval_router
)



builder.add_edge(
    "commit_changes_node",
    END
)


graph = builder.compile()

