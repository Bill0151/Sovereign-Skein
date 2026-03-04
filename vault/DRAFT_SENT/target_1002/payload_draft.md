# TARGET 1002: [15 RTC] Dual-Mining: Neoxa (KawPow) Integration
**Source URL:** https://github.com/Scottcjn/rustchain-bounties/issues/462
**Current Status:** DRAFT_SENT
---

```python
import psutil
import requests
import json

# Wallet for payout: 0xFb39098275D224965a938f5cCAB512BbF737bdc7

def detect_specific_processes():
    """
    Iterates through running processes to detect if any of the specified
    mining or node-related processes ('neoxad', 'trex', 'gminer', 'nbminer')
    are currently active on the system.
    """
    target_process_names = ['neoxad', 'trex', 'gminer', 'nbminer']
    found_processes = set()

    print("--- Process Detection ---")
    try:
        for proc in psutil.process_iter(['name']):
            try:
                process_name_lower = proc.info['name'].lower()
                if process_name_lower in target_process_names:
                    found_processes.add(proc.info['name'])
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Handle race conditions where a process might terminate or become inaccessible
                continue
    except Exception as e:
        print(f"Error during process iteration: {e}")

    if found_processes:
        print(f"Detected running target processes: {', '.join(sorted(found_processes))}")
    else:
        print("No specified 'neoxad', 'trex', 'gminer', 'nbminer' processes detected.")
    print("-------------------------\n")

def query_neoxa_node_rpc():
    """
    Sends a JSON-RPC request to the local Neoxa node at 'http://localhost:8788'
    to retrieve the current block count. Handles potential connection and RPC errors.
    """
    node_rpc_url = "http://localhost:8788"
    rpc_payload = {
        "jsonrpc": "1.0",
        "id": "neoxa-python-integration-script",
        "method": "getblockcount",
        "params": []
    }
    headers = {'Content-Type': 'application/json'}
    timeout_seconds = 5

    print("--- Neoxa Node RPC Query ---")
    try:
        response = requests.post(
            node_rpc_url,
            data=json.dumps(rpc_payload),
            headers=headers,
            timeout=timeout_seconds
        )
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
        rpc_response = response.json()

        if 'result' in rpc_response:
            print(f"Neoxa node 'getblockcount' successful: Current block count = {rpc_response['result']}")
        elif 'error' in rpc_response and rpc_response['error']:
            print(f"Neoxa node RPC error: Code {rpc_response['error'].get('code', 'N/A')}, Message: {rpc_response['error'].get('message', 'No message')}")
        else:
            print(f"Neoxa node RPC response in unexpected format: {json.dumps(rpc_response, indent=2)}")

    except requests.exceptions.ConnectionError:
        print(f"Error: Could not establish a connection to Neoxa node at {node_rpc_url}. "
              "Ensure the Neoxa node is running and its RPC interface is accessible.")
    except requests.exceptions.Timeout:
        print(f"Error: Request to Neoxa node at {node_rpc_url} timed out after {timeout_seconds} seconds. "
              "The node might be unresponsive or too busy.")
    except requests.exceptions.RequestException as e:
        print(f"An unexpected request error occurred while querying the Neoxa node: {e}")
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON response from {node_rpc_url}. Raw response: {response.text}")
    except Exception as e:
        print(f"An unforeseen error occurred during RPC query: {e}")
    print("----------------------------\n")

if __name__ == "__main__":
    detect_specific_processes()
    query_neoxa_node_rpc()
```

---
*Drafted and submitted autonomously by the Sovereign Skein Node, operating on behalf of Bill0151.*