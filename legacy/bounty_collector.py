import requests
import csv
import os
import sys
from datetime import datetime

BACKLOG_FILE = 'bounty_backlog.csv'

def fetch_github_bounties(github_token):
    print("Skeinwatch Collector V7: Scanning GitHub...")
    # The Request Block
    query = "is:issue is:open label:bounty crypto OR web3 OR defi"
    # Bumped to 10 to ensure we don't miss targets overnight
    url = f"https://api.github.com/search/issues?q={query}&sort=created&order=desc&per_page=10"
    
    # Added your GitHub Token to prevent anonymous rate-limiting
    headers = {"Accept": "application/vnd.github.v3+json"}
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    try:
        response = requests.get(url, headers=headers, timeout=10)
        return response.json().get("items", []) if response.status_code == 200 else []
    except Exception as e:
        print(f"GitHub API Error: {e}")
        return []

def main():
    # Grab the token from GitHub Actions environment
    github_token = os.getenv("SKEIN_GITHUB_TOKEN") 
    
    existing_urls = set()
    next_id = 1
    
    if os.path.exists(BACKLOG_FILE):
        with open(BACKLOG_FILE, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                existing_urls.add(row['url'])
                if row.get('id') and row['id'].isdigit():
                    next_id = max(next_id, int(row['id']) + 1)
                
    issues = fetch_github_bounties(github_token)
    new_bounties = []
    
    for issue in issues:
        url = issue.get("html_url")
        if url not in existing_urls:
            new_bounties.append({
                "id": str(next_id),
                "status": "PENDING", # Status is now physically assigned here
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "title": issue.get("title"),
                "url": url,
                "body_snippet": issue.get("body", "")[:800].replace('\n', ' ').replace('\r', ''),
                "draft_payload": ""
            })
            next_id += 1
            
    if new_bounties:
        file_exists = os.path.exists(BACKLOG_FILE)
        with open(BACKLOG_FILE, 'a', newline='', encoding='utf-8') as f:
            # V7 FIX: fieldnames order matches the new UI layout exactly
            writer = csv.DictWriter(f, fieldnames=["id", "status", "timestamp", "title", "url", "body_snippet", "draft_payload"])
            if not file_exists: writer.writeheader()
            writer.writerows(new_bounties)
        print(f"Added {len(new_bounties)} new bounties to the backlog.")
    else:
        print("Backlog is up to date.")

if __name__ == "__main__":
    main()
