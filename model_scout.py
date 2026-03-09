"""
FILE: model_scout.py
PURPOSE: Forensics. Use this to find the exact model strings allowed by your API key.
"""
import os
import sys
from google import genai
from dotenv import load_dotenv

# --- V12 PATH RESOLUTION ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if "departments" in current_dir:
    project_root = os.path.abspath(os.path.join(current_dir, "../../"))
else:
    project_root = current_dir 

env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

api_key = os.getenv("GEMINI_API_KEY")

print(f"📂 System: Searching for .env at {env_path}")

if not api_key:
    print("❌ ERROR: GEMINI_API_KEY not found.")
else:
    masked_key = f"{api_key[:8]}...{api_key[-4:]}"
    print(f"🔑 Key Detected: {masked_key}")
    
    try:
        client = genai.Client(api_key=api_key)
        print("📡 Querying ALL available models (Unfiltered)...")
        print("-" * 60)
        
        models_found = 0
        # We are removing all filters. If Google sees a model, we print it.
        for m in client.models.list():
            # Get the internal name (e.g., 'models/gemini-1.5-flash')
            full_name = getattr(m, 'name', 'Unknown')
            # Get the display name (e.g., 'Gemini 1.5 Flash')
            display = getattr(m, 'display_name', 'No Display Name')
            # Extract supported methods for diagnostic purposes
            methods = getattr(m, 'supported_methods', []) or []
            
            clean_name = full_name.replace('models/', '')
            
            print(f"📦 MODEL: {clean_name}")
            print(f"   Name: {display}")
            print(f"   Methods: {', '.join(methods) if methods else 'None listed'}")
            print("-" * 30)
            models_found += 1
        
        if models_found == 0:
            print("⚠️ ZERO MODELS RETURNED. This usually means:")
            print("1. Your API Key project has no enabled models in the Google Cloud Console.")
            print("2. You are using a 'restricted' key that hasn't been provisioned yet.")
        else:
            print(f"💡 Found {models_found} models total.")
            print("👉 Copy any string after 'MODEL:' (e.g., gemini-1.5-flash) and paste it into executor.py")
            
    except Exception as e:
        print(f"❌ SCOUT ERROR: {e}")