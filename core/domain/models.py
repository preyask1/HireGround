from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime, date

class JobStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    SCORED = "SCORED"
    REJECTED = "REJECTED"
    APPROVED = "APPROVED"
    APPLIED = "APPLIED"

class Company(BaseModel):
    id: Optional[int] = None
    name: str
    industry: Optional[str] = None
    website: Optional[str] = None

class JobDetails(BaseModel):
    job_id: Optional[int] = None
    raw_description: str
    parsed_skills: Optional[List[str]] = Field(default_factory=list)

class Job(BaseModel):
    id: Optional[int] = None
    company_id: Optional[int] = None
    title: str
    location: Optional[str] = None
    url: str
    posted_date: Optional[date] = None
    status: JobStatus = JobStatus.DISCOVERED
    details: Optional[JobDetails] = None

class Score(BaseModel):
    id: Optional[int] = None
    job_id: int
    model_name: str
    fit_score: int = Field(ge=0, le=100)
    reasoning_summary: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Application(BaseModel):
    id: Optional[int] = None
    job_id: int
    applied_date: date = Field(default_factory=date.today)
    resume_version_used: Optional[str] = None
