from typing import Optional

from pydantic import BaseModel, Field


class ParsedJD(BaseModel):
    role_title: str = Field(description="Job title or closest match")
    must_have_skills: list[str] = Field(description="Required technical skills")
    nice_to_have_skills: list[str] = Field(default_factory=list)
    seniority: str = Field(description="e.g. junior, mid, senior, staff")
    summary: str = Field(description="One-sentence role summary")


class ProfileBrief(BaseModel):
    username: str
    name: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    public_repos: int = 0
    followers: int = 0
    top_repos: list[str] = Field(description="Up to 5 notable repo names")
    languages: list[str] = Field(description="Languages inferred from repos")
    highlights: list[str] = Field(description="3-5 bullet highlights with evidence")


class MatchResult(BaseModel):
    score: int = Field(ge=0, le=100, description="Fit score 0-100")
    strengths: list[str]
    gaps: list[str]
    rationale: str = Field(description="2-3 sentence explanation")


class SearchPlan(BaseModel):
    queries: list[str] = Field(
        description=(
            "GitHub repository search queries derived from the JD, e.g. "
            "'language:python topic:fastapi stars:>50'. Use qualifiers like "
            "language:, topic:, and stars: to find relevant projects."
        )
    )
    rationale: str = Field(description="Why these queries match the JD")
