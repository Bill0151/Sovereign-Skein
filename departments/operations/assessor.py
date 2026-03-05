import os
import sys
import csv
import time
import requests
import subprocess

# --- V12 PATH RESOLUTION ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if "departments" in current_dir:
    project_root = os.path.abspath(os.path.join(current_dir, "../../"))
else:
    project_root = current_dir 

if project_root not in sys.path:
    sys.path.insert(0, project_root)

DATABASE_FILE = os.path.join(project_root, 'database/skein_index.csv')
COLLECTOR_SCRIPT = os.path.join(project_root, 'departments', 'intelligence', 'collector.py')
EXECUTOR_SCRIPT = os.path.join(project_root, 'departments', 'operations', 'executor.py')

def send_message(bot_token, chat_id, text):
    """Sends a message back to the Director."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def get_pending_targets():
    """Reads the CSV and returns the top 5 targets."""
    if not os.path.exists(DATABASE_FILE):
        return "No database found. Run /pulse first."
    
    with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
        
    pending = [r for r in rows if r['status'] == 'PENDING']
    if not pending:
        return "No pending targets found in the Ledger."
        
    msg = "🎯 <b>Top 5 Pending Targets:</b>\n\n"
    for r in pending[:5]:
        msg += f"• <b>T{r['id']}</b>: {r['title'][:45]}...\n"
    
    msg += "\n<i>Reply with `/draft T[ID]` to triage.</i>"
    return msg

def set_target_draft(target_id):
    """Updates the CSV status to DRAFT_REQUESTED."""
    if not os.path.exists(DATABASE_FILE):
        return False
        
    clean_id = target_id.replace('T', '').strip()
    updated = False
    
    with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
        
    for row in rows:
        if row['id'] == clean_id:
            row['status'] = 'DRAFT_REQUESTED'
            updated = True
            break
            
    if updated:
        with open(DATABASE_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
            
    return updated

def main():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("❌ TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing.")
        return

    print("🎧 MIND-SKEIN Assessor (C2 Link) is ONLINE and listening...")
    send_message(bot_token, chat_id, "🟢 <b>MIND-SKEIN V12 C2 Link Established.</b>\nSystem is awake and awaiting commands.")

    offset = 0
    
    # --- CONTINUOUS HEARTBEAT LOOP ---
    while True:
        try:
            url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
            params = {"timeout": 30, "offset": offset}
            res = requests.get(url, params=params, timeout=40)
            
            if res.status_code == 200:
                data = res.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    
                    message = update.get("message", {})
                    text = message.get("text", "").strip()
                    msg_chat_id = str(message.get("chat", {}).get("id", ""))
                    
                    # Security check: Only respond to YOUR chat ID!
                    if msg_chat_id != str(chat_id):
                        continue
                        
                    print(f"📥 Received Command: {text}")
                    
                    if text == '/list':
                        send_message(bot_token, chat_id, get_pending_targets())
                        
                    elif text == '/pulse':
                        send_message(bot_token, chat_id, "📡 <b>Running Intelligence Pulse...</b>\nFiring Radar across GitHub.")
                        # Run the collector in the background so the bot doesn't freeze
                        subprocess.Popen([sys.executable, COLLECTOR_SCRIPT])
                        
                    elif text.startswith('/draft '):
                        target = text.split(' ')[1]
                        if set_target_draft(target):
                            send_message(bot_token, chat_id, f"⚙️ <b>{target} marked for DRAFT.</b>\nWaking Executor Node...")
                            # Run the executor in the background automatically!
                            subprocess.Popen([sys.executable, EXECUTOR_SCRIPT])
                        else:
                            send_message(bot_token, chat_id, f"❌ Target {target} not found in index.")
                            
        except Exception as e:
            time.sleep(5) # Back off if internet drops
            
        time.sleep(1) # Prevent CPU spinning

if __name__ == "__main__":
    main()