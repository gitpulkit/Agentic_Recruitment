from graph.runner import run_campaign

from api.db import mark_failed, mark_ready


def run_campaign_job(campaign_id: str, jd_text: str, top_k: int, outreach_n: int) -> None:
    try:
        result = run_campaign(jd_text, top_k=top_k, outreach_n=outreach_n)
        mark_ready(campaign_id, result)
    except Exception as exc:
        mark_failed(campaign_id, str(exc))
