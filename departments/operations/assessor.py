import os
import sys
import csv
import json
import requests
from datetime import datetime

# --- V12 PATH RESOLUTION ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if "departments" in current_dir:
    project_root = os.path.abspath(os.path.join(current_dir, "../../"))
else:
    project_root = current_dir 

if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- V12.0 CONFIGURATION ---
SETTINGS_FILE = os.path.join(project_root, 'core/settings.json')
DATABASE_FILE = os.path.join(project_root, 'database/skein_index.csv')
LEARNING_LOG = os.path.join(project_root, 'logs/self_learning.jsonl')

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {"project": "SILICON CHRYSALIS", "autonomy_level": 1}
    with open(SETTINGS_FILE, 'r') as f:
        return json.load(f)

def send_telegram(bot_token, chat_id, text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram Send Error: {e}")

def log_learning_event(event_type, target_id, feedback):
    """Records HITL decisions for recursive learning."""
    event = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": event_type,
        "target_id": target_id,
        "feedback": feedback
    }
    with open(LEARNING_LOG, 'a') as f:
        f.write(json.dumps(event) + "\n")

def process_commands(bot_token, chat_id, rows):
    """Listens for Director commands to update the Skein State."""
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    updates_made = False
    
    try:
        res = requests.get(url, timeout=10).json()
        if not res.get("ok") or not res.get("result"):
            return rows, False

        highest_id = 0
        for item in res["result"]:
            update_id = item["update_id"]
            highest_id = max(highest_id, update_id)
            
            message = item.get("message", {})
            text = message.get("text", "").strip()
            
            # --- COMMAND: /status ---
            if text == "/status":
                settings = load_settings()
                msg = (
                    f"🛰️ <b>MIND-SKEIN V12 STATUS</b>\n"
                    f"Project: {settings.get('project')}\n"
                    f"Autonomy: L{settings.get('autonomy_level')}\n"
                    f"Ledger: {len(rows)} entries."
                )
                send_telegram(bot_token, chat_id, msg)

            # --- COMMAND: /list ---
            elif text == "/list":
                pending = [r for r in rows if r['status'] == 'PENDING'][:5]
                msg = "🔭 <b>TOP PENDING SMCs:</b>\n\n"
                for p in pending:
                    msg += f"• <b>T{p['id']}</b>: {p['title'][:50]}...\n"
                msg += "\nUse /draft [id] or /reject [id]"
                send_telegram(bot_token, chat_id, msg)

            # --- COMMAND: /draft [id] ---
            elif text.startswith("/draft"):
                parts = text.split()
                if len(parts) >= 2:
                    t_id = parts[1].replace("T", "")
                    for row in rows:
                        if row['id'] == t_id:
                            row['status'] = 'DRAFT_REQUESTED'
                            updates_made = True
                            send_telegram(bot_token, chat_id, f"🫡 <b>T{t_id}</b> marked for Drafting.")
                            log_learning_event("MANUAL_TRIAGE", t_id, "Director requested draft.")

            # --- COMMAND: /reject [id] ---
            elif text.startswith("/reject"):
                parts = text.split(" ", 2)
                if len(parts) >= 2:
                    t_id = parts[1].replace("T", "")
                    reason = parts[2] if len(parts) > 2 else "No reason provided."
                    for row in rows:
                        if row['id'] == t_id:
                            row['status'] = 'REJECTED'
                            updates_made = True
                            send_telegram(bot_token, chat_id, f"🗑️ <b>T{t_id}</b> Rejected: {reason}")
                            log_learning_event("MANUAL_REJECTION", t_id, reason)

            # --- COMMAND: /shadow [id] ---
            elif text.startswith("/shadow"):
                parts = text.split()
                if len(parts) >= 2:
                    t_id = parts[1].replace("T", "")
                    for row in rows:
                        if row['id'] == t_id:
                            row['status'] = 'SHADOW_TRIAL'
                            updates_made = True
                            send_telegram(bot_token, chat_id, f"👻 <b>T{t_id}</b> entering Shadow Mode for self-grading.")

        # Clear the queue
        if highest_id > 0:
            requests.get(f"{url}?offset={highest_id + 1}", timeout=10)

        return rows, updates_made
    except Exception as e:
        print(f"Assessor Error: {e}")
        return rows, False

def main():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not all([bot_token, chat_id]):
        print("Telegram credentials missing. Assessor ears are closed.")
        sys.exit(0)

    if not os.path.exists(DATABASE_FILE):
        print("Database not found. Radar required.")
        sys.exit(0)

    # 1. Read Index
    with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("Ledger is empty.")
        sys.exit(0)

    # 2. Process Telegram Directives
    updated_rows, needs_save = process_commands(bot_token, chat_id, rows)

    # 3. Save if State Changed
    if needs_save:
        with open(DATABASE_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(updated_rows)
        print("📊 Ledger updated via Director Command.")

if __name__ == "__main__":
    main()