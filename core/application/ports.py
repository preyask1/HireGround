from abc import ABC, abstractmethod
from typing import List, Optional
from core.domain.models import Job, Company, Score, Application, JobStatus

class JobRepository(ABC):
    @abstractmethod
    def save_job(self, job: Job) -> Job:
        pass

    @abstractmethod
    def get_job_by_url(self, url: str) -> Optional[Job]:
        pass

    @abstractmethod
    def get_jobs_by_status(self, status: JobStatus) -> List[Job]:
        pass

    @abstractmethod
    def update_job_status(self, job_id: int, status: JobStatus) -> None:
        pass

    @abstractmethod
    def save_score(self, score: Score) -> Score:
        pass
        
    @abstractmethod
    def get_score_for_job(self, job_id: int) -> Optional[Score]:
        pass

class BrowserService(ABC):
    @abstractmethod
    def start_session(self) -> None:
        pass
        
    @abstractmethod
    def navigate(self, url: str) -> None:
        pass
        
    @abstractmethod
    def extract_job_details(self, url: str) -> dict:
        pass
        
    @abstractmethod
    def close_session(self) -> None:
        pass

class LLMService(ABC):
    @abstractmethod
    def extract_information(self, text: str) -> dict:
        """Uses the fast extraction model"""
        pass
        
    @abstractmethod
    def evaluate_fit(self, job_description: str, resume: str) -> dict:
        """Uses the reasoning model to return score and summary"""
        pass
