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
YIELD_LOG = os.path.join(project_root, 'database/skein_yield_log.csv')

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {"project": "SILICON CHRYSALIS", "autonomy_level": 1, "bankroll_gbp": 6.0}
    with open(SETTINGS_FILE, 'r') as f:
        return json.load(f)

def fetch_yield_opportunities():
    """Scans DeFi Llama for high-yield, stable-risk pools."""
    print("🔍 MIND-SKEIN: Scanning DeFi Llama for Yield Pools...")
    try:
        res = requests.get("https://yields.llama.fi/pools", timeout=15).json()
        pools = res.get("data", [])
        
        # Filter for viable pools: > $1M TVL to avoid rugs, 5-50% APY to avoid hyper-inflation traps
        viable_pools = [p for p in pools if p.get('tvlUsd', 0) > 1000000 and 5 < p.get('apy', 0) < 50]
        
        # Sort by highest APY
        viable_pools.sort(key=lambda x: x.get('apy', 0), reverse=True)
        return viable_pools[:5]
    except Exception as e:
        print(f"Yield Radar Offline: {e}")
        return []

def log_shadow_trial(pool_data, settings):
    """Records an intended investment for later accuracy grading."""
    file_exists = os.path.exists(YIELD_LOG)
    
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": "SHADOW_TRIAL",
        "project": pool_data.get('project', 'Unknown'),
        "symbol": pool_data.get('symbol', 'Unknown'),
        "apy_percent": round(pool_data.get('apy', 0), 2),
        "tvl_usd": pool_data.get('tvlUsd', 0),
        "simulated_investment_gbp": settings.get('bankroll_gbp', 6.0),
        "status": "PENDING_REVIEW"
    }

    with open(YIELD_LOG, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=entry.keys())
        if not file_exists or os.stat(YIELD_LOG).st_size == 0:
            writer.writeheader()
        writer.writerow(entry)
        
    return entry

def main():
    settings = load_settings()
    autonomy_level = settings.get("autonomy_level", 1)
    
    pools = fetch_yield_opportunities()
    if not pools:
        print("No viable yield pools found today.")
        return

    top_pool = pools[0]
    print(f"🏆 Top Yield Target: {top_pool['project']} ({top_pool['symbol']}) @ {round(top_pool['apy'], 2)}% APY")

    if autonomy_level < 4:
        print("🛡️ Autonomy Level < 4. Executing SHADOW TRIAL (Paper Trade).")
        trial = log_shadow_trial(top_pool, settings)
        print(f"👻 Logged Shadow Trial to Yield Ledger: Simulated £{trial['simulated_investment_gbp']} allocated to {trial['symbol']}.")
    else:
        # V12 Future Feature: Actual Web3 Execution requires the Director Authorization Gate for moves > £50
        print("⚠️ L4+ Autonomy Detected. Initiating Director Authorization Gate...")
        print(f"Pending Live Execution for {top_pool['project']}. Web3 keys required.")

if __name__ == "__main__":
    main()