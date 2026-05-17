# Autonomous Tech Recruiter

A multi-agent system that simulates a full tech recruitment funnel: parse a job description, find and research candidates, rank fit, and draft personalized outreach.

This repo starts with a **hello-world pipeline** — one job description and one GitHub profile — built with [LangGraph](https://langchain-ai.github.io/langgraph/) and OpenAI.

**Continuing in a new chat?** Read [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) for product vision, architecture decisions, milestone status, and what to build next.

## What this hello world does

Given a JD file and a GitHub username, the graph runs three steps:

1. **parse_jd** — Extract structured requirements (skills, seniority, role title) from the job description.
2. **research_github** — Fetch profile and repo data from the GitHub API, then summarize into a recruiter brief.
3. **score_match** — Score the candidate 0–100 with strengths, gaps, and a short rationale.

```text
START → parse_jd → research_github → score_match → END
```

No sourcing, LinkedIn, email drafts, or UI yet — just the core “is this person a fit?” loop.

## Prerequisites

- Python 3.9+ (3.10+ recommended)
- An [OpenAI API key](https://platform.openai.com/api-keys)
- (Optional) A [GitHub personal access token](https://github.com/settings/tokens) for higher API rate limits

## Setup

```bash
cd agentic_recruitment

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY
```

Example `.env`:

```env
OPENAI_API_KEY=sk-your-key-here

# Optional — avoids GitHub rate limits (60 req/hr unauthenticated)
# GITHUB_TOKEN=ghp_your_token_here

# Optional — defaults to gpt-4o-mini
# OPENAI_MODEL=gpt-4o-mini
```

## Run

```bash
source .venv/bin/activate

python main.py --jd samples/jd.txt --github octocat
```

You can pass a username or a full profile URL:

```bash
python main.py --jd samples/jd.txt --github https://github.com/torvalds
```

Output is JSON printed to the terminal: `parsed_jd`, `profile_brief`, and `match_result`.

## Project layout

```text
agentic_recruitment/
├── main.py              # CLI entrypoint
├── graph/
│   ├── state.py         # Shared graph state (TypedDict)
│   ├── schemas.py       # Pydantic models for structured LLM output
│   ├── nodes.py         # parse_jd, research_github, score_match
│   └── workflow.py      # LangGraph definition
├── samples/
│   └── jd.txt           # Sample backend engineer JD
├── requirements.txt
└── .env.example
```

## How it fits the full product

| Phase | Scope |
|-------|--------|
| **Now (hello world)** | JD + one GitHub user → structured parse, profile brief, match score |
| **Next** | JD + multiple usernames → ranked table |
| **Later** | GitHub search sourcing, LinkedIn, outreach drafts, human approval UI |

The full vision is an autonomous recruiter: upload a JD, AI sources candidates, summarizes GitHub/LinkedIn profiles, and drafts personalized reach-out emails — with human gates before anything is sent.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `OPENAI_API_KEY` not set | Create `.env` from `.env.example` and add your key |
| GitHub `403` / rate limit | Add `GITHUB_TOKEN` to `.env` |
| Slow first run | Three LLM calls + GitHub API; typically under a minute |

## License

Private / learning project — add a license if you open-source it.
