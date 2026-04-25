import re
from core.domain.models import JobDetails, Score
from core.application.ports import LLMService

class AnalystScoringService:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

        self.keyword_weights = {
            "RAG": 20,
            "AI Agents": 20,
            "Enterprise Data Warehouse": 20,
            "EDW": 20,
            "Databricks": 20,
            "MCP": 20
        }
        
        self.methodology_weights = {
            "Lean Six Sigma": 15,
            "Agile": 15,
            "Scrum": 15,
            "Kanban": 15,
            "SAFe": 15
        }
        
        self.experience_weights = {
            "Senior": 10,
            "10+ years": 10,
            "Consulting": 10
        }

        self.penalty_keywords = [
            "Junior", "Internship", "Intern"
        ]
        
    def _calculate_score(self, description: str, location: str) -> int:
        score = 0
        desc_lower = description.lower()
        
        # Add Keywords
        for kw, weight in self.keyword_weights.items():
            if kw.lower() in desc_lower:
                score += weight
                
        # Add Methodologies
        for kw, weight in self.methodology_weights.items():
            if kw.lower() in desc_lower:
                score += weight
                
        # Add Experience
        for kw, weight in self.experience_weights.items():
            if kw.lower() in desc_lower:
                score += weight
                
        # Apply Penalties for role level
        for kw in self.penalty_keywords:
            if kw.lower() in desc_lower:
                score -= 50
                break # Apply penalty once
                
        # Apply Location Penalty (must be Jaipur or Remote, else penalty)
        loc_lower = location.lower() if location else ""
        if "jaipur" not in loc_lower and "remote" not in loc_lower:
            score -= 50
            
        return min(max(score, 0), 100) # Clamp between 0 and 100

    def score_job(self, job_id: int, job_description: str, location: str, profile_summary: str = "Senior Product Manager with AI/Data experience") -> Score:
        # Calculate algorithmic score
        fit_score = self._calculate_score(job_description, location)
        
        # Get reasoning from LLM
        eval_result = self.llm_service.evaluate_fit(job_description, profile_summary)
        
        return Score(
            job_id=job_id,
            model_name=self.llm_service.scoring_model if hasattr(self.llm_service, 'scoring_model') else "custom-eval",
            fit_score=fit_score,
            reasoning_summary=eval_result.get("reasoning_summary", "No reasoning provided.")
        )
