import os
from collections import Counter

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from graph.schemas import MatchResult, ParsedJD, ProfileBrief

GITHUB_API = "https://api.github.com"


def _llm() -> ChatOpenAI:
    return ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)


def parse_jd_node(state: dict) -> dict:
    llm = _llm().with_structured_output(ParsedJD)
    parsed: ParsedJD = llm.invoke(
        [
            SystemMessage(
                content=(
                    "You extract structured hiring requirements from job descriptions. "
                    "Use only information stated or clearly implied in the JD."
                )
            ),
            HumanMessage(content=f"Job description:\n\n{state['jd_text']}"),
        ]
    )
    return {"parsed_jd": parsed.model_dump()}


def _fetch_github_user(username: str) -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with httpx.Client(timeout=30.0) as client:
        user_resp = client.get(f"{GITHUB_API}/users/{username}", headers=headers)
        user_resp.raise_for_status()
        user = user_resp.json()

        repos_resp = client.get(
            f"{GITHUB_API}/users/{username}/repos",
            headers=headers,
            params={"sort": "updated", "per_page": 10},
        )
        repos_resp.raise_for_status()
        repos = repos_resp.json()

    return {"user": user, "repos": repos}


def _infer_languages(repos: list[dict]) -> list[str]:
    counts: Counter[str] = Counter()
    for repo in repos:
        lang = repo.get("language")
        if lang:
            counts[lang] += 1
    return [lang for lang, _ in counts.most_common(5)]


def research_github_node(state: dict) -> dict:
    username = state["github_username"].strip().lstrip("@")
    if "github.com/" in username:
        username = username.rstrip("/").split("github.com/")[-1].split("/")[0]

    data = _fetch_github_user(username)
    user = data["user"]
    repos = data["repos"]

    top_repos = [r["name"] for r in repos[:5]]
    languages = _infer_languages(repos)

    repo_lines = "\n".join(
        f"- {r['name']}: {r.get('description') or 'No description'} "
        f"(stars: {r.get('stargazers_count', 0)}, language: {r.get('language')})"
        for r in repos[:8]
    )

    llm = _llm().with_structured_output(ProfileBrief)
    brief: ProfileBrief = llm.invoke(
        [
            SystemMessage(
                content=(
                    "Summarize this GitHub profile for a recruiter. "
                    "Only use facts from the provided data. "
                    "Highlights must cite specific repos or profile fields."
                )
            ),
            HumanMessage(
                content=(
                    f"Username: {user.get('login')}\n"
                    f"Name: {user.get('name')}\n"
                    f"Bio: {user.get('bio')}\n"
                    f"Location: {user.get('location')}\n"
                    f"Public repos: {user.get('public_repos')}\n"
                    f"Followers: {user.get('followers')}\n"
                    f"Inferred languages: {', '.join(languages) or 'unknown'}\n\n"
                    f"Repositories:\n{repo_lines}"
                )
            ),
        ]
    )

    return {
        "profile_brief": {
            **brief.model_dump(),
            "profile_url": user.get("html_url"),
        }
    }


def score_match_node(state: dict) -> dict:
    llm = _llm().with_structured_output(MatchResult)
    result: MatchResult = llm.invoke(
        [
            SystemMessage(
                content=(
                    "Score how well a candidate fits a job. "
                    "Be honest about gaps. Score 0-100. "
                    "Base strengths and gaps only on the provided JD and profile."
                )
            ),
            HumanMessage(
                content=(
                    f"Parsed JD:\n{state['parsed_jd']}\n\n"
                    f"Profile brief:\n{state['profile_brief']}"
                )
            ),
        ]
    )
    return {"match_result": result.model_dump()}
