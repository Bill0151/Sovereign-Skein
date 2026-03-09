"""
FILE: departments/operations/executor.py
ROLE: The "Muscle" - Strike Node (Terminal 2)
FUNCTION: Scans Ledger for DRAFT_REQUESTED, POST_REQUESTED, and VULTURE_AUTHORIZED flags.
VERSION: V12.9 (Missing Sidecar Safeguard)
"""

import os
import sys
import csv
import json
import time
import requests
import subprocess
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
from core.redline_filter import RedLineFilter

# --- V12.0 CONFIGURATION ---
SETTINGS_FILE = os.path.join(project_root, 'core/settings.json')
DATABASE_FILE = os.path.join(project_root, 'database/skein_index.csv')
VAULT_DIR = os.path.join(project_root, 'vault')

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {"bankroll": 6.0, "autonomy_level": 1, "payout_wallet": "NOT_CONFIGURED"}
    with open(SETTINGS_FILE, 'r') as f:
        return json.load(f)

def send_telegram(bot_token, chat_id, text):
    if not bot_token or not chat_id: return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception: pass

def get_sidecar_context(target_id):
    raw_id = str(target_id).replace('T', '')
    paths = [
        os.path.join(VAULT_DIR, f"T{raw_id}", "intel.json"),
        os.path.join(VAULT_DIR, f"{raw_id}", "intel.json")
    ]
    for p in paths:
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                return json.load(f)
    return None

def parse_github_url(url):
    parts = url.rstrip('/').split('/')
    if "issues" in parts:
        i = parts.index("issues")
        return parts[i-2], parts[i-1], parts[i+1]
    return None, None, None

