import os
import sys
import csv
import requests
from google import genai

BACKLOG_FILE = 'bounty_backlog.csv'

def get_telegram_commands(bot_token):
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    try:
        res = requests.get(url, timeout=10).json()
        commands = []
        if res.get("ok"):
            for update in res["result"]:
                text = update.get("message", {}).get("text", "")
                if text.startswith("/"):
                    commands.append(text)
        return commands
    except:
        return []

def send_telegram(bot_token, chat_id, message):
    requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"})

def check_is_open(url, github_token):
    try:
        parts = url.rstrip('/').split('/')
        i = parts.index("issues")
        owner, repo, issue_num = parts[i-2], parts[i-1], parts[i+1]
        api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_num}"
        headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}
        res = requests.get(api_url, headers=headers).json()
        return res.get('state') == 'open'
    except Exception as e:
        return True # Fail open to avoid accidental deletion

def assess_bounty(prompt, api_key):
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text.strip()
    except Exception as e:
        return f"BRAIN ERROR: {e}"

def main():
    api_key, bot_token, chat_id = os.getenv("GEMINI_API_KEY"), os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    github_token = os.getenv("SKEIN_GITHUB_TOKEN")
    
    if not all([api_key, bot_token, chat_id, github_token]) or not os.path.exists(BACKLOG_FILE): 
        sys.exit(0)

    commands = get_telegram_commands(bot_token)
    
    with open(BACKLOG_FILE, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    # Process Telegram Commands
    for cmd in commands:
        parts = cmd.split()
        action = parts[0].lower()
        
        if action == "/help":
            help_text = (
                "🤖 <b>Agent Frankenskein V6</b>\n\n"
                "<b>STRIKE COMMANDS</b>\n"
                "<code>/draft [id]</code> - Draft with Flash (Free)\n"
                "<code>/draft [id] pro</code> - Draft with Pro (Heavy)\n"
                "<code>/amend [id] [notes]</code> - Rewrite draft\n"
                "<code>/post [id]</code> - Fire payload to GitHub\n\n"
                "<b>PULSE COMMANDS</b>\n"
                "<code>/retry [id]</code> - Clear ERROR state\n"
                "<code>/refresh</code> - Check for closed targets\n"
                "<code>/reject [id]</code> - Discard target"
            )
            send_telegram(bot_token, chat_id, help_text)
            
        elif action == "/refresh":
            for row in rows:
                if row['status'] in ['PENDING', 'MENU_SENT', 'DRAFT_SENT', 'ERROR', 'DRAFT_REQUESTED']:
                    if not check_is_open(row['url'], github_token):
                        row['status'] = 'CLOSED'
                        send_telegram(bot_token, chat_id, f"🗑️ <b>Target #{row['id']} marked CLOSED.</b>\nBounty is no longer active.")
                        
        elif len(parts) >= 2 and parts[1].isdigit():
            target_id = parts[1]
            for row in rows:
                if row['id'] == target_id:
                    if action == "/draft" and row['status'] in ['MENU_SENT', 'ERROR']:
                        row['status'] = 'DRAFT_REQUESTED'
                        # Inject engine choice into payload to pass to Executor
                        row['draft_payload'] = "ENGINE:PRO" if "pro" in cmd.lower() else "ENGINE:FLASH"
                    elif action == "/amend" and row['status'] in ['DRAFT_SENT', 'ERROR']:
                        row['status'] = 'AMEND_REQUESTED'
                        row['draft_payload'] = cmd.replace(f"/amend {target_id}", "").strip()
                    elif action == "/post" and row['status'] == 'DRAFT_SENT':
                        row['status'] = 'POST_REQUESTED'
                    elif action == "/reject":
                        row['status'] = 'REJECTED'
                    elif action == "/retry" and row['status'] == 'ERROR':
                        row['status'] = 'MENU_SENT'
                        send_telegram(bot_token, chat_id, f"♻️ Target #{target_id} reset to MENU_SENT.")

    # Process New Bounties (The Flash Filter)
    for row in rows:
        if row['status'] == 'PENDING':
            prompt = f"Analyze this GitHub bounty. Title: {row['title']} Details: {row['body_snippet']}\nCRITERIA: If it requires video recording, external Reddit/Twitter posting, physical hardware, or is marked as 'AI Agents Only', say 'REJECT'. Otherwise, provide a crisp summary.\nFORMAT STRICTLY AS:\nVERDICT: [CAPABLE or REJECT]\nSUMMARY: [1 sentence explaining the task]\nREQUIREMENTS: [2 bullet points on what needs to be done]\nPLAN: [1 sentence on how you will solve it]"
            analysis = assess_bounty(prompt, api_key)
            
            if "VERDICT: REJECT" in analysis or "BRAIN ERROR" in analysis:
                row['status'] = 'REJECTED'
            else:
                msg = f"🚨 <b>SKEINWATCH V6</b> 🚨\n<b>Target ID:</b> #{row['id']}\n<b>Title:</b> {row['title']}\n\n{analysis}\n\n⚡ Reply <code>/draft {row['id']}</code> to begin.\nLink: {row['url']}"
                send_telegram(bot_token, chat_id, msg)
                row['status'] = 'MENU_SENT'

    with open(BACKLOG_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["id", "status", "timestamp", "title", "url", "body_snippet", "draft_payload"])
        writer.writeheader()
        writer.writerows(rows)

if __name__ == "__main__":
    main()
