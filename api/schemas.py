from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CreateCampaignResponse(BaseModel):
    id: str
    status: str


class DraftPreview(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    personalization_hooks: List[str] = Field(default_factory=list)


class QAPreview(BaseModel):
    passed: bool = False
    severity: str = "unknown"
    issues: List[str] = Field(default_factory=list)


class ReviewRow(BaseModel):
    username: str
    score: Optional[int] = None
    rationale: Optional[str] = None
    profile_url: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    draft: DraftPreview
    qa: QAPreview


class SendResultItem(BaseModel):
    username: str
    status: str
    detail: str
    email: Optional[str] = None


class CampaignResponse(BaseModel):
    id: str
    status: str
    top_k: int
    outreach_n: int
    error: Optional[str] = None
    rows: List[ReviewRow] = Field(default_factory=list)
    selected_usernames: Optional[List[str]] = None
    recipient_emails: Optional[Dict[str, str]] = None
    send_results: Optional[List[SendResultItem]] = None
    email_configured: bool = False


class SelectionRequest(BaseModel):
    usernames: List[str]
    emails: Dict[str, str] = Field(default_factory=dict)


class ExportResponse(BaseModel):
    id: str
    selected_usernames: List[str]
    drafts: List[dict]


class EmailSettingsResponse(BaseModel):
    configured: bool
    from_address: Optional[str] = None


class SendResponse(BaseModel):
    id: str
    status: str
    results: List[SendResultItem]
