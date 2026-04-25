import time
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from core.domain.models import JobStatus
from infrastructure.persistence.repository import SQLiteJobRepository

class ApplyAdapter:
    def __init__(self, user_data_dir: str):
        self.user_data_dir = user_data_dir
        self.repo = SQLiteJobRepository()

    def process_approved_jobs(self):
        jobs = self.repo.get_jobs_by_status(JobStatus.APPROVED)
        if not jobs:
            print("No approved jobs to apply to.")
            return

        with sync_playwright() as p:
            browser_context = p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox"
                ]
            )
            
            page = browser_context.new_page()
            stealth_sync(page)
            
            for job in jobs:
                print(f"Applying for: {job.title} at {job.url}")
                try:
                    self._apply_to_job(page, job)
                    self.repo.update_job_status(job.id, JobStatus.APPLIED)
                    print(f"Successfully applied to {job.id}")
                except Exception as e:
                    print(f"Failed to apply to {job.id}: {e}")
                    
            browser_context.close()

    def _apply_to_job(self, page, job):
        page.goto(job.url)
        page.wait_for_load_state("networkidle")
        
        # Look for the Easy Apply button
        easy_apply_button = page.locator("button.jobs-apply-button")
        if easy_apply_button.count() > 0:
            easy_apply_button.first.click()
            
            # Auto-fill logic loop
            # This is highly dependent on the form structure and often requires iterative next button clicks
            for _ in range(10): # Prevent infinite loops
                time.sleep(2)
                # If there's a submit application button, click it
                submit_button = page.locator("button[aria-label='Submit application']")
                if submit_button.count() > 0:
                    submit_button.first.click()
                    break
                    
                # Otherwise, click next
                next_button = page.locator("button[aria-label='Continue to next step']")
                if next_button.count() > 0:
                    next_button.first.click()
                else:
                    # Break if no next or submit button (could be a custom form or redirect)
                    break
                    
        else:
            raise Exception("Easy Apply button not found or it's a standard Apply link.")
