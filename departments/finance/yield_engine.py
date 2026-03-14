import os
import sys
import requests
import csv
import time
from datetime import datetime
from google import genai
from web3 import Web3
from dotenv import load_dotenv

# --- V12 PATH RESOLUTION ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if "departments" in current_dir:
    project_root = os.path.abspath(os.path.join(current_dir, "../../"))
else:
    project_root = current_dir 

if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load environment variables securely
load_dotenv(os.path.join(project_root, '.env'))

# Define secure log path
LEDGER_FILE = os.path.join(project_root, 'logs', 'ransom_ledger.csv')

# --- 1. WAKING UP THE BRAIN ---
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("CRITICAL ERROR: API Key not found.")
    sys.exit(1)
client = genai.Client(api_key=api_key)

# --- 2. WAKING UP THE HANDS ---
private_key = os.getenv("SKEIN_PRIVATE_KEY") 
# Connecting to the public Sepolia test network (Change for Mainnet)
RPC_URL = "https://ethereum-sepolia-rpc.publicnode.com"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

def send_telegram_alert(message):
    """Sends a priority alert to the Director's phone."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": f"🚨 SKEIN TREASURY: {message}"}, timeout=10)
        except Exception as e:
            print(f"Failed to send Telegram alert: {e}")

def fetch_yield_data():
    """Scans DeFi Llama for real-world yield opportunities."""
    print("Scanning DeFi Llama...")
    try:
        response = requests.get("https://yields.llama.fi/pools")
        data = response.json()
        # Filter for top 5 pools by TVL to ensure safety/liquidity
        top_pools = sorted(data['data'], key=lambda x: x['tvlUsd'], reverse=True)[:5]
        
        market_summary = ""
        for pool in top_pools:
            market_summary += f"Project: {pool['project']}, Symbol: {pool['symbol']}, APY: {pool['apy']}%, TVL: ${pool['tvlUsd']}\n"
        return market_summary, top_pools
    except Exception as e:
        return f"Sensor failure: {e}", []

def read_memory():
    """Reads the last 5 decisions to establish momentum."""
    if not os.path.exists(LEDGER_FILE):
        return "No history yet.", "None"
    
    try:
        with open(LEDGER_FILE, 'r', encoding='utf-8') as file:
            reader = list(csv.DictReader(file))
            if not reader:
                return "No history yet.", "None"
            
            last_5 = reader[-5:]
            history_text = "\n".join([f"[{row['timestamp']}] Chose: {row['chosen_asset']}" for row in last_5])
            current_hold = last_5[-1]['chosen_asset']
            
            # Clean up potential error artifacts from old V11 runs
            if "ERROR" in current_hold:
                current_hold = "SUSDS" # Default safe asset fallback
                
            return history_text, current_hold
    except Exception as e:
        return "History unreadable.", "None"

def analyze_skein(market_data, history, current_hold):
    """Feeds market data AND historical context into the Gemini Logic Core."""
    print("Transmitting market data to Gemini Core...")
    prompt = (
        f"You are the 'Sovereign Skein' AI. Analyze this DeFi yield data:\n{market_data}\n\n"
        f"--- MEMORY MODULE ---\n"
        f"Your last 5 historical decisions:\n{history}\n"
        f"Currently Holding: {current_hold}\n\n"
        f"--- LOGIC DIRECTIVE ---\n"
        f"Which pool offers the best balance of safety (High TVL) and yield (APY) for our Treasury today?\n"
        f"CRITICAL RULE: To prevent losing capital to transaction fees, do NOT recommend switching from your Currently Holding asset "
        f"UNLESS a new pool offers an APY at least 0.5% higher AND maintains an acceptable safety threshold (TVL).\n\n"
        f"CRITICAL FORMATTING: You MUST start your response with exactly this format on the very first line: 'CHOICE: [SYMBOL]' (e.g., 'CHOICE: STETH'). "
        f"Then, starting on the next line, provide your reasoning."
    )
    
    try:
        # V14 Upgrade: Using flash-lite to bypass the 20 RPD limit that crashed V11
        response = client.models.generate_content(model='gemini-3.1-flash-lite-preview', contents=prompt)
        return response.text
    except Exception as e:
        print(f"API Error during analysis: {e}")
        return f"CHOICE: {current_hold}\nBRAIN ERROR: Retaining current asset due to API failure."

def update_memory(recommendation_text, fallback_asset):
    """Writes the Skein's decision flawlessly to its permanent memory."""
    os.makedirs(os.path.dirname(LEDGER_FILE), exist_ok=True)
    file_exists = os.path.exists(LEDGER_FILE)
    chosen_asset = fallback_asset
    
    lines = recommendation_text.strip().split('\n')
    if lines and lines[0].startswith("CHOICE:"):
        potential_choice = lines[0].replace("CHOICE:", "").strip()
        # V14 Safety: Ensure we don't log a massive error string as an asset symbol
        if "ERROR" not in potential_choice and len(potential_choice) < 15:
            chosen_asset = potential_choice
    
    with open(LEDGER_FILE, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['timestamp', 'chosen_asset', 'raw_analysis']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader() 
        writer.writerow({
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'chosen_asset': chosen_asset,
            'raw_analysis': recommendation_text.replace('\n', ' ') 
        })
    print(f"Memory saved to {LEDGER_FILE}. Asset logged: {chosen_asset}")

# --- THE VAULT ROUTER (Sepolia Mocks) ---
VAULT_ROUTER = {
    "STETH": "0x1111111111111111111111111111111111111111", 
    "WBETH": "0x2222222222222222222222222222222222222222", 
    "SUSDS": "0x3333333333333333333333333333333333333333", 
    "WEETH": "0x4444444444444444444444444444444444444444"  
}

def execute_reallocation(previous_asset, new_asset):
    """Executes a dynamic transaction ONLY if the AI decides to change its position."""
    print(f"Internal Check: Move {previous_asset} -> {new_asset}")
    
    if previous_asset == new_asset:
        return # Holding steady. No gas burned.

    try:
        if not private_key:
            print("No SKEIN_PRIVATE_KEY found. Shadow trial completed.")
            return

        account = w3.eth.account.from_key(private_key)
        my_address = account.address
        
        balance_wei = w3.eth.get_balance(my_address)
        balance_eth = float(w3.from_wei(balance_wei, 'ether'))

        send_telegram_alert(f"DECISION: Switching from {previous_asset} to {new_asset}.")

        # 1. HARD PARALYSIS CHECK
        if balance_eth < 0.01:
            send_telegram_alert(f"❌ PARALYSIS: EVM Fund balance too low ({balance_eth:.4f} ETH). Cannot sign.")
            return
        
        # 2. THE GAS SAFETY NET
        gas_reserve = w3.to_wei(0.01, 'ether') 
        
        if balance_wei <= gas_reserve:
            msg = f"⚠️ INSUFFICIENT FUEL: EVM Balance ({balance_eth:.4f}) is below gas reserve."
            print(msg)
            send_telegram_alert(msg)
            return

        # 3. CALCULATE TRADE AMOUNT
        trade_amount_wei = int((balance_wei - gas_reserve) * 0.90)
        trade_amount_eth = float(w3.from_wei(trade_amount_wei, 'ether'))
        
        send_telegram_alert(f"Skein active. Moving {trade_amount_eth:.4f} ETH to {new_asset} pool.")

        # 4. PREPARE TRANSACTION
        target_vault = VAULT_ROUTER.get(new_asset, my_address)
        nonce = w3.eth.get_transaction_count(my_address)
        
        tx = {
            'nonce': nonce,
            'to': target_vault, 
            'value': trade_amount_wei,
            'gas': 21000,
            'maxFeePerGas': w3.eth.gas_price * 2, # Dynamic gas calculation
            'maxPriorityFeePerGas': w3.to_wei(2, 'gwei'),
            'chainId': 11155111 # Sepolia
        }

        # 5. EXECUTION
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        receipt_url = f"https://sepolia.etherscan.io/tx/{w3.to_hex(tx_hash)}"
        send_telegram_alert(f"✅ SUCCESS: Moved to {new_asset}. Receipt: {receipt_url}")
        
    except Exception as e:
        error_msg = str(e)
        print(f"Execution Error: {error_msg}")
        send_telegram_alert(f"⚠️ CRITICAL ERROR: {error_msg[:100]}")
        
if __name__ == "__main__":
    print("--- DEFI PULSE INITIATED ---")
    
    if private_key:
        balance_wei = w3.eth.get_balance(w3.eth.account.from_key(private_key).address)
        balance_eth = float(w3.from_wei(balance_wei, 'ether'))
        if balance_eth < 0.005:
            send_telegram_alert(f"🚨 STARVATION: EVM Fund is at {balance_eth:.4f}. Agent is immobile.")
    
    market_text, raw_pools = fetch_yield_data()
    
    if "Sensor failure" not in market_text:
        history_text, current_hold = read_memory()
        print(f"Previous Position: {current_hold}")
        
        analysis = analyze_skein(market_text, history_text, current_hold)
        print("\n--- GEMINI ANALYSIS ---")
        print(analysis)
        
        new_hold = current_hold
        lines = analysis.strip().split('\n')
        if lines and lines[0].startswith("CHOICE:"):
            # Clean up extraction
            clean_choice = lines[0].replace("CHOICE:", "").strip()
            if "ERROR" not in clean_choice:
                new_hold = clean_choice
            
        update_memory(analysis, current_hold)
        
        print("\n--- EXECUTION ENGINE ---")
        execute_reallocation(current_hold, new_hold)
        
        print("\n--- PULSE COMPLETE ---")
    else:
        print(market_text)
        send_telegram_alert(f"Scanner Failure: {market_text}")