# Job Autopilot

Job Autopilot is an AI-powered job application automation system designed to streamline the process of finding, matching, and applying for jobs.

## Features

- **Resume Parsing**: Automatically extract skills, experience, and education from resumes.
- **Job Scraping**: Scrape job listings from various sources.
- **Job Matching**: AI-driven matching of candidate profiles with job descriptions.
- **Automated Application**: Intelligent bot to assist in or automate filling out job applications.
- **Human-in-the-Loop (HITL)**: Approval mechanism before submitting applications to ensure accuracy and quality control.

## Project Structure

```text
job-autopilot/
├── backend/
│   ├── main.py            # API Gateway & server entry point
│   ├── resume_parser.py   # Extracts information from resumes (e.g. PDF parser)
│   ├── scraper.py         # Scrapes job boards for job postings
│   ├── matcher.py         # Matches resumes against job listings using LLMs
│   ├── apply_bot.py       # automates browser interactions for application submission
│   └── hitl.py            # Human-in-the-loop validation and approvals
├── frontend/              # Frontend web application (to be implemented)
├── sessions/              # Scraper and browser session state storage
├── resumes/               # Uploaded resume files storage
├── requirements.txt       # Python dependencies
└── .env                   # Local configuration variables
```

## Getting Started

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/) with the `llama3` model pulled:
  ```bash
  ollama pull llama3
  ```

### Installation

1. Clone the repository and navigate to the project directory:
   ```bash
   cd job-autopilot
   ```

2. Install the required Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Initialize the Playwright browsers:
   ```bash
   playwright install
   ```

4. Configure local environment variables in `.env`.
