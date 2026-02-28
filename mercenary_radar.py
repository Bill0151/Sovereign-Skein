import os
import requests
import csv
from datetime import datetime
import google.generativeai as genai

# 1. Awaken the Brain
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY missing from GitHub Secrets.")
    exit(1)
genai.configure(api_key=api_key)
# Using the fastest, most cost-effective model for high-frequency pulses
model = genai.GenerativeModel('gemini-1.5-flash-latest') 

def fetch_defillama_pools():
    print("Scanning DefiLlama Yields API...")
    try:
        url = "https://yields.llama.fi/pools"
        response = requests.get(url, timeout=15).json()
        pools = response.get("data", [])
        
        valid_pools = []
        for p in pools:
            # Filter: Binance Smart Chain, >$1M TVL, >100% APY
            if p.get("chain") == "Binance" and p.get("tvlUsd", 0) > 1000000 and p.get("apy", 0) > 100:
                valid_pools.append({
                    "project": p.get("project"),
                    "symbol": p.get("symbol"),
                    "tvl": p.get("tvlUsd"),
                    "apy": round(p.get("apy"), 2)
                })
        
        # Sort by highest APY and take the top 3
        valid_pools.sort(key=lambda x: x["apy"], reverse=True)
        return valid_pools[:3]
    except Exception as e:
        print(f"API Error: {e}")
        return []

def analyze_with_gemini(pools):
    if not pools:
        return "VERDICT: REJECT. No pools met the safety (>$1M TVL) and yield (>100% APY) criteria on BSC."
        
    prompt = f"""
    You are a ruthless quantitative Web3 AI. 
    Bankroll: £6.00
    Gas Fee (Round Trip): £0.30
    
    Analyze these top high-yield pools on the Binance Smart Chain:
    {pools}
    
    Calculate the exact daily profit in GBP for the highest APY pool based on the £6 bankroll. 
    Calculate exactly how many days it will take just to break even on the £0.30 gas fee. 
    Provide a strict VERDICT (EXECUTE or REJECT) for a paper trade. Keep the response under 4 sentences. Be highly analytical.
    """
    try:
        response = model.generate_content(prompt)
        # Clean up the text so it fits nicely in one CSV cell
        return response.text.replace('\n', ' ').strip()
    except Exception as e:
        return f"Brain Error: {e}"

def main():
    pools = fetch_defillama_pools()
    verdict = analyze_with_gemini(pools)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    top_pool_name = pools[0]['project'] if pools else "NONE"
    top_pool_apy = pools[0]['apy'] if pools else 0.0
    
    # Log to the new Mercenary CSV
    file_exists = os.path.isfile('mercenary_radar.csv')
    with open('mercenary_radar.csv', 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['timestamp', 'top_project', 'top_apy', 'gemini_verdict'])
        writer.writerow([timestamp, top_pool_name, f"{top_pool_apy}%", verdict])
        
    print(f"Pulse complete. Top Pool: {top_pool_name} @ {top_pool_apy}%. Verdict logged.")

if __name__ == "__main__":
    main()
