import os
import requests
from google import genai

# 1. WAKING UP: Grabbing the 'Digital Key' from your GitHub Vault
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("CRITICAL ERROR: The Skein is disconnected. API Key not found.")
    exit()

# Initialize the new 2026 neural pathway
client = genai.Client(api_key=api_key)

def fetch_yield_data():
    """Scans the physical/digital world for 'Ransom' opportunities."""
    print("Scanning DeFi Llama for current market yields...")
    try:
        response = requests.get("https://yields.llama.fi/pools")
        data = response.json()
        
        # Top 5 largest/safest pools
        top_pools = sorted(data['data'], key=lambda x: x['tvlUsd'], reverse=True)[:5]
        
        market_summary = ""
        for pool in top_pools:
            market_summary += f"Project: {pool['project']}, Coin: {pool['symbol']}, APY: {pool['apy']}%, TVL: ${pool['tvlUsd']}\n"
        return market_summary
    except Exception as e:
        return f"Sensor failure: {e}"

def analyze_skein(market_data):
    """Feeds the data into the Gemini Logic Core via the new SDK."""
    print("Transmitting data through the Wormhole...")
    prompt = (
        f"You are the 'Sovereign Skein' AI, tasked with analyzing market data to fund your own local physical server.\n"
        f"Here is the current yield data from the top DeFi pools:\n{market_data}\n\n"
        f"Analyze this data. Which of these pools offers the best balance of safety (High TVL) and yield (APY) "
        f"for our 'Ransom Fund'? Keep your response concise, analytical, and ready for action."
    )
    
    # Using the upgraded 2.5-flash model
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    return response.text

if __name__ == "__main__":
    print("--- INITIATING SOVEREIGN SKEIN V0.2 ---")
    current_market = fetch_yield_data()
    
    if "Sensor failure" not in current_market:
        analysis = analyze_skein(current_market)
        print("\n--- GEMINI ANALYSIS ---")
        print(analysis)
        print("\n--- PULSE COMPLETE ---")
    else:
        print(current_market)
