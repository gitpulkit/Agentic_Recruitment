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
            "parsed_jd": None,
            "search_plan": None,
            "candidate_usernames": [],
            "candidate_results": [],
            "ranked_shortlist": None,
            "username": None,
        }
    )

    _print_table(result.get("ranked_shortlist") or [])
    print("\nFull result JSON:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
