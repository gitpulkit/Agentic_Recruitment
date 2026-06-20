import os

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from api.db import create_campaign, get_campaign, init_db, save_selection, save_send_results
from api.email import is_smtp_configured, send_campaign_emails
from api.jobs import run_campaign_job
from api.review import build_review_rows
from api.schemas import (
    CampaignResponse,
    CreateCampaignResponse,
    DraftPreview,
    EmailSettingsResponse,
    ExportResponse,
    QAPreview,
    ReviewRow,
    SelectionRequest,
    SendResponse,
    SendResultItem,
)

load_dotenv()

app = FastAPI(title="Agentic Recruiter API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def _to_response(campaign: dict) -> CampaignResponse:
    rows = []
    if campaign.get("result"):
        for row in build_review_rows(campaign["result"]):
            rows.append(
                ReviewRow(
                    username=row["username"],
                    score=row.get("score"),
                    rationale=row.get("rationale"),
                    profile_url=row.get("profile_url"),
                    name=row.get("name"),
                    email=row.get("email"),
                    draft=DraftPreview(**row["draft"]),
                    qa=QAPreview(**row["qa"]),
                )
            )

    send_results = None
    if campaign.get("send_results"):
        send_results = [SendResultItem(**item) for item in campaign["send_results"]]

    recipient_emails = campaign.get("recipient_emails")
    if recipient_emails:
        for row in rows:
            if row.username in recipient_emails:
                row.email = recipient_emails[row.username] or row.email

    return CampaignResponse(
        id=campaign["id"],
        status=campaign["status"],
        top_k=campaign["top_k"],
        outreach_n=campaign["outreach_n"],
        error=campaign.get("error"),
        rows=rows,
        selected_usernames=campaign.get("selected_usernames"),
        recipient_emails=recipient_emails,
        send_results=send_results,
        email_configured=is_smtp_configured(),
    )


def _selected_drafts(campaign: dict) -> list[dict]:
    selected = campaign.get("selected_usernames") or []
    drafts_by_user = {
        d["username"]: d
        for d in (campaign.get("result") or {}).get("outreach_drafts", [])
    }
    return [
        {
            "username": username,
            "subject": drafts_by_user[username].get("subject"),
            "body": drafts_by_user[username].get("body"),
        }
        for username in selected
        if username in drafts_by_user
    ]


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "email_configured": is_smtp_configured()}


@app.get("/settings/email", response_model=EmailSettingsResponse)
def email_settings() -> EmailSettingsResponse:
    return EmailSettingsResponse(
        configured=is_smtp_configured(),
        from_address=os.getenv("SMTP_FROM"),
    )


@app.post("/campaigns", response_model=CreateCampaignResponse)
async def create_campaign_endpoint(
    background_tasks: BackgroundTasks,
    jd_file: UploadFile = File(...),
    top_k: int = Form(5),
    outreach_n: int = Form(3),
) -> CreateCampaignResponse:
    jd_text = (await jd_file.read()).decode("utf-8")
    if not jd_text.strip():
        raise HTTPException(status_code=400, detail="Job description file is empty")

    campaign = create_campaign(jd_text, top_k=top_k, outreach_n=outreach_n)
    background_tasks.add_task(
        run_campaign_job,
        campaign["id"],
        jd_text,
        top_k,
        outreach_n,
    )
    return CreateCampaignResponse(id=campaign["id"], status=campaign["status"])


@app.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
def get_campaign_endpoint(campaign_id: str) -> CampaignResponse:
    campaign = get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return _to_response(campaign)


@app.post("/campaigns/{campaign_id}/selection", response_model=CampaignResponse)
def save_selection_endpoint(
    campaign_id: str, body: SelectionRequest
) -> CampaignResponse:
    campaign = get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    valid_usernames = {row.username for row in _to_response(campaign).rows}
    invalid = [u for u in body.usernames if u not in valid_usernames]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown usernames: {', '.join(invalid)}",
        )

    try:
        updated = save_selection(campaign_id, body.usernames, body.emails)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _to_response(updated)


@app.post("/campaigns/{campaign_id}/send", response_model=SendResponse)
def send_emails_endpoint(campaign_id: str) -> SendResponse:
    if not is_smtp_configured():
        raise HTTPException(
            status_code=400,
            detail="SMTP is not configured. Add SMTP_HOST and SMTP_FROM to .env",
        )

    campaign = get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign["status"] not in {"confirmed", "sent"}:
        raise HTTPException(
            status_code=400,
            detail="Confirm your candidate selection before sending emails",
        )

    drafts = _selected_drafts(campaign)
    if not drafts:
        raise HTTPException(status_code=400, detail="No drafts selected to send")

    recipient_emails = campaign.get("recipient_emails") or {}
    results = send_campaign_emails(drafts, recipient_emails)
    updated = save_send_results(campaign_id, results)

    return SendResponse(
        id=campaign_id,
        status=updated["status"],
        results=[SendResultItem(**item) for item in results],
    )


@app.get("/campaigns/{campaign_id}/export", response_model=ExportResponse)
def export_selection_endpoint(campaign_id: str) -> ExportResponse:
    campaign = get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign["status"] not in {"confirmed", "sent"}:
        raise HTTPException(
            status_code=400,
            detail="Campaign selection has not been confirmed yet",
        )

    selected = campaign.get("selected_usernames") or []
    drafts = _selected_drafts(campaign)

    return ExportResponse(
        id=campaign_id,
        selected_usernames=selected,
        drafts=drafts,
    )
