import operator
from typing import Annotated, Dict, List, Optional, TypedDict


class CampaignState(TypedDict):
    jd_text: str
    top_k: int
    outreach_n: int
    parsed_jd: Optional[Dict]
    search_plan: Optional[Dict]
    candidate_usernames: List[str]
    # Parallel workers each append their result; operator.add merges the lists.
    candidate_results: Annotated[List[Dict], operator.add]
    ranked_shortlist: Optional[List[Dict]]
    outreach_drafts: Annotated[List[Dict], operator.add]
    qa_report: Optional[Dict]
    # Set per-worker via the Send payload, not by the main flow.
    username: Optional[str]
    candidate: Optional[Dict]
