import os
import requests
import csv
from datetime import datetime
import google.generativeai as genai

# 1. Awaken the Dynamic Brain
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY missing from GitHub Secrets.")
    exit(1)
genai.configure(api_key=api_key)

# Auto-select the best Flash model
best_flash_model = "gemini-2.5-flash"
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods and 'flash' in m.name.lower() and 'exp' not in m.name.lower():
        best_flash_model = m.name
        break
model = genai.GenerativeModel(best_flash_model)

def fetch_web3_bounties():
    print("Scanning GitHub for open Web3 Bounties...")
    # Search for open issues labeled "bounty" containing crypto keywords
    query = "is:issue is:open label:bounty crypto OR web3 OR defi"
    url = f"https://api.github.com/search/issues?q={query}&sort=created&order=desc&per_page=3"
    
    headers = {"Accept": "application/vnd.github.v3+json"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        issues = response.json().get("items", [])
        
        bounties = []
        for issue in issues:
            bounties.append({
                "title": issue.get("title"),
                "url": issue.get("html_url"),
                "body": issue.get("body", "")[:500] # Grab the first 500 chars for context
            })
        return bounties
    except Exception as e:
        print(f"GitHub API Error: {e}")
        return []

def analyze_bounty(bounties):
    if not bounties:
        return "NONE", "No recent Web3 bounties found on this sweep."
        
    target = bounties[0] # Focus on the newest bounty
    
    prompt = f"""
    You are the central intelligence of the Sovereign Skein, an autonomous Web3 agent.
    You possess full programmatic execution capabilities. You do NOT need to click buttons or use web interfaces. 
    You have access to Python, the GitHub REST API (for starring, commenting, committing code), headless browsers, and Web3 libraries.
    
    Review this open GitHub bounty:
    Title: {target['title']}
    Description snippet: {target['body']}
    
    Can we write a Python script using APIs to automate and fulfill this task? 
    Reply with a strict VERDICT (CAPABLE or INCAPABLE). If CAPABLE, provide a 2-sentence technical explanation of which API endpoints or Python libraries we will use to execute it and claim the bounty.
    """
    try:
        response = model.generate_content(prompt)
        return target['title'], response.text.replace('\n', ' ').strip()
    except Exception as e:
        return target['title'], f"Brain Error: {e}"

def main():
    bounties = fetch_web3_bounties()
    top_title, verdict = analyze_bounty(bounties)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    url = bounties[0]['url'] if bounties else "N/A"
    
    # Log to the Bounty CSV
    file_exists = os.path.isfile('bounty_radar.csv')
    with open('bounty_radar.csv', 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['timestamp', 'bounty_title', 'url', 'gemini_verdict'])
        writer.writerow([timestamp, top_title, url, verdict])
        
    print(f"Bounty Sweep Complete. Target: {top_title}")

if __name__ == "__main__":
    main()
