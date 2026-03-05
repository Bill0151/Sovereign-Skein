import os
import sys
import csv
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

# --- V12 PATH RESOLUTION ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if "departments" in current_dir:
    project_root = os.path.abspath(os.path.join(current_dir, "../../"))
else:
    project_root = current_dir

if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- SECURE VAULT DECRYPTION ---
load_dotenv(os.path.join(project_root, '.env'))

# --- V12.0 CONFIGURATION ---
GITHUB_TOKEN = os.getenv("SKEIN_GITHUB_TOKEN")
DATABASE_FILE = os.path.join(project_root, 'database/skein_index.csv')
VAULT_DIR = os.path.join(project_root, 'vault')

# Ensure directories exist
os.makedirs(os.path.dirname(DATABASE_FILE), exist_ok=True)
os.makedirs(VAULT_DIR, exist_ok=True)

# --- NEW: NEGATIVE KEYWORD FILTER ---
BOT_SIGNATURES = [
    "auto-update failed",
    "pulse 20",
    "dependency health report",
    "ci daily health report",
    "docs eval report",
    "monthly activity",
    "sync failed",
    "github trending",
    "automated tests("
]

def search_github():
    """Scours GitHub for high-value Python issues."""
    print("📡 INTELLIGENCE: Initiating Radar Sweep...")
    
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Example Query: Open issues in Python with 'bounty' or 'reward' created recently
    query = "is:issue is:open language:python (bounty OR reward OR \"help wanted\") no:assignee"
    url = f"https://api.github.com/search/issues?q={query}&sort=created&order=desc&per_page=30"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        new_targets = []
        for item in data.get("items", []):
            title = item.get("title", "")
            
            # --- APPLY NEGATIVE FILTER ---
            title_lower = title.lower()
            is_bot = any(bot_sig in title_lower for bot_sig in BOT_SIGNATURES)
            
            if is_bot:
                print(f"   [FILTERED] Bot detected: {title}")
                continue
                
            # Convert GitHub Issue ID to our internal Target ID (T-prefix)
            target_id = f"T{item['id']}"
            
            # Extract basic intel
            intel = {
                "id": target_id,
                "title": title,
                "url": item.get("html_url"),
                "body": item.get("body", "")[:2000], # Grab first 2000 chars of context
                "repository_url": item.get("repository_url"),
                "created_at": item.get("created_at")
            }
            new_targets.append(intel)
            
        return new_targets
        
    except requests.exceptions.RequestException as e:
        print(f"❌ INTELLIGENCE ERROR: GitHub API connection failed: {e}")
        return []

def update_database(new_targets):
    """Adds new targets to the CSV and creates vault sidecars."""
    print(f"💾 INTELLIGENCE: Processing {len(new_targets)} potential targets...")
    
    existing_ids = set()
    
    # Read existing IDs to avoid duplicates
    if os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_ids.add(row['id'])
                
    new_additions = 0
    
    # Append new targets
    with open(DATABASE_FILE, mode='a', newline='', encoding='utf-8') as f:
        fieldnames = ['id', 'status', 'timestamp', 'title', 'url', 'payout_est', 'sidecar_link']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not existing_ids:
            writer.writeheader()
            
        for target in new_targets:
            if target['id'] not in existing_ids:
                # 1. Create Vault Sidecar (Full Context)
                target_dir = os.path.join(VAULT_DIR, target['id'])
                os.makedirs(target_dir, exist_ok=True)
                sidecar_path = os.path.join(target_dir, 'intel.json')
                
                with open(sidecar_path, 'w', encoding='utf-8') as sf:
                    json.dump(target, sf, indent=4)
                    
                # 2. Add to Ledger (Fast Lookup)
                writer.writerow({
                    'id': target['id'],
                    'status': 'PENDING',
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'title': target['title'],
                    'url': target['url'],
                    'payout_est': '0.00', # Assessor agent will update this later
                    'sidecar_link': f"vault/{target['id']}/intel.json"
                })
                new_additions += 1
                
    print(f"✅ INTELLIGENCE: Added {new_additions} new viable targets to the index.")

if __name__ == "__main__":
    targets = search_github()
    if targets:
        update_database(targets)