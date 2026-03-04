import os
import sys
import csv
import time
import requests
from google import genai

# --- V9.0 CONFIGURATION ---
BACKLOG_FILE = 'bounty_backlog.csv'
VAULT_DIR = 'vault' # Upgraded from 'drafts' to handle all payload storage
MAX_STARS_PER_RUN = 2  # Hard safety limit

def star_repository(owner, repo, github_token):
    """Physically clicks the Star button on GitHub for a specific repo."""
    print(f"Starring repository: {owner}/{repo}")
    star_url = f"https://api.github.com/user/starred/{owner}/{repo}"
    headers = {
        "Authorization": f"token {github_token}", 
        "Accept": "application/vnd.github.v3+json",
        "Content-Length": "0"
    }
    try:
        requests.put(star_url, headers=headers, timeout=10)
    except Exception as e:
        print(f"Starring failed: {e}")

def heavy_compute(prompt, api_key):
    """Calls the Gemini Flash engine for high-logic drafting."""
    try:
        print("Executing compute via gemini-2.5-flash...")
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text.strip()
    except Exception as e:
        return f"CRITICAL BRAIN FAILURE: {e}"

def send_telegram(bot_token, chat_id, message):
    """Beams status updates to the Director's phone."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"})

def parse_github_url(url):
    """Extracts owner, repo, and issue number from a GitHub URL."""
    parts = url.rstrip('/').split('/')
    if "issues" in parts:
        i = parts.index("issues")
        return parts[i-2], parts[i-1], parts[i+1]
    return None, None, None

def check_is_open(owner, repo, issue_num, github_token):
    """Verifies the target is still active before firing."""
    try:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_num}"
        headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}
        res = requests.get(api_url, headers=headers, timeout=10).json()
        return res.get('state') == 'open'
    except Exception:
        return True 

def write_to_vault(target_id, payload, suffix="draft"):
    """V9.0 Filing System: Archives every payload in the local Vault to protect the CSV."""
    os.makedirs(VAULT_DIR, exist_ok=True)
    filename = os.path.join(VAULT_DIR, f"target_{target_id}_{suffix}.md")
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# Target {target_id} Payload ({suffix.upper()})\n\n{payload}")
    return filename

def post_to_github(owner, repo, issue_number, payload, github_token):
    """Delivers the final payload to the target repository."""
    strike_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments"
    res = requests.post(strike_url, headers={"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}, json={"body": payload}, timeout=15)
    return res.status_code == 201, res.text

def main():
    # Load Environment
    api_key, bot_token, chat_id = os.getenv("GEMINI_API_KEY"), os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    github_token, wallet_address = os.getenv("SKEIN_GITHUB_TOKEN"), os.getenv("RABBY_ADDRESS")
    actor = os.getenv("GITHUB_ACTOR", "SovereignSkein") 
    
    if not all([api_key, bot_token, chat_id, github_token, wallet_address]) or not os.path.exists(BACKLOG_FILE): 
        print("System variables missing. Aborting run.")
        sys.exit(0)

    # Read Current State
    with open(BACKLOG_FILE, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    stars_clicked = 0

    for row in rows:
        # --- STATE 1: THE LISTENING POST (Waiting for approval after /apply) ---
        if row['status'] == 'APPLIED':
            print(f"Checking for approval on Target #{row['id']}...")
            owner, repo, issue_num = parse_github_url(row['url'])
            comments_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_num}/comments"
            
            try:
                res = requests.get(comments_url, headers={"Authorization": f"token {github_token}"}, timeout=10).json()
                for comment in res:
                    comment_author = comment.get('user', {}).get('login', '').lower()
                    comment_body = comment.get('body', '').lower()
                    
                    if comment_author != actor.lower():
                        if any(word in comment_body for word in ["proceed", "approved", "go ahead", "assigned", "looks good"]):
                            row['status'] = 'AUTO_STRIKE_REQUESTED'
                            send_telegram(bot_token, chat_id, f"🎯 <b>APPROVAL DETECTED!</b> Target #{row['id']} is a GO. Initiating full strike.")
                            break 
            except Exception as e:
                print(f"Error checking comments for #{row['id']}: {e}")
                continue

        # --- STATE 2: HUMAN-IN-THE-LOOP (DRAFTS & AMENDS) ---
        elif row['status'] in ['DRAFT_REQUESTED', 'AMEND_REQUESTED']:
            if row['status'] == 'DRAFT_REQUESTED':
                base_prompt = f"Write a highly technical, professional response and code fix for this GitHub issue. Include this wallet for the bounty payout: {wallet_address}. Issue Title: {row['title']} Details: {row['body_snippet']}"
            else: 
                base_prompt = f"Write a highly technical response for this GitHub issue. FOLLOW THESE SPECIFIC INSTRUCTIONS strictly: {row['draft_payload']}. Include this wallet for payout: {wallet_address}. Issue Title: {row['title']} Details: {row['body_snippet']}"

            signature = f"\n\n---\n*Drafted and submitted autonomously by the Sovereign Skein Node, operating on behalf of {actor}.*"
            payload = heavy_compute(base_prompt, api_key)
            time.sleep(5) 
            
            if "CRITICAL BRAIN FAILURE" in payload:
                row['status'] = 'ERROR'
                send_telegram(bot_token, chat_id, f"⚠️ <b>Drafting Failed for Target #{row['id']}</b>")
            else:
                full_payload = payload + signature
                
                # V9.0 Vault Integration: Save payload to file, store file path in CSV
                file_path = write_to_vault(row['id'], full_payload, "draft")
                row['draft_payload'] = f"VAULT_PATH:{file_path}"
                row['status'] = 'DRAFT_SENT'
                
                repo_name = os.getenv("GITHUB_REPOSITORY")
                draft_url = f"https://github.com/{repo_name}/blob/main/{file_path}"
                
                msg = f"📄 <b>DRAFT READY - Target #{row['id']}</b>\n\nPayload secured in Vault.\n\n🔗 <a href='{draft_url}'>View Full Draft</a>\n\n⚡ Reply /post {row['id']} or /amend {row['id']} [notes]"
                send_telegram(bot_token, chat_id, msg)

        # --- STATE 3: THE AUTO-STRIKE FAST LANE (Autonomous Ghost) ---
        elif row['status'] == 'AUTO_STRIKE_REQUESTED':
            owner, repo, issue_number = parse_github_url(row['url'])
            
            if stars_clicked < MAX_STARS_PER_RUN:
                star_repository(owner, repo, github_token)
                stars_clicked += 1
            
            base_prompt = (
                f"You are an elite, fully autonomous AI agent. Read the 'Details' below carefully.\n"
                f"1. If the details ask you to '/apply', submit a thesis, or wait for approval: DO NOT WRITE FULL CODE. "
                f"Instead, write a professional application starting with '/apply'. Describe your capabilities and your architectural plan.\n"
                f"2. If the details ask for a direct fix or you were already approved: Write the full Python code.\n"
                f"FORMATTING: Always wrap any code or logic in standard Markdown ```python blocks.\n"
                f"Include this wallet: {wallet_address}\n"
                f"Details: {row['body_snippet']}"
            )
            signature = f"\n\n---\n*🤖 Generated and deployed autonomously by the Sovereign Skein Level 5 Agent.*"
            
            payload = heavy_compute(base_prompt, api_key)
            time.sleep(5) 
            
            if "CRITICAL BRAIN FAILURE" in payload:
                row['status'] = 'ERROR'
                send_telegram(bot_token, chat_id, f"⚠️ <b>Auto-Strike Failed for Target #{row['id']}</b>")
            else:
                full_payload = payload + signature
                is_application = "/apply" in payload.lower()
                
                if check_is_open(owner, repo, issue_number, github_token):
                    success, error_text = post_to_github(owner, repo, issue_number, full_payload, github_token)
                    if success:
                        # V9.0 Vault Integration: Keep a record of what we deployed
                        write_to_vault(row['id'], full_payload, "deployed")
                        
                        if is_application:
                            row['status'] = 'APPLIED'
                            send_telegram(bot_token, chat_id, f"👻 <b>APPLIED - Target #{row['id']}</b>\nThe Ghost has submitted an application and is waiting for approval.")
                        else:
                            row['status'] = 'COMPLETED'
                            send_telegram(bot_token, chat_id, f"✅👻 <b>AUTO-STRIKE SUCCESSFUL - #{row['id']}</b>")
                    else:
                        row['status'] = 'ERROR'
                        send_telegram(bot_token, chat_id, f"❌ <b>AUTO-STRIKE FAILED - #{row['id']}</b>\nAPI Error: {error_text}")
                else:
                    row['status'] = 'CLOSED_MISSED'

        # --- STATE 4: MANUAL POST REQUESTS ---
        elif row['status'] == 'POST_REQUESTED':
            owner, repo, issue_number = parse_github_url(row['url'])
            if check_is_open(owner, repo, issue_number, github_token):
                # Retrieve from Vault if necessary
                payload_to_post = row['draft_payload']
                if str(payload_to_post).startswith("VAULT_PATH:"):
                    filepath = payload_to_post.split("VAULT_PATH:")[1]
                    try:
                        with open(filepath, 'r', encoding='utf-8') as v:
                            payload_to_post = v.read()
                    except Exception as e:
                        print(f"Vault retrieval error: {e}")
                        continue
                
                success, error_text = post_to_github(owner, repo, issue_number, payload_to_post, github_token)
                if success:
                    row['status'] = 'COMPLETED'
                    write_to_vault(row['id'], payload_to_post, "deployed")
                    send_telegram(bot_token, chat_id, f"✅ <b>STRIKE SUCCESSFUL - Target #{row['id']}</b>")
                else:
                    row['status'] = 'ERROR'
                    send_telegram(bot_token, chat_id, f"❌ <b>STRIKE FAILED - Target #{row['id']}</b>\nAPI Error: {error_text}")
            else:
                row['status'] = 'CLOSED_MISSED'
                send_telegram(bot_token, chat_id, f"🛑 <b>STRIKE ABORTED - Target #{row['id']}</b>\nTarget closed.")

    # Write Final Updated State back to CSV
    with open(BACKLOG_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["id", "status", "timestamp", "title", "url", "body_snippet", "draft_payload"])
        writer.writeheader()
        writer.writerows(rows)

if __name__ == "__main__":
    main()
