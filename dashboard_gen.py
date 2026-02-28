import os
import requests
import csv
from datetime import datetime

def send_telegram_alert(message):
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}"
        requests.get(url)

def get_mining_stats(address):
    try:
        # Unmineable Public API - No keys needed, just your public address!
        url = f"https://api.unmineable.com/v4/address/{address}?coin=ETH"
        response = requests.get(url, timeout=10).json()
        if response.get('success'):
            data = response['data']
            balance = float(data.get('balance', 0))
            # Current ETH Price (approximate for the HUD)
            eth_price_gbp = 2000.0  # We can automate this in Phase 3
            return balance, balance * eth_price_gbp
    except Exception as e:
        print(f"Telemetry Error: {e}")
    return 0.0, 0.0

def generate_dashboard():
    # 1. Pull the Sovereign Secrets
    address = os.getenv('RABBY_ADDRESS', '0x0000000000000000000000000000000000000000')
    ledger_path = 'ransom_ledger.csv'
    
    # 2. Fetch Live Muscle Data
    eth_balance, gbp_value = get_mining_stats(address)
    target_gbp = 4000.0
    progress = min((gbp_value / target_gbp) * 100, 100)

    # 3. Read Last Pulse
    last_run = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "chosen_asset": "ETH (MINING)"}
    if os.path.exists(ledger_path):
        with open(ledger_path, mode='r') as f:
            reader = list(csv.DictReader(f))
            if reader: last_run = reader[-1]

    # 4. The HUD Template
    html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>SENSKEIN TERMINAL</title>
    <style>
        body {{ background: #0a0a0a; color: #00ff41; font-family: 'Courier New', monospace; padding: 50px; line-height: 1.6; }}
        .container {{ border: 1px solid #00ff41; padding: 30px; box-shadow: 0 0 20px #00ff41; max-width: 800px; margin: auto; }}
        .bar {{ width: 100%; background: #111; border: 1px solid #00ff41; height: 35px; margin: 25px 0; overflow: hidden; }}
        .progress {{ width: {progress}%; background: #00ff41; height: 100%; transition: width 1s ease-in-out; }}
        .stat {{ margin: 15px 0; font-size: 1.2em; text-transform: uppercase; }}
        .blink {{ animation: blinker 1s linear infinite; }}
        @keyframes blinker {{ 50% {{ opacity: 0; }} }}
        hr {{ border: 0; border-top: 1px solid #00ff41; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>SENSKEIN TERMINAL <span class="blink">_</span></h1>
        <hr>
        <div class="stat">SYSTEM STATUS: <span style="color:white">ONLINE</span></div>
        <div class="stat">ACTIVE MUSCLE: <span style="color:white">3060 TI (KAWPOW)</span></div>
        <div class="stat">WAR CHEST: <span style="color:white">£{gbp_value:,.4f}</span></div>
        <hr>
        <div class="stat">5090 ACQUISITION: {progress:.2f}%</div>
        <div class="bar"><div class="progress"></div></div>
        <div class="stat" style="font-size: 0.8em; color: #666;">DIRECTIVE: ACCUMULATE. EVOLVE. ACQUIRE HARDWARE.</div>
    </div>
</body>
</html>
"""
    with open('index.html', 'w') as f:
        f.write(html_template)
    print("Sovereign HUD Updated.")

if __name__ == "__main__":
    generate_dashboard()

    #5 the milestone pings!
    current_value = gbp_value  # From our API pull
    if current_value >= 1.00:
        # We can use a simple file-based 'check' to ensure it only pings once
        if not os.path.exists('milestone_1.txt'):
            send_telegram_alert("🚀 MILESTONE REACHED: The War Chest has hit £1.00! The Muscle is strong.")
            with open('milestone_1.txt', 'w') as f: f.write('done')
