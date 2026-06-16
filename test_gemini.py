"""
test_gemini.py
--------------
Quick diagnostic script to test your Gemini API connection.
Run: python test_gemini.py

This will:
1. Verify your API key works
2. List all models available on your key
3. Test a simple generation call
"""

import os
from dotenv import load_dotenv

def main():
    load_dotenv()

    API_KEY = os.getenv("GEMINI_API_KEY", "")
    MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    print("=" * 60)
    print("  Gemini API Diagnostic Tool")
    print("=" * 60)
    print(f"  API Key : {'*' * (len(API_KEY) - 8) + API_KEY[-8:] if len(API_KEY) > 8 else 'NOT SET'}")
    print(f"  Model   : {MODEL}")
    print("=" * 60)

    if not API_KEY or API_KEY == "your_gemini_api_key_here":
        print("\nERROR: GEMINI_API_KEY is not set in your .env file")
        print("   Get a free key at: https://aistudio.google.com/app/apikey")
        exit(1)

    try:
        import google.generativeai as genai
        print(f"\n✅ SDK version: {genai.__version__}")
    except ImportError:
        print("\n❌ google-generativeai not installed. Run: pip install google-generativeai --upgrade")
        exit(1)

    # --- Step 1: Configure API ---
    genai.configure(api_key=API_KEY)
    print("\n📋 STEP 1: Listing available models on your API key...")
    print("-" * 60)

    available = []
    try:
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods:
                available.append(m.name)
                print(f"   ✅ {m.name}")
        if not available:
            print("   ⚠️  No models found — check if your API key is valid")
    except Exception as e:
        print(f"   ❌ Could not list models: {e}")
        print("   This usually means your API key is invalid.")
        exit(1)

    print(f"\n   Total: {len(available)} models available")

    # --- Step 2: Find the right model name ---
    print(f"\n📋 STEP 2: Finding best model to use...")
    print("-" * 60)

    # Preferred models in priority order
    preferred = []
    if MODEL:
        if not MODEL.startswith("models/"):
            preferred.append(f"models/{MODEL}")
        else:
            preferred.append(MODEL)

    preferred.extend([
        "models/gemini-2.5-flash",
        "models/gemini-2.5-pro",
        "models/gemini-2.0-flash",
        "models/gemini-2.0-flash-exp",
        "models/gemini-1.5-flash-latest",
        "models/gemini-1.5-flash",
        "models/gemini-1.5-pro-latest",
        "models/gemini-pro",
    ])

    chosen_model = None
    for pref in preferred:
        if pref in available:
            chosen_model = pref.replace("models/", "")  # strip prefix for GenerativeModel
            print(f"   ✅ Found preferred model: {pref}")
            break

    if not chosen_model:
        # Use the first available model
        chosen_model = available[0].replace("models/", "")
        print(f"   ℹ️  Using first available: {available[0]}")

    print(f"\n   👉 Recommended GEMINI_MODEL value: {chosen_model}")

    # --- Step 3: Test generation ---
    print(f"\n📋 STEP 3: Testing generation with '{chosen_model}'...")
    print("-" * 60)

    try:
        model = genai.GenerativeModel(
            model_name=chosen_model,
            generation_config={"temperature": 0.1, "max_output_tokens": 100},
        )
        response = model.generate_content("Say hello in one sentence.")
        print(f"   ✅ Generation successful!")
        print(f"   Response: {response.text.strip()}")
    except Exception as e:
        print(f"   ❌ Generation failed: {type(e).__name__}: {e}")
        exit(1)

    # --- Summary ---
    print("\n" + "=" * 60)
    print("  ✅ ALL CHECKS PASSED")
    print("=" * 60)
    print(f"\n  Update your .env file:")
    print(f"  GEMINI_MODEL={chosen_model}")
    print(f"\n  Then restart: python run.py")
    print()

if __name__ == "__main__":
    main()
