from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from graph.nodes import (
    parse_jd_node,
    plan_search_node,
    rank_node,
    research_and_score_node,
    search_candidates_node,
)
from graph.state import CampaignState


def fan_out(state: CampaignState):
    """Spawn one research_and_score worker per candidate (parallel map)."""
    return [
        Send("research_and_score", {"username": u, "parsed_jd": state["parsed_jd"]})
        for u in state.get("candidate_usernames", [])
    ]


def build_graph():
    builder = StateGraph(CampaignState)

    builder.add_node("parse_jd", parse_jd_node)
    builder.add_node("plan_search", plan_search_node)
    builder.add_node("search_candidates", search_candidates_node)
    builder.add_node("research_and_score", research_and_score_node)
    builder.add_node("rank", rank_node)

    builder.add_edge(START, "parse_jd")
    builder.add_edge("parse_jd", "plan_search")
    builder.add_edge("plan_search", "search_candidates")
    builder.add_conditional_edges(
        "search_candidates", fan_out, ["research_and_score"]
    )
    builder.add_edge("research_and_score", "rank")
    builder.add_edge("rank", END)

    return builder.compile()
