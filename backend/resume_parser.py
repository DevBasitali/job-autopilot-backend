import os
import json
import ollama
from PyPDF2 import PdfReader
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ResumeParser:
    def __init__(self, model_name: str = None):
        """Initializes the ResumeParser with a specific Ollama model."""
        self.model_name = model_name or os.getenv("OLLAMA_MODEL", "llama3")

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extracts plain text from a PDF resume file using PyPDF2."""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found at {pdf_path}")
        
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text

    def parse_resume(self, pdf_path: str) -> dict:
        """Parses resume PDF using Ollama to return structured JSON.
        
        If JSON parsing fails, it retries exactly once.
        """
        raw_text = self.extract_text_from_pdf(pdf_path)
        
        prompt = (
            "You are a precise resume parser. Extract structured details from the following resume text.\n"
            "You must return a valid JSON object matching the following structure:\n"
            "{\n"
            '  "name": "Full Name as string, or null",\n'
            '  "email": "Email address as string, or null",\n'
            '  "phone": "Phone number as string, or null",\n'
            '  "skills": ["List of skill strings"],\n'
            '  "experience_years": Total years of professional experience as a number (float or int), or null,\n'
            '  "job_titles": ["List of past/present job titles"],\n'
            '  "education": "Highest degree, field of study, and institution name as a string, or null",\n'
            '  "languages": ["List of languages spoken"],\n'
            '  "summary": "2-3 line professional summary as string, or null",\n'
            '  "suggested_roles": ["List of 4-6 job titles that closely match the profile. Include seniority variations if appropriate (e.g. Senior Backend Engineer, Mid-Level Node Developer, etc)"]\n'
            "}\n"
            "Do not include any chat formatting, markdown JSON block wrapping (like ```json), or explanatory text outside the JSON object.\n"
            "Return only the raw JSON string.\n\n"
            f"Resume Text:\n{raw_text}"
        )

        for attempt in range(2):
            try:
                # Using Ollama chat API to query local model
                response = ollama.chat(
                    model=self.model_name,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    options={"temperature": 0.0},
                    format="json"  # Instructs Ollama to return JSON output
                )
                
                content = response["message"]["content"].strip()
                parsed_json = json.loads(content)
                
                return self._normalize_fields(parsed_json)
                
            except Exception as e:
                if attempt == 0:
                    print(f"Warning: Attempt 1 failed with error: {e}. Retrying once...")
                    continue
                else:
                    print(f"Error: Failed to parse resume after 2 attempts. Final error: {e}")
                    raise e

    def _normalize_fields(self, data: dict) -> dict:
        """Ensures the parsed dict contains all expected keys with correct default types."""
        expected_fields = {
            "name": str,
            "email": str,
            "phone": str,
            "skills": list,
            "experience_years": (int, float),
            "job_titles": list,
            "education": str,
            "languages": list,
            "summary": str,
            "suggested_roles": list
        }
        
        normalized = {}
        for field, expected_type in expected_fields.items():
            value = data.get(field, None)
            
            # Type correction/coercion if needed
            if value is not None:
                if isinstance(expected_type, tuple):
                    # For experience_years
                    if not isinstance(value, expected_type):
                        try:
                            value = float(value)
                        except (ValueError, TypeError):
                            value = None
                else:
                    if not isinstance(value, expected_type):
                        if expected_type == list:
                            value = [str(value)] if value else []
                        else:
                            value = str(value)
            
            # Default empty lists for list fields if they are null
            if expected_type == list and value is None:
                value = []
                
            normalized[field] = value
            
        return normalized

if __name__ == "__main__":
    import sys
    
    # Simple check for CLI argument, otherwise look for or create sample_resume.pdf
    sample_path = "resumes/sample_resume.pdf"
    if len(sys.argv) > 1:
        sample_path = sys.argv[1]
        
    print(f"Using resume path: {sample_path}")
    
    if not os.path.exists(sample_path) and sample_path == "resumes/sample_resume.pdf":
        print("Sample PDF not found. Creating a mock resume PDF using Playwright...")
        os.makedirs("resumes", exist_ok=True)
        
        html_content = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }
                h1 { color: #333; margin-bottom: 5px; }
                .contact { color: #666; margin-bottom: 20px; }
                .section { margin-top: 20px; }
                .section-title { font-weight: bold; border-bottom: 1px solid #ccc; padding-bottom: 5px; margin-bottom: 10px; }
                ul { margin-top: 5px; }
            </style>
        </head>
        <body>
            <h1>John Doe</h1>
            <div class="contact">Email: john.doe@example.com | Phone: 555-0199 | Languages: English, Spanish</div>
            
            <div class="section">
                <div class="section-title">Professional Summary</div>
                <p>Results-oriented Software Engineer with 5 years of experience designing and building scalable web applications. Skilled in backend service development and API integration using modern frameworks.</p>
            </div>
            
            <div class="section">
                <div class="section-title">Skills</div>
                <p>Python, JavaScript, FastAPI, Node.js, SQL, Docker, AWS, Git</p>
            </div>
            
            <div class="section">
                <div class="section-title">Work Experience</div>
                <p><strong>Senior Software Engineer</strong> - TechCorp (2023 - Present)<br/>
                Led the development of a microservices backend that improved transaction speed by 30%.</p>
                <p><strong>Software Developer</strong> - WebSolutions (2021 - 2023)<br/>
                Developed and maintained client websites using Django and React.</p>
            </div>
            
            <div class="section">
                <div class="section-title">Education</div>
                <p>Bachelor of Science in Computer Science - State University (2017 - 2021)</p>
            </div>
        </body>
        </html>
        """
        
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_content(html_content)
                page.pdf(path=sample_path)
                browser.close()
            print(f"Mock resume PDF created at: {sample_path}")
        except Exception as e:
            print(f"Failed to generate PDF using Playwright: {e}")
            print("Please ensure playwright is installed and initialized.")
            sys.exit(1)
            
    # Run Parser
    parser = ResumeParser()
    try:
        result = parser.parse_resume(sample_path)
        print("\n--- PARSED RESULT ---")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"\nExecution failed: {e}")

