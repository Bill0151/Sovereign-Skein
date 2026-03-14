"""
FILE: departments/finance/finance.py
ROLE: The "Treasury" - Finance Node
FUNCTION: Base L2 Wallet Management, AI-Intent to Calldata, and Autonomous USDC Settlement.
VERSION: V12.1 (Dual-Wallet Architecture Support)
"""

import os
import sys
import csv
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from web3 import Web3
from google import genai

# --- V12 PATH RESOLUTION ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if "departments" in current_dir:
    project_root = os.path.abspath(os.path.join(current_dir, "../../"))
else:
    project_root = current_dir 

if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- SECURE VAULT DECRYPTION & CONFIG ---
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- DUAL WALLET ARCHITECTURE ---
# Explicitly look for the EVM wallet. Fallback to SKEIN_WALLET only if it's an 0x string.
_raw_evm = os.getenv("EVM_WALLET_ADDRESS", os.getenv("SKEIN_WALLET_ADDRESS", ""))
EVM_WALLET_ADDRESS = _raw_evm if _raw_evm.startswith("0x") else None
PRIVATE_KEY = os.getenv("SKEIN_PRIVATE_KEY")       # Target Base L2 Private Key

# Default to Level 3 (Shadow Trials only) if not explicitly set to 4 or 5
AUTONOMY_LEVEL = int(os.getenv("SKEIN_AUTONOMY_LEVEL", 3))

SHADOW_LEDGER = os.path.join(project_root, 'logs/shadow_ledger.csv')

# --- WEB3 BASE L2 CONFIGURATION ---
BASE_RPC_URL = "https://mainnet.base.org"
USDC_BASE_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

# Minimal ERC-20 ABI for USDC transfers and balance checks
ERC20_ABI = json.loads('[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}]')

