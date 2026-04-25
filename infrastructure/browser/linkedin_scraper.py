import os
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from core.application.ports import BrowserService
from typing import Optional

class LinkedInScraper(BrowserService):
    def __init__(self):
        self.playwright = None
        self.browser_context = None
        self.page = None
        self.user_data_dir = os.environ.get("CHROME_PROFILE_PATH")

    def start_session(self) -> None:
        if not self.user_data_dir:
            raise ValueError("CHROME_PROFILE_PATH environment variable is not set.")
            
        self.playwright = sync_playwright().start()
        
        # Launch persistent context to use the existing Chrome profile
        self.browser_context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=False, # Set to True for production, False for debugging
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )
        
        self.page = self.browser_context.new_page()
        # Apply stealth to avoid detection
        stealth_sync(self.page)

    def navigate(self, url: str) -> None:
        if not self.page:
            self.start_session()
        self.page.goto(url)
        # Add random delay/wait for network idle to simulate human behavior
        self.page.wait_for_load_state("networkidle")

    def extract_job_details(self, url: str) -> dict:
        self.navigate(url)
        
        # Example logic for extracting job description and details from LinkedIn
        try:
            # Wait for the main job description container to load
            self.page.wait_for_selector(".job-view-layout", timeout=10000)
            
            # Extract basic info
            title = self.page.locator(".job-details-jobs-unified-top-card__job-title").inner_text() if self.page.locator(".job-details-jobs-unified-top-card__job-title").count() > 0 else ""
            company = self.page.locator(".job-details-jobs-unified-top-card__company-name").inner_text() if self.page.locator(".job-details-jobs-unified-top-card__company-name").count() > 0 else ""
            location = self.page.locator(".job-details-jobs-unified-top-card__bullet").first.inner_text() if self.page.locator(".job-details-jobs-unified-top-card__bullet").count() > 0 else ""
            
            # Extract description
            description_html = self.page.locator("#job-details").inner_html() if self.page.locator("#job-details").count() > 0 else ""
            
            # Use BeautifulSoup to clean HTML and extract raw text
            soup = BeautifulSoup(description_html, "html.parser")
            raw_description = soup.get_text(separator="\n").strip()
            
            return {
                "title": title.strip(),
                "company": company.strip(),
                "location": location.strip(),
                "raw_description": raw_description,
                "url": url
            }
        except Exception as e:
            print(f"Failed to extract job details for {url}: {e}")
            return {}

    def close_session(self) -> None:
        if self.browser_context:
            self.browser_context.close()
        if self.playwright:
            self.playwright.stop()
