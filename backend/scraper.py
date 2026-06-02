import os
import time
import random
import urllib.parse
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

def random_delay(min_sec: float = 1.0, max_sec: float = 3.0):
    """Sleeps for a random duration between min_sec and max_sec."""
    time.sleep(random.uniform(min_sec, max_sec))

def scrape_indeed(job_title: str, location: str = "Remote", max_jobs: int = 20) -> list[dict]:
    """Scrapes job listings from Indeed using Playwright."""
    jobs = []
    
    with sync_playwright() as p:
        # Launch Chromium in NON-headless mode to avoid detection
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # Format the Indeed search URL
        query = urllib.parse.quote(job_title)
        loc = urllib.parse.quote(location)
        url = f"https://www.indeed.com/jobs?q={query}&l={loc}"
        
        print(f"Navigating to Indeed: {url}")
        try:
            page.goto(url, timeout=60000)
            random_delay(2, 4)
        except Exception as e:
            print(f"Failed to load Indeed: {e}")
            browser.close()
            return jobs

        # Wait for the main job cards to load
        try:
            page.wait_for_selector(".job_seen_beacon", timeout=10000)
        except Exception:
            print("Timeout waiting for job listings on Indeed (might be a captcha or no results).")
            browser.close()
            return jobs

        job_cards = page.locator(".job_seen_beacon").all()
        
        for i, card in enumerate(job_cards):
            if len(jobs) >= max_jobs:
                break
                
            try:
                # Scroll card into view to mimic human behavior
                card.scroll_into_view_if_needed()
                random_delay(1, 2)
                
                # Click the card to open the details pane
                card.click()
                random_delay(2, 3)
                
                # Extract basic info
                title = card.locator("h2.jobTitle").inner_text(timeout=5000).strip()
                company = card.locator("[data-testid='company-name']").inner_text(timeout=5000).strip()
                
                try:
                    job_location = card.locator("[data-testid='text-location']").inner_text(timeout=5000).strip()
                except Exception:
                    job_location = location
                
                # Extract URL
                a_tag = card.locator("h2.jobTitle a")
                href = a_tag.get_attribute("href")
                if href and href.startswith("/"):
                    apply_url = f"https://www.indeed.com{href}"
                else:
                    apply_url = href or url
                
                # Extract description from the details pane
                try:
                    desc_locator = page.locator("#jobsearch-ViewJobLayout-jobDisplay .jobsearch-jobDescriptionText")
                    desc_locator.wait_for(state="visible", timeout=5000)
                    description = desc_locator.inner_text().strip()
                except Exception:
                    description = "Description not available."

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": job_location,
                    "description": description,
                    "apply_url": apply_url
                })
                print(f"Successfully scraped Indeed job: {title} at {company}")
                
            except Exception as e:
                # Handle errors per listing with try/except — skip failed ones, continue rest
                print(f"Error scraping Indeed job card {i+1}: {e}")
                continue
                
        browser.close()
        
    return jobs

def scrape_linkedin(job_title: str, location: str = "Remote", max_jobs: int = 20) -> list[dict]:
    """Scrapes job listings from LinkedIn using Playwright."""
    jobs = []
    
    with sync_playwright() as p:
        # Launch Chromium in NON-headless mode
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # Format the LinkedIn search URL
        query = urllib.parse.quote(job_title)
        loc = urllib.parse.quote(location)
        url = f"https://www.linkedin.com/jobs/search?keywords={query}&location={loc}"
        
        print(f"Navigating to LinkedIn: {url}")
        try:
            page.goto(url, timeout=60000)
            random_delay(2, 4)
        except Exception as e:
            print(f"Failed to load LinkedIn: {e}")
            browser.close()
            return jobs

        # Scroll down to load more jobs (simulating user scrolling)
        for _ in range(3):
            page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            random_delay(1, 2)

        try:
            page.wait_for_selector("ul.jobs-search__results-list li", timeout=10000)
            job_cards = page.locator("ul.jobs-search__results-list li").all()
        except Exception:
            try:
                page.wait_for_selector(".job-search-card", timeout=10000)
                job_cards = page.locator(".job-search-card").all()
            except Exception:
                print("Timeout waiting for job listings on LinkedIn.")
                browser.close()
                return jobs

        for i, card in enumerate(job_cards):
            if len(jobs) >= max_jobs:
                break
                
            try:
                card.scroll_into_view_if_needed()
                random_delay(1, 2)
                
                try:
                    title_elem = card.locator(".base-search-card__title, .job-search-card__title")
                    title = title_elem.inner_text(timeout=2000).strip()
                except Exception:
                    title = "Unknown Title"
                    
                try:
                    company_elem = card.locator(".base-search-card__subtitle, .job-search-card__subtitle")
                    company = company_elem.inner_text(timeout=2000).strip()
                except Exception:
                    company = "Unknown Company"
                    
                try:
                    location_elem = card.locator(".job-search-card__location")
                    job_location = location_elem.inner_text(timeout=2000).strip()
                except Exception:
                    job_location = location
                    
                try:
                    a_tag = card.locator("a.base-card__full-link")
                    apply_url = a_tag.get_attribute("href")
                    if apply_url:
                        # Clean up URL parameters
                        apply_url = apply_url.split("?")[0]
                except Exception:
                    apply_url = url
                
                # Attempt to get description
                description = "Description not readily available without navigation."
                try:
                    card.click()
                    random_delay(2, 3)
                    desc_loc = page.locator(".show-more-less-html__markup")
                    if desc_loc.is_visible():
                        description = desc_loc.inner_text().strip()
                except Exception:
                    pass
                
                jobs.append({
                    "title": title,
                    "company": company,
                    "location": job_location,
                    "description": description,
                    "apply_url": apply_url or url
                })
                print(f"Successfully scraped LinkedIn job: {title} at {company}")
                
            except Exception as e:
                # Handle errors per listing with try/except
                print(f"Error scraping LinkedIn job card {i+1}: {e}")
                continue
                
        browser.close()
        
    return jobs

if __name__ == "__main__":
    print("Testing Scrapers...")
    test_title = "Python Developer"
    test_location = "Remote"
    test_max = 2
    
    print("\\n--- Starting Indeed Scraper ---")
    indeed_jobs = scrape_indeed(test_title, test_location, test_max)
    print(f"Scraped {len(indeed_jobs)} jobs from Indeed.")
    for j in indeed_jobs:
        print(f" - {j['title']} @ {j['company']} ({j['location']})")
        print(f"   URL: {j['apply_url']}")
        print(f"   Desc snippet: {j['description'][:100]}...")
        
    print("\\n--- Starting LinkedIn Scraper ---")
    linkedin_jobs = scrape_linkedin(test_title, test_location, test_max)
    print(f"Scraped {len(linkedin_jobs)} jobs from LinkedIn.")
    for j in linkedin_jobs:
        print(f" - {j['title']} @ {j['company']} ({j['location']})")
        print(f"   URL: {j['apply_url']}")
        print(f"   Desc snippet: {j['description'][:100]}...")

