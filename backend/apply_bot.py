import os
import json
from datetime import datetime
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from dotenv import load_dotenv

load_dotenv()


def apply_to_job(job: dict, candidate_profile: dict, platform: str, resume_filename: str = "sample_resume.pdf") -> bool:
    """
    Automates the job application process using a saved browser session.
    """
    session_file = os.path.join("sessions", f"{platform.lower()}_session.json")
    if not os.path.exists(session_file):
        print(f"Error: No saved session found for platform '{platform}'. Run session_manager.py first.")
        return False
        
    resume_path = os.path.join("resumes", resume_filename)
    if not os.path.exists(resume_path):
        print(f"Error: Resume file not found at {resume_path}")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False, 
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"]
        )
        context = browser.new_context(
            storage_state=session_file,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        stealth_sync(page)
        
        apply_url = job.get("apply_url")
        job_title = job.get("title", "Unknown Title")
        company = job.get("company", "Unknown Company")
        
        print(f"\nNavigating to application page: {apply_url}")
        try:
            page.goto(apply_url, timeout=60000)
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception as e:
            print(f"Failed to load application page: {e}")
            _log_application(job_title, company, platform, "failed_to_load")
            browser.close()
            return False

        # CAPTCHA Detection
        captcha_selectors = [
            "iframe[src*='recaptcha']",
            ".g-recaptcha", 
            "#captcha", 
            "iframe[src*='hcaptcha']"
        ]
        
        captcha_found = False
        for selector in captcha_selectors:
            if page.locator(selector).count() > 0:
                captcha_found = True
                break
                
        if captcha_found:
            print(f"⚠️ CAPTCHA detected at: {job_title} - {company}")
            print("Solve it in the browser window, then press ENTER to continue...")
            input()
            
        # Smart form filling
        print("Attempting to fill form fields...")
        try:
            # Map semantic profile data to variations of HTML input names
            fill_mapping = {
                "name": candidate_profile.get("name", ""),
                "first name": candidate_profile.get("name", "").split()[0] if candidate_profile.get("name") else "",
                "last name": candidate_profile.get("name", "").split()[-1] if candidate_profile.get("name") else "",
                "email": candidate_profile.get("email", ""),
                "phone": candidate_profile.get("phone", "")
            }
            
            # Simple heuristic: find inputs by name, id, or placeholder and map data
            inputs = page.locator("input[type='text'], input[type='email'], input[type='tel']").all()
            for inp in inputs:
                name_attr = (inp.get_attribute("name") or "").lower()
                id_attr = (inp.get_attribute("id") or "").lower()
                placeholder = (inp.get_attribute("placeholder") or "").lower()
                identifier = f"{name_attr} {id_attr} {placeholder}"
                
                for key, val in fill_mapping.items():
                    if key in identifier and val:
                        try:
                            inp.fill(val, timeout=1000)
                            break
                        except Exception:
                            pass

            # Try to fill cover letter / summary in textareas
            textareas = page.locator("textarea").all()
            for ta in textareas:
                identifier = (ta.get_attribute("name") or ta.get_attribute("id") or ta.get_attribute("placeholder") or "").lower()
                if "cover" in identifier or "summary" in identifier or "message" in identifier:
                    try:
                        ta.fill(candidate_profile.get("summary", ""), timeout=1000)
                    except Exception:
                        pass
        except Exception as e:
            print(f"Warning during form filling: {e}")

        # Resume Upload
        try:
            file_inputs = page.locator("input[type='file']").all()
            for fi in file_inputs:
                identifier = (fi.get_attribute("name") or fi.get_attribute("id") or "").lower()
                if "resume" in identifier or "cv" in identifier or "file" in identifier:
                    fi.set_input_files(resume_path, timeout=5000)
                    print(f"Uploaded resume: {resume_filename}")
                    break
        except Exception as e:
            print(f"Warning during resume upload: {e}")

        # Final Submit confirmation
        choice = input(f"\nSubmit application to {company} for {job_title}? (y/n): ").strip().lower()
        
        status = "skipped"
        if choice == 'y':
            # Attempt to automatically click standard submit buttons
            submit_selectors = ["button[type='submit']", "input[type='submit']", "button:has-text('Submit')", "button:has-text('Apply')"]
            clicked = False
            for selector in submit_selectors:
                if page.locator(selector).count() > 0:
                    try:
                        page.locator(selector).first.click(timeout=3000)
                        clicked = True
                        print("Application submitted!")
                        status = "applied"
                        # Wait briefly for submission to process
                        page.wait_for_timeout(3000)
                        break
                    except Exception:
                        pass
            if not clicked:
                print("Could not find a submit button automatically. Please click it manually in the browser window.")
                status = "manual_submit_needed"
        else:
            print("Application skipped.")
            
        browser.close()
        
        _log_application(job_title, company, platform, status)
        return status == "applied"


def _log_application(job_title: str, company: str, platform: str, status: str):
    """Logs the application result to applications_log.json"""
    log_file = "applications_log.json"
    log_entry = {
        "job_title": job_title,
        "company": company,
        "platform": platform,
        "status": status,
        "timestamp": datetime.now().isoformat()
    }
    
    logs = []
    if os.path.exists(log_file):
        try:
            with open(log_file, "r") as f:
                logs = json.load(f)
        except json.JSONDecodeError:
            pass
            
    logs.append(log_entry)
    
    with open(log_file, "w") as f:
        json.dump(logs, f, indent=4)
