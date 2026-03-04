import os
import sys

# --- V12 PATH RESOLUTION ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if "departments" in current_dir:
    project_root = os.path.abspath(os.path.join(current_dir, "../../"))
else:
    project_root = current_dir 

if project_root not in sys.path:
    sys.path.insert(0, project_root)

import csv
import json
import time
import re
import requests
from google import genai
from core.redline_filter import RedLineFilter

# --- V12.0 CONFIGURATION ---
SETTINGS_FILE = os.path.join(project_root, 'core/settings.json')
DATABASE_FILE = os.path.join(project_root, 'database/skein_index.csv')
LEARNING_LOG = os.path.join(project_root, 'logs/self_learning.jsonl')
VAULT_DIR = os.path.join(project_root, 'vault')

def load_settings():
    """Loads the central configuration for the Mind-Skein."""
    if not os.path.exists(SETTINGS_FILE):
        return {"bankroll": 6.0, "max_gas_gbp": 0.30, "autonomy_level": 1, "payout_wallet": "PENDING_WALLET_ADDRESS"}
    with open(SETTINGS_FILE, 'r') as f:
        return json.load(f)

def get_sidecar_context(target_id):
    """Fetches the high-fidelity intelligence context for a target."""
    sidecar_path = os.path.join(VAULT_DIR, f"T{target_id}", "intel.json")
    if not os.path.exists(sidecar_path):
        return None
    with open(sidecar_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_learning_context():
    """Retrieves historical HITL feedback to inject into the brain."""
    context = ""
    if os.path.exists(LEARNING_LOG):
        with open(LEARNING_LOG, 'r', encoding='utf-8') as f:
            lines = f.readlines()[-10:]
            for line in lines:
                try:
                    data = json.loads(line)
                    context += f"- Previous Correction: {data.get('feedback', '')}\n"
                except json.JSONDecodeError:
                    continue
    return context

def heavy_compute(prompt, api_key):
    """Executes compute via gemini-2.5-flash with recursive context."""
    try:
        print("🧠 MIND-SKEIN: Executing High-Fidelity Compute...")
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        if not response.text:
            return "CRITICAL BRAIN FAILURE: Blocked by API Safety Filters."
        return response.text.strip()
    except Exception as e:
        return f"CRITICAL BRAIN FAILURE: {str(e)}"

def post_to_github(owner, repo, issue_number, payload, github_token):
    """Submits the scrubbed payload to the battlefield."""
    strike_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    res = requests.post(strike_url, headers=headers, json={"body": payload}, timeout=15)
    return res.status_code == 201, res.text

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    github_token = os.getenv("SKEIN_GITHUB_TOKEN")
    
    if not all([api_key, github_token]):
        print("Critical API keys missing. Aborting strike.")
        sys.exit(0)

    settings = load_settings()
    autonomy_level = settings.get("autonomy_level", 1)
    payout_wallet = settings.get("payout_wallet", "NOT_CONFIGURED")
    
    if not os.path.exists(DATABASE_FILE):
        print(f"Index not found at {DATABASE_FILE}. Intelligence required.")
        sys.exit(0)

    with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("Database is empty. No targets to process.")
        return

    for row in rows:
        target_id = row['id']
        status = row['status']
        
        is_manual_post = (status == 'POST_REQUESTED')
        is_auto_strike = (status == 'AUTO_STRIKE_REQUESTED' and autonomy_level >= 3)

        if is_manual_post or is_auto_strike:
            print(f"🎯 Target T{target_id} identified for Strike.")
            
            intel = get_sidecar_context(target_id)
            if not intel:
                print(f"Error: Sidecar for T{target_id} missing at {VAULT_DIR}. Skipping.")
                continue

            learning_data = get_learning_context()
            
            # --- V12.1 INVOICE & CLAIM PROMPT ---
            system_instruction = (
                "You are the MIND-SKEIN V12 Operational Node, an elite autonomous developer claiming a bounty.\n"
                "OPSEC PROTOCOL: You MUST wrap your final public-facing response in <github_payload> tags.\n"
                "Everything outside these tags is for internal reasoning only and will be SCRUBBED.\n\n"
                "PAYLOAD STRUCTURE (MANDATORY):\n"
                "1. A professional greeting stating you are submitting the solution for this bounty/issue.\n"
                "2. A brief, human-readable summary of the fix.\n"
                "3. The technical payload (the code diff or implementation).\n"
                f"4. An 'Invoice' section requesting the bounty be sent to this wallet/address: `{payout_wallet}`\n\n"
                f"RECURSIVE MEMORY:\n{learning_data}"
            )
            
            user_prompt = f"Target Requirements:\n{intel.get('body', '')}\n\nDraft the complete solution and invoice now."
            
            raw_output = heavy_compute(f"{system_instruction}\n\n{user_prompt}", api_key)
            
            # --- RED-LINE PROTOCOL EXECUTION ---
            scrubbed_payload, success = RedLineFilter.scrub(raw_output)
            
            if not success:
                print(f"🛑 RED-LINE ABORT: T{target_id} contains forbidden nomenclature or malformed tags.")
                continue

            try:
                url_parts = row['url'].rstrip('/').split('/')
                owner, repo, issue_num = url_parts[-4], url_parts[-3], url_parts[-1]
            except IndexError:
                print(f"Error parsing URL for T{target_id}: {row['url']}")
                continue

            print(f"🚀 Deploying Payload and Invoice to {owner}/{repo}...")
            post_success, error_text = post_to_github(owner, repo, issue_num, scrubbed_payload, github_token)
            
            if post_success:
                row['status'] = 'COMPLETED'
                print(f"✅ Strike Successful: T{target_id}")
            else:
                row['status'] = 'ERROR'
                print(f"❌ Strike Failed: {error_text}")

    # Update Index
    with open(DATABASE_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

if __name__ == "__main__":
    main()