# Project context (session handoff)

**Last updated:** 2026-06-18  
**Status:** Milestone 4 complete — outreach draft + QA nodes on ranked shortlist (draft-only, no send).

Use this file when starting a **new Cursor chat** so the agent can pick up without re-explaining the product. Say: *“Read `PROJECT_CONTEXT.md` and continue from the next milestone.”*

---

## Product vision: Autonomous Tech Recruiter

User uploads a **Job Description**. AI autonomously:

1. Finds matching candidates  
2. Summarizes GitHub / LinkedIn profiles  
3. Drafts personalized reach-out emails  

**Human gates (planned):** approve search plan → approve shortlist → approve emails before send. v1 should **not** auto-send email.

---

## Architecture we agreed on (full product)

```text
JD upload → JD Analyst → [human: search plan] → Sourcer → Profile Researcher
         → Matcher → [human: shortlist] → Outreach Writer → QA → [human: emails]
```

| Layer | Choice |
|-------|--------|
| Orchestration | LangGraph for agent steps; Temporal later for long/async jobs |
| LLM | **OpenAI** (`gpt-4o-mini` default) — user has an API key |
| State | Shared `CampaignState` object in DB eventually; now in-memory per run |
| Outputs | Structured JSON (Pydantic), not free-form prose |
| Sourcing v1 | GitHub API only; LinkedIn deferred (ToS / manual upload later) |
| Matching | Hybrid later: embeddings + LLM rubric; hello world is LLM-only |

**Agent roles (future):** Supervisor, JD Analyst, Sourcer, Profile Researcher, Matcher, Outreach Writer, QA/Compliance.

**Framework note:** LangGraph = graph/steps/state; LangChain = LLM + structured output inside nodes. Start with linear pipeline, split into multiple agents only when each step is stable.

---

## What’s built now (Milestone 4)

**Scope:** One JD file → AI sources GitHub candidates, researches and scores them in parallel, returns a ranked shortlist, drafts personalized outreach emails for the top N, and QA-checks each draft. Draft-only — never auto-sends.

```text
START → parse_jd → plan_search → search_candidates
      → (Send: research_and_score per candidate) → rank
      → (Send: outreach_writer per shortlisted candidate) → qa → END
```

| File | Role |
|------|------|
| `main.py` | CLI: `--jd`, `--top-k`, `--outreach-n`; prints ranked table, outreach drafts, QA, JSON |
| `graph/workflow.py` | LangGraph with two `Send` fan-outs (research/score + outreach) |
| `graph/state.py` | `CampaignState`; reducers on `candidate_results` and `outreach_drafts` |
| `graph/schemas.py` | `ParsedJD`, `ProfileBrief`, `MatchResult`, `SearchPlan`, `OutreachDraft`, `QAReport` |
| `graph/nodes.py` | All pipeline nodes including `outreach_writer` and `qa` |
| `samples/jd.txt` | Sample backend engineer JD |

**Run:**

```bash
source .venv/bin/activate
python main.py --jd samples/jd.txt --top-k 5 --outreach-n 3
```

---

## Decisions & lessons from this session

1. **Learning path:** Fake agent (JD → JSON) → one-tool agent (GitHub) → linear LangGraph pipeline → multi-agent later.  
2. **Hello world intentionally skips:** sourcing, LinkedIn, email, UI, DB.  
3. **Python 3.9:** User’s venv is 3.9. Use `Optional[str]` not `str | None` in Pydantic models (`graph/schemas.py`, `graph/state.py`).  
4. **OpenAI 429 `insufficient_quota`:** Not request rate limits — billing/credits. Fix at platform.openai.com billing/usage.  
5. **GitHub:** Unauthenticated works but rate-limits quickly; `GITHUB_TOKEN` strongly recommended for M3 (parallel workers + `/search` endpoints hit limits fast). Keep `--top-k` small.  
6. **Sourcing = repo owners:** GitHub user search matches name/bio poorly, so we search repos (`/search/repositories` by language/topic/stars) and take user-type owners.  
7. **LangGraph fan-out:** `from langgraph.types import Send` (not `langgraph.constants`, deprecated). `Send("node", payload)` runs the node once per item; payload becomes that node's state. Accumulator field must use a reducer (`Annotated[List, operator.add]`) or parallel writes overwrite each other.  
8. **Worker resilience:** `research_and_score` wraps GitHub/LLM calls in try/except so one failed candidate doesn't abort the whole run.

---

## Environment

```env
OPENAI_API_KEY=...          # required
GITHUB_TOKEN=...              # optional
OPENAI_MODEL=gpt-4o-mini      # optional
```

`.env` is gitignored. `.env.example` is the template.

---

## Roadmap (ordered)

| Milestone | Scope | Status |
|-----------|--------|--------|
| **M1** | JD + 1 GitHub user → parse, brief, score (LangGraph) | **Done** |
| **M2** | JD + N usernames → ranked table | **Done** (absorbed into M3) |
| **M3** | GitHub repo-search sourcing: JD → queries → top K owners → parallel research/score → rank | **Done** |
| **M4** | Outreach draft node + QA node (draft-only, no send) | **Done** |
| **M5** | Human approval checkpoints (LangGraph `interrupt`) | Next |
| **M6** | API + UI + persistence (Postgres) | |

**Suggested M5 implementation:**

- Add LangGraph `interrupt` after `plan_search` (approve search plan), after `rank` (approve shortlist), and after `qa` (approve emails).
- Resume graph with human-edited state when checkpoints pass.

---

## Repo layout

```text
agentic_recruitment/
├── PROJECT_CONTEXT.md    ← this file (session handoff)
├── README.md             ← how to run
├── main.py
├── graph/
│   ├── workflow.py
│   ├── state.py
│   ├── schemas.py
│   └── nodes.py
├── samples/jd.txt
├── requirements.txt
└── .env.example
```

---

## Open questions (pick up later)

- [ ] Recreate venv on Python 3.11+ to avoid LibreSSL / typing warnings?  
- [ ] Add friendlier error in `main.py` for `insufficient_quota` vs `rate_limit_exceeded`?  
- [ ] LangSmith tracing for debugging graph runs?  
- [ ] When to split nodes into separate “agent” modules vs keep one `nodes.py`?

---

## For the next agent session

1. Read this file + skim `graph/workflow.py` and `graph/nodes.py`.  
2. Continue from **M5 (human approval checkpoints)** unless the user asks otherwise.  
3. Do not rebuild M1–M4 unless user asks — they’re working.
