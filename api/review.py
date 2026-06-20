from typing import Any, Dict, List


def build_review_rows(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Merge shortlist, outreach drafts, and QA into rows for the recruiter UI."""
    drafts = {d["username"]: d for d in result.get("outreach_drafts") or []}
    qa = {
        r["username"]: r for r in (result.get("qa_report") or {}).get("results", [])
    }
    rows: List[Dict[str, Any]] = []

    for item in result.get("ranked_shortlist") or []:
        username = item.get("username")
        if not username or username not in drafts:
            continue

        match = item.get("match_result") or {}
        brief = item.get("profile_brief") or {}
        draft = drafts[username]
        qa_result = qa.get(username, {})

        rows.append(
            {
                "username": username,
                "score": match.get("score"),
                "rationale": match.get("rationale"),
                "profile_url": brief.get("profile_url"),
                "name": brief.get("name"),
                "email": brief.get("email"),
                "draft": {
                    "subject": draft.get("subject"),
                    "body": draft.get("body"),
                    "personalization_hooks": draft.get("personalization_hooks", []),
                },
                "qa": {
                    "passed": qa_result.get("passed", False),
                    "severity": qa_result.get("severity", "unknown"),
                    "issues": qa_result.get("issues", []),
                },
            }
        )

    return rows
