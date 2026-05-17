from typing import Dict, Optional, TypedDict


class CampaignState(TypedDict):
    jd_text: str
    github_username: str
    parsed_jd: Optional[Dict]
    profile_brief: Optional[Dict]
    match_result: Optional[Dict]
