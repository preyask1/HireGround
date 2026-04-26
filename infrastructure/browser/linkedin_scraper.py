import os
import time
import random
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from core.application.ports import BrowserService
from typing import List, Optional

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
        Stealth().apply_stealth_sync(self.page)

    def _human_delay(self, min_sec: float = 1.0, max_sec: float = 3.0) -> None:
        """Simulate human-like delays between actions."""
        time.sleep(random.uniform(min_sec, max_sec))

    def _build_search_url(self, keywords: str, location: str = "", time_filter: str = "r86400") -> str:
        """
        Build a LinkedIn job search URL.
        
        Args:
            keywords: Job search keywords (e.g., "Product Manager AI")
            location: Location filter (e.g., "India")
            time_filter: Time posted filter. Options:
                - "r86400"  = Past 24 hours
                - "r604800" = Past week
                - "r2592000" = Past month
                - "" = Any time
        """
        base = "https://www.linkedin.com/jobs/search/?"
        params = f"keywords={quote_plus(keywords)}"
        if location:
            params += f"&location={quote_plus(location)}"
        if time_filter:
            params += f"&f_TPR={time_filter}"
        # Sort by most recent
        params += "&sortBy=DD"
        return base + params

    def search_jobs(self, keywords: str, location: str = "", max_pages: int = 1) -> List[dict]:
        """
        Search LinkedIn for jobs and return a list of discovered job card metadata.
        
        Returns a list of dicts with keys: title, company, location, url
        """
        if not self.page:
            self.start_session()

        search_url = self._build_search_url(keywords, location)
        discovered_jobs = []

        for page_num in range(max_pages):
            url = search_url + (f"&start={page_num * 25}" if page_num > 0 else "")
            print(f"  [Scout] Navigating to search page {page_num + 1}...")
            self.page.goto(url)
            self.page.wait_for_load_state("networkidle")
            self._human_delay(2, 4)

            # Scroll down to load all job cards on the page
            for _ in range(3):
                self.page.evaluate("window.scrollBy(0, 800)")
                self._human_delay(0.5, 1.5)

            try:
                # Wait for job cards to render
                self.page.wait_for_selector(".job-card-container", timeout=15000)
                job_cards = self.page.locator(".job-card-container").all()

                for card in job_cards:
                    try:
                        # Extract link - the job card anchor tag
                        link_el = card.locator("a.job-card-container__link")
                        href = link_el.get_attribute("href") if link_el.count() > 0 else None

                        if not href:
                            continue

                        # Normalize the URL
                        if href.startswith("/"):
                            href = "https://www.linkedin.com" + href
                        # Clean tracking params, keep base job URL
                        if "?" in href:
                            href = href.split("?")[0]

                        # Extract title
                        title_el = card.locator(".job-card-list__title--link")
                        title = title_el.inner_text().strip() if title_el.count() > 0 else "Unknown Title"

                        # Extract company name
                        company_el = card.locator(".artdeco-entity-lockup__subtitle")
                        company = company_el.inner_text().strip() if company_el.count() > 0 else ""

                        # Extract location
                        loc_el = card.locator(".artdeco-entity-lockup__caption")
                        loc = loc_el.inner_text().strip() if loc_el.count() > 0 else ""

                        discovered_jobs.append({
                            "title": title,
                            "company": company,
                            "location": loc,
                            "url": href
                        })
                    except Exception:
                        continue  # Skip malformed cards

            except Exception as e:
                print(f"  [Scout] Could not load job cards on page {page_num + 1}: {e}")
                break

            self._human_delay(2, 5)

        print(f"  [Scout] Discovered {len(discovered_jobs)} job(s) from search.")
        return discovered_jobs

    def navigate(self, url: str) -> None:
        if not self.page:
            self.start_session()
        self.page.goto(url)
        # Add random delay/wait for network idle to simulate human behavior
        self.page.wait_for_load_state("networkidle")

    def extract_job_details(self, url: str) -> dict:
        self.navigate(url)
        self._human_delay(1, 3)
        
        # Extract job description and details from LinkedIn
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
