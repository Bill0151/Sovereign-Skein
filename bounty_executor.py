import os
import sys
import csv
import requests
from google import genai

BACKLOG_FILE = 'bounty_backlog.csv'
DRAFTS_DIR = 'drafts'

def heavy_compute(prompt, api_key):
    try:
        # V7 Hardcode: Relying exclusively on the unlimited Flash engine
        print("Executing compute via gemini-2.5-flash...")
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text.strip()
    except Exception as e:
        return f"CRITICAL BRAIN FAILURE: {e}"

def send_telegram(bot_token, chat_id, message):
    requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"})

def parse_github_url(url):
    parts = url.rstrip('/').split('/')
    if "issues" in parts:
        i = parts.index("issues")
        return parts[i-2], parts[i-1], parts[i+1]
    return None, None, None

def check_is_open(owner, repo, issue_num, github_token):
    try:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_num}"
        headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}
        res = requests.get(api_url, headers=headers).json()
        return res.get('state') == 'open'
    except Exception:
        return True # Fail open to avoid blocking strikes on API glitch

def write_draft_file(target_id, payload):
    # V7 Upgrade: Create drafts directory if it doesn't exist
    os.makedirs(DRAFTS_DIR, exist_ok=True)
    filename = os.path.join(DRAFTS_DIR, f"target_{target_id}_draft.md")
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# Target {target_id} Draft\n\n{payload}")
    return f"drafts/target_{target_id}_draft.md"

def main():
    api_key, bot_token, chat_id = os.getenv("GEMINI_API_KEY"), os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    github_token, wallet_address = os.getenv("SKEIN_GITHUB_TOKEN"), os.getenv("RABBY_ADDRESS")
    actor = os.getenv("GITHUB_ACTOR", "SovereignSkein") # Automatically grabs your exact GitHub Username
    
    if not all([api_key, bot_token, chat_id, github_token, wallet_address]): 
        print("Missing environment variables. Aborting.")
        sys.exit(0)

    if not os.path.exists(BACKLOG_FILE):
        print("Backlog missing. Aborting.")
        sys.exit(0)

    with open(BACKLOG_FILE, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        if row['status'] in ['DRAFT_REQUESTED', 'AMEND_REQUESTED']:
            
            if row['status'] == 'DRAFT_REQUESTED':
                base_prompt = f"Write a highly technical, professional response and code fix for this GitHub issue. Include this wallet for the bounty payout: {wallet_address}. Issue Title: {row['title']} Details: {row['body_snippet']}"
            else: # AMEND_REQUESTED
                base_prompt = f"Write a highly technical response for this GitHub issue. FOLLOW THESE SPECIFIC INSTRUCTIONS strictly: {row['draft_payload']}. Include this wallet for payout: {wallet_address}. Issue Title: {row['title']} Details: {row['body_snippet']}"

            signature = f"\n\n---\n*Drafted and submitted autonomously by the Sovereign Skein Node, operating on behalf of {actor}.*"
            
            payload = heavy_compute(base_prompt, api_key)
            
            if "CRITICAL BRAIN FAILURE" in payload:
                row['status'] = 'ERROR'
                send_telegram(bot_token, chat_id, f"⚠️ <b>Drafting Failed for Target #{row['id']}</b>\n{payload}")
            else:
                full_payload = payload + signature
                row['draft_payload'] = full_payload
                row['status'] = 'DRAFT_SENT'
                
                # Write to the new filing system
                file_path = write_draft_file(row['id'], full_payload)
                
                repo_name = os.getenv("GITHUB_REPOSITORY")
                draft_url = f"https://github.com/{repo_name}/blob/main/{file_path}"
                
                msg = f"📄 <b>DRAFT READY - Target #{row['id']}</b>\nEngine: FLASH\n\n"
                msg += f"{full_payload[:800]}...\n\n"
                msg += f"🔗 <a href='{draft_url}'>View Full Draft Here</a>\n\n"
                msg += f"⚡ Reply <code>/post {row['id']}</code> or <code>/amend {row['id']} [notes]</code>"
                send_telegram(bot_token, chat_id, msg)

        elif row['status'] == 'POST_REQUESTED':
            owner, repo, issue_number = parse_github_url(row['url'])
            
            # The Pre-Strike Safety Check
            if not check_is_open(owner, repo, issue_number, github_token):
                row['status'] = 'CLOSED_MISSED'
                send_telegram(bot_token, chat_id, f"🛑 <b>STRIKE ABORTED - Target #{row['id']}</b>\nThe bounty was closed before we could fire.")
                continue

            strike_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments"
            res = requests.post(strike_url, headers={"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}, json={"body": row['draft_payload']})
            
            if res.status_code == 201:
                row['status'] = 'COMPLETED'
                send_telegram(bot_token, chat_id, f"✅ <b>STRIKE SUCCESSFUL - Target #{row['id']}</b>\nPayload delivered to GitHub.")
            else:
                row['status'] = 'ERROR'
                send_telegram(bot_token, chat_id, f"❌ <b>STRIKE FAILED - Target #{row['id']}</b>\nGitHub API Error: {res.text}")

    with open(BACKLOG_FILE, 'w', newline='', encoding='utf-8') as f:
        # Synced V7 Headers
        writer = csv.DictWriter(f, fieldnames=["id", "status", "timestamp", "title", "url", "body_snippet", "draft_payload"])
        writer.writeheader()
        writer.writerows(rows)

if __name__ == "__main__":
    main()
