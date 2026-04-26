import os
import sys
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from core.domain.models import Job, JobDetails, JobStatus
from core.services.scoring import AnalystScoringService
from infrastructure.browser.linkedin_scraper import LinkedInScraper
from infrastructure.external.llm_gateway import LitellmGateway
from infrastructure.persistence.repository import SQLiteJobRepository


# ─── Search Profiles ───────────────────────────────────────────────────────────
# Define your search queries here. Each dict is one search to perform.
SEARCH_PROFILES = [
    {"keywords": "Product Manager AI", "location": "India"},
    {"keywords": "Senior Product Manager Data", "location": "India"},
    {"keywords": "AI Product Lead", "location": "Remote"},
]


def run_scout(scraper: LinkedInScraper, repo: SQLiteJobRepository, max_pages: int = 1):
    """
    SCOUT AGENT: Discovers new jobs from LinkedIn search and persists them.
    """
    print("\n" + "=" * 60)
    print("🔍  SCOUT AGENT — Discovering new jobs...")
    print("=" * 60)

    total_new = 0

    for profile in SEARCH_PROFILES:
        print(f"\n→ Searching: '{profile['keywords']}' in '{profile.get('location', 'Any')}'")
        try:
            cards = scraper.search_jobs(
                keywords=profile["keywords"],
                location=profile.get("location", ""),
                max_pages=max_pages,
            )
        except Exception as e:
            print(f"  [Scout] Search failed: {e}")
            continue

        for card in cards:
            # Skip if already in DB
            existing = repo.get_job_by_url(card["url"])
            if existing:
                continue

            job = Job(
                title=card["title"],
                location=card.get("location"),
                url=card["url"],
                status=JobStatus.DISCOVERED,
            )
            repo.save_job(job)
            total_new += 1
            print(f"  ✚ New: {card['title']} — {card.get('company', '')}")

    print(f"\n📊  Scout complete. {total_new} new job(s) added to the pipeline.")
    return total_new


def run_analyst(scraper: LinkedInScraper, repo: SQLiteJobRepository, scoring_service: AnalystScoringService):
    """
    ANALYST AGENT: For every DISCOVERED job, scrape details → score → persist.
    """
    print("\n" + "=" * 60)
    print("🧠  ANALYST AGENT — Scoring discovered jobs...")
    print("=" * 60)

    discovered = repo.get_jobs_by_status(JobStatus.DISCOVERED)
    if not discovered:
        print("  No new jobs to analyze.")
        return

    print(f"  Found {len(discovered)} job(s) to analyze.\n")

    for job in discovered:
        print(f"  ── Analyzing: {job.title} ({job.url})")

        # 1. Scrape full details
        try:
            details = scraper.extract_job_details(job.url)
        except Exception as e:
            print(f"     ⚠ Scrape failed: {e}")
            continue

        if not details or not details.get("raw_description"):
            print("     ⚠ No description found, skipping.")
            continue

        # 2. Persist scraped details on the job
        job.details = JobDetails(
            job_id=job.id,
            raw_description=details["raw_description"],
        )
        # Update location/title from the detail page if richer
        if details.get("title"):
            job.title = details["title"]
        if details.get("location"):
            job.location = details["location"]

        repo.save_job(job)

        # 3. Score the job
        try:
            score = scoring_service.score_job(
                job_id=job.id,
                job_description=details["raw_description"],
                location=job.location or "",
            )
            repo.save_score(score)
        except Exception as e:
            print(f"     ⚠ Scoring failed: {e}")
            continue

        # 4. Move status to SCORED
        repo.update_job_status(job.id, JobStatus.SCORED)
        print(f"     ✔ Score: {score.fit_score}/100")

    print("\n📊  Analyst complete.")


def run_apply(repo: SQLiteJobRepository):
    """
    APPLY AGENT: Process jobs that have been human-approved in the UI.
    """
    from infrastructure.browser.apply_adapter import ApplyAdapter

    print("\n" + "=" * 60)
    print("🚀  APPLY AGENT — Submitting approved applications...")
    print("=" * 60)

    user_data_dir = os.environ.get("CHROME_PROFILE_PATH")
    if not user_data_dir:
        print("  ⚠ CHROME_PROFILE_PATH not set. Cannot apply.")
        return

    adapter = ApplyAdapter(user_data_dir)
    adapter.process_approved_jobs()
    print("\n📊  Apply agent complete.")


def main():
    parser = argparse.ArgumentParser(
        description="HireGround Job Copilot — Automated LinkedIn Job Discovery & Scoring"
    )
    parser.add_argument(
        "mode",
        nargs="?",
        default="full",
        choices=["scout", "analyst", "apply", "full"],
        help="Which agent to run. 'full' runs scout → analyst pipeline. (default: full)",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=1,
        help="Number of LinkedIn search result pages to scan per query (default: 1)",
    )
    args = parser.parse_args()

    # ─── Dependency Injection ───────────────────────────────────────────────────
    repo = SQLiteJobRepository()
    scraper = LinkedInScraper()
    llm = LitellmGateway()
    scoring = AnalystScoringService(llm_service=llm)

    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║        HireGround Job Copilot — Initialized            ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  Mode         : {args.mode:<40} ║")
    print(f"║  Search Pages : {args.pages:<40} ║")
    print(f"║  LLM (Extract): {llm.extraction_model:<40} ║")
    print(f"║  LLM (Score)  : {llm.scoring_model:<40} ║")
    print("╚══════════════════════════════════════════════════════════╝")

    try:
        if args.mode in ("scout", "full"):
            run_scout(scraper, repo, max_pages=args.pages)

        if args.mode in ("analyst", "full"):
            run_analyst(scraper, repo, scoring)

        if args.mode == "apply":
            run_apply(repo)

    finally:
        scraper.close_session()

    print("\n✅  Done. Run 'streamlit run ui/app.py' to review scored jobs.\n")


if __name__ == "__main__":
    main()
