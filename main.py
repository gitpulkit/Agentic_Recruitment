import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from graph.workflow import build_graph


def _print_table(ranked: list) -> None:
    if not ranked:
        print("\nNo candidates found. Try a different JD or add a GITHUB_TOKEN.\n")
        return

    print("\nRanked shortlist")
    print("-" * 72)
    print(f"{'#':<3} {'score':<6} {'username':<22} profile")
    print("-" * 72)
    for i, item in enumerate(ranked, 1):
        match = item.get("match_result") or {}
        brief = item.get("profile_brief") or {}
        score = match.get("score", "-")
        username = item.get("username", "?")
        url = brief.get("profile_url", "")
        print(f"{i:<3} {str(score):<6} {username:<22} {url}")
        rationale = match.get("rationale")
        if rationale:
            print(f"      -> {rationale}")
    print("-" * 72)


def _print_outreach(drafts: list, qa_report: dict) -> None:
    if not drafts:
        print("\nNo outreach drafts (no eligible candidates in shortlist).\n")
        return

    qa_by_user = {
        item.get("username"): item for item in (qa_report or {}).get("results", [])
    }

    print("\nOutreach drafts (review only — not sent)")
    print("=" * 72)
    for draft in drafts:
        username = draft.get("username", "?")
        qa = qa_by_user.get(username, {})
        status = "PASS" if qa.get("passed") else "NEEDS REVIEW"
        severity = qa.get("severity", "unknown")
        print(f"\n@{username}  [{status}, severity: {severity}]")
        print(f"Subject: {draft.get('subject', '')}")
        print("-" * 72)
        print(draft.get("body", ""))
        issues = qa.get("issues") or []
        if issues:
            print("-" * 72)
            print("QA issues:")
            for issue in issues:
                print(f"  - {issue}")
    print("=" * 72)
    overall = (qa_report or {}).get("overall_passed")
    if overall is not None:
        label = "all drafts passed QA" if overall else "some drafts need edits"
        print(f"\nQA overall: {label}\n")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Source and rank GitHub candidates from a job description"
    )
    parser.add_argument("--jd", required=True, help="Path to job description text file")
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Max number of candidates to research and rank (default: 5)",
    )
    parser.add_argument(
        "--outreach-n",
        type=int,
        default=3,
        help="Max number of shortlisted candidates to draft outreach for (default: 3)",
    )
    args = parser.parse_args()

    jd_path = Path(args.jd)
    if not jd_path.exists():
        print(f"JD file not found: {jd_path}", file=sys.stderr)
        sys.exit(1)

    graph = build_graph()
    result = graph.invoke(
        {
            "jd_text": jd_path.read_text(),
            "top_k": args.top_k,
            "outreach_n": args.outreach_n,
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
    )

    _print_table(result.get("ranked_shortlist") or [])
    _print_outreach(
        result.get("outreach_drafts") or [],
        result.get("qa_report") or {},
    )
    print("\nFull result JSON:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
