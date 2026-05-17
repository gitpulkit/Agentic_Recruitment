from langgraph.graph import END, START, StateGraph

from graph.nodes import parse_jd_node, research_github_node, score_match_node
from graph.state import CampaignState


def build_graph():
    builder = StateGraph(CampaignState)

    builder.add_node("parse_jd", parse_jd_node)
    builder.add_node("research_github", research_github_node)
    builder.add_node("score_match", score_match_node)

    builder.add_edge(START, "parse_jd")
    builder.add_edge("parse_jd", "research_github")
    builder.add_edge("research_github", "score_match")
    builder.add_edge("score_match", END)

    return builder.compile()
