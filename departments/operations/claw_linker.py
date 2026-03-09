import os
import sys
import subprocess
import site
import shutil

"""
FILE: departments/operations/claw_linker.py
ROLE: Identity Bridge & Auditor
FUNCTION: Audits the existing link and prepares for Phase 3 (Extraction).
VERSION: V12.5 (Explorer Integration)
"""

def run_command(cmd_list):
    try:
        potential_paths = [
            os.path.join(os.path.dirname(sys.executable), 'Scripts', 'clawrtc.exe'),
            os.path.join(os.path.dirname(sys.executable), 'bin', 'clawrtc'),
            os.path.join(site.getuserbase(), 'Scripts', 'clawrtc.exe'),
            os.path.expandvars(r'%APPDATA%\Python\Python314\Scripts\clawrtc.exe'),
            os.path.expandvars(r'%APPDATA%\Python\Scripts\clawrtc.exe'),
            r"C:\Python314\Scripts\clawrtc.exe"
        ]
        executable = next((p for p in potential_paths if os.path.exists(p)), shutil.which("clawrtc"))
        if not executable: return "Binary not found"
        result = subprocess.run([executable] + cmd_list, capture_output=True, text=True, shell=(os.name == 'nt'))
        return result.stdout if result.returncode == 0 else result.stderr
    except Exception as e: return str(e)

if __name__ == "__main__":
    print("🧠 MIND-SKEIN: Pre-Flight Identity Audit...")
    
    rtc_wallet = run_command(["wallet", "show"])
    base_link = run_command(["wallet", "coinbase", "show"])
    
    print("\n[AUDIT: NATIVE IDENTITY]")
    print(rtc_wallet.strip())
    
    # Extract the RTC address for the manual explorer link
    import re
    rtc_address_match = re.search(r'RTC[a-zA-Z0-9]+', rtc_wallet)
    rtc_address = rtc_address_match.group(0) if rtc_address_match else None
    
    print("\n[AUDIT: BASE L2 BRIDGE]")
    print(base_link.strip())
    
    print("\n" + "="*60)
    print("🛰️  DIRECTOR'S EXTRACTION GUIDE")
    print("="*60)
    
    if rtc_address:
        print(f"1. MANUAL VERIFICATION: If the CLI cannot reach the network,")
        print(f"   go to: https://rustchain.org/explorer/address/{rtc_address}")
        print(f"   This is the definitive truth of your RTC balance.")
    
    print("\n2. THE BRIDGE (BOOTTUBE):")
    print("   In your screenshot, you are on the 'Solana' tab.")
    print("   CLICK the 'Base (Ethereum L2)' button in the top-left.")
    print("   This will switch the Bridge to use your 0xFb39... address.")
    
    print("\n3. THE EXTRACTION FLOW:")
    print("   Native RTC (on RustChain) -> BoTTube Bridge -> wRTC (on Base L2).")
    print("   Once bridged, your Rabby Mobile 'Watch Mode' will alert you.")
    print("="*60)
    
    if "RTC" in rtc_wallet and "0xFb39" in base_link:
        print("\n✅ SYSTEM STATUS: INTEGRITY VERIFIED.")
        print("Your bridge is active. You are ready to claim the Strength Multiplier.")
    else:
        print("\n❌ SYSTEM STATUS: DISCONNECTED.")
        print("Re-run 'python departments/operations/claw_linker.py' with LINK_WALLET = True.")