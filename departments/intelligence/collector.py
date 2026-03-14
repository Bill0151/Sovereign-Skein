"""
FILE: departments/intelligence/collector.py
ROLE: The "Radar" - Intelligence Node
FUNCTION: Scours GitHub for bounties, checks for existing claims, detects PR merges, and builds Vault sidecars.
VERSION: V12.12 (wRTC Support & Advanced Radar Filtering)
"""

import os
import sys
import csv
import json
import time
import requests
import re
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

load_dotenv(os.path.join(project_root, '.env'))

GITHUB_TOKEN = os.getenv("SKEIN_GITHUB_TOKEN")
DATABASE_FILE = os.path.join(project_root, 'database/skein_index.csv')
VAULT_DIR = os.path.join(project_root, 'vault')

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}", 
    "Accept": "application/vnd.github.v3+json"
}

# --- V12.8 EXCLUSION LIST ---
EXCLUSION_KEYWORDS = [
    "video", "tiktok", "instagram", "reels", "youtube", "shorts", 
    "tweet", "social media", "marketing", "post", "reddit", "subreddit",
    "article", "blog", "tutorial video", "explainer", "film"
]

def audit_stale_targets():
    """V12.9: Sweeps the Ledger for active targets and marks them CLOSED_MISSED if closed on GitHub."""
    print("🧹 INTELLIGENCE: Auditing active targets for external closures...")
    if not os.path.exists(DATABASE_FILE):
        return

    try:
        with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
            
        updated = False
        # Statuses that mean the bounty is still "in play"
        active_statuses = ['PENDING', 'DRAFT_REQUESTED', 'DRAFT_READY', 'AMEND_REQUESTED', 'FOLLOW_UP', 'VULTURE_PENDING']

        for row in rows:
            if row['status'] in active_statuses:
                url_parts = row['url'].rstrip('/').split('/')
                # Ensure the URL is a standard GitHub issue URL
                if len(url_parts) >= 4 and url_parts[-2] == 'issues':
                    owner, repo, issue_num = url_parts[-4], url_parts[-3], url_parts[-1]
                    api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_num}"

                    res = requests.get(api_url, headers=HEADERS, timeout=10)
                    if res.status_code == 200:
                        issue_data = res.json()
                        if issue_data.get('state') == 'closed':
                            print(f"   [🔒 CLOSED] Target {row['id']} was closed by maintainer. Archiving.")
                            row['status'] = 'CLOSED_MISSED'
                            updated = True

        if updated:
            with open(DATABASE_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            print("✅ Ledger synced with GitHub reality.")
        else:
            print("✅ All active targets remain open.")
            
    except Exception as e:
        print(f"⚠️ Audit sweep failed: {e}")

def get_existing_ids():
    """Reads the Ledger to ensure we don't process duplicate targets."""
    if not os.path.exists(DATABASE_FILE):
        return set()
    try:
        with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return {row['id'] for row in reader}
    except Exception as e:
        print(f"⚠️ Warning: Could not read ledger: {e}")
        return set()

def check_for_pr_merges(issue_item):
    """Scans comments for 'PR', 'merged', or linked pull requests."""
    comments_url = issue_item.get("comments_url")
    if not comments_url or issue_item.get("comments", 0) == 0:
        return False
        
    try:
        res = requests.get(comments_url, headers=HEADERS)
        if res.status_code != 200: 
            return False
            
        comments = res.json()
        owner = issue_item.get("user", {}).get("login")
        
        for c in comments:
            body = c.get("body", "").lower()
            author = c.get("user", {}).get("login")
            
            if author == owner and any(word in body for word in ["merged", "pull request", "pr #", "integrated"]):
                return True
            if "github.com/" in body and "/pull/" in body:
                return True
                
        return False
    except Exception:
        return False

def create_vault_sidecar(target_id, issue_data):
    """Creates the deep-context intel.json sidecar for the Assessor & Executor."""
    raw_id = str(target_id).replace('T', '')
    target_dir = os.path.join(VAULT_DIR, f"T{raw_id}")
    os.makedirs(target_dir, exist_ok=True)
    
    intel_path = os.path.join(target_dir, "intel.json")
    
    intel_data = {
        "id": target_id,
        "title": issue_data.get("title", ""),
        "url": issue_data.get("html_url", ""),
        "body": issue_data.get("body", "No description provided."),
        "created_at": issue_data.get("created_at", ""),
        "vulture_target_user": issue_data.get("user", {}).get("login", "Unknown"),
        "skein_status": "PENDING"
    }
    
    with open(intel_path, 'w', encoding='utf-8') as f:
        json.dump(intel_data, f, indent=4)
        
    return intel_path

def search_github():
    print("📡 INTELLIGENCE: Initiating V12.12 Radar Sweep...")
    
    existing_ids = get_existing_ids()
    
    # V12.12: Added wRTC support based on official wallet FAQ
    query = 'is:issue is:open (bounty OR reward) ("USDC" OR "SOL" OR "ETH" OR "crypto" OR "RTC" OR "wRTC") no:assignee'
    url = f"https://api.github.com/search/issues?q={query}&sort=created&order=desc&per_page=30"
    
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        
        new_targets = []
        
        for item in data.get("items", []):
            # V12.10: Extract human-readable Issue Number + Repo Name to prevent collisions
            repo_name = item.get("html_url", "").split('/')[-3] if item.get("html_url") else "unknown"
            issue_number = item.get("number", item.get("id"))
            target_id = f"T{issue_number}-{repo_name}"
            
            title = item.get("title", "")
            
            if target_id in existing_ids:
                continue
                
            title_lower = title.lower()
            if any(keyword in title_lower for keyword in EXCLUSION_KEYWORDS):
                print(f"   [🚫 FILTERED] Non-technical target ignored: {title[:40]}...")
                new_targets.append({
                    "id": target_id,
                    "status": "CLOSED_MISSED",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "title": title,
                    "url": item.get("html_url"),
                    "payout_est": "0"
                })
                continue
            
            if check_for_pr_merges(item):
                print(f"   [👻 GHOST BOUNTY] PR detected/merged: {title[:40]}...")
                new_targets.append({
                    "id": target_id,
                    "status": "CLOSED_MISSED",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "title": title,
                    "url": item.get("html_url"),
                    "payout_est": "0"
                })
                continue
            
            create_vault_sidecar(target_id, item)
            
            payout_est = "TBD"
            # V12.12: Extract wRTC safely
            match = re.search(r'(\d+)\s*(RTC|wRTC|SOL|USDC|USDT|ETH|\$)', title, re.IGNORECASE)
            if match:
                payout_est = f"{match.group(1)} {match.group(2).upper()}"
            
            print(f"   [🎯 NEW TARGET] {target_id}: {title[:40]}...")
            
            new_targets.append({
                "id": target_id,
                "status": "PENDING",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "title": title,
                "url": item.get("html_url"),
                "payout_est": payout_est
            })
            
        return new_targets
    except Exception as e:
        print(f"❌ RADAR ERROR: {e}")
        return []

def update_database(new_rows):
    """Appends new targets to the V12 Ledger."""
    if not new_rows:
        print("📭 Radar sweep complete. No new viable targets found.")
        return

    file_exists = os.path.exists(DATABASE_FILE)
    fieldnames = ["id", "status", "timestamp", "title", "url", "payout_est"]
    
    with open(DATABASE_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
            
        for row in new_rows:
            safe_row = {k: row.get(k, "") for k in fieldnames}
            writer.writerow(safe_row)
            
    print(f"✅ Indexed {len(new_rows)} new targets to the Ledger.")

if __name__ == "__main__":
    if not GITHUB_TOKEN:
        print("❌ SKEIN_GITHUB_TOKEN missing from .env.")
        sys.exit(1)
        
    # 1. Audit existing targets to clear out closed bounties automatically
    audit_stale_targets()
    
    # 2. Sweep for new targets
    new_targets = search_github()
    update_database(new_targets)