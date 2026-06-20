# Autonomous Tech Recruiter

A multi-agent system that simulates a full tech recruitment funnel: parse a job description, find and research candidates, rank fit, and draft personalized outreach.

This repo starts with a **hello-world pipeline** — one job description and one GitHub profile — built with [LangGraph](https://langchain-ai.github.io/langgraph/) and OpenAI.

**Continuing in a new chat?** Read [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) for product vision, architecture decisions, milestone status, and what to build next.

## What this does

Given just a JD file, the graph sources candidates from GitHub, ranks them, and drafts outreach emails:

1. **parse_jd** — Extract structured requirements (skills, seniority, role title) from the job description.
2. **plan_search** — Turn the requirements into GitHub repository search queries.
3. **search_candidates** — Run the queries and collect repo owners as candidate usernames.
4. **research_and_score** — For each candidate (in parallel), fetch GitHub data, write a recruiter brief, and score the fit 0–100.
5. **rank** — Sort candidates by score into a shortlist.
6. **outreach_writer** — For the top N shortlisted candidates (in parallel), draft a personalized recruiter email citing profile highlights.
7. **qa** — Check each draft for unsupported claims and tone issues before human review.

```text
START → parse_jd → plan_search → search_candidates
      → (Send: research_and_score per candidate) → rank
      → (Send: outreach_writer per shortlisted candidate) → qa → END
```

The fan-out uses LangGraph's `Send` for parallel workers and list reducers (`operator.add`) to collect results. Emails are **draft-only** — nothing is sent automatically.

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

python main.py --jd samples/jd.txt --top-k 5 --outreach-n 3
```

`--top-k` caps how many candidates are researched and ranked (default 5). `--outreach-n` caps how many get outreach drafts (default 3). Keep both small to stay within GitHub search rate limits; a `GITHUB_TOKEN` in `.env` is strongly recommended.

Output is a ranked shortlist table, outreach drafts with QA status, plus the full result JSON.

## Web UI (recruiter review)

Run the API and UI in two terminals:

```bash
source .venv/bin/activate
pip install -r requirements.txt

# Terminal 1 — API on :8000
uvicorn api.main:app --reload --port 8000

# Terminal 2 — UI on :5173
cd ui
npm install
npm run dev
```

Open `http://localhost:5173`, upload a JD file, wait for the pipeline to finish, then:

1. **Review** candidates in the card grid
2. **Check** who should receive outreach and enter their email (or use a public GitHub email if shown)
3. **Open in Gmail** — opens a pre-filled compose window in your browser; sign in if needed, then click **Send** in Gmail

Optional: configure SMTP in `.env` to send automatically from the app without opening Gmail.

### Send via Gmail (recommended)

No extra setup. After selecting candidates and adding emails, click **Open in Gmail** for each person. Gmail opens with To, Subject, and Body filled in. You stay in control and press Send yourself.

### Email setup (optional SMTP)

Add these to `.env` and restart the API:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=your@gmail.com
SMTP_USE_TLS=true
```

For Gmail, create an [App Password](https://myaccount.google.com/apppasswords). Most candidates won't have a public GitHub email — you'll need to add addresses manually in the UI.

API endpoints:

- `POST /campaigns` — upload JD, start background run
- `GET /campaigns/{id}` — poll status and review rows
- `POST /campaigns/{id}/selection` — save selected usernames + recipient emails
- `POST /campaigns/{id}/send` — send outreach to saved recipients via SMTP
- `GET /settings/email` — check whether SMTP is configured

Campaign results are stored in `data/campaigns.db` (SQLite, local dev).

## Project layout

```text
agentic_recruitment/
├── main.py              # CLI entrypoint
├── api/
│   ├── main.py          # FastAPI app
│   ├── db.py            # SQLite campaign storage
│   ├── jobs.py          # Background graph runs
│   └── review.py        # Merge shortlist + drafts for UI rows
├── graph/
│   ├── runner.py        # Shared graph invoke helper
│   ├── state.py         # Shared graph state (TypedDict + reducer)
│   ├── schemas.py       # Pydantic models for structured LLM output
│   ├── nodes.py         # parse_jd … rank, outreach_writer, qa
│   └── workflow.py      # LangGraph definition (Send fan-out)
├── ui/                  # React recruiter review app (Vite)
├── samples/
│   └── jd.txt           # Sample backend engineer JD
├── requirements.txt
└── .env.example
```

## How it fits the full product

| Phase | Scope |
|-------|--------|
| **Done** | JD → GitHub sourcing → rank → outreach drafts + QA (draft-only) |
| **Done** | FastAPI + SQLite campaigns + recruiter checkbox UI |
| **Done** | SMTP email send for selected candidates |
| **Next** | Better candidate email discovery, auth, Postgres |

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
