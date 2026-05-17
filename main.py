import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from graph.workflow import build_graph


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Hello-world recruiter: JD + one GitHub profile → match score"
    )
    parser.add_argument("--jd", required=True, help="Path to job description text file")
    parser.add_argument(
        "--github",
        required=True,
        help="GitHub username or profile URL (e.g. octocat)",
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
            "github_username": args.github,
            "parsed_jd": None,
            "profile_brief": None,
            "match_result": None,
        }
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
