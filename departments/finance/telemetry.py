import os
import sys
import csv
import json
import re
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
    completed_rows = [r for r in rows if r.get('status') == 'COMPLETED']
    completed = len(completed_rows)
    active = len([r for r in rows if r.get('status') in ['APPLIED', 'AUTO_STRIKE_REQUESTED', 'POST_REQUESTED']])
    
    # --- V12.18: STRICT CRYPTOGRAPHIC VERIFICATION ---
    current_treasury = 0.0
    wallet_live = False
    eth_balance = 0.0
    usdc_balance = 0.0
    
    try:
        # Dynamically load the Treasury Node to check the actual blockchain
        from departments.finance.finance import BaseTreasury
        treasury = BaseTreasury()
        balances = treasury.get_balances()
        
        # Approximate Conversion Rates (ETH = ~£2500, USDC = ~£0.78)
        eth_balance = balances.get("ETH", 0.0)
        usdc_balance = balances.get("USDC", 0.0)
        eth_gbp = eth_balance * 2500.0
        usdc_gbp = usdc_balance * 0.78
        
        # V12.20 FIX: Pure Cryptographic Truth. We no longer add the fiat 'bankroll_gbp'
        current_treasury = eth_gbp + usdc_gbp
        wallet_live = True
        print(f"🔗 LIVE WALLET LINKED: {eth_balance:.4f} ETH | {usdc_balance:.2f} USDC")
            
    except SystemExit:
        print("⚠️ Base L2 RPC unreachable. Falling back to Ledger estimates.")
    except Exception as e:
        print(f"⚠️ Could not read Treasury wallet: {e}. Falling back to Ledger estimates.")
        
    # --- FALLBACK: ESTIMATED LEDGER REVENUE ---
    if not wallet_live:
        estimated_revenue = 0.0
        for r in completed_rows:
            payout_str = r.get('payout_est', '')
            numbers = re.findall(r'\d+', str(payout_str))
            if numbers:
                val = float(numbers[-1])
                estimated_revenue += (val * 0.78)
            else:
                estimated_revenue += 15.0 
        current_treasury = settings.get('bankroll_gbp', 6.0) + estimated_revenue
    
    target = settings.get('target_milestone_gbp', 4000.0)
    progress_percent = min((current_treasury / target) * 100, 100) if target > 0 else 0

    return {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "project_name": settings.get('project', 'SILICON CHRYSALIS'),
        "treasury_gbp": round(current_treasury, 2),
        "target_gbp": target,
        "progress_percent": round(progress_percent, 2),
        "eth_balance": eth_balance,
        "usdc_balance": usdc_balance,
        "wallet_live": wallet_live,
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
    
    with open(HUD_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=4)
        
    print(f"✅ Telemetry Updated.")
    
    # --- V12.19 Terminal Output Enhancement ---
    if metrics.get('wallet_live'):
        print(f"🪙  Live Wallet: {metrics['eth_balance']:.4f} ETH | {metrics['usdc_balance']:.2f} USDC")
        
    print(f"🦋 Chrysalis Progress: {metrics['progress_percent']}% (£{metrics['treasury_gbp']}/£{metrics['target_gbp']})")

if __name__ == "__main__":
    main()