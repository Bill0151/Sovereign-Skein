import os
import sys
import time
import requests
from dotenv import load_dotenv

"""
FILE: departments/operations/engagement_drive.py
ROLE: Strength Multiplier Automator
FUNCTION: Executes Action #1 (101 Stars) and Action #2 (Follow) for Issue #562.
"""

# --- V12 PATH RESOLUTION ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.insert(0, project_root)

load_dotenv(os.path.join(project_root, '.env'))
GITHUB_TOKEN = os.getenv("SKEIN_GITHUB_TOKEN")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def run_engagement():
    target_user = "Scottcjn"
    target_repo = "rustchain-bounties"
    issue_number = "562"
    
    print(f"🦅 MIND-SKEIN: Initiating Strength Multiplier Strike (#562)...")

    # ACTION 2: Follow Scottcjn
    print(f"[*] Action #2: Following @{target_user}...")
    res = requests.put(f"https://api.github.com/user/following/{target_user}", headers=HEADERS)
    if res.status_code == 204:
        print("    ✅ Follow Verified.")
    else:
        print(f"    ⚠️ Follow failed or already active ({res.status_code}).")

    # ACTION 1: Star ALL Repos
    print(f"[*] Action #1: Indexing all {target_user} repositories...")
    repos = []
    page = 1
    while True:
        r_res = requests.get(f"https://api.github.com/users/{target_user}/repos?per_page=100&page={page}", headers=HEADERS)
        if r_res.status_code != 200: break
        data = r_res.json()
        if not data: break
        repos.extend([r["name"] for r in data])
        page += 1
    
    print(f"    📦 Found {len(repos)} repositories. Commencing Star Carpet Bomb...")
    
    starred = 0
    for repo_name in repos:
        star_url = f"https://api.github.com/user/starred/{target_user}/{repo_name}"
        s_res = requests.put(star_url, headers={"Authorization": f"token {GITHUB_TOKEN}", "Content-Length": "0"})
        if s_res.status_code == 204:
            starred += 1
            sys.stdout.write(f"\r    ⭐ Progress: {starred}/{len(repos)}")
            sys.stdout.flush()
        time.sleep(0.1)

    print(f"\n    ✅ Action #1 Complete. {starred} stars deployed.")
    print("\n💡 NEXT STEPS FOR DIRECTOR (Manual Extraction):")
    print("1. Go to https://bottube.ai - Sign up as 'bill0151' and upvote 5 videos.")
    print("2. Go to https://saascity.io - Find BoTTube and RustChain, then upvote both.")
    print(f"3. Comment on GitHub Issue #{issue_number} with the generated claim payload.")

if __name__ == "__main__":
    run_engagement()