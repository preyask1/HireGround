from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import json

from core.domain.models import JobStatus

Base = declarative_base()

class CompanyModel(Base):
    __tablename__ = 'companies'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    industry = Column(String, nullable=True)
    website = Column(String, nullable=True)
    
    jobs = relationship("JobPostingModel", back_populates="company")


class JobPostingModel(Base):
    __tablename__ = 'job_postings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=True)
    title = Column(String, nullable=False)
    location = Column(String, nullable=True)
    url = Column(String, unique=True, nullable=False)
    posted_date = Column(Date, nullable=True)
    status = Column(Enum(JobStatus), default=JobStatus.DISCOVERED, nullable=False)
    
    company = relationship("CompanyModel", back_populates="jobs")
    details = relationship("JobDetailsModel", back_populates="job", uselist=False, cascade="all, delete-orphan")
    score = relationship("ScoreModel", back_populates="job", uselist=False, cascade="all, delete-orphan")
    application = relationship("ApplicationModel", back_populates="job", uselist=False, cascade="all, delete-orphan")


class JobDetailsModel(Base):
    __tablename__ = 'job_details'
    
    job_id = Column(Integer, ForeignKey('job_postings.id'), primary_key=True)
    raw_description = Column(Text, nullable=False)
    parsed_skills = Column(Text, nullable=True) # Stored as JSON string
    
    job = relationship("JobPostingModel", back_populates="details")
    
    @property
    def parsed_skills_list(self):
        if self.parsed_skills:
            return json.loads(self.parsed_skills)
        return []

    @parsed_skills_list.setter
    def parsed_skills_list(self, value):
        self.parsed_skills = json.dumps(value) if value else None


class ScoreModel(Base):
    __tablename__ = 'scores'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey('job_postings.id'), nullable=False)
    model_name = Column(String, nullable=False)
    fit_score = Column(Integer, nullable=False)
    reasoning_summary = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    job = relationship("JobPostingModel", back_populates="score")


class ApplicationModel(Base):
    __tablename__ = 'applications'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey('job_postings.id'), nullable=False)
    applied_date = Column(Date, nullable=False)
    resume_version_used = Column(String, nullable=True)
    
    job = relationship("JobPostingModel", back_populates="application")
