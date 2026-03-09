import os
import csv
from datetime import datetime

"""
FILE: departments/operations/sync_manual_ops.py
ROLE: Database Synchronization
FUNCTION: Injects manually handled targets (like #562) into the Ledger so the HUD is accurate.
"""

# --- V12 PATH RESOLUTION ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../"))
DATABASE_FILE = os.path.join(project_root, 'database/skein_index.csv')

def sync_target_562():
    print("🔄 MIND-SKEIN: Syncing Manual Operations to Ledger...")
    
    target_data = {
        "id": "T562",
        "status": "AWAITING_REVIEW",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "title": "[STRENGTH MULTIPLIER] Community Engagement Drive",
        "url": "https://github.com/Scottcjn/rustchain-bounties/issues/562",
        "payout_est": "330 RTC"
    }

    if not os.path.exists(DATABASE_FILE):
        print("❌ ERROR: Ledger not found at database/skein_index.csv")
        return

    # Check if already exists
    with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
        if any(r['id'] == 'T562' for r in rows):
            print("⚠️ Target T562 is already present in the Ledger.")
            return

    # Append to Ledger
    with open(DATABASE_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["id", "status", "timestamp", "title", "url", "payout_est"])
        writer.writerow(target_data)

    print("✅ SUCCESS: Target #562 injected. HUD will now reflect 357 RTC total pending.")

if __name__ == "__main__":
    sync_target_562()