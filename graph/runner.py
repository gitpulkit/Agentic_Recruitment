from graph.workflow import build_graph


def initial_state(jd_text: str, top_k: int, outreach_n: int) -> dict:
    return {
        "jd_text": jd_text,
        "top_k": top_k,
        "outreach_n": outreach_n,
        "parsed_jd": None,
        "search_plan": None,
        "candidate_usernames": [],
        "candidate_results": [],
        "ranked_shortlist": None,
        "outreach_drafts": [],
        "qa_report": None,
        "username": None,
        "candidate": None,
    }


def run_campaign(jd_text: str, top_k: int = 5, outreach_n: int = 3) -> dict:
    graph = build_graph()
    return graph.invoke(initial_state(jd_text, top_k, outreach_n))
