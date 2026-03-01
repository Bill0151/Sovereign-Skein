import os
import sys
import csv
import requests
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

BACKLOG_FILE = 'bounty_backlog.csv'

def generate_with_resilience(prompt, api_key):
    genai.configure(api_key=api_key)
    # Assessor is a simple task: Try Flash first, fallback to Pro
    primary = "gemini-2.5-flash"
    fallback = "gemini-2.5-pro"
    
    try:
        print(f"Attempting neural link with {primary}...")
        return genai.GenerativeModel(primary).generate_content(prompt).text.strip()
    except ResourceExhausted:
        print(f"⚠️ 429 Error on {primary}. Engaging Fallback Cascade: {fallback}...")
        try:
            return genai.GenerativeModel(fallback).generate_content(prompt).text.strip()
        except Exception as e:
            return f"CRITICAL BRAIN FAILURE: {e}"
    except Exception as e:
        return f"BRAIN ERROR: {e}"

def send_telegram(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"})

def main():
    api_key, bot_token, chat_id = os.getenv("GEMINI_API_KEY"), os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not all([api_key, bot_token, chat_id]) or not os.path.exists(BACKLOG_FILE):
        sys.exit(0)

    rows, pending = [], []
    with open(BACKLOG_FILE, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            rows.append(row)
            if row['status'] == 'PENDING' and len(pending) < 3:
                pending.append(row)

    if not pending:
        print("No PENDING targets. Sleeping.")
        sys.exit(0)

    for target in pending:
        prompt = f"Evaluate this GitHub bounty. Title: {target['title']} Details: {target['body_snippet']}. Reply STRICTLY:\nVERDICT: [CAPABLE or INCAPABLE]\nREASON: [1 short sentence]\nTYPE: [TECHNICAL or ENGAGEMENT]"
        response = generate_with_resilience(prompt, api_key)
        
        msg = f"🚨 <b>SKEINWATCH DISPATCH</b> 🚨\n<b>Target:</b> {target['title']}\n<b>Analysis:</b>\n{response}\n<b>Link:</b> {target['url']}"
        send_telegram(bot_token, chat_id, msg)
        target['status'] = 'ASSESSED'

    with open(BACKLOG_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "title", "url", "body_snippet", "status"])
        writer.writeheader()
        writer.writerows(rows)

if __name__ == "__main__":
    main()
