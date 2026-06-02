import os
import sys
from playwright.sync_api import sync_playwright

def save_session(platform: str):
    """
    Launches a browser to let the user log in manually, then saves the session state.
    """
    platform = platform.lower()
    if platform not in ["indeed", "linkedin"]:
        print(f"Unsupported platform: {platform}")
        return

    # Determine login URL based on platform
    if platform == "indeed":
        url = "https://secure.indeed.com/auth"
    elif platform == "linkedin":
        url = "https://www.linkedin.com/login"

    session_dir = "sessions"
    os.makedirs(session_dir, exist_ok=True)
    session_file = os.path.join(session_dir, f"{platform}_session.json")

    print(f"\n--- Saving session for {platform.capitalize()} ---")
    print("1. A browser window will now open.")
    print("2. Please log in manually.")
    print("3. Return to this terminal and press ENTER when you are done logging in.")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto(url)
        
        # Wait for user to manually login and press Enter in the terminal
        input("\nPress ENTER here once you have successfully logged in...")
        
        # Save storage state into the JSON file
        context.storage_state(path=session_file)
        print(f"\nSession saved successfully to {session_file}")
        
        browser.close()

def load_session(platform: str) -> str:
    """
    Checks if a session exists for the given platform and returns the path.
    If no session exists, it prints an error and exits the program.
    """
    platform = platform.lower()
    session_file = os.path.join("sessions", f"{platform}_session.json")
    
    if os.path.exists(session_file):
        return session_file
    else:
        print(f"No session found. Run save_session first for {platform}.")
        sys.exit(1)

if __name__ == "__main__":
    try:
        choice = input("Which platform to save session for? (indeed/linkedin): ").strip().lower()
        if choice in ["indeed", "linkedin"]:
            save_session(choice)
        else:
            print("Invalid choice. Please run the script again and type 'indeed' or 'linkedin'.")
    except KeyboardInterrupt:
        print("\nSession saving cancelled.")
        sys.exit(0)
