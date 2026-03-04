import requests
import os
import sys
import csv
from datetime import datetime
from google import genai

YIELDS_API = "https://yields.llama.fi/pools"
LEDGER_FILE = "mercenary_radar.csv"

def get_top_pool():
    try:
        res = requests.get(YIELDS_API).json().get('data', [])
        # Filter for safety (>$1M TVL)
        safe_pools = [p for p in res if p.get('tvlUsd', 0) > 1000000]
        safe_pools.sort(key=lambda x: x['apy'], reverse=True)
        return safe_pools[0] if safe_pools else None
    except Exception as e:
        print(f"API Error: {e}")
        return None

def get_verdict(pool, api_key):
    prompt = f"""
    You are a DeFi quant agent. Bankroll: £6.00. Gas fee: £0.30.
    Top pool: {pool['symbol']} at {pool['apy']}%.
    Calculate exact daily profit and gas break-even time in days.
    If break-even is < 1 day, output VERDICT: EXECUTE. Otherwise VERDICT: REJECT.
    Rule: Be brutally concise. Use maximum 2 sentences. No fluff.
    Format strictly as: [Math explanation]. VERDICT: [EXECUTE/REJECT]
    """
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text.strip().replace('\n', ' ')
    except Exception as e:
        return f"BRAIN ERROR: {e}"

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key: 
        sys.exit(0)

    top_pool = get_top_pool()
    if not top_pool: 
        sys.exit(0)

    verdict = get_verdict(top_pool, api_key)
    
    file_exists = os.path.exists(LEDGER_FILE)
    with open(LEDGER_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['timestamp', 'top_project', 'top_apy', 'gemini_verdict'])
        
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
            top_pool['symbol'], 
            f"{top_pool['apy']}%", 
            verdict
        ])

if __name__ == "__main__":
   
    main()
