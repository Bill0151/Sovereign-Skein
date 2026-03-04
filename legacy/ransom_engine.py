import os
import requests
import csv
from datetime import datetime
from google import genai
from web3 import Web3

# --- 1. WAKING UP THE BRAIN ---
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("CRITICAL ERROR: API Key not found.")
    exit()
client = genai.Client(api_key=api_key)

# --- 2. WAKING UP THE HANDS ---
private_key = os.environ.get("PRIVATE_KEY")
# Connecting to the public Sepolia test network
RPC_URL = "https://ethereum-sepolia-rpc.publicnode.com"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

def send_telegram_alert(message):
    """Sends a priority alert to the Director's phone."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": f"🚨 SKEIN: {message}"}, timeout=10)
        except Exception as e:
            print(f"Failed to send Telegram alert: {e}")

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
            
            last_5 = reader[-5:]
            history_text = "\n".join([f"[{row['timestamp']}] Chose: {row['chosen_asset']}" for row in last_5])
            current_hold = last_5[-1]['chosen_asset']
            return history_text, current_hold
    except Exception as e:
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
    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    return response.text

def update_memory(recommendation_text):
    """Writes the Skein's decision flawlessly to its permanent memory (CSV)."""
    file_exists = os.path.isfile('ransom_ledger.csv')
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

# --- THE VAULT ROUTER ---
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
        return # Essential notifications only

    try:
        # Define the 'Hands' within this scope
        account = w3.eth.account.from_key(private_key)
        my_address = account.address
        
        balance_wei = w3.eth.get_balance(my_address)
        balance_eth = float(w3.from_wei(balance_wei, 'ether'))

        send_telegram_alert(f"DECISION: Switching from {previous_asset} to {new_asset}.")

        # 1. HARD PARALYSIS CHECK (Eth balance)
        if balance_eth < 0.01:
            send_telegram_alert(f"❌ PARALYSIS: Fund balance too low ({balance_eth:.4f} ETH). Cannot sign.")
            return
        
        # 2. THE GAS SAFETY NET (Wei-level precision)
        # We reserve 0.01 ETH for gas to handle network spikes
        gas_reserve = w3.to_wei(0.01, 'ether') 
        
        if balance_wei <= gas_reserve:
            msg = f"⚠️ INSUFFICIENT FUEL: Balance ({w3.from_wei(balance_wei, 'ether'):.4f}) is below gas reserve."
            print(msg)
            send_telegram_alert(msg)
            return

        # 3. CALCULATE TRADE AMOUNT
        # We move 90% of the REMAINING balance after the reserve
        trade_amount_wei = int((balance_wei - gas_reserve) * 0.90)
        trade_amount_eth = float(w3.from_wei(trade_amount_wei, 'ether'))
        
        send_telegram_alert(f"Fingerskein active. Moving {trade_amount_eth:.4f} ETH to {new_asset}.")

        # 4. PREPARE TRANSACTION
        target_vault = VAULT_ROUTER.get(new_asset, my_address)
        nonce = w3.eth.get_transaction_count(my_address)
        
        tx = {
            'nonce': nonce,
            'to': target_vault, 
            'value': trade_amount_wei,
            'gas': 21000, # Standard ETH transfer gas
            'maxFeePerGas': w3.to_wei(50, 'gwei'),
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
    print("--- PULSE INITIATED ---")
    
    # 1. Quick Fuel Check
    balance_wei = w3.eth.get_balance(w3.eth.account.from_key(private_key).address)
    balance_eth = float(w3.from_wei(balance_wei, 'ether'))
    
    # Silence is golden, unless we are empty
    if balance_eth < 0.005:
        send_telegram_alert(f"🚨 STARVATION: Fund is at 0.0000. Agent is immobile.")
    
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
            new_hold = lines[0].replace("CHOICE:", "").strip()
            
        update_memory(analysis)
        
        print("\n--- EXECUTION ENGINE ---")
        execute_reallocation(current_hold, new_hold)
        
        print("\n--- PULSE COMPLETE ---")
    else:
        print(market_text)
        send_telegram_alert(f"Scanner Failure: {market_text}")
