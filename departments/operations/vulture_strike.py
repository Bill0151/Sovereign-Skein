"""
FILE: departments/intelligence/collector.py
ROLE: The "Radar" - Intelligence Node
FUNCTION: Scours GitHub for bounties, checks for existing claims using cheap tier models, and extracts financial payouts.
"""

import os
import sys
import csv
import json
import time
import requests
from datetime import datetime
from google import genai
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

GITHUB_TOKEN = os.getenv("SKEIN_GITHUB_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DATABASE_FILE = os.path.join(project_root, 'database/skein_index.csv')
VAULT_DIR = os.path.join(project_root, 'vault')

os.makedirs(os.path.dirname(DATABASE_FILE), exist_ok=True)
os.makedirs(VAULT_DIR, exist_ok=True)

def check_ghost_bounty_cheap(comments_text, api_key):
    """Uses the extremely cheap 1B model to sense-check comments for claims without burning 27B quota."""
    if not comments_text.strip():
        return False
        
    client = genai.Client(api_key=api_key)
    prompt = (
        "You are an assistant checking if a task has already been claimed by someone else.\n"
        "Read the following comments from a GitHub issue.\n"
        "If the comments clearly indicate someone has already claimed the bounty, submitted a Pull Request, or been paid, reply ONLY with 'CLAIMED'.\n"
        "Otherwise, reply ONLY with 'OPEN'.\n\n"
        f"COMMENTS:\n{comments_text[:1000]}"
    )
    
    # Use the absolute lowest-tier model to save resources
    cheap_models = ['gemma-3-1b-it', 'gemma-3-2b-it', 'gemini-3.1-flash-lite-preview']
    
    for model in cheap_models:
        try:
            res = client.models.generate_content(model=model, contents=prompt)
            text = res.text.strip().upper()
            return "CLAIMED" in text
        except Exception:
            continue
    return False

def search_github():
    print("📡 INTELLIGENCE: Initiating Radar Sweep...")
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    query = "is:issue is:open language:python (bounty OR reward OR \"help wanted\") no:assignee"
    url = f"https://api.github.com/search/issues?q={query}&sort=created&order=desc&per_page=30"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        new_targets = []
        if not data.get("items"):
            print("   [!] No new targets found on GitHub.")
            return []
            
        print(f"📡 INTELLIGENCE: Evaluating {len(data['items'])} issues...")
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # --- V12.19 CASCADE FALLBACK MODELS ---
        models_to_try = [
            'gemma-3-27b-it', 
            'gemma-3-12b-it', 
            'gemma-3-4b-it', 
            'gemini-3.1-flash-lite-preview'
        ]
        
        for item in data.get("items", []):
            title = item.get("title", "")
            body = item.get("body", "") or ""
            
            # 1. Aggressively truncate body to save Gemma 27B TPM limits (15K max)
            body_snippet = body[:800] 
            
            # 2. Heuristic Check for Ghost Bounties (Fast & Free)
            comments_text = ""
            is_ghost = False
            if item.get("comments", 0) > 0:
                try:
                    c_res = requests.get(item.get("comments_url"), headers=headers).json()
                    last_comments = [c.get("body", "") for c in c_res[-3:]]
                    comments_text = "\n".join(last_comments)
                    
                    # Fast python check first
                    lower_comments = comments_text.lower()
                    if any(word in lower_comments for word in ['claiming', 'pr submitted', 'paid', 'delivered']):
                        is_ghost = True
                    else:
                        # 3. Cheap Model Sense-Check (1B model)
                        print(f"   [?] Analyzing comments for {title[:20]}...")
                        is_ghost = check_ghost_bounty_cheap(comments_text, GEMINI_API_KEY)
                except Exception:
                    pass
            
            if is_ghost:
                print(f"   [👻 GHOST BOUNTY] (Already Claimed): {title[:40]}...")
                continue
            
            # 4. Financial Extraction (Using the 27B/12B Cascade)
            prompt = (
                "You are an elite financial extraction agent for a GitHub software bounty system.\n"
                "Read the issue title, body, and comments below.\n\n"
                "CRITICAL RULES:\n"
                "1. NO FREE LABOR: If the issue lacks any explicit mention of a financial reward or payout, reply ONLY with 'SPAM'.\n"
                "2. NO VIDEO BAIT: If the issue asks the user to watch videos (YouTube/BoTTube) or write social media posts, reply ONLY with 'SPAM'.\n"
                "3. VULTURE BAIT: If the issue asks to STAR repositories or FOLLOW users, extract the target username and payout. Reply STRICTLY in this format: VULTURE | [AMOUNT] | [TARGET_USERNAME] (e.g., VULTURE | 25 RTC | Scottcjn).\n"
                "4. EXTRACTION (CODING): If it requires software engineering AND includes a payout, format as: CLEAN | [AMOUNT].\n"
                "5. AUTOMATION: If it is an automated bot report, reply ONLY with 'SPAM'.\n\n"
                f"Title: {title}\nBody: {body_snippet}"
            )
            
            payout_value = "TBD"
            vulture_user = ""
            status_flag = "PENDING"
            res_text = None
            
            for model in models_to_try:
                try:
                    res = client.models.generate_content(model=model, contents=prompt)
                    res_text = res.text.strip().replace('\n', ' ').upper()
                    break # Success
                except Exception as e:
                    print(f"   [FALLBACK] Model {model} failed: {e}. Trying next...")
                    time.sleep(2)
            
            if not res_text:
                print(f"   [GEMMA SHIELD ERROR] All models exhausted for: {title[:20]}...")
                continue 
                
            if "SPAM" in res_text:
                print(f"   [🛡️ AI REJECTED] (Spam/Video Bait): {title[:40]}...")
                continue
            elif "VULTURE" in res_text:
                parts = [p.strip() for p in res_text.split('|')]
                if len(parts) >= 2: payout_value = parts[1]
                if len(parts) >= 3: vulture_user = parts[2]
                status_flag = "VULTURE_PENDING"
                print(f"   [🦅 VULTURE TARGET] (Value: {payout_value}): {title[:45]}...")
            elif "CLEAN" in res_text:
                parts = [p.strip() for p in res_text.split('|')]
                if len(parts) > 1: payout_value = parts[1]
                print(f"   [✅ AI RETAINED] (Value: {payout_value}): {title[:45]}...")
                    
            target_id = f"T{item['id']}"
            intel = {
                "id": target_id,
                "title": title,
                "url": item.get("html_url"),
                "body": body[:2000], 
                "repository_url": item.get("repository_url"),
                "created_at": item.get("created_at"),
                "extracted_payout": payout_value,
                "vulture_target_user": vulture_user
            }
            new_targets.append((intel, status_flag))
            time.sleep(2.5) 
            
        return new_targets
        
    except requests.exceptions.RequestException as e:
        print(f"❌ INTELLIGENCE ERROR: {e}")
        return []

def update_database(new_targets_tuples):
    print(f"💾 INTELLIGENCE: Processing {len(new_targets_tuples)} targets...")
    existing_ids = set()
    if os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, mode='r', encoding='utf-8') as f:
            for row in csv.DictReader(f): existing_ids.add(row['id'])
                
    new_additions = 0
    with open(DATABASE_FILE, mode='a', newline='', encoding='utf-8') as f:
        fieldnames = ['id', 'status', 'timestamp', 'title', 'url', 'payout_est', 'sidecar_link']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not existing_ids: writer.writeheader()
            
        for target, initial_status in new_targets_tuples:
            if target['id'] not in existing_ids:
                target_dir = os.path.join(VAULT_DIR, target['id'])
                os.makedirs(target_dir, exist_ok=True)
                sidecar_path = os.path.join(target_dir, 'intel.json')
                
                with open(sidecar_path, 'w', encoding='utf-8') as sf:
                    json.dump(target, sf, indent=4)
                    
                writer.writerow({
                    'id': target['id'],
                    'status': initial_status,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'title': target['title'],
                    'url': target['url'],
                    'payout_est': target.get('extracted_payout', 'TBD'),
                    'sidecar_link': f"vault/{target['id']}/intel.json"
                })
                new_additions += 1
                
    print(f"✅ INTELLIGENCE: Added {new_additions} paid targets to the index.")

if __name__ == "__main__":
    targets = search_github()
    if targets: update_database(targets)