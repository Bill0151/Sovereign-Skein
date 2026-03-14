"""
FILE: pulse.py
ROLE: The "Heartbeat" & Daemon Manager
FUNCTION: Launches background nodes (Assessor/Executor) and triggers the 4-hour GitHub & DeFi cycles.
VERSION: V14.1 (Integrated Yield Engine)
"""

import subprocess
import time
import sys
import os
import atexit

# --- PATH RESOLUTION ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if "departments" in current_dir:
    project_root = os.path.abspath(os.path.join(current_dir, "../../"))
else:
    project_root = current_dir

daemons = []

def cleanup():
    """Ensures background nodes are killed if the Director stops the script."""
    print("\n🛑 Shutting down background nodes...")
    for p in daemons:
        p.terminate()

atexit.register(cleanup)

def launch_daemons():
    """Spawns the continuous background loops for C2 and Execution."""
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 🚀 LAUNCHING BACKGROUND DAEMONS...")
    
    env = os.environ.copy()
    env["PYTHONPATH"] = project_root
    
    # 1. Launch Assessor (Telegram C2 Link)
    assessor_path = os.path.join(project_root, "departments", "operations", "assessor.py")
    if os.path.exists(assessor_path):
        daemons.append(subprocess.Popen([sys.executable, assessor_path], env=env, cwd=project_root))
    
    # 2. Launch Executor (Strike Node)
    executor_path = os.path.join(project_root, "departments", "operations", "executor.py")
    if os.path.exists(executor_path):
        daemons.append(subprocess.Popen([sys.executable, executor_path], env=env, cwd=project_root))
    
    time.sleep(2) # Give them a moment to spin up

def run_pulse():
    """The 4-hour chronological Radar, Treasury, and Telemetry sweep."""
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 💓 INITIATING 4-HOUR PULSE CYCLE...")
    
    env = os.environ.copy()
    env["PYTHONPATH"] = project_root
    
    # --- PHASE 1: GITHUB SOURCING ---
    print("[1/4] 📡 Intelligence: Sweeping GitHub...")
    collector_path = os.path.join(project_root, "departments", "intelligence", "collector.py")
    if os.path.exists(collector_path):
        subprocess.run([sys.executable, collector_path], env=env, cwd=project_root)
    
    time.sleep(5)
    
    # --- PHASE 2: GITHUB TRIAGE ---
    print("[2/4] 🧠 Operations: Triggering Assessor Triage...")
    subprocess.run([sys.executable, "-c", "from departments.operations.assessor import triage_targets; print(triage_targets())"], env=env, cwd=project_root)
    
    # --- PHASE 3: DEFI YIELD ENGINE (NEW) ---
    print("[3/4] 🏦 Finance: Executing DeFi Yield Engine...")
    yield_engine_path = os.path.join(project_root, "departments", "finance", "yield_engine.py")
    if os.path.exists(yield_engine_path):
        subprocess.run([sys.executable, yield_engine_path], env=env, cwd=project_root)
    else:
        print("   ⚠️ Yield Engine script not found. Skipping DeFi pulse.")
    
    # --- PHASE 4: HUD UPDATES ---
    print("[4/4] 💰 Finance: Updating Telemetry & HUD...")
    telemetry_path = os.path.join(project_root, "departments", "finance", "telemetry.py")
    if os.path.exists(telemetry_path):
        subprocess.run([sys.executable, telemetry_path], env=env, cwd=project_root)
    
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] ✅ PULSE COMPLETE. Sleeping for 4 hours.")

if __name__ == "__main__":
    print("🟢 MIND-SKEIN Master Pulse Controller Online.")
    
    # Launch the persistent background listeners
    launch_daemons()
    
    # Enter the 4-hour cron loop
    while True:
        try:
            run_pulse()
            time.sleep(14400) # 4 hours
        except KeyboardInterrupt:
            # Cleanup is handled automatically by atexit
            sys.exit(0)
        except Exception as e:
            print(f"\n⚠️ PULSE ERROR: {e}")
            time.sleep(60)