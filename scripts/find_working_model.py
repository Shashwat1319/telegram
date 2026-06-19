import requests
import os
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

models_to_try = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-pro",
    "gemini-pro",
]

versions = ["v1", "v1beta"]

def test_model(model, version):
    url = f"https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": "Say hi"}]}]
    }
    try:
        response = requests.post(url, json=payload)
        res = response.json()
        if "candidates" in res:
            return True, None
        return False, res.get("error", {}).get("message", "Unknown error")
    except Exception as e:
        return False, str(e)

for version in versions:
    for model in models_to_try:
        print(f"Testing {model} on {version}...")
        success, error = test_model(model, version)
        if success:
            print(f"✅ WORKING: {model} on {version}")
            exit(0)
        else:
            print(f"❌ FAILED: {error}")

print("No working model found.")
