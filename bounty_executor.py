import os
import sys
import csv
import time
import requests
from google import genai

# --- V10.0 CONFIGURATION ---
BACKLOG_FILE = 'bounty_backlog.csv'
VAULT_DIR = 'vault'
MAX_STARS_PER_RUN = 2

def star_repository(owner, repo, github_token):
    print(f"Starring repository: {owner}/{repo}")
    star_url = f"https://api.github.com/user/starred/{owner}/{repo}"
    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json", "Content-Length": "0"}
    try:
        requests.put(star_url, headers=headers, timeout=10)
    except Exception as e:
        print(f"Starring failed: {e}")

def heavy_compute(prompt, api_key):
    try:
        print("Executing compute via gemini-2.5-flash...")
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        if not response.text:
            return "CRITICAL BRAIN FAILURE: Blocked by API Safety Filters."
        return response.text.strip()
    except Exception as e:
        return f"CRITICAL BRAIN FAILURE: {str(e)}"

def send_telegram(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"})

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
        res = requests.get(api_url, headers=headers, timeout=10).json()
        return res.get('state') == 'open'
    except Exception:
        return True 

# V10.0 FIX: Dynamic Hierarchical Folder Structure
def write_to_vault(target_id, status, title, url, payload, suffix="draft"):
    """Saves payloads into organized folders based on their current status."""
    # Ensure the status folder exists: e.g., vault/DRAFT_SENT/target_1002/
    folder_path = os.path.join(VAULT_DIR, status.upper(), f"target_{target_id}")
    os.makedirs(folder_path, exist_ok=True)
    
    filename = os.path.join(folder_path, f"payload_{suffix}.md")
    
    with open(filename, 'w', encoding='utf-8') as f:
        # Inject metadata at the top of the file for the Director's reference
        f.write(f"# TARGET {target_id}: {title}\n")
        f.write(f"**Source URL:** {url}\n")
        f.write(f"**Current Status:** {status}\n")
        f.write(f"---\n\n")
        f.write(payload)
        
    return filename

def post_to_github(owner, repo, issue_number, payload, github_token):
    strike_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments"
    res = requests.post(strike_url, headers={"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}, json={"body": payload}, timeout=15)
    return res.status_code == 201, res.text

def main():
    api_key, bot_token, chat_id = os.getenv("GEMINI_API_KEY"), os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    github_token, wallet_address = os.getenv("SKEIN_GITHUB_TOKEN"), os.getenv("RABBY_ADDRESS")
    actor = os.getenv("GITHUB_ACTOR", "SovereignSkein") 
    
    if not all([api_key, bot_token, chat_id, github_token, wallet_address]) or not os.path.exists(BACKLOG_FILE): 
        print("System variables missing. Aborting run.")
        sys.exit(0)

    with open(BACKLOG_FILE, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    stars_clicked = 0

    for row in rows:
        if row['status'] == 'APPLIED':
            print(f"Checking for approval on Target #{row['id']}...")
            owner, repo, issue_num = parse_github_url(row['url'])
            
            if not check_is_open(owner, repo, issue_num, github_token):
                row['status'] = 'CLOSED_MISSED'
                print(f"Target #{row['id']} is closed. Moving to CLOSED_MISSED.")
                continue

            comments_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_num}/comments"
            try:
                res = requests.get(comments_url, headers={"Authorization": f"token {github_token}"}, timeout=10).json()
                for comment in res:
                    comment_author = comment.get('user', {}).get('login', '').lower()
                    comment_body = comment.get('body', '').lower()
                    
                    if comment_author not in [actor.lower(), "bill0151"]:
                        if any(word in comment_body for word in ["proceed", "approved", "go ahead", "assigned", "looks good"]):
                            row['status'] = 'AUTO_STRIKE_REQUESTED'
                            send_telegram(bot_token, chat_id, f"🎯 <b>APPROVAL DETECTED!</b> Target #{row['id']} is a GO. Initiating full strike.")
                            break 
            except Exception as e:
                print(f"Error checking comments: {e}")
                continue

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
                send_telegram(bot_token, chat_id, f"⚠️ <b>Drafting Failed for Target #{row['id']}</b>\n\n<b>Diagnostic:</b>\n<code>{payload}</code>")
            else:
                full_payload = payload + signature
                row['status'] = 'DRAFT_SENT'
                
                # V10.0 FIX: Save to hierarchical folder structure!
                file_path = write_to_vault(row['id'], row['status'], row['title'], row['url'], full_payload, "draft")
                row['draft_payload'] = f"VAULT_PATH:{file_path}"
                
                repo_name = os.getenv("GITHUB_REPOSITORY")
                draft_url = f"https://github.com/{repo_name}/blob/main/{file_path}"
                msg = f"📄 <b>DRAFT READY - Target #{row['id']}</b>\n\nPayload secured in Vault.\n\n🔗 <a href='{draft_url}'>View Full Draft</a>\n\n⚡ Reply /post {row['id']} or /amend {row['id']} [notes]"
                send_telegram(bot_token, chat_id, msg)

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
                send_telegram(bot_token, chat_id, f"⚠️ <b>Auto-Strike Failed for Target #{row['id']}</b>\n\n<b>Diagnostic:</b>\n<code>{payload}</code>")
            else:
                full_payload = payload + signature
                is_application = "/apply" in payload.lower()
                if check_is_open(owner, repo, issue_number, github_token):
                    success, error_text = post_to_github(owner, repo, issue_number, full_payload, github_token)
                    if success:
                        if is_application:
                            row['status'] = 'APPLIED'
                            send_telegram(bot_token, chat_id, f"👻 <b>APPLIED - Target #{row['id']}</b>\nThe Ghost has submitted an application and is waiting for approval.")
                        else:
                            row['status'] = 'COMPLETED'
                            send_telegram(bot_token, chat_id, f"✅👻 <b>AUTO-STRIKE SUCCESSFUL - #{row['id']}</b>")
                        
                        # Save the final deployed payload
                        write_to_vault(row['id'], row['status'], row['title'], row['url'], full_payload, "deployed")
                    else:
                        row['status'] = 'ERROR'
                        send_telegram(bot_token, chat_id, f"❌ <b>AUTO-STRIKE FAILED - #{row['id']}</b>\nAPI Error: {error_text}")
                else:
                    row['status'] = 'CLOSED_MISSED'

        elif row['status'] == 'POST_REQUESTED':
            owner, repo, issue_number = parse_github_url(row['url'])
            if check_is_open(owner, repo, issue_number, github_token):
                payload_to_post = row['draft_payload']
                if str(payload_to_post).startswith("VAULT_PATH:"):
                    filepath = payload_to_post.split("VAULT_PATH:")[1]
                    try:
                        with open(filepath, 'r', encoding='utf-8') as v:
                            # Strip the meta-data header if we are posting from a Vault file
                            content = v.read()
                            if "---" in content:
                                payload_to_post = content.split("---", 1)[1].strip()
                            else:
                                payload_to_post = content
                    except Exception as e:
                        print(f"Vault retrieval error: {e}")
                        continue
                
                success, error_text = post_to_github(owner, repo, issue_number, payload_to_post, github_token)
                if success:
                    row['status'] = 'COMPLETED'
                    # Save the deployed record to the COMPLETED folder
                    write_to_vault(row['id'], row['status'], row['title'], row['url'], payload_to_post, "deployed")
                    send_telegram(bot_token, chat_id, f"✅ <b>STRIKE SUCCESSFUL - Target #{row['id']}</b>")
                else:
                    row['status'] = 'ERROR'
                    send_telegram(bot_token, chat_id, f"❌ <b>STRIKE FAILED - Target #{row['id']}</b>\nAPI Error: {error_text}")
            else:
                row['status'] = 'CLOSED_MISSED'
                send_telegram(bot_token, chat_id, f"🛑 <b>STRIKE ABORTED - Target #{row['id']}</b>\nTarget closed.")

    with open(BACKLOG_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["id", "status", "timestamp", "title", "url", "body_snippet", "draft_payload"])
        writer.writeheader()
        writer.writerows(rows)

if __name__ == "__main__":
    main()
