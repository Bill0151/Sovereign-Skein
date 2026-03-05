import os
import sys
import csv
import json
import time
import requests
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

# --- SECURE VAULT DECRYPTION ---
load_dotenv(os.path.join(project_root, '.env'))

# --- V12.0 CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GITHUB_TOKEN = os.getenv("SKEIN_GITHUB_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DATABASE_FILE = os.path.join(project_root, 'database/skein_index.csv')
VAULT_DIR = os.path.join(project_root, 'vault')
MEMORY_LOG = os.path.join(project_root, 'logs/self_learning.jsonl')

def send_telegram(message):
    """Fires a message to the Director's HUD (Telegram)."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"})

def parse_github_url(url):
    """Extracts owner, repo, and issue number from a standard GitHub URL."""
    parts = url.rstrip('/').split('/')
    if "issues" in parts:
        i = parts.index("issues")
        return parts[i-2], parts[i-1], parts[i+1]
    return None, None, None

def update_vault_sidecar(target_id, updates):
    """Injects live status and metadata directly into the Vault's JSON sidecar."""
    sidecar_path = os.path.join(VAULT_DIR, target_id, 'intel.json')
    if os.path.exists(sidecar_path):
        with open(sidecar_path, 'r', encoding='utf-8') as f:
            try:
                intel = json.load(f)
            except json.JSONDecodeError:
                intel = {}
                
        # Merge new updates into the intel dictionary
        intel.update(updates)
        
        with open(sidecar_path, 'w', encoding='utf-8') as f:
            json.dump(intel, f, indent=4)

def sync_target_deadlines():
    """Checks active targets against live GitHub data to see if we missed the bounty."""
    if not os.path.exists(DATABASE_FILE):
        return

    print("🔄 ASSESSOR: Syncing target deadlines with live GitHub state...")
    
    with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    updates_made = 0

    for row in rows:
        # Only check targets we are actively pursuing
        if row['status'] in ['PENDING', 'DRAFT_REQUESTED', 'DRAFT_SENT', 'APPLIED']:
            owner, repo, issue_number = parse_github_url(row['url'])
            if not owner:
                continue
                
            api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
            try:
                res = requests.get(api_url, headers=headers, timeout=10)
                if res.status_code == 200:
                    issue_data = res.json()
                    
                    # If the issue is closed or assigned to a competitor, the bounty is dead.
                    is_closed = issue_data.get('state') == 'closed'
                    is_assigned = len(issue_data.get('assignees', [])) > 0
                    
                    if is_closed or is_assigned:
                        old_status = row['status']
                        row['status'] = 'CLOSED_MISSED'
                        updates_made += 1
                        
                        # 1. Update the Vault Sidecar with the exact time of death
                        update_vault_sidecar(row['id'], {
                            "skein_status": "CLOSED_MISSED",
                            "github_state": "closed" if is_closed else "assigned",
                            "closed_at": issue_data.get('closed_at', datetime.now().isoformat())
                        })
                        
                        print(f"   [DEADLINE MISSED] Target #{row['id']} was closed/assigned by repository owner.")
                else:
                    print(f"   [API ERROR] Could not fetch status for #{row['id']}")
            except Exception as e:
                print(f"   [NETWORK ERROR] {e}")

    # Save the updated Ledger
    if updates_made > 0:
        with open(DATABASE_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["id", "status", "timestamp", "title", "url", "payout_est", "sidecar_link"])
            writer.writeheader()
            writer.writerows(rows)
            
        return f"🔄 <b>Sync Complete:</b> {updates_made} targets expired and removed from active roster."
    return "🔄 <b>Sync Complete:</b> All active targets are still open and viable."