class BaseTreasury:
    def __init__(self):
        print("🏦 TREASURY: Initializing Base L2 Uplink...")
        self.w3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))
        
        if not self.w3.is_connected():
            print("❌ TREASURY ERROR: Failed to connect to Base Mainnet RPC.")
            sys.exit(1)
            
        print("🟢 TREASURY: Connected to Base Mainnet.")
        self.usdc_contract = self.w3.eth.contract(address=self.w3.to_checksum_address(USDC_BASE_ADDRESS), abi=ERC20_ABI)
        
        # USDC uses 6 decimals on Base
        self.usdc_decimals = 6 

    def get_balances(self):
        """Fetches live ETH (for gas) and USDC balances."""
        if not EVM_WALLET_ADDRESS:
            print("⚠️ TREASURY WARNING: No valid 0x EVM_WALLET_ADDRESS found in .env")
            return {"ETH": 0.0, "USDC": 0.0}
            
        address = self.w3.to_checksum_address(EVM_WALLET_ADDRESS)
        eth_wei = self.w3.eth.get_balance(address)
        eth_balance = self.w3.from_wei(eth_wei, 'ether')
        
        usdc_raw = self.usdc_contract.functions.balanceOf(address).call()
        usdc_balance = usdc_raw / (10 ** self.usdc_decimals)
        
        return {"ETH": float(eth_balance), "USDC": float(usdc_balance)}

    def parse_ai_intent(self, intent_string):
        """
        Translates a natural language command into structured transaction data using Gemini.
        """
        print(f"🧠 TREASURY: Translating Intent -> Calldata...")
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = f"""
        You are a Web3 financial transaction parser for a Base L2 AI Agent.
        Extract the transaction details from the following intent.
        
        INTENT: "{intent_string}"
        
        Respond STRICTLY with a valid JSON object. No markdown, no backticks, no conversational text.
        Format:
        {{
            "action": "transfer",
            "token": "USDC",
            "amount": 5.5,
            "to_address": "0x..."
        }}
        """
        
        try:
            res = client.models.generate_content(model='gemini-3.1-flash-lite-preview', contents=prompt)
            clean_json = res.text.strip().replace("```json", "").replace("```", "")
            tx_data = json.loads(clean_json)
            
            if tx_data.get('action') == 'transfer' and self.w3.is_address(tx_data.get('to_address')):
                return tx_data
            else:
                print("   [!] Intent parsing failed validation (Invalid Address or Action).")
                return None
                
        except Exception as e:
            print(f"   [BRAIN ERROR] Could not parse intent: {e}")
            return None

    def execute_transaction(self, tx_data):
        """
        The Autonomy Gate. Routes the transaction to Shadow Ledger (L1-L3) or Live Base L2 (L4-L5).
        """
        if not tx_data: return
        
        to_address = self.w3.to_checksum_address(tx_data['to_address'])
        amount = tx_data['amount']
        token = tx_data['token']
        
        print(f"\n⚡ TRANSACTION PRE-FLIGHT:")
        print(f"   Target: {to_address}")
        print(f"   Amount: {amount} {token}")
        print(f"   Network: Base L2")
        print(f"   Autonomy Level: {AUTONOMY_LEVEL}")
        
        if AUTONOMY_LEVEL < 4:
            print("🛡️ AUTONOMY GATE: Level < 4. Initiating Shadow Trial.")
            self._log_shadow_trial(tx_data)
        else:
            print("⚠️ AUTONOMY GATE: Level 4+. LIVE EXECUTION AUTHORIZED.")
            self._execute_live_usdc_transfer(to_address, amount)

    def _log_shadow_trial(self, tx_data):
        """Simulates the transaction and logs it without using real gas/funds."""
        os.makedirs(os.path.dirname(SHADOW_LEDGER), exist_ok=True)
        
        # Estimate theoretical gas 
        gas_price = self.w3.eth.gas_price
        est_gas_cost_eth = self.w3.from_wei(gas_price * 65000, 'ether') # Rough ERC20 transfer limit
        
        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "SHADOW_TRIAL_SUCCESS",
            "action": tx_data['action'],
            "token": tx_data['token'],
            "amount": tx_data['amount'],
            "to_address": tx_data['to_address'],
            "est_gas_eth": float(est_gas_cost_eth),
            "network": "Base L2"
        }
        
        file_exists = os.path.exists(SHADOW_LEDGER)
        with open(SHADOW_LEDGER, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=log_entry.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(log_entry)
            
        print(f"✅ SHADOW TRIAL: Successfully paper-traded {tx_data['amount']} {tx_data['token']}. Logged to shadow_ledger.csv")

    def _execute_live_usdc_transfer(self, to_address, amount_usdc):
        """DANGER: Actually signs and broadcasts a Web3 transaction."""
        if not EVM_WALLET_ADDRESS or not PRIVATE_KEY:
            print("❌ TREASURY ERROR: Live execution failed. Missing EVM_WALLET_ADDRESS or SKEIN_PRIVATE_KEY in .env.")
            return
            
        try:
            raw_amount = int(amount_usdc * (10 ** self.usdc_decimals))
            nonce = self.w3.eth.get_transaction_count(self.w3.to_checksum_address(EVM_WALLET_ADDRESS))
            
            tx = self.usdc_contract.functions.transfer(to_address, raw_amount).build_transaction({
                'chainId': 8453, # Base Mainnet Chain ID
                'gas': 100000,   # Safe limit for standard ERC20
                'gasPrice': self.w3.eth.gas_price,
                'nonce': nonce,
            })
            
            print("   Signing transaction...")
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
            
            print("   Broadcasting to Base L2...")
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            hex_hash = self.w3.to_hex(tx_hash)
            print(f"✅ LIVE TRANSACTION SENT! TX Hash: {hex_hash}")
            print(f"🔍 View on basescan: https://basescan.org/tx/{hex_hash}")
            
        except Exception as e:
            print(f"❌ LIVE TRANSACTION FAILED: {e}")

if __name__ == "__main__":
    print("🟢 MIND-SKEIN V12 Treasury Uplink Established.")
    treasury = BaseTreasury()
    
    balances = treasury.get_balances()
    print(f"💰 Vault Balances: {balances['ETH']:.6f} ETH | {balances['USDC']:.2f} USDC")
    
    test_intent = "Please send 2.5 USDC to the smart contract address 0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B for the API fees."
    parsed_tx = treasury.parse_ai_intent(test_intent)
    
    if parsed_tx:
        treasury.execute_transaction(parsed_tx)