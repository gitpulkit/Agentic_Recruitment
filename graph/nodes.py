import os
from collections import Counter

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from graph.schemas import MatchResult, OutreachDraft, ParsedJD, ProfileBrief, QAReport, SearchPlan

GITHUB_API = "https://api.github.com"


def _llm() -> ChatOpenAI:
    return ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)


def _github_headers() -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


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


def plan_search_node(state: dict) -> dict:
    llm = _llm().with_structured_output(SearchPlan)
    plan: SearchPlan = llm.invoke(
        [
            SystemMessage(
                content=(
                    "You turn structured hiring requirements into GitHub repository "
                    "search queries to find candidates who maintain relevant projects. "
                    "Produce 2-4 focused queries using qualifiers like language:, "
                    "topic:, and stars:. Prefer must-have skills. Return query strings "
                    "only (no URLs)."
                )
            ),
            HumanMessage(content=f"Parsed JD:\n{state['parsed_jd']}"),
        ]
    )
    return {"search_plan": plan.model_dump()}


def _search_repositories(query: str, per_page: int = 10) -> list[dict]:
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(
            f"{GITHUB_API}/search/repositories",
            headers=_github_headers(),
            params={"q": query, "sort": "stars", "order": "desc", "per_page": per_page},
        )
        resp.raise_for_status()
        return resp.json().get("items", [])


def search_candidates_node(state: dict) -> dict:
    top_k = state.get("top_k", 5)
    plan = state.get("search_plan") or {}
    queries = plan.get("queries", [])

    usernames: list[str] = []
    seen: set[str] = set()

    for query in queries:
        try:
            repos = _search_repositories(query, per_page=10)
        except httpx.HTTPError:
            continue

        for repo in repos:
            owner = repo.get("owner") or {}
            if owner.get("type") != "User":
                continue
            login = owner.get("login")
            if login and login not in seen:
                seen.add(login)
                usernames.append(login)

        if len(usernames) >= top_k:
            break

    return {"candidate_usernames": usernames[:top_k]}


def _fetch_github_user(username: str) -> dict:
    with httpx.Client(timeout=30.0) as client:
        user_resp = client.get(
            f"{GITHUB_API}/users/{username}", headers=_github_headers()
        )
        user_resp.raise_for_status()
        user = user_resp.json()

        repos_resp = client.get(
            f"{GITHUB_API}/users/{username}/repos",
            headers=_github_headers(),
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


def _build_profile_brief(username: str) -> dict:
    data = _fetch_github_user(username)
    user = data["user"]
    repos = data["repos"]

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

    return {**brief.model_dump(), "profile_url": user.get("html_url")}


def _score(parsed_jd: dict, profile_brief: dict) -> dict:
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
                    f"Parsed JD:\n{parsed_jd}\n\nProfile brief:\n{profile_brief}"
                )
            ),
        ]
    )
    return result.model_dump()


def research_and_score_node(state: dict) -> dict:
    username = state["username"]
    try:
        brief = _build_profile_brief(username)
        match = _score(state["parsed_jd"], brief)
        result = {
            "username": username,
            "profile_brief": brief,
            "match_result": match,
        }
    except (httpx.HTTPError, KeyError) as exc:
        result = {
            "username": username,
            "profile_brief": None,
            "match_result": None,
            "error": str(exc),
        }
    return {"candidate_results": [result]}


def rank_node(state: dict) -> dict:
    results = state.get("candidate_results", [])

    def score_of(item: dict) -> int:
        match = item.get("match_result") or {}
        return match.get("score", -1)

    ranked = sorted(results, key=score_of, reverse=True)
    return {"ranked_shortlist": ranked}


def outreach_writer_node(state: dict) -> dict:
    candidate = state["candidate"]
    username = candidate["username"]
    profile_brief = candidate.get("profile_brief") or {}
    match_result = candidate.get("match_result") or {}

    llm = _llm().with_structured_output(OutreachDraft)
    draft: OutreachDraft = llm.invoke(
        [
            SystemMessage(
                content=(
                    "You draft personalized recruiter outreach emails for GitHub candidates. "
                    "Cite specific highlights from the profile brief. "
                    "Do not invent employers, projects, skills, or achievements. "
                    "Keep tone warm and professional, not salesy. "
                    "This is a draft for human review only — never imply the email was sent."
                )
            ),
            HumanMessage(
                content=(
                    f"Job description excerpt:\n{state['jd_text'][:1200]}\n\n"
                    f"Parsed JD:\n{state['parsed_jd']}\n\n"
                    f"Candidate username: {username}\n"
                    f"Profile brief:\n{profile_brief}\n\n"
                    f"Match strengths:\n{match_result.get('strengths', [])}\n"
                    f"Match rationale:\n{match_result.get('rationale', '')}"
                )
            ),
        ]
    )

    return {
        "outreach_drafts": [
            {
                **draft.model_dump(),
                "username": username,
                "profile_brief": profile_brief,
            }
        ]
    }


def qa_node(state: dict) -> dict:
    drafts = state.get("outreach_drafts") or []
    if not drafts:
        return {
            "qa_report": {
                "results": [],
                "overall_passed": True,
            }
        }

    draft_blocks = []
    for draft in drafts:
        draft_blocks.append(
            f"--- {draft.get('username', '?')} ---\n"
            f"Subject: {draft.get('subject', '')}\n"
            f"Body:\n{draft.get('body', '')}\n"
            f"Personalization hooks: {draft.get('personalization_hooks', [])}\n"
            f"Profile brief (source of truth):\n{draft.get('profile_brief', {})}"
        )

    llm = _llm().with_structured_output(QAReport)
    report: QAReport = llm.invoke(
        [
            SystemMessage(
                content=(
                    "You QA recruiter outreach email drafts before a human sends them. "
                    "Flag unsupported claims that are not backed by the profile brief. "
                    "Flag spammy, overly familiar, or misleading tone. "
                    "Mark severity 'major' for fabricated facts; 'minor' for tone tweaks. "
                    "passed=True only when the draft is factually grounded and send-ready "
                    "after human review."
                )
            ),
            HumanMessage(content="\n\n".join(draft_blocks)),
        ]
    )

    return {"qa_report": report.model_dump()}
