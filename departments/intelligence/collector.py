import os
import sys
import csv
import json
import requests
from datetime import datetime

# --- V12 PATH RESOLUTION ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if "departments" in current_dir:
    project_root = os.path.abspath(os.path.join(current_dir, "../../"))
else:
    project_root = current_dir 

if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- V12.0 CONFIGURATION ---
SETTINGS_FILE = os.path.join(project_root, 'core/settings.json')
DATABASE_FILE = os.path.join(project_root, 'database/skein_index.csv')
VAULT_DIR = os.path.join(project_root, 'vault')

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {"project": "SILICON CHRYSALIS", "autonomy_level": 1}
    with open(SETTINGS_FILE, 'r') as f:
        return json.load(f)

def ensure_vault_structure(target_id):
    """Creates the sidecar directory for a specific target."""
    target_dir = os.path.join(VAULT_DIR, f"T{target_id}")
    os.makedirs(target_dir, exist_ok=True)
    return target_dir

def save_sidecar(target_id, data):
    """Saves the full issue context into a JSON sidecar."""
    target_dir = ensure_vault_structure(target_id)
    sidecar_path = os.path.join(target_dir, "intel.json")
    with open(sidecar_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def fetch_github_issues(query, token):
    """Scrapes GitHub for potential Strategic Merit Contracts."""
    url = f"https://api.github.com/search/issues?q={query}&sort=created&order=desc"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            return res.json().get('items', [])
        return []
    except Exception as e:
        print(f"Scrape Failed: {e}")
        return []

def main():
    github_token = os.getenv("SKEIN_GITHUB_TOKEN")
    if not github_token:
        print("SKEIN_GITHUB_TOKEN missing. Radar offline.")
        sys.exit(0)

    # 1. Define Search Parameters
    # Focus on 'AI Agent', 'Bounty', and 'Automation' tasks
    search_query = "is:open is:issue label:bounty,AI,automation"
    
    print(f"📡 MIND-SKEIN: Scanning GitHub for SMCs...")
    new_targets = fetch_github_issues(search_query, github_token)
    
    # 2. Load existing index to avoid duplicates
    existing_ids = []
    if os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            existing_ids = [row['id'] for row in reader]

    # 3. Process Discoveries
    new_entries = []
    for issue in new_targets:
        issue_id = str(issue['id'])
        if issue_id in existing_ids:
            continue

        print(f"✨ New SMC Identified: T{issue_id} - {issue['title'][:40]}...")
        
        # Prepare Index Data (Lightweight)
        entry = {
            "id": issue_id,
            "status": "PENDING",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "title": issue['title'],
            "url": issue['html_url'],
            "payout_est": "0.00", # Placeholder for manual/AI triage
            "sidecar_link": f"vault/T{issue_id}/intel.json"
        }
        new_entries.append(entry)

        # Prepare Sidecar Data (Heavy)
        sidecar_data = {
            "id": issue_id,
            "title": issue['title'],
            "body": issue['body'],
            "user": issue['user']['login'],
            "labels": [l['name'] for l in issue['labels']],
            "repo_url": issue['repository_url'],
            "created_at": issue['created_at'],
            "raw_api_url": issue['url']
        }
        save_sidecar(issue_id, sidecar_data)

    # 4. Update the Master Index
    file_exists = os.path.exists(DATABASE_FILE)
    fieldnames = ["id", "status", "timestamp", "title", "url", "payout_est", "sidecar_link"]
    
    with open(DATABASE_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists or os.stat(DATABASE_FILE).st_size == 0:
            writer.writeheader()
        writer.writerows(new_entries)

    print(f"📊 Scan Complete. {len(new_entries)} new contracts added to the Ledger.")

if __name__ == "__main__":
    main()