import os
import json
import shutil
import requests
from typing import List, Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import threading
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from pydantic import BaseModel
from dotenv import load_dotenv

# Import internal modules
from backend.resume_parser import ResumeParser
from backend.scraper import scrape_indeed, scrape_linkedin
from backend.matcher import filter_jobs
from backend.apply_bot import apply_to_job

# Load environment variables
load_dotenv()

app = FastAPI(title="Job Autopilot API", version="0.1.0")

# CORS middleware for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class FindJobsRequest(BaseModel):
    profile: Dict[str, Any]
    job_title: str
    location: str = "Remote"
    min_score: int = 90
    max_jobs: int = 20
    
class ApplyRequest(BaseModel):
    job: Dict[str, Any]
    profile: Dict[str, Any]
    platform: str

@app.post("/parse-resume")
async def parse_resume(file: UploadFile = File(...)):
    """Accepts PDF upload, saves it, and parses structural data via Ollama."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    os.makedirs("resumes", exist_ok=True)
    file_path = os.path.join("resumes", file.filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
        
    try:
        parser = ResumeParser()
        parsed_data = parser.parse_resume(file_path)
        return parsed_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse resume: {e}")

@app.post("/find-jobs")
def find_jobs(req: FindJobsRequest):
    """Scrapes Indeed and LinkedIn, removes duplicates, and filters based on profile matching."""
    try:
        # Scrape jobs
        indeed_jobs = scrape_indeed(req.job_title, req.location, req.max_jobs)
        for j in indeed_jobs:
            j["platform"] = "indeed"
            
        linkedin_jobs = scrape_linkedin(req.job_title, req.location, req.max_jobs)
        for j in linkedin_jobs:
            j["platform"] = "linkedin"
            
        all_jobs = indeed_jobs + linkedin_jobs
        
        # Remove duplicates by title and company
        unique_jobs = {}
        for j in all_jobs:
            key = f"{j['title'].lower()}_{j['company'].lower()}"
            if key not in unique_jobs:
                unique_jobs[key] = j
                
        job_list = list(unique_jobs.values())
        
        # AI Matching Filter
        matched_jobs = filter_jobs(req.profile, job_list, min_score=req.min_score)
        
        return matched_jobs
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding jobs: {e}")

@app.post("/apply")
def apply(req: ApplyRequest):
    """Automates application submission using saved browser session."""
    try:
        success = apply_to_job(req.job, req.profile, req.platform)
        if success:
            return {"status": "applied"}
        else:
            return {"status": "failed_or_skipped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error applying to job: {e}")

@app.get("/applications")
def get_applications():
    """Returns the history of processed applications."""
    log_file = "applications_log.json"
    if not os.path.exists(log_file):
        return []
    try:
        with open(log_file, "r") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading applications log: {e}")

@app.get("/sessions")
def get_sessions():
    """Checks which platform sessions have been saved."""
    sessions_dir = "sessions"
    indeed_saved = os.path.exists(os.path.join(sessions_dir, "indeed_session.json"))
    linkedin_saved = os.path.exists(os.path.join(sessions_dir, "linkedin_session.json"))
    
    return {
        "indeed": indeed_saved,
        "linkedin": linkedin_saved
    }

session_done_event = threading.Event()

@app.post("/start-session/{platform}")
def start_session(platform: str):
    """Launches the browser and waits for the frontend to signal it's done."""
    session_done_event.clear()
    platform = platform.lower()
    
    if platform == "indeed":
        url = "https://secure.indeed.com/auth"
    elif platform == "linkedin":
        url = "https://www.linkedin.com/login"
    else:
        raise HTTPException(status_code=400, detail="Invalid platform")

    os.makedirs("sessions", exist_ok=True)
    session_file = os.path.join("sessions", f"{platform}_session.json")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False, 
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        stealth_sync(page)
        page.goto(url)
        
        # Block until the /finish-session endpoint is called or browser is closed
        while not session_done_event.is_set():
            if page.is_closed():
                break
            page.wait_for_timeout(1000)
            
        if not page.is_closed():
            context.storage_state(path=session_file)
            page.close()
            browser.close()
            return {"status": "success", "message": "Session saved successfully"}
        else:
            return {"status": "error", "message": "Browser closed before saving"}

@app.post("/finish-session")
def finish_session():
    """Signals the waiting playwright thread to save and close the browser."""
    session_done_event.set()
    return {"status": "ok"}

@app.get("/health")
def health_check():
    """Simple health check verifying API and Ollama connection."""
    ollama_status = "not found"
    try:
        # Attempt to reach local Ollama
        resp = requests.get("http://localhost:11434/api/tags", timeout=2)
        if resp.status_code == 200:
            ollama_status = "connected"
    except Exception:
        pass
        
    return {
        "status": "ok",
        "ollama": ollama_status
    }

if __name__ == "__main__":
    import uvicorn
    # Execute the server locally when run as main
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

