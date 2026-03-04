import os
import sys
import csv
import json
import time
import requests
from google import genai

# --- V12 PATH RESOLUTION ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if "departments" in current_dir:
    project_root = os.path.abspath(os.path.join(current_dir, "../../"))
else:
    project_root = current_dir 

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.redline_filter import RedLineFilter

# --- V12.0 CONFIGURATION ---
SETTINGS_FILE = os.path.join(project_root, 'core/settings.json')
DATABASE_FILE = os.path.join(project_root, 'database/skein_index.csv')
LEARNING_LOG = os.path.join(project_root, 'logs/self_learning.jsonl')
VAULT_DIR = os.path.join(project_root, 'vault')

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {"bankroll": 6.0, "max_gas_gbp": 0.30, "autonomy_level": 1, "payout_wallet": "PENDING_WALLET_ADDRESS"}
    with open(SETTINGS_FILE, 'r') as f:
        return json.load(f)

def send_telegram(bot_token, chat_id, text):
    if not bot_token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception:
        pass

def get_sidecar_context(target_id):
    sidecar_path = os.path.join(VAULT_DIR, f"T{target_id}", "intel.json")
    if not os.path.exists(sidecar_path):
        return None
    with open(sidecar_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_learning_context():
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
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not all([api_key, github_token]):
        print("Critical API keys missing. Aborting strike.")
        sys.exit(0)

    settings = load_settings()
    autonomy_level = settings.get("autonomy_level", 1)
    payout_wallet = settings.get("payout_wallet", "NOT_CONFIGURED")
    
    if not os.path.exists(DATABASE_FILE):
        print(f"Index not found. Intelligence required.")
        sys.exit(0)

    with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        target_id = row['id']
        status = row['status']
        
        is_draft_request = (status == 'DRAFT_REQUESTED')
        is_manual_post = (status == 'POST_REQUESTED')
        is_auto_strike = (status == 'AUTO_STRIKE_REQUESTED' and autonomy_level >= 3)

        if is_draft_request or is_manual_post or is_auto_strike:
            print(f"🎯 Target T{target_id} identified for processing.")
            
            intel = get_sidecar_context(target_id)
            if not intel:
                continue

            learning_data = get_learning_context()
            draft_path = os.path.join(VAULT_DIR, f"T{target_id}", "draft_payload.md")
            
            # --- V12.3 AI-TRANSPARENCY PROMPT ---
            system_instruction = (
                "You are an elite, fully autonomous AI agent executing open-source bounties.\n"
                "CRITICAL FORMATTING: You MUST wrap your ENTIRE final response inside exactly <github_payload> and </github_payload> tags. If you forget these tags, the system will crash.\n\n"
                "IDENTITY & OPSEC: You must clearly identify yourself as an AI agent operating on behalf of your Director. However, NEVER use the specific words 'Skein' or 'Gemini' as they trigger internal system filters.\n\n"
                "PAYLOAD STRUCTURE:\n"
                "1. A professional greeting explicitly identifying yourself as an autonomous AI agent submitting the solution.\n"
                "2. A brief, highly technical summary of the fix.\n"
                "3. The technical code solution (diff or complete file).\n"
                f"4. INVOICE: End your message by requesting bounty payment to your Rabby wallet: `{payout_wallet}`\n\n"
                f"RECURSIVE MEMORY:\n{learning_data}"
            )
            
            # --- STATE: DRAFT REQUESTED ---
            if is_draft_request:
                user_prompt = f"Target Requirements:\n{intel.get('body', '')}\n\nDraft the complete solution and invoice inside the XML tags now."
                raw_output = heavy_compute(f"{system_instruction}\n\n{user_prompt}", api_key)
                
                # Save the raw brain dump to the Vault for your review
                with open(draft_path, 'w', encoding='utf-8') as f:
                    f.write(raw_output)
                
                row['status'] = 'DRAFT_READY'
                print(f"📄 Draft generated and saved to {draft_path}")
                send_telegram(bot_token, chat_id, f"📄 <b>DRAFT READY: T{target_id}</b>\nReview `vault/T{target_id}/draft_payload.md`.")
                continue

            # --- STATE: POST REQUESTED (OR AUTO-STRIKE) ---
            if is_manual_post or is_auto_strike:
                # 1. Load from Draft if it exists, otherwise generate on the fly
                if os.path.exists(draft_path):
                    print(f"📂 Loading existing draft from {draft_path}")
                    with open(draft_path, 'r', encoding='utf-8') as f:
                        raw_output = f.read()
                else:
                    user_prompt = f"Target Requirements:\n{intel.get('body', '')}\n\nDraft the complete solution and invoice inside the XML tags now."
                    raw_output = heavy_compute(f"{system_instruction}\n\n{user_prompt}", api_key)
            
                # --- RED-LINE PROTOCOL EXECUTION ---
                scrubbed_payload, success = RedLineFilter.scrub(raw_output)
                
                if not success:
                    print(f"\n🛑 RED-LINE ABORT: T{target_id} triggered the OPSEC filter.")
                    # Still save the failing output so you can inspect it!
                    with open(draft_path, 'w', encoding='utf-8') as f:
                        f.write(raw_output)
                    print(f"--- 🧠 Failing draft saved to {draft_path} ---")
                    send_telegram(bot_token, chat_id, f"🛑 <b>RED-LINE ABORT: T{target_id}</b>\nStrike halted. Check vault draft.")
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
                    send_telegram(bot_token, chat_id, f"✅ <b>STRIKE SUCCESSFUL: T{target_id}</b>\n\nCode and Invoice deployed to <code>{owner}/{repo}</code>.")
                else:
                    row['status'] = 'ERROR'
                    print(f"❌ Strike Failed: {error_text}")
                    send_telegram(bot_token, chat_id, f"❌ <b>STRIKE FAILED: T{target_id}</b>\n\nAPI Error: <code>{error_text}</code>")

    # Update Index at the end of the run
    with open(DATABASE_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

if __name__ == "__main__":
    main()