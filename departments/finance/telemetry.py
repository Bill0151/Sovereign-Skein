import os
import sys
import csv
import json
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
HUD_DATA_FILE = os.path.join(project_root, 'database/hud_telemetry.json')

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {"project": "SILICON CHRYSALIS", "target_milestone_gbp": 4000.0, "bankroll_gbp": 6.0}
    with open(SETTINGS_FILE, 'r') as f:
        return json.load(f)

def calculate_metrics(rows, settings):
    total_targets = len(rows)
    completed = len([r for r in rows if r.get('status') == 'COMPLETED'])
    active = len([r for r in rows if r.get('status') in ['APPLIED', 'AUTO_STRIKE_REQUESTED', 'POST_REQUESTED']])
    
    # Simulated revenue calculation 
    # (Future V12 update: Fetch live wallet balances from Web3/RPC APIs)
    # Using an estimated average SMC value of £15.00 for HUD visualization tracking
    estimated_revenue = completed * 15.0
    current_treasury = settings.get('bankroll_gbp', 0.0) + estimated_revenue
    
    target = settings.get('target_milestone_gbp', 4000.0)
    progress_percent = min((current_treasury / target) * 100, 100) if target > 0 else 0

    return {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "project_name": settings.get('project', 'MIND-SKEIN V12'),
        "treasury_gbp": round(current_treasury, 2),
        "target_gbp": target,
        "progress_percent": round(progress_percent, 2),
        "stats": {
            "total": total_targets,
            "completed": completed,
            "active_ops": active
        }
    }

def main():
    print("📈 MIND-SKEIN: Generating Telemetry Data...")
    
    settings = load_settings()
    
    if not os.path.exists(DATABASE_FILE):
        print("Ledger not found. Telemetry offline.")
        sys.exit(0)

    with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    metrics = calculate_metrics(rows, settings)
    
    # Write telemetry data for the HUD to safely consume
    with open(HUD_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=4)
        
    print(f"✅ Telemetry Updated.")
    print(f"🦋 Chrysalis Progress: {metrics['progress_percent']}% (£{metrics['treasury_gbp']}/£{metrics['target_gbp']})")

if __name__ == "__main__":
    main()