def triage_targets():
    """AI Brain: Evaluates PENDING targets against learned memory to auto-reject spam."""
    if not os.path.exists(DATABASE_FILE):
        return "❌ Ledger missing."

    # 1. Load the Brain's Memory
    rules = []
    if os.path.exists(MEMORY_LOG):
        with open(MEMORY_LOG, 'r', encoding='utf-8') as mf:
            for line in mf:
                try:
                    mem = json.loads(line.strip())
                    if mem.get('type') == 'DIRECTOR_AMENDMENT':
                        rules.append(mem.get('lesson'))
                except:
                    pass
                    
    rules_text = "\n".join([f"- {r}" for r in rules]) if rules else "No specific rules yet."

    with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
        
    pending_rows = [r for r in rows if r['status'] == 'PENDING']
    if not pending_rows:
        return "🧠 <b>Triage Complete:</b> No PENDING targets to evaluate."

    print(f"🧠 ASSESSOR: Triaging {len(pending_rows)} PENDING targets against memory...")
    client = genai.Client(api_key=GEMINI_API_KEY)
    rejected_count = 0

    # 2. Evaluate targets against rules
    for row in pending_rows:
        target_id = row['id']
        sidecar_path = os.path.join(VAULT_DIR, target_id, 'intel.json')
        body = "No details."
        
        if os.path.exists(sidecar_path):
            with open(sidecar_path, 'r', encoding='utf-8') as sf:
                try:
                    intel = json.load(sf)
                    body = intel.get('body', '')[:1000] # Grab first 1000 chars of context
                except:
                    pass

        prompt = f"""You are an elite AI triage agent filtering GitHub issues.
        Here are your learned rules from the Director:
        {rules_text}
        
        Evaluate this incoming target:
        Title: {row['title']}
        Details: {body}
        
        Does this target violate any of your learned rules or look like automated bot spam? 
        Respond strictly in this format:
        DECISION: [REJECT or PENDING]
        REASON: [1 sentence why]
        """
        
        try:
            response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
            res_text = response.text.upper()
            
            if "DECISION: REJECT" in res_text:
                row['status'] = 'REJECTED'
                rejected_count += 1
                update_vault_sidecar(target_id, {"skein_status": "REJECTED", "reject_reason": "AI_MEMORY_TRIAGE"})
                print(f"   [AI REJECTED] {row['title'][:40]}... (Violates Memory)")
        except Exception as e:
            print(f"   [BRAIN ERROR] Could not triage {target_id}: {e}")

    # 3. Save Ledger if changes were made
    if rejected_count > 0:
        with open(DATABASE_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["id", "status", "timestamp", "title", "url", "payout_est", "sidecar_link"])
            writer.writeheader()
            writer.writerows(rows)
            
    return f"🧠 <b>Triage Complete:</b> Evaluated {len(pending_rows)} targets. Auto-rejected {rejected_count} targets based on Memory."

def process_telegram_commands():
    """Listens for Director commands and manages State/Learning loop."""
    print("🎧 ASSESSOR: Listening for telemetry...")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    
    try:
        res = requests.get(url, timeout=10).json()
        if not res.get("ok") or not res.get("result"):
            return

        highest_update_id = 0

        for item in res["result"]:
            update_id = item["update_id"]
            highest_update_id = max(highest_update_id, update_id)
            
            message = item.get("message", {})
            text = message.get("text", "").strip()
            chat_id = message.get("chat", {}).get("id")
            
            # --- THE COMMAND MENU ---
            
            if text == "/sync":
                result_msg = sync_target_deadlines()
                send_telegram(result_msg)
                
            elif text == "/triage":
                result_msg = triage_targets()
                send_telegram(result_msg)
                
            elif text == "/list":
                # Just an example of how to list viable targets
                send_telegram("📡 <b>Fetching active targets...</b> (Integration with Ledger required)")
                
            # --- V12: SELF-LEARNING LOOP INGESTION ---
            elif text.startswith("/amend"):
                parts = text.split(" ", 2)
                if len(parts) >= 3:
                    target_id, feedback = parts[1], parts[2]
                    
                    # Log the feedback permanently to the brain's memory
                    with open(MEMORY_LOG, 'a', encoding='utf-8') as mf:
                        memory = {
                            "timestamp": datetime.now().isoformat(),
                            "target_id": target_id,
                            "type": "DIRECTOR_AMENDMENT",
                            "lesson": feedback
                        }
                        mf.write(json.dumps(memory) + "\n")
                        
                    send_telegram(f"🧠 <b>Memory Updated:</b> Amendment logged for #{target_id}. The Skein will remember this.")

        # Clear the queue
        if highest_update_id > 0:
            requests.get(f"{url}?offset={highest_update_id + 1}", timeout=10)
            
    except Exception as e:
        print(f"Error checking Telegram: {e}")

if __name__ == "__main__":
    print("🟢 MIND-SKEIN V12 C2 Link Established.")
    while True:
        process_telegram_commands()
        time.sleep(5) # Poll every 5 seconds