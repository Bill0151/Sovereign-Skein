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
    """Scans the physical/digital world for 'Ransom' opportunities."""
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

def read_memory():
    """Reads the last 5 decisions to establish momentum and current holdings."""
    if not os.path.isfile('ransom_ledger.csv'):
        return "No history yet.", "None"
    
    try:
        with open('ransom_ledger.csv', 'r') as file:
            reader = list(csv.DictReader(file))
            if not reader:
                return "No history yet.", "None"
            
            # Extract the last 5 rows for momentum context
            last_5 = reader[-5:]
            history_text = "\n".join([f"[{row['timestamp']}] Chose: {row['chosen_asset']}" for row in last_5])
            
            # Identify the absolute current holding (the very last decision)
            current_hold = last_5[-1]['chosen_asset']
            return history_text, current_hold
    except Exception as e:
        print(f"Memory read error: {e}")
        return "History unreadable.", "None"

def analyze_skein(market_data, history, current_hold):
    """Feeds market data AND historical context into the Gemini Logic Core."""
    print("Transmitting through the Wormhole...")
    prompt = (
        f"You are the 'Sovereign Skein' AI. Analyze this DeFi yield data:\n{market_data}\n\n"
        f"--- MEMORY MODULE ---\n"
        f"Your last 5 historical decisions:\n{history}\n"
        f"Currently Holding: {current_hold}\n\n"
        f"--- LOGIC DIRECTIVE ---\n"
        f"Which pool offers the best balance of safety (High TVL) and yield (APY) for our 'Ransom Fund' today?\n"
        f"CRITICAL RULE: To prevent losing capital to transaction fees, do NOT recommend switching from your Currently Holding asset "
        f"UNLESS a new pool offers an APY at least 0.5% higher AND maintains an acceptable safety threshold (TVL).\n\n"
        f"CRITICAL FORMATTING: You MUST start your response with exactly this format on the very first line: 'CHOICE: [SYMBOL]' (e.g., 'CHOICE: STETH'). "
        f"Then, starting on the next line, provide your reasoning."
    )
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    return response.text

def update_memory(recommendation_text):
    """Writes the Skein's decision flawlessly to its permanent memory (CSV)."""
    file_exists = os.path.isfile('ransom_ledger.csv')
    
    # THE FILING CLERK FIX: Just read the barcode on the first line!
    chosen_asset = "Unknown"
    lines = recommendation_text.strip().split('\n')
    if lines[0].startswith("CHOICE:"):
        chosen_asset = lines[0].replace("CHOICE:", "").strip()
    
    with open('ransom_ledger.csv', 'a', newline='') as csvfile:
        fieldnames = ['timestamp', 'chosen_asset', 'raw_analysis']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader() 
            
        writer.writerow({
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'chosen_asset': chosen_asset,
            'raw_analysis': recommendation_text.replace('\n', ' ') 
        })
    print(f"Memory saved to ransom_ledger.csv. Asset logged: {chosen_asset}")

if __name__ == "__main__":
    print("--- INITIATING SOVEREIGN SKEIN V0.4 (Full Cognitive Loop) ---")
    market_text, raw_pools = fetch_yield_data()
    
    if "Sensor failure" not in market_text:
        # 1. Read the past
        history_text, current_hold = read_memory()
        print(f"Current Hold Identified: {current_hold}")
        
        # 2. Analyze the present
        analysis = analyze_skein(market_text, history_text, current_hold)
        print("\n--- GEMINI ANALYSIS ---")
        print(analysis)
        
        # 3. Write the future
        update_memory(analysis)
        print("\n--- PULSE COMPLETE ---")
    else:
        print(market_text)
