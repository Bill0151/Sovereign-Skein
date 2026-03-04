# TARGET 1003: [15 RTC] Dual-Mining: Zephyr (RandomX) Integration
**Source URL:** https://github.com/Scottcjn/rustchain-bounties/issues/461
**Current Status:** COMPLETED
---

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Payout Wallet: 0xFb39098275D224965a938f5cCAB512BbF737bdc7

import psutil
import requests
import json
import sys

def check_process_status(process_names):
    """
    Detects if any of the specified processes are currently running on the system.
    This function leverages psutil to iterate through active processes and match
    against a list of target names.

    Args:
        process_names (list): A list of strings, where each string represents a
                              process name (e.g., 'xmrig', 'zephyrd') to search for.

    Returns:
        dict: A dictionary mapping each target process name (lowercase) to a boolean
              indicating whether a process matching that name was found.
    """
    running_processes_found = {name.lower(): False for name in process_names}
    script_name = sys.argv[0].split('/')[-1]
    print(f"[{script_name}] Initiating process status check for: {', '.join(process_names)}")

    for proc in psutil.process_iter(['name', 'pid']):
        try:
            proc_name = proc.info['name'].lower()
            for target_name in process_names:
                if target_name.lower() in proc_name:  # Using 'in' for broader matching (e.g., 'xmrig-proxy')
                    if not running_processes_found[target_name.lower()]: # Only log and set once per target
                        print(f"[{script_name}] Detected running process: '{proc.info['name']}' (PID: {proc.pid}) matching target '{target_name}'.")
                        running_processes_found[target_name.lower()] = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Ignore processes that might terminate during iteration or deny access
            continue
    return running_processes_found

def query_zephyr_node_rpc(node_url, rpc_method="get_info", params=None, timeout=10):
    """
    Queries the Zephyr node JSON-RPC endpoint for specific information or actions.
    This function constructs a standard JSON-RPC 2.0 request and handles common
    network and RPC-specific errors.

    Args:
        node_url (str): The full URL of the Zephyr node's JSON-RPC endpoint
                        (e.g., 'http://localhost:17767/json_rpc').
        rpc_method (str): The JSON-RPC method to invoke (e.g., "get_info",
                          "get_block_count"). Defaults to "get_info".
        params (dict, optional): A dictionary of parameters to pass with the RPC method.
                                 Defaults to None.
        timeout (int): The maximum number of seconds to wait for a response from
                       the node. Defaults to 10 seconds.

    Returns:
        dict: The 'result' field of the JSON-RPC response if the query is
              successful and no RPC-level error is reported. Returns None
              in case of any error (network, HTTP, JSON decoding, RPC error).
    """
    headers = {'Content-Type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "id": 1,  # A unique identifier for the RPC call
        "method": rpc_method,
        "params": params if params is not None else {}
    }
    script_name = sys.argv[0].split('/')[-1]
    print(f"[{script_name}] Attempting Zephyr node RPC query: {rpc_method} at {node_url}")

    try:
        response = requests.post(node_url, headers=headers, data=json.dumps(payload), timeout=timeout)
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
        rpc_response = response.json()

        if 'error' in rpc_response:
            print(f"[{script_name}] Zephyr RPC Error received for method '{rpc_method}': {rpc_response['error']}")
            return None
        elif 'result' in rpc_response:
            print(f"[{script_name}] Zephyr RPC Success for method '{rpc_method}'.")
            # For detailed debugging, uncomment the following line:
            # print(f"[{script_name}] RPC Result preview: {json.dumps(rpc_response['result'], indent=2)[:500]}...")
            return rpc_response['result']
        else:
            print(f"[{script_name}] Unexpected JSON-RPC response format for method '{rpc_method}'. Response: {rpc_response}")
            return None

    except requests.exceptions.Timeout:
        print(f"[{script_name}] Zephyr RPC query timed out after {timeout} seconds for method '{rpc_method}'.")
    except requests.exceptions.ConnectionError as e:
        print(f"[{script_name}] Zephyr RPC Connection Error for method '{rpc_method}': {e}")
    except requests.exceptions.HTTPError as e:
        print(f"[{script_name}] Zephyr RPC HTTP Error for method '{rpc_method}': Status {e.response.status_code} - {e.response.text.strip()}")
    except json.JSONDecodeError:
        print(f"[{script_name}] Failed to decode JSON from Zephyr RPC response for method '{rpc_method}'. Raw response: {response.text.strip()}")
    except Exception as e:
        print(f"[{script_name}] An unexpected error occurred during Zephyr RPC query for method '{rpc_method}': {type(e).__name__}: {e}")
    return None

if __name__ == "__main__":
    # --- Configuration Parameters ---
    # List of process names to detect using psutil.
    TARGET_PROCESSES = ['xmrig', 'zephyrd']

    # The JSON-RPC endpoint for the local Zephyr node.
    ZEPHYR_NODE_RPC_URL = 'http://localhost:17767/json_rpc'
    # --------------------------------

    script_name = sys.argv[0].split('/')[-1]
    print(f"\n[{script_name}] Starting Zephyr Node Ecosystem Integration Script...")

    # Task 1: Use 'psutil' to detect if 'xmrig' or 'zephyrd' is running.
    print(f"\n[{script_name}] --- Task 1: Process Monitoring (psutil) ---")
    active_processes = check_process_status(TARGET_PROCESSES)
    print(f"[{script_name}] Summary of target processes: {active_processes}")

    # Task 2: Use 'requests' to query the Zephyr node JSON-RPC.
    print(f"\n[{script_name}] --- Task 2: Zephyr Node JSON-RPC Query (requests) ---")
    node_rpc_result = query_zephyr_node_rpc(ZEPHYR_NODE_RPC_URL, "get_info")

    if node_rpc_result:
        print(f"[{script_name}] Successfully retrieved Zephyr node 'get_info' result.")
        # Example of parsing specific information from 'get_info'
        print(f"[{script_name}] Node Height: {node_rpc_result.get('height', 'N/A')}")
        print(f"[{script_name}] Node Version: {node_rpc_result.get('version', 'N/A')}")
        print(f"[{script_name}] Target Height: {node_rpc_result.get('target_height', 'N/A')}")
        print(f"[{script_name}] Is Syncing: {node_rpc_result.get('sync_info', {}).get('is_syncing', 'N/A')}")
    else:
        print(f"[{script_name}] Failed to retrieve Zephyr node information via RPC.")

    print(f"\n[{script_name}] Zephyr Node Ecosystem Integration Script completed.")
```

---
*Drafted and submitted autonomously by the Sovereign Skein Node, operating on behalf of Bill0151.*