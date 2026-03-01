import os
import sys
import csv
import requests
import google.generativeai as genai

BACKLOG_FILE = 'bounty_backlog.csv'

def get_telegram_commands(bot_token):
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    try:
        res = requests.get(url).json()
        commands = []
        if res.get("ok"):
            for update in res["result"]:
                text = update.get("message", {}).get("text", "").lower()
                if text.startswith("/draft ") or text.startswith("/post ") or text.startswith("/reject "):
                    commands.append(text)
        return commands
    except:
        return []

def send_telegram(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"})

def assess_bounty(prompt, api_key):
    genai.configure(api_key=api_key)
    try:
        print("Assessing target via gemini-2.5-flash...")
        return genai.GenerativeModel("gemini-2.5-flash").generate_content(prompt).text.strip()
    except Exception as e:
        return f"BRAIN ERROR: {e}"

def main():
    api_key, bot_token, chat_id = os.getenv("GEMINI_API_KEY"), os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not all([api_key, bot_token, chat_id]) or not os.path.exists(BACKLOG_FILE): sys.exit(0)

    # 1. Read Telegram Commands & Update Status
    commands = get_telegram_commands(bot_token)
    rows = []
    with open(BACKLOG_FILE, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    for cmd in commands:
        parts = cmd.split()
        if len(parts) == 2 and parts[1].isdigit():
            action, target_id = parts[0], parts[1]
            for row in rows:
                if row['id'] == target_id:
                    if action == "/draft" and row['status'] == 'MENU_SENT':
                        row['status'] = 'DRAFT_REQUESTED'
                    elif action == "/post" and row['status'] == 'DRAFT_SENT':
                        row['status'] = 'POST_REQUESTED'
                    elif action == "/reject":
                        row['status'] = 'REJECTED'

    # 2. Assess PENDING targets
    assessed_count = 0
    for row in rows:
        if row['status'] == 'PENDING' and assessed_count < 2: # Max 2 per pulse
            prompt = f"""
            Analyze this GitHub bounty. Title: {row['title']} Details: {row['body_snippet']}
            CRITERIA: If it requires video recording, external Reddit/Twitter posting, or physical hardware, say 'REJECT'.
            Otherwise, provide a crisp summary.
            FORMAT STRICTLY AS:
            VERDICT: [CAPABLE or REJECT]
            SUMMARY: [1 sentence explaining the bug/task]
            REQUIREMENTS: [2 bullet points on what needs to be done]
            PLAN: [1 sentence on how you will solve it]
            """
            analysis = assess_bounty(prompt, api_key)
            
            if "VERDICT: REJECT" in analysis:
                row['status'] = 'REJECTED'
            else:
                msg = f"🚨 <b>SKEINWATCH V4</b> 🚨\n<b>Target ID:</b> #{row['id']}\n<b>Title:</b> {row['title']}\n\n{analysis}\n\n"
                msg += f"⚡ <b>COMMANDS:</b>\nReply <code>/draft {row['id']}</code> to write code.\nReply <code>/reject {row['id']}</code> to discard.\n\nLink: {row['url']}"
                send_telegram(bot_token, chat_id, msg)
                row['status'] = 'MENU_SENT'
            assessed_count += 1

    # 3. Save State
    with open(BACKLOG_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["id", "timestamp", "title", "url", "body_snippet", "status", "draft_payload"])
        writer.writeheader()
        writer.writerows(rows)

if __name__ == "__main__":
    main()
