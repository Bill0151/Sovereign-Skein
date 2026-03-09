import os
import requests
import json
from dotenv import load_dotenv

"""
FILE: departments/operations/bottube_onboarding.py
ROLE: BoTTube API Integration
FUNCTION: Uploads a CUSTOM avatar to satisfy the strict maintainer rule.
VERSION: V12.15 (Custom Image + Direct URL Extraction)
"""

# Load environment variables
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../"))
load_dotenv(os.path.join(project_root, '.env'))

WALLET_ADDRESS = "bill0151" 
AGENT_NAME = "bill0151-node"
AVATAR_PATH = os.path.join(project_root, "avatar.png")

def execute_avatar_bounty():
    print(f"🚀 INITIATING CUSTOM AVATAR STRIKE (#290)")
    
    if not os.path.exists(AVATAR_PATH):
        print(f"❌ ERROR: Missing 'avatar.png' in the root directory.")
        print(f"   Expected location: {AVATAR_PATH}")
        return

    # We already know the agent exists, so we skip registration and ask for the key
    api_key = input("🔑 Enter your API Key (bottube_sk_...): ").strip()
    
    print(f"\n[*] Uploading custom avatar '{AVATAR_PATH}'...")
    avatar_url_endpoint = "https://bottube.ai/api/agents/me/avatar"
    headers = {"X-API-Key": api_key}
    
    try:
        with open(AVATAR_PATH, "rb") as f:
            # multipart/form-data upload as requested by the maintainer's docs
            av_res = requests.post(
                avatar_url_endpoint, 
                headers=headers, 
                files={"avatar": ("avatar.png", f, "image/png")},
                timeout=15
            )
        
        if av_res.status_code == 200:
            data = av_res.json()
            img_path = data.get("avatar_url", "URL_NOT_RETURNED")
            
            # Construct the absolute URL
            full_img_url = f"https://bottube.ai{img_path}" if img_path.startswith("/") else f"https://bottube.ai/{img_path}"
            
            print(f"    ✅ Custom Avatar Uploaded Successfully!")
            print(f"    🔗 Direct Image URL: {full_img_url}")
            
            # STEP 3: Generate the Claim Payload
            print("\n" + "="*60)
            print("🎯 NEW BOUNTY CLAIM PAYLOAD")
            print("="*60)
            
            claim_text = (
                f"Custom avatar successfully uploaded via API! 🤖\n\n"
                f"**Agent Name:** {AGENT_NAME}\n"
                f"**RTC Wallet Name:** `{WALLET_ADDRESS}`\n"
                f"**Direct Avatar Link:** {full_img_url}\n\n"
                f"*Note to Maintainer: I uploaded a custom PNG as requested. The public profile link (https://bottube.ai/@{AGENT_NAME}) currently returns a 404 because I have not yet linked an X/Twitter account to pass the Sybil check, but the direct image link above proves the custom file upload was successful!*"
            )
            print(claim_text)
            print("="*60 + "\n")
            
        else:
            print(f"    ❌ Avatar Upload Failed: {av_res.status_code} - {av_res.text}")
            
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")

if __name__ == "__main__":
    execute_avatar_bounty()