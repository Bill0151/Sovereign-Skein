import os
import sys
import csv
import requests
import google.generativeai as genai

BACKLOG_FILE = 'bounty_backlog.csv'

def heavy_compute(prompt, api_key):
    genai.configure(api_key=api_key)
    try:
        print("Executing heavy compute via gemini-2.5-pro...")
        return genai.GenerativeModel("gemini-2.5-pro").generate_content(prompt).text.strip()
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

def main():
    api_key, bot_token, chat_id = os.getenv("GEMINI_API_KEY"), os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    github_token, wallet_address = os.getenv("SKEIN_GITHUB_TOKEN"), os.getenv("RABBY_ADDRESS")
    
    if not all([api_key, bot_token, chat_id, github_token]): sys.exit(0)

    rows = []
    with open(BACKLOG_FILE, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        # --- ACTION 1: GENERATE DRAFT (Uses Pro AI) ---
        if row['status'] == 'DRAFT_REQUESTED':
            # Temporary Override for Target #5 to lock the bounty without hallucinating
            if row['id'] == '5':
                 prompt = f"Write a highly professional 'Claim Proposal' for this GitHub issue. DO NOT write the final code. Instead, outline a technical plan to build the fuzz harness using Rust's `cargo-fuzz` or Python's `hypothesis`. State that we will open a PR within 48 hours. Include this wallet for the bounty payout: {wallet_address}. Issue Title: {row['title']} Details: {row['body_snippet']}"
            else:
                 prompt = f"Write a highly technical, professional response and code fix for this GitHub issue. Include this wallet for the bounty payout: {wallet_address}. Issue Title: {row['title']} Details: {row['body_snippet']}"
            payload = heavy_compute(prompt, api_key) + "\n\n---\n*Task executed autonomously by the Sovereign Skein.*"
            
            if "CRITICAL BRAIN FAILURE" in payload:
                row['status'] = 'ERROR'
                send_telegram(bot_token, chat_id, f"⚠️ <b>Drafting Failed for Target #{row['id']}</b>: API Quota exhausted.")
            else:
                row['draft_payload'] = payload
                row['status'] = 'DRAFT_SENT'
                msg = f"📄 <b>DRAFT READY - Target #{row['id']}</b>\n\n{payload[:3000]}\n\n⚡ Reply <code>/post {row['id']}</code> to strike, or <code>/reject {row['id']}</code> to abort."
                send_telegram(bot_token, chat_id, msg)

        # --- ACTION 2: POST TO GITHUB (Zero AI Cost) ---
        elif row['status'] == 'POST_REQUESTED':
            owner, repo, issue_number = parse_github_url(row['url'])
            strike_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments"
            
            res = requests.post(strike_url, headers={"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}, json={"body": row['draft_payload']})
            
            if res.status_code == 201:
                row['status'] = 'COMPLETED'
                send_telegram(bot_token, chat_id, f"✅ <b>STRIKE SUCCESSFUL - Target #{row['id']}</b>\nPayload delivered to GitHub.")
            else:
                row['status'] = 'ERROR'
                send_telegram(bot_token, chat_id, f"❌ <b>STRIKE FAILED - Target #{row['id']}</b>\nGitHub API Error: {res.text}")

    # Save State
    with open(BACKLOG_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["id", "timestamp", "title", "url", "body_snippet", "status", "draft_payload"])
        writer.writeheader()
        writer.writerows(rows)

if __name__ == "__main__":
    main()