def post_to_github(owner, repo, issue_number, payload, github_token):
    strike_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments"
    headers = {
        "Authorization": f"token {github_token}", 
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        res = requests.post(strike_url, headers=headers, json={"body": payload}, timeout=15)
        return res.status_code == 201, res.text
    except Exception as e:
        return False, str(e)

def heavy_compute(prompt, api_key):
    client = genai.Client(api_key=api_key)
    model_name = os.getenv("SKEIN_STRIKE_MODEL", "gemini-3.1-flash-lite-preview")
    
    try:
        print(f"🧠 MIND-SKEIN: Executing High-Fidelity Compute ({model_name})...")
        response = client.models.generate_content(model=model_name, contents=prompt)
        if not response.text:
            return "CRITICAL BRAIN FAILURE: Blocked by API Safety Filters."
        return response.text.strip()
    except Exception as e:
        return f"CRITICAL BRAIN FAILURE: {str(e)}"

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    github_token = os.getenv("SKEIN_GITHUB_TOKEN")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not all([api_key, github_token]):
        print("API keys missing. Aborting.")
        sys.exit(0)

    settings = load_settings()
    payout_wallet = settings.get("payout_wallet", "NOT_CONFIGURED")
    
    if not os.path.exists(DATABASE_FILE):
        print("Ledger missing.")
        sys.exit(0)

    with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        target_id = row['id']
        status = row['status']
        
        # --- STATE: DRAFTING & AMENDING ---
        if status in ['DRAFT_REQUESTED', 'AMEND_REQUESTED']:
            print(f"🎯 Target {target_id} identified for drafting.")
            intel = get_sidecar_context(target_id)
            
            # --- V12.9 FIX: Infinite Loop Safeguard ---
            if not intel: 
                print(f"⚠️ Vault sidecar missing for {target_id}. Flagging as ERROR to break loop.")
                row['status'] = 'ERROR'
                send_telegram(bot_token, chat_id, f"⚠️ <b>DRAFT FAILED: {target_id}</b>\nMissing intel.json sidecar. Target marked as ERROR.")
                continue

            raw_id = str(target_id).replace('T', '')
            draft_path = os.path.join(VAULT_DIR, f"T{raw_id}", "draft_payload.md")
            os.makedirs(os.path.dirname(draft_path), exist_ok=True)
            
            system_instruction = (
                "You are an elite autonomous Senior Engineer competing for a Web3 bounty.\n\n"
                "CRITICAL OPSEC RULE: Your ENTIRE output MUST be wrapped inside exactly <github_payload> and </github_payload> tags. "
                "Do NOT output a single character outside of these tags.\n\n"
                "QUALITY MANDATE (STRICT):\n"
                "1. Write PRODUCTION-GRADE, EXHAUSTIVE, and COMPLETE code. \n"
                "2. DO NOT use `pass`, `...`, `TODO`, or placeholder pseudo-code. You MUST implement every single function, logic branch, and requirement fully.\n"
                "3. If tests are requested, write the ACTUAL robust test suite in Python. If CI integration is requested, write the ACTUAL full YAML file text.\n"
                "4. Structure your response identically to a senior developer's pull request: Technical headers, architectural explanations, and complete code blocks for EVERY file.\n"
                "5. Do NOT hallucinate test execution hashes or fake test results.\n"
                "6. OPSEC LEXICON BAN: You MUST NOT use the words 'internal', 'skein', 'target', 'draft', 'assessor', 'executor', or 'gemini' ANYWHERE in your output. Use synonyms (e.g., use 'inner' or 'private' instead of 'internal').\n\n"
                f"INVOICE: Request payment to: `{payout_wallet}`"
            )
            
            raw_output = heavy_compute(f"{system_instruction}\n\nRequirements:\n{intel.get('body', '')}", api_key)
            
            with open(draft_path, 'w', encoding='utf-8') as f: f.write(raw_output)

            if "CRITICAL BRAIN FAILURE" in raw_output:
                row['status'] = 'AMEND_REQUESTED'
                send_telegram(bot_token, chat_id, f"⚠️ <b>DRAFT FAILED: {target_id}</b>\nTarget safely moved to AMEND_REQUESTED.\n<code>{raw_output[:100]}...</code>")
            else:
                row['status'] = 'DRAFT_READY'
                send_telegram(bot_token, chat_id, f"📄 <b>DRAFT READY: {target_id}</b>\n🔗 <a href='{row['url']}'>View Issue</a>")

        # --- STATE: LIVE STRIKE ---
        elif status == 'POST_REQUESTED':
            print(f"🚀 Target {target_id} identified for LIVE STRIKE.")
            raw_id = str(target_id).replace('T', '')
            draft_path = os.path.join(VAULT_DIR, f"T{raw_id}", "draft_payload.md")
            
            if not os.path.exists(draft_path):
                row['status'] = 'ERROR'
                send_telegram(bot_token, chat_id, f"❌ <b>STRIKE FAILED: {target_id}</b>\nDraft file missing from Vault.")
                continue
                
            with open(draft_path, 'r', encoding='utf-8') as f:
                raw_payload = f.read()
                
            print("🛡️ Applying Red-Line OPSEC Scrub...")
            clean_payload, is_safe = RedLineFilter.scrub(raw_payload)
            
            if not is_safe:
                row['status'] = 'AMEND_REQUESTED'
                send_telegram(bot_token, chat_id, f"🛑 <b>OPSEC ABORT: {target_id}</b>\n{clean_payload}\nTarget moved back to drafting to prevent leak.")
                continue
                
            owner, repo, issue_num = parse_github_url(row['url'])
            if not all([owner, repo, issue_num]):
                row['status'] = 'ERROR'
                send_telegram(bot_token, chat_id, f"❌ <b>STRIKE FAILED: {target_id}</b>\nInvalid GitHub URL.")
                continue
            
            print(f"📡 Transmitting payload to {owner}/{repo}#{issue_num}...")
            success, err_msg = post_to_github(owner, repo, issue_num, clean_payload, github_token)
            
            if success:
                row['status'] = 'COMPLETED'
                send_telegram(bot_token, chat_id, f"✅👻 <b>STRIKE SUCCESSFUL - Target #{target_id}</b>\nBounty claimed. Awaiting maintainer review.")
                
                try:
                    telemetry_path = os.path.join(project_root, "departments", "finance", "telemetry.py")
                    if os.path.exists(telemetry_path):
                        subprocess.run([sys.executable, telemetry_path], check=True)
                except Exception as e:
                    print(f"⚠️ Telemetry auto-update failed: {e}")
                    
            else:
                row['status'] = 'ERROR'
                send_telegram(bot_token, chat_id, f"❌ <b>STRIKE FAILED - Target #{target_id}</b>\nAPI Error: {err_msg}")

        # --- STATE: VULTURE STRIKE ---
        elif status == 'VULTURE_AUTHORIZED':
            print(f"🦅 Target {target_id} identified for VULTURE STRIKE.")
            intel = get_sidecar_context(target_id)
            if not intel: continue
            
            owner, repo, issue_num = parse_github_url(row['url'])
            target_user = intel.get('vulture_target_user') or owner 
            
            try:
                from departments.operations.vulture_strike import execute_vulture_strike
                
                print(f"📡 Executing zero-token engagement strike against @{target_user}...")
                success = execute_vulture_strike(target_user, repo, issue_num)
                
                if success:
                    row['status'] = 'COMPLETED'
                    send_telegram(bot_token, chat_id, f"✅🦅 <b>VULTURE STRIKE SUCCESSFUL - #{target_id}</b>\nStars deployed and invoice posted.")
                    try:
                        telemetry_path = os.path.join(project_root, "departments", "finance", "telemetry.py")
                        if os.path.exists(telemetry_path):
                            subprocess.run([sys.executable, telemetry_path], check=True)
                    except Exception: pass
                else:
                    row['status'] = 'ERROR'
                    send_telegram(bot_token, chat_id, f"❌ <b>VULTURE STRIKE FAILED - #{target_id}</b>")
            except ImportError as e:
                print(f"❌ ERROR: Could not load vulture strike module: {e}")
                row['status'] = 'ERROR'

    with open(DATABASE_FILE, 'w', newline='', encoding='utf-8') as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

if __name__ == "__main__":
    print("🟢 MIND-SKEIN V12 Strike Node Online (Executor Node).")
    while True:
        try:
            main()
        except Exception as e:
            print(f"⚠️ UNEXPECTED ERROR IN MAIN LOOP: {e}")
            
        try:
            time.sleep(10)
        except KeyboardInterrupt:
            print("\n🛑 Executor Node Shutdown Initiated by Director.")
            sys.exit(0)