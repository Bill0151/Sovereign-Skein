"""
FILE: departments/operations/assessor.py
ROLE: The "Ears" - Command & Control Link (Terminal 1)
FUNCTION: Listens for Telegram telemetry, triages targets, and manages AI memory.
VERSION: V12.11 (Poison Pill Crash Loop Fix)
"""

import os
import sys
import csv
import json
import time
import requests
import re
import subprocess
import traceback
from datetime import datetime
from google import genai
from dotenv import load_dotenv

# --- V12 PATH RESOLUTION ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if "departments" in current_dir:
    project_root = os.path.abspath(os.path.join(current_dir, "../../"))
else:
    project_root = current_dir 

if project_root not in sys.path:
    sys.path.insert(0, project_root)

load_dotenv(os.path.join(project_root, '.env'))

_original_print = print
def print(*args, **kwargs):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _original_print(f"[{timestamp}]", *args, **kwargs)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DATABASE_FILE = os.path.join(project_root, 'database/skein_index.csv')
VAULT_DIR = os.path.join(project_root, 'vault')
MEMORY_LOG = os.path.join(project_root, 'logs/self_learning.jsonl')
TRIAGE_AUDIT_LOG = os.path.join(project_root, 'logs/triage_audit.jsonl')

def trigger_telemetry():
    """Auto-rebuilds the HUD data when the Assessor changes a target's state."""
    try:
        telemetry_path = os.path.join(project_root, "departments", "finance", "telemetry.py")
        if os.path.exists(telemetry_path):
            subprocess.run([sys.executable, telemetry_path], check=True)
    except Exception as e:
        print(f"⚠️ Telemetry auto-update failed: {e}")

def send_telegram(message):
    if not message: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": str(message), "parse_mode": "HTML", "disable_web_page_preview": True})

def update_vault_sidecar(target_id, updates):
    raw_id = str(target_id).replace('T', '')
    paths = [
        os.path.join(VAULT_DIR, f"T{raw_id}", 'intel.json'),
        os.path.join(VAULT_DIR, f"{raw_id}", 'intel.json')
    ]
    for sidecar_path in paths:
        if os.path.exists(sidecar_path):
            with open(sidecar_path, 'r', encoding='utf-8') as f:
                try:
                    intel = json.load(f)
                except json.JSONDecodeError:
                    intel = {}
            intel.update(updates)
            with open(sidecar_path, 'w', encoding='utf-8') as f:
                json.dump(intel, f, indent=4)
            return

def compute_similarity(vec1, vec2):
    try:
        dot = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = sum(a * a for a in vec1) ** 0.5
        mag2 = sum(b * b for b in vec2) ** 0.5
        return dot / (mag1 * mag2) if mag1 and mag2 else 0.0
    except Exception:
        return 0.0

def embed_text(client, text):
    try:
        res = client.models.embed_content(model='gemini-embedding-001', contents=text)
        if res.embeddings: return res.embeddings[0].values
    except Exception as e:
        print(f"   [EMBEDDING ERROR] Could not vectorize: {e}")
    return None

