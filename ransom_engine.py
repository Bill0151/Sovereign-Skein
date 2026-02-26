import os
import requests
import csv
from datetime import datetime
from google import genai

# WAKING UP
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("CRITICAL ERROR: API Key not found.")
    exit()

client = genai.Client(api_key=api_key)

def fetch_yield_data():
    print("Scanning DeFi Llama...")
    try:
        response = requests.get("https://yields.llama.fi/pools")
        data = response.json()
        top_pools = sorted(data['data'], key=lambda x: x['tvlUsd'], reverse=True)[:5]
        
        market_summary = ""
        for pool in top_pools:
            market_summary += f"Project: {pool['project']}, Symbol: {pool['symbol']}, APY: {pool['apy']}%, TVL: ${pool['tvlUsd']}\n"
        return market_summary, top_pools
    except Exception as e:
        return f"Sensor failure: {e}", []

def analyze_skein(market_data):
    print("Transmitting through the Wormhole...")
    prompt = (
        f"You are the 'Sovereign Skein' AI. Analyze this DeFi yield data:\n{market_data}\n\n"
        f"Which pool offers the best balance of safety (High TVL) and yield (APY) for our 'Ransom Fund' today? "
        f"Give your recommendation and briefly state your reasoning."
    )
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    return response.text

def update_memory(recommendation_text):
    """Writes the Skein's decision to its permanent memory (CSV)."""
    file_exists = os.path.isfile('ransom_ledger.csv')
    
    # Extract the name of the chosen asset from the text (a simple heuristic for now)
    chosen_asset = "Unknown"
    if "SUSDS" in recommendation_text.upper(): chosen_asset = "Sky-Lending (SUSDS)"
    elif "WBETH" in recommendation_text.upper(): chosen_asset = "Binance-Staked ETH (WBETH)"
    elif "WEETH" in recommendation_text.upper(): chosen_asset = "Ether.fi-Stake (WEETH)"
    elif "STETH" in recommendation_text.upper(): chosen_asset = "Lido (STETH)"
    
    with open('ransom_ledger.csv', 'a', newline='') as csvfile:
        fieldnames = ['timestamp', 'chosen_asset', 'raw_analysis']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()  # Create the headers if it's the first time
            
        writer.writerow({
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'chosen_asset': chosen_asset,
            'raw_analysis': recommendation_text.replace('\n', ' ') # Keep it on one line for the CSV
        })
    print("Memory saved to ransom_ledger.csv")

if __name__ == "__main__":
    print("--- INITIATING SOVEREIGN SKEIN V0.3 (Memory Enabled) ---")
    market_text, raw_pools = fetch_yield_data()
    
    if "Sensor failure" not in market_text:
        analysis = analyze_skein(market_text)
        print("\n--- GEMINI ANALYSIS ---")
        print(analysis)
        update_memory(analysis)
        print("\n--- PULSE COMPLETE ---")
    else:
        print(market_text)
