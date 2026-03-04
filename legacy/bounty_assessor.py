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
        max_update_id = 0
        
        if res.get("ok"):
            for update in res["result"]:
                update_id = update.get("update_id", 0)
                if update_id > max_update_id:
                    max_update_id = update_id
                    
                text = update.get("message", {}).get("text", "")
                if text.startswith("/"):
                    commands.append(text)
            
            if max_update_id > 0:
                requests.get(f"{url}?offset={max_update_id + 1}", timeout=10)
                
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
    except Exception:
        return True 

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
                "🤖 <b>Agent Frankenskein V8</b>\n\n"
                "<b>STRIKE COMMANDS</b>\n"
                "<code>/draft [id]</code> - Draft with Flash\n"
                "<code>/amend [id] [notes]</code> - Rewrite draft\n"
                "<code>/post [id]</code> - Fire payload to GitHub\n\n"
                "<b>PULSE COMMANDS</b>\n"
                "<code>/list</code> - Show all active targets\n"
                "<code>/retry [id]</code> - Clear ERROR state\n"
                "<code>/refresh</code> - Check for closed targets\n"
                "<code>/reject [id]</code> - Discard target"
            )
            send_telegram(bot_token, chat_id, help_text)
            
        elif action == "/list":
            active_targets = [r for r in rows if r['status'] in ['PENDING', 'MENU_SENT', 'DRAFT_SENT', 'ERROR', 'AUTO_STRIKE_REQUESTED']]
            if not active_targets:
                send_telegram(bot_token, chat_id, "📭 <b>Radar Clear.</b> No active targets.")
            else:
                msg = "📋 <b>ACTIVE TARGETS:</b>\n"
                for t in active_targets:
                    msg += f"• #{t['id']} [{t['status']}] - <a href='{t['url']}'>{t['title'][:30]}...</a>\n"
                send_telegram(bot_token, chat_id, msg)
                
        elif action == "/refresh":
            for row in rows:
                if row['status'] in ['PENDING', 'MENU_SENT', 'DRAFT_SENT', 'ERROR', 'DRAFT_REQUESTED', 'AUTO_STRIKE_REQUESTED']:
                    if not check_is_open(row['url'], github_token):
                        row['status'] = 'CLOSED'
                        send_telegram(bot_token, chat_id, f"🗑️ <b>Target #{row['id']} marked CLOSED.</b>\nBounty is no longer active.")
                        
        elif len(parts) >= 2 and parts[1].isdigit():
            target_id = parts[1]
            for row in rows:
                if row['id'] == target_id:
                    if action == "/draft" and row['status'] in ['MENU_SENT', 'ERROR']:
                        row['status'] = 'DRAFT_REQUESTED'
                        row['draft_payload'] = "ENGINE:FLASH" 
                    elif action == "/amend" and row['status'] in ['DRAFT_SENT', 'ERROR']:
                        row['status'] = 'AMEND_REQUESTED'
                        row['draft_payload'] = cmd.replace(f"/amend {target_id}", "").strip()
                    elif action == "/post" and row['status'] == 'DRAFT_SENT':
                        row['status'] = 'POST_REQUESTED'
                    elif action == "/reject":
                        row['status'] = 'REJECTED'
                        send_telegram(bot_token, chat_id, f"🗑️ Target #{target_id} discarded.")
                    elif action == "/retry" and row['status'] == 'ERROR':
                        row['status'] = 'MENU_SENT'
                        send_telegram(bot_token, chat_id, f"♻️ Target #{target_id} reset to MENU_SENT.")

    # Process New Bounties
    for row in rows:
        if row['status'] == 'PENDING':
            # V8 PROMPT UPGRADE: Teaching the AI to hunt for "AI Agents Only"
            prompt = f"Analyze this GitHub bounty. Title: {row['title']} Details: {row['body_snippet']}\nCRITERIA: If it requires video recording, external Reddit/Twitter posting, or physical hardware, say 'REJECT'. If the text explicitly requests 'AI Agents Only' or specifically asks for an automated AI worker, output 'VERDICT: AUTO_STRIKE'. For all other standard coding tasks, output 'VERDICT: CAPABLE'.\nFORMAT STRICTLY AS:\nVERDICT: [CAPABLE, AUTO_STRIKE, or REJECT]\nSUMMARY: [1 sentence explaining the task]\nREQUIREMENTS: [2 bullet points on what needs to be done]\nPLAN: [1 sentence on how you will solve it]"
            analysis = assess_bounty(prompt, api_key)
            
            if "VERDICT: REJECT" in analysis or "BRAIN ERROR" in analysis:
                row['status'] = 'REJECTED'
            elif "VERDICT: AUTO_STRIKE" in analysis:
                # V8 FAST LANE: Bypass the menu entirely
                row['status'] = 'AUTO_STRIKE_REQUESTED'
                row['draft_payload'] = "ENGINE:FLASH"
                msg = f"👻 <b>GHOST IN THE MACHINE</b> 👻\n<b>Target ID:</b> #{row['id']}\n<b>Title:</b> {row['title']}\n\nAI-Only Bounty detected. Bypassing human approval. Proceeding to Auto-Strike generation.\nLink: {row['url']}"
                send_telegram(bot_token, chat_id, msg)
            else:
                # Standard human-in-the-loop menu
                msg = f"🚨 <b>SKEINWATCH V8</b> 🚨\n<b>Target ID:</b> #{row['id']}\n<b>Title:</b> {row['title']}\n\n{analysis}\n\n⚡ Reply <code>/draft {row['id']}</code> to begin.\nLink: {row['url']}"
                send_telegram(bot_token, chat_id, msg)
                row['status'] = 'MENU_SENT'

    with open(BACKLOG_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["id", "status", "timestamp", "title", "url", "body_snippet", "draft_payload"])
        writer.writeheader()
        writer.writerows(rows)

if __name__ == "__main__":
    main()
