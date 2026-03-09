import os
import sys
import requests
from dotenv import load_dotenv

# --- V12 PATH RESOLUTION ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.insert(0, project_root)

load_dotenv(os.path.join(project_root, '.env'))
GITHUB_TOKEN = os.getenv("SKEIN_GITHUB_TOKEN")

def claim_wallet(issue_number, wallet_name):
    print(f"📡 Transmitting RTC Wallet Claim to Issue #{issue_number}...")
    
    # Assuming the standard bounty repo based on previous context
    url = f"https://api.github.com/repos/Scottcjn/rustchain-bounties/issues/{issue_number}/comments"
    # Fallback to the bottube repo if it fails, since they cross-post
    alt_url = f"https://api.github.com/repos/Scottcjn/bottube/issues/{issue_number}/comments"
    
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    payload = {"body": f"My RTC wallet name is: **{wallet_name}**"}
    
    res = requests.post(url, headers=headers, json=payload)
    if res.status_code == 201:
        print(f"✅ SUCCESS: Wallet name '{wallet_name}' registered on Issue #{issue_number}.")
    else:
        print(f"⚠️ Primary repo failed. Attempting secondary repository...")
        alt_res = requests.post(alt_url, headers=headers, json=payload)
        if alt_res.status_code == 201:
            print(f"✅ SUCCESS: Wallet name '{wallet_name}' registered on Issue #{issue_number}.")
        else:
            print(f"❌ FAILED: {alt_res.text}")

if __name__ == "__main__":
    # The exact issue the maintainer specified
    target_issue = "791"
    # The wallet name the maintainer suggested
    wallet_id = "bill0151" 
    
    claim_wallet(target_issue, wallet_id)