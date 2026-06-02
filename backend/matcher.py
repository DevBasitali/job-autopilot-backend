import os
import json
import ollama
from dotenv import load_dotenv

load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

def score_job(candidate_profile: dict, job: dict) -> dict:
    """Uses Ollama to score how well a candidate profile matches a job."""
    prompt = (
        "You are an expert technical recruiter evaluating a candidate for a job.\n"
        "Compare the candidate profile and the job description below.\n"
        "Return your evaluation STRICTLY as a JSON object matching this exact schema:\n"
        "{\n"
        '  "score": integer between 0 and 100,\n'
        '  "matching_skills": ["List of skills the candidate has that match the job"],\n'
        '  "missing_skills": ["List of required skills the candidate is missing"],\n'
        '  "reason": "A 1-2 sentence explanation of the score"\n'
        "}\n"
        "Do not include any other text, markdown formatting blocks, or explanation outside the JSON.\n\n"
        f"--- CANDIDATE PROFILE ---\n{json.dumps(candidate_profile, indent=2)}\n\n"
        f"--- JOB DETAILS ---\n{json.dumps(job, indent=2)}"
    )

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.0},
            format="json"
        )
        
        content = response["message"]["content"].strip()
        parsed = json.loads(content)
        
        # Ensure correct types and handle edge cases safely
        return {
            "score": int(parsed.get("score", 0)),
            "matching_skills": list(parsed.get("matching_skills", [])),
            "missing_skills": list(parsed.get("missing_skills", [])),
            "reason": str(parsed.get("reason", ""))
        }
    except Exception as e:
        print(f"Error scoring job '{job.get('title', 'Unknown')}': {e}")
        return {
            "score": 0,
            "matching_skills": [],
            "missing_skills": [],
            "reason": "Failed to parse Ollama output or connection error."
        }

def filter_jobs(candidate_profile: dict, jobs: list, min_score: int = 90) -> list:
    """Scores a list of jobs and filters out those below the min_score."""
    matched_jobs = []
    total_jobs = len(jobs)
    
    for i, job in enumerate(jobs, 1):
        print(f"Scoring job {i} of {total_jobs}...")
        match_result = score_job(candidate_profile, job)
        job['match'] = match_result
        
        if match_result['score'] >= min_score:
            matched_jobs.append(job)
            
    return matched_jobs

if __name__ == "__main__":
    # Sample candidate profile
    sample_candidate = {
        "name": "Jane Smith",
        "skills": ["Python", "Django", "PostgreSQL", "Docker", "AWS"],
        "experience_years": 4,
        "job_titles": ["Backend Engineer", "Software Developer"],
        "education": "B.S. Computer Science",
        "summary": "Backend focused Python engineer with 4 years building scalable web services."
    }
    
    # Sample jobs (3 items)
    sample_jobs = [
        {
            "title": "Senior Python Developer",
            "company": "TechInnovate",
            "location": "Remote",
            "description": "Looking for a Python expert with 5+ years of experience. Must know Django, AWS, and Kubernetes. Strong database skills (PostgreSQL) required."
        },
        {
            "title": "Frontend React Engineer",
            "company": "WebCorp",
            "location": "New York, NY",
            "description": "We need a frontend specialist with deep React, CSS, and TypeScript experience. No backend knowledge needed."
        },
        {
            "title": "Backend Python Engineer",
            "company": "DataSystems",
            "location": "Remote",
            "description": "Seeking a backend engineer with 3+ years experience. Required: Python, Docker, SQL (PostgreSQL preferred). Nice to have: AWS."
        }
    ]
    
    print(f"Running job matcher filter (Model: {OLLAMA_MODEL})...")
    filtered_results = filter_jobs(sample_candidate, sample_jobs, min_score=70)
    
    print("\n--- MATCHED JOBS ---")
    if not filtered_results:
        print("No jobs met the minimum score criteria.")
        
    for j in filtered_results:
        print(f"\n{j['title']} @ {j['company']}")
        print(f"Score: {j['match']['score']}/100")
        print(f"Reason: {j['match']['reason']}")
        print(f"Matching Skills: {', '.join(j['match']['matching_skills'])}")
        print(f"Missing Skills: {', '.join(j['match']['missing_skills'])}")

