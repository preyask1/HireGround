from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from core.application.ports import JobRepository
from core.domain.models import Job, JobDetails, Score, JobStatus
from infrastructure.persistence.models import Base, JobPostingModel, JobDetailsModel, ScoreModel, CompanyModel

class SQLiteJobRepository(JobRepository):
    def __init__(self, db_path: str = "sqlite:///hireground.db"):
        self.engine = create_engine(db_path)
        Base.metadata.create_all(self.engine)

    def _to_domain_job(self, model: JobPostingModel) -> Job:
        details = None
        if model.details:
            details = JobDetails(
                job_id=model.id,
                raw_description=model.details.raw_description,
                parsed_skills=model.details.parsed_skills_list
            )
        
        return Job(
            id=model.id,
            company_id=model.company_id,
            title=model.title,
            location=model.location,
            url=model.url,
            posted_date=model.posted_date,
            status=model.status,
            details=details
        )

    def save_job(self, job: Job) -> Job:
        with Session(self.engine) as session:
            db_job = session.query(JobPostingModel).filter_by(url=job.url).first()
            if not db_job:
                db_job = JobPostingModel(
                    company_id=job.company_id,
                    title=job.title,
                    location=job.location,
                    url=job.url,
                    posted_date=job.posted_date,
                    status=job.status
                )
                session.add(db_job)
                session.flush() # To get the id
            else:
                db_job.title = job.title
                db_job.location = job.location
                db_job.status = job.status
                db_job.company_id = job.company_id

            if job.details:
                db_details = session.query(JobDetailsModel).filter_by(job_id=db_job.id).first()
                if not db_details:
                    db_details = JobDetailsModel(
                        job_id=db_job.id,
                        raw_description=job.details.raw_description,
                        parsed_skills_list=job.details.parsed_skills
                    )
                    session.add(db_details)
                else:
                    db_details.raw_description = job.details.raw_description
                    db_details.parsed_skills_list = job.details.parsed_skills
            
            session.commit()
            session.refresh(db_job)
            return self._to_domain_job(db_job)

    def get_job_by_url(self, url: str) -> Optional[Job]:
        with Session(self.engine) as session:
            db_job = session.query(JobPostingModel).filter_by(url=url).first()
            if db_job:
                return self._to_domain_job(db_job)
            return None

    def get_jobs_by_status(self, status: JobStatus) -> List[Job]:
        with Session(self.engine) as session:
            db_jobs = session.query(JobPostingModel).filter_by(status=status).all()
            return [self._to_domain_job(db_job) for db_job in db_jobs]

    def update_job_status(self, job_id: int, status: JobStatus) -> None:
        with Session(self.engine) as session:
            db_job = session.query(JobPostingModel).filter_by(id=job_id).first()
            if db_job:
                db_job.status = status
                session.commit()

    def save_score(self, score: Score) -> Score:
        with Session(self.engine) as session:
            db_score = session.query(ScoreModel).filter_by(job_id=score.job_id).first()
            if not db_score:
                db_score = ScoreModel(
                    job_id=score.job_id,
                    model_name=score.model_name,
                    fit_score=score.fit_score,
                    reasoning_summary=score.reasoning_summary
                )
                session.add(db_score)
            else:
                db_score.model_name = score.model_name
                db_score.fit_score = score.fit_score
                db_score.reasoning_summary = score.reasoning_summary
            
            session.commit()
            session.refresh(db_score)
            score.id = db_score.id
            return score

    def get_score_for_job(self, job_id: int) -> Optional[Score]:
        with Session(self.engine) as session:
            db_score = session.query(ScoreModel).filter_by(job_id=job_id).first()
            if db_score:
                return Score(
                    id=db_score.id,
                    job_id=db_score.job_id,
                    model_name=db_score.model_name,
                    fit_score=db_score.fit_score,
                    reasoning_summary=db_score.reasoning_summary,
                    created_at=db_score.created_at
                )
            return None