def triage_targets():
    if not os.path.exists(DATABASE_FILE): return "❌ Ledger missing."
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    memories = []
    updated_lines = []
    needs_rewrite = False
    
    if os.path.exists(MEMORY_LOG):
        with open(MEMORY_LOG, 'r', encoding='utf-8') as mf:
            for line in mf:
                try:
                    mem = json.loads(line.strip())
                    if mem.get('type') == 'DIRECTOR_AMENDMENT':
                        if 'embedding' not in mem:
                            vec = embed_text(client, mem.get('lesson', ''))
                            if vec:
                                mem['embedding'] = vec
                                needs_rewrite = True
                        memories.append(mem)
                    updated_lines.append(mem)
                except Exception: pass
        
        if needs_rewrite:
            with open(MEMORY_LOG, 'w', encoding='utf-8') as mf:
                for m in updated_lines: mf.write(json.dumps(m) + '\n')

    with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
        
    pending_rows = [r for r in rows if r['status'] == 'PENDING']
    vulture_rows = [r for r in rows if r['status'] == 'VULTURE_PENDING']
    
    # Alert Director to Vulture Targets instantly
    for v_row in vulture_rows:
        target_id = v_row['id']
        raw_id = str(target_id).replace('T', '')
        sidecar_path = os.path.join(VAULT_DIR, f"T{raw_id}", 'intel.json')
        target_user = "Unknown"
        if os.path.exists(sidecar_path):
            with open(sidecar_path, 'r', encoding='utf-8') as sf:
                target_user = json.load(sf).get('vulture_target_user', 'Unknown')
                
        msg = f"🦅 <b>VULTURE TARGET ACQUIRED</b>\n"
        msg += f"<b>Target:</b> @{target_user}\n"
        msg += f"<b>Value:</b> {v_row.get('payout_est', 'TBD')}\n"
        msg += f"🔗 <a href='{v_row['url']}'>Verify Issue</a>\n\n"
        msg += f"⚡ Reply <code>/vulture {target_id}</code> to authorize strike."
        send_telegram(msg)
        v_row['status'] = 'VULTURE_AWAITING_CMD'
        
    # --- V12.10 AMNESIA SPAM FIX ---
    actual_targets = []
    retained_skipped = 0
    for row in pending_rows:
        raw_id = str(row['id']).replace('T', '')
        sidecar_path = os.path.join(VAULT_DIR, f"T{raw_id}", 'intel.json')
        
        skip_evaluation = False
        if os.path.exists(sidecar_path):
            with open(sidecar_path, 'r', encoding='utf-8') as sf:
                try: 
                    intel_data = json.load(sf)
                    if intel_data.get('skein_status') in ['RETAINED', 'REJECTED']:
                        skip_evaluation = True
                except json.JSONDecodeError: pass
        
        if skip_evaluation:
            retained_skipped += 1
        else:
            actual_targets.append(row)
    
    if not actual_targets and not vulture_rows: 
        return None 
        
    print(f"🧠 ASSESSOR: Initializing Semantic Memory Engine...")
    print(f"🧠 ASSESSOR: Triaging {len(actual_targets)} NEW targets...")
    rejected_count = 0

    models_to_try = ['gemini-3.1-flash-lite-preview', 'gemini-2.0-flash-lite', 'gemma-3-27b-it']

    for row in actual_targets:
        target_id = row['id']
        raw_id = str(target_id).replace('T', '')
        
        body = "No details."
        sidecar_path = os.path.join(VAULT_DIR, f"T{raw_id}", 'intel.json')
        
        skip_evaluation = False
        if os.path.exists(sidecar_path):
            with open(sidecar_path, 'r', encoding='utf-8') as sf:
                try: 
                    intel_data = json.load(sf)
                    if intel_data.get('skein_status') in ['RETAINED', 'REJECTED']:
                        skip_evaluation = True
                        
                    # V12.11 FIX: Poison Pill Catch (NoneType check)
                    raw_body = intel_data.get('body')
                    if not raw_body: raw_body = "No details."
                    body = str(raw_body)[:1000]
                    
                except json.JSONDecodeError: pass
                
        if skip_evaluation:
            retained_skipped += 1
            continue

        target_text = f"Title: {row['title']}\nDetails: {body}"
        target_vec = embed_text(client, target_text)
        
        active_rules = ["MANDATORY CORE RULE: You MUST REJECT any target that does not explicitly state a financial reward, bounty value, or cryptocurrency payout. If there is no money on the table, reject it."]
        
        if target_vec and memories:
            for m in memories:
                m['score'] = compute_similarity(target_vec, m.get('embedding', [])) if m.get('embedding') else 0.0
            top_memories = sorted(memories, key=lambda x: x.get('score', 0.0), reverse=True)[:3]
            for m in top_memories: active_rules.append(m['lesson'])
        else:
            for m in memories: active_rules.append(m['lesson'])

        rules_text = "\n".join([f"- {r}" for r in active_rules])
        prompt = f"""Evaluate this target against these rules:\n{rules_text}\n\nTitle: {row['title']}\nDetails: {body}\n\nRespond: DECISION: [REJECT or PENDING], REASON: [1 sentence]"""
        
        res_text = None
        for model in models_to_try:
            try:
                response = client.models.generate_content(model=model, contents=prompt)
                res_text = response.text.strip()
                break
            except Exception as e:
                print(f"   [FALLBACK] Model {model} failed: {e}. Trying next...")
                time.sleep(2)

        if not res_text:
            print(f"   [BRAIN ERROR] {target_id}: All fallback models exhausted.")
            continue
            
        audit_entry = {"timestamp": datetime.now().isoformat(), "target_id": target_id, "title": row['title'], "ai_response": res_text}
        os.makedirs(os.path.dirname(TRIAGE_AUDIT_LOG), exist_ok=True)
        with open(TRIAGE_AUDIT_LOG, 'a', encoding='utf-8') as af:
            af.write(json.dumps(audit_entry) + '\n')
        
        if "DECISION: REJECT" in res_text.upper():
            row['status'] = 'REJECTED'
            rejected_count += 1
            update_vault_sidecar(target_id, {"skein_status": "REJECTED", "reject_reason": res_text})
            print(f"   [AI REJECTED] {row['title'][:35]}...")
        else:
            update_vault_sidecar(target_id, {"skein_status": "RETAINED", "reason": res_text})
            print(f"   [AI RETAINED] {row['title'][:35]}...")
            
        time.sleep(3) 

    with open(DATABASE_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
        
    trigger_telemetry()
    return f"🧠 <b>Triage Complete:</b> Auto-rejected {rejected_count} targets. Skipped {retained_skipped} already retained targets."

def list_pending_targets():
    if not os.path.exists(DATABASE_FILE): return "❌ Ledger missing."
    with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    pending = [r for r in rows if r['status'] == 'PENDING']
    if not pending: return "📭 No PENDING targets."
    
    def extract_numeric_value(payout_str):
        numbers = re.findall(r'\d+', str(payout_str))
        return int(numbers[0]) if numbers else 0
        
    pending.sort(key=lambda x: extract_numeric_value(x.get('payout_est', '0')), reverse=True)
    
    msg = "🎯 <b>Top Viable Targets:</b>\n\n"
    for r in pending[:5]:
        title = r['title'][:45] + "..." if len(r['title']) > 45 else r['title']
        msg += f"• <code>{r['id']}</code>: <a href='{r.get('url', '#')}'>{title}</a>\n"
        msg += f"  💰 <b>Est. Value:</b> {r.get('payout_est', 'TBD')}\n\n"
        
    msg += "Reply with <code>/draft [ID]</code> to initiate."
    return msg

def change_target_status(target_id, new_status):
    if not os.path.exists(DATABASE_FILE): return False
    with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    found = False
    for row in rows:
        if row['id'] == target_id or f"T{row['id']}" == target_id or row['id'] == f"T{target_id}":
            row['status'] = new_status
            found = True
            break
    if found:
        with open(DATABASE_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        trigger_telemetry()
        return True
    return False

def process_telegram_commands():
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    try:
        res = requests.get(url, timeout=10).json()
        if not res.get("ok") or not res.get("result"): return
        highest_update_id = 0
        kill_requested = False
        
        for item in res["result"]:
            update_id = item["update_id"]
            highest_update_id = max(highest_update_id, update_id)
            message = item.get("message", {})
            text = message.get("text", "").strip()
            
            # V12.11: Command Error Trapping guarantees the Telegram offset advances
            try:
                if text == "/kill":
                    kill_requested = True
                    print("🛑 /kill command received. Preparing for graceful shutdown...")
                elif text == "/triage":
                    msg = triage_targets()
                    if msg: send_telegram(msg)
                elif text == "/list":
                    send_telegram(list_pending_targets())
                elif text.startswith("/draft"):
                    parts = text.split()
                    if len(parts) >= 2:
                        if change_target_status(parts[1], 'DRAFT_REQUESTED'):
                            print(f"📡 COMMAND RECEIVED: /draft for Target #{parts[1]}. Delegated to Executor.")
                            send_telegram(f"⚙️ <b>Drafting Initiated:</b> <code>{parts[1]}</code> sent to Executor.")
                elif text.startswith("/post"):
                    parts = text.split()
                    if len(parts) >= 2:
                        if change_target_status(parts[1], 'POST_REQUESTED'):
                            print(f"📡 COMMAND RECEIVED: /post for Target #{parts[1]}. Authorizing live strike.")
                            send_telegram(f"🚀 <b>Strike Authorized:</b> <code>{parts[1]}</code> sent to Executor for live deployment.")
                elif text.startswith("/reject"):
                    parts = text.split()
                    if len(parts) >= 2:
                        if change_target_status(parts[1], 'REJECTED'):
                            print(f"🛑 COMMAND RECEIVED: /reject for Target #{parts[1]}. Target neutralized.")
                            update_vault_sidecar(parts[1], {"skein_status": "REJECTED", "reject_reason": "DIRECTOR_OVERRIDE"})
                            send_telegram(f"🗑️ <b>Target Neutralized:</b> <code>{parts[1]}</code> has been marked as REJECTED.")
                elif text.startswith("/amend"):
                    parts = text.split(" ", 2)
                    if len(parts) >= 3:
                        print(f"🧠 COMMAND RECEIVED: /amend for Target #{parts[1]}. Injecting new memory...")
                        with open(MEMORY_LOG, 'a', encoding='utf-8') as mf:
                            json.dump({"timestamp": datetime.now().isoformat(), "target_id": parts[1], "type": "DIRECTOR_AMENDMENT", "lesson": parts[2]}, mf)
                            mf.write("\n")
                        change_target_status(parts[1], 'DRAFT_REQUESTED')
                        send_telegram(f"🧠 <b>Memory Updated:</b> #{parts[1]} recorded. Sent back to Executor for re-drafting.")
                elif text.startswith("/vulture"):
                    parts = text.split()
                    if len(parts) >= 2:
                        if change_target_status(parts[1], 'VULTURE_AUTHORIZED'):
                            print(f"📡 COMMAND RECEIVED: /vulture for Target #{parts[1]}")
                            send_telegram(f"🦅 <b>Vulture Strike Authorized:</b> <code>{parts[1]}</code> sent to Executor.")
            except Exception as e:
                print(f"⚠️ COMMAND ERROR ('{text}'): {e}")
                traceback.print_exc()

        # We MUST clear the telegram queue even if a command crashed, to prevent infinite re-tries
        if highest_update_id > 0:
            requests.get(f"{url}?offset={highest_update_id + 1}", timeout=10)
            
        if kill_requested:
            send_telegram("🛑 <b>EMERGENCY STOP</b>: Assessor Node has been terminated by the Director.")
            print("🛑 SYSTEM KILLED. Assessor Node Offline.")
            sys.exit(0)
            
    except requests.exceptions.RequestException:
        pass # Ignore simple network timeouts
    except Exception as e:
        print(f"⚠️ TELEGRAM POLLING ERROR: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    print("🟢 MIND-SKEIN V12 C2 Link Established (Assessor Node).")
    while True:
        process_telegram_commands()
        time.sleep(5)