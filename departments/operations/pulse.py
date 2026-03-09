"""
FILE: pulse.py
ROLE: The "Heartbeat" - Automation Hub
FUNCTION: Sequentially triggers the Collector, Assessor, and Finance Telemetry using bulletproof absolute paths.
VERSION: V12.1 (Self-Locating Path Resolution)
"""

import subprocess
import time
import sys
import os

# --- V12 PATH RESOLUTION ---
current_dir = os.path.dirname(os.path.abspath(__file__))
# Intelligently find the project root regardless of where pulse.py is saved
if "departments" in current_dir:
    project_root = os.path.abspath(os.path.join(current_dir, "../../"))
else:
    project_root = current_dir

def run_pulse():
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 💓 INITIATING PULSE CYCLE...")
    
    # 1. RADAR SWEEP
    print("[1/3] 📡 Intelligence: Sweeping GitHub...")
    collector_path = os.path.join(project_root, "departments", "intelligence", "collector.py")
    subprocess.run([sys.executable, collector_path], cwd=project_root)
    
    # 2. TRIAGE
    time.sleep(5)
    print("[2/3] 🧠 Operations: Triggering Assessor Triage...")
    env = os.environ.copy()
    env["PYTHONPATH"] = project_root
    subprocess.run([sys.executable, "-c", "from departments.operations.assessor import triage_targets; print(triage_targets())"], env=env, cwd=project_root)
    
    # 3. FINANCE UPDATE
    print("[3/3] 💰 Finance: Updating Telemetry & HUD...")
    telemetry_path = os.path.join(project_root, "departments", "finance", "telemetry.py")
    subprocess.run([sys.executable, telemetry_path], cwd=project_root)
    
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] ✅ PULSE COMPLETE. Sleeping for 4 hours.")

if __name__ == "__main__":
    print("🟢 MIND-SKEIN Master Pulse Controller Online.")
    # Run once immediately on startup, then enter the 4-hour loop
    while True:
        try:
            run_pulse()
            time.sleep(14400) # 4 hours
        except KeyboardInterrupt:
            print("\n🛑 Pulse Controller Shutdown Initiated.")
            sys.exit(0)
        except Exception as e:
            print(f"\n⚠️ PULSE ERROR: {e}")
            time.sleep(60)