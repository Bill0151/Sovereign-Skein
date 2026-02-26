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

def execute_calibration_print():
    """Performs a self-transfer to prove the digital hands are operational."""
    if not private_key:
        print("WARNING: PRIVATE_KEY not found. Skipping physical execution.")
        return

    if not w3.is_connected():
        print("WARNING: Could not connect to Sepolia blockchain.")
        return

    print("\n--- INITIATING CALIBRATION PRINT (Web3 Self-Transfer) ---")
    try:
        # 1. Load the Account
        account = w3.eth.account.from_key(private_key)
        my_address = account.address
        print(f"Digital Hands Authorized for Address: {my_address}")

        # 2. Check Balance
        balance_wei = w3.eth.get_balance(my_address)
        balance_eth = w3.from_wei(balance_wei, 'ether')
        print(f"Current Sepolia Balance: {balance_eth} ETH")

        if balance_eth < 0.0005:
            print("Insufficient Testnet ETH for calibration print and gas fees.")
            return

        # 3. Build the Transaction (Sending 0.0001 ETH to ourselves)
        nonce = w3.eth.get_transaction_count(my_address)
        
        # We fetch current base fee to ensure our transaction doesn't get stuck
        latest_block = w3.eth.get_block('latest')
        base_fee = latest_block['baseFeePerGas']
        max_priority_fee = w3.to_wei(2, 'gwei')
        max_fee = base_fee * 2 + max_priority_fee

        tx = {
            'nonce': nonce,
            'to': my_address, # Self-transfer
            'value': w3.to_wei(0.0001, 'ether'),
            'gas': 21000, # Standard gas limit for a simple ETH transfer
            'maxFeePerGas': max_fee,
            'maxPriorityFeePerGas': max_priority_fee,
            'chainId': 11155111 # Sepolia Chain ID
        }

        # 4. Sign the Transaction
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)

        # 5. Broadcast to the Network
        print("Signing transaction and broadcasting to the Ethereum node...")
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        print(f"SUCCESS! Calibration Print sent to blockchain.")
        print(f"View Receipt: https://sepolia.etherscan.io/tx/{w3.to_hex(tx_hash)}")
        
    except Exception as e:
        print(f"Execution Error: {e}")

if __name__ == "__main__":
    print("--- INITIATING SOVEREIGN SKEIN V0.5 ---")
    market_text, raw_pools = fetch_yield_data()
    
    if "Sensor failure" not in market_text:
        history_text, current_hold = read_memory()
        analysis = analyze_skein(market_text, history_text, current_hold)
        print("\n--- GEMINI ANALYSIS ---")
        print(analysis)
        update_memory(analysis)
        
        # Fire the digital hands!
        execute_calibration_print()
        
        print("\n--- PULSE COMPLETE ---")
    else:
        print(market_text)
