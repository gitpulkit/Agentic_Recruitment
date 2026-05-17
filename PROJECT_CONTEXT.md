# Project context (session handoff)

**Last updated:** 2026-05-16  
**Status:** Milestone 1 complete — LangGraph hello world runs end-to-end.

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

## What’s built now (Milestone 1)

**Scope:** One JD file + one GitHub username → JSON with `parsed_jd`, `profile_brief`, `match_result`.

```text
START → parse_jd → research_github → score_match → END
```

| File | Role |
|------|------|
| `main.py` | CLI: `--jd` and `--github` |
| `graph/workflow.py` | LangGraph `StateGraph` definition |
| `graph/state.py` | `CampaignState` TypedDict |
| `graph/schemas.py` | `ParsedJD`, `ProfileBrief`, `MatchResult` (Pydantic) |
| `graph/nodes.py` | Three nodes: LLM parse, GitHub fetch + LLM brief, LLM score |
| `samples/jd.txt` | Sample backend engineer JD |

**Run:**

```bash
source .venv/bin/activate
python main.py --jd samples/jd.txt --github octocat
```

See `README.md` for setup (venv, `.env`, optional `GITHUB_TOKEN`).

---

## Decisions & lessons from this session

1. **Learning path:** Fake agent (JD → JSON) → one-tool agent (GitHub) → linear LangGraph pipeline → multi-agent later.  
2. **Hello world intentionally skips:** sourcing, LinkedIn, email, UI, DB.  
3. **Python 3.9:** User’s venv is 3.9. Use `Optional[str]` not `str | None` in Pydantic models (`graph/schemas.py`, `graph/state.py`).  
4. **OpenAI 429 `insufficient_quota`:** Not request rate limits — billing/credits. Fix at platform.openai.com billing/usage.  
5. **GitHub:** Unauthenticated works but rate-limits quickly; optional `GITHUB_TOKEN` in `.env`.

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
| **M2** | JD + N usernames (CLI list or file) → ranked table | Next |
| **M3** | GitHub search tool: JD → queries → top K users → rank | |
| **M4** | Outreach draft node + QA node | |
| **M5** | Human approval checkpoints (LangGraph `interrupt`) | |
| **M6** | API + UI + persistence (Postgres) | |

**Suggested M2 implementation:**

- Accept `--github user1,user2,user3` or `--candidates candidates.txt`  
- Loop `research_github` + `score_match` per user (or map as parallel nodes)  
- Print sorted table by `match_result.score`

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
2. Confirm with user whether to start **M2 (multi-candidate rank)** or **M3 (GitHub search sourcing)**.  
3. Do not rebuild M1 unless user asks — it’s working.
