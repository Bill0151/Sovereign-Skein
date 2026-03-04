import os
import sys
import csv
import time
import requests
from google import genai

# --- V11.0 CONFIGURATION ---
BACKLOG_FILE = 'bounty_backlog.csv'
VAULT_DIR = 'vault'
MAX_STARS_PER_RUN = 2

def process_telegram_commands(bot_token, rows):
    """V11.0: Reads /post and /amend commands from Telegram and updates the CSV state."""
    print("Checking Telegram for Director commands...")
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    updates_made = False
    try:
        res = requests.get(url, timeout=10).json()
        if not res.get("ok") or not res.get("result"):
            return rows, False

        highest_update_id = 0

        for item in res["result"]:
            update_id = item["update_id"]
            highest_update_id = max(highest_update_id, update_id)
            
            message = item.get("message", {})
            text = message.get("text", "").strip()
            
            if text.startswith("/post"):
                parts = text.split()
                if len(parts) >= 2:
                    target_id = parts[1]
                    for row in rows:
                        if row['id'] == target_id and row['status'] in ['DRAFT_SENT', 'DRAFT_REQUESTED', 'AMEND_REQUESTED']:
                            row['status'] = 'POST_REQUESTED'
                            updates_made = True
                            print(f"📡 COMMAND RECEIVED: Authorized POST for Target #{target_id}")
                            send_telegram(bot_token, message.get("chat", {}).get("id"), f"🫡 <b>Order Acknowledged:</b> Executing strike on Target #{target_id}")
            
            elif text.startswith("/amend"):
                parts = text.split(" ", 2)
                if len(parts) >= 3:
                    target_id = parts[1]
                    notes = parts[2]
                    for row in rows:
                        if row['id'] == target_id:
                            row['status'] = 'AMEND_REQUESTED'
                            row['draft_payload'] = f"CRITICAL CORRECTION: {notes}"
                            updates_made = True
                            print(f"📡 COMMAND RECEIVED: Ordered AMEND for Target #{target_id}")
                            send_telegram(bot_token, message.get("chat", {}).get("id"), f"🫡 <b>Order Acknowledged:</b> Amending Target #{target_id} with new parameters.")

        # Clear the queue by requesting updates starting from the next ID
        if highest_update_id > 0:
            requests.get(f"{url}?offset={highest_update_id + 1}", timeout=10)
            
        return rows, updates_made
    except Exception as e:
        print(f"Error checking Telegram commands: {e}")
        return rows, False

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

def write_to_vault(target_id, status, title, url, payload, suffix="draft"):
    folder_path = os.path.join(VAULT_DIR, status.upper(), f"target_{target_id}")
    os.makedirs(folder_path, exist_ok=True)
    filename = os.path.join(folder_path, f"payload_{suffix}.md")
    
    with open(filename, 'w', encoding='utf-8') as f:
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

    # V11.0: Intercept and process Telegram commands before acting
    rows, csv_needs_update = process_telegram_commands(bot_token, rows)

    stars_clicked = 0

    for row in rows:
        if row['status'] == 'APPLIED':
            print(f"Checking for approval on Target #{row['id']}...")
            owner, repo, issue_num = parse_github_url(row['url'])
            
            if not check_is_open(owner, repo, issue_num, github_token):
                row['status'] = 'CLOSED_MISSED'
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
                    # V10.2 Smart Status Check
                    is_application = any(keyword in payload_to_post.lower() for keyword in ["/apply", "proposal", "will be opened", "acknowledge the bounty"])
                    if is_application:
                        row['status'] = 'APPLIED'
                        write_to_vault(row['id'], row['status'], row['title'], row['url'], payload_to_post, "applied")
                        send_telegram(bot_token, chat_id, f"👻 <b>APPLIED - Target #{row['id']}</b>\nProposal posted. Now listening for approval.")
                    else:
                        row['status'] = 'COMPLETED'
                        write_to_vault(row['id'], row['status'], row['title'], row['url'], payload_to_post, "deployed")
                        send_telegram(bot_token, chat_id, f"✅ <b>STRIKE SUCCESSFUL - Target #{row['id']}</b>")
                else:
                    row['status'] = 'ERROR'
                    send_telegram(bot_token, chat_id, f"❌ <b>STRIKE FAILED - Target #{row['id']}</b>\nAPI Error: {error_text}")
            else:
                row['status'] = 'CLOSED_MISSED'
                send_telegram(bot_token, chat_id, f"🛑 <b>STRIKE ABORTED - Target #{row['id']}</b>\nTarget closed.")

    # Save CSV back out with any Telegram modifications + execution modifications
    with open(BACKLOG_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["id", "status", "timestamp", "title", "url", "body_snippet", "draft_payload"])
        writer.writeheader()
        writer.writerows(rows)

if __name__ == "__main__":
    main()
