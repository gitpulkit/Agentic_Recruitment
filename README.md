# Autonomous Tech Recruiter

A multi-agent system that simulates a full tech recruitment funnel: parse a job description, find and research candidates, rank fit, and draft personalized outreach.

This repo starts with a **hello-world pipeline** — one job description and one GitHub profile — built with [LangGraph](https://langchain-ai.github.io/langgraph/) and OpenAI.

**Continuing in a new chat?** Read [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) for product vision, architecture decisions, milestone status, and what to build next.

## What this does

Given just a JD file, the graph sources candidates from GitHub and ranks them:

1. **parse_jd** — Extract structured requirements (skills, seniority, role title) from the job description.
2. **plan_search** — Turn the requirements into GitHub repository search queries.
3. **search_candidates** — Run the queries and collect repo owners as candidate usernames.
4. **research_and_score** — For each candidate (in parallel), fetch GitHub data, write a recruiter brief, and score the fit 0–100.
5. **rank** — Sort candidates by score into a shortlist.

```text
START → parse_jd → plan_search → search_candidates → (Send: research_and_score per candidate) → rank → END
```

The fan-out uses LangGraph's `Send` to run the research/score step for every candidate in parallel, and a list reducer (`operator.add`) to collect their results.

No LinkedIn, email drafts, or UI yet — this is the sourcing + ranking funnel.

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

python main.py --jd samples/jd.txt --top-k 5
```

`--top-k` caps how many candidates are researched and ranked (default 5). Keep it small to stay within GitHub search rate limits; a `GITHUB_TOKEN` in `.env` is strongly recommended.

Output is a ranked shortlist table plus the full result JSON (`parsed_jd`, `search_plan`, `candidate_usernames`, `ranked_shortlist`).

## Project layout

```text
agentic_recruitment/
├── main.py              # CLI entrypoint
├── graph/
│   ├── state.py         # Shared graph state (TypedDict + reducer)
│   ├── schemas.py       # Pydantic models for structured LLM output
│   ├── nodes.py         # parse_jd, plan_search, search_candidates, research_and_score, rank
│   └── workflow.py      # LangGraph definition (Send fan-out)
├── samples/
│   └── jd.txt           # Sample backend engineer JD
├── requirements.txt
└── .env.example
```

## How it fits the full product

| Phase | Scope |
|-------|--------|
| **Done** | JD → GitHub repo-search sourcing → parallel research/score → ranked shortlist |
| **Next** | Outreach draft + QA nodes; human approval checkpoints |
| **Later** | LinkedIn, persistence, API + UI |

The full vision is an autonomous recruiter: upload a JD, AI sources candidates, summarizes GitHub/LinkedIn profiles, and drafts personalized reach-out emails — with human gates before anything is sent.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `OPENAI_API_KEY` not set | Create `.env` from `.env.example` and add your key |
| GitHub `403` / rate limit | Add `GITHUB_TOKEN` to `.env`; lower `--top-k` |
| Empty shortlist | Search queries matched no user-owned repos; try a different JD or add `GITHUB_TOKEN` |
| Slow run | Several LLM + GitHub calls per candidate; keep `--top-k` small |

## License

Private / learning project — add a license if you open-source it.
