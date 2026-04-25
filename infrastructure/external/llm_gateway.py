import os
import json
from litellm import completion
from core.application.ports import LLMService

class LitellmGateway(LLMService):
    def __init__(self):
        self.extraction_model = os.environ.get("EXTRACTION_MODEL", "groq/llama3-8b-8192")
        self.scoring_model = os.environ.get("SCORING_MODEL", "groq/llama3-70b-8192")
        self.api_base = os.environ.get("OLLAMA_BASE_URL") if "ollama" in self.extraction_model else None

    def extract_information(self, text: str) -> dict:
        """Uses the fast extraction model"""
        prompt = f"""
        Extract the required skills from the following job description. 
        Return the result as a valid JSON object with a single key 'skills' containing a list of strings.
        
        Job Description:
        {text}
        
        JSON Output:
        """
        
        try:
            response = completion(
                model=self.extraction_model,
                messages=[{"role": "user", "content": prompt}],
                api_base=self.api_base,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            print(f"Error during extraction: {e}")
            return {"skills": []}

    def evaluate_fit(self, job_description: str, resume_or_profile: str) -> dict:
        """
        Uses the reasoning model to evaluate fit but the actual scoring logic 
        is delegated to core/services/scoring.py for the strict weights.
        This method will provide the reasoning summary.
        """
        prompt = f"""
        Evaluate the fit for the following job description based on the candidate's profile.
        Provide a concise reasoning summary (1-2 paragraphs) of why the candidate is or isn't a good fit.
        Do not calculate a numerical score.
        
        Candidate Profile:
        {resume_or_profile}
        
        Job Description:
        {job_description}
        
        Reasoning Summary:
        """
        
        try:
            response = completion(
                model=self.scoring_model,
                messages=[{"role": "user", "content": prompt}],
                api_base=self.api_base
            )
            summary = response.choices[0].message.content
            return {"reasoning_summary": summary.strip()}
        except Exception as e:
            print(f"Error during evaluation: {e}")
            return {"reasoning_summary": "Error evaluating fit."}
