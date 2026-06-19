from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from graph.nodes import (
    outreach_writer_node,
    parse_jd_node,
    plan_search_node,
    qa_node,
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


def fan_out_outreach(state: CampaignState):
    """Spawn one outreach_writer worker per shortlisted candidate (parallel map)."""
    ranked = state.get("ranked_shortlist") or []
    outreach_n = state.get("outreach_n", 3)
    eligible = [
        item
        for item in ranked
        if item.get("profile_brief") and item.get("match_result")
    ][:outreach_n]

    if not eligible:
        return "qa"

    return [
        Send(
            "outreach_writer",
            {
                "candidate": item,
                "parsed_jd": state["parsed_jd"],
                "jd_text": state["jd_text"],
            },
        )
        for item in eligible
    ]


def build_graph():
    builder = StateGraph(CampaignState)

    builder.add_node("parse_jd", parse_jd_node)
    builder.add_node("plan_search", plan_search_node)
    builder.add_node("search_candidates", search_candidates_node)
    builder.add_node("research_and_score", research_and_score_node)
    builder.add_node("rank", rank_node)
    builder.add_node("outreach_writer", outreach_writer_node)
    builder.add_node("qa", qa_node)

    builder.add_edge(START, "parse_jd")
    builder.add_edge("parse_jd", "plan_search")
    builder.add_edge("plan_search", "search_candidates")
    builder.add_conditional_edges(
        "search_candidates", fan_out, ["research_and_score"]
    )
    builder.add_edge("research_and_score", "rank")
    builder.add_conditional_edges(
        "rank", fan_out_outreach, ["outreach_writer", "qa"]
    )
    builder.add_edge("outreach_writer", "qa")
    builder.add_edge("qa", END)

    return builder.compile()
