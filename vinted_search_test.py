from curl_cffi import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Load credentials from environment variables
REAL_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
REAL_COOKIE = "_vinted_fr_session=" + os.getenv("VINTED_SESSION_COOKIE", "")
MY_BEARER = "Bearer " + os.getenv("VINTED_BEARER_TOKEN", "")


HEADERS = {
    "User-Agent": REAL_USER_AGENT,
    # PASTE YOUR FULL COOKIE HERE
    "Cookie": REAL_COOKIE,
    # PASTE YOUR BEARER HERE
    "Authorization": MY_BEARER,
    # PASTE CSRF (Optional, but good to have)
    # "X-Csrf-Token": "..."
}


if __name__ == '__main__':
    search_text = "levis 501"
    page = 1
    per_page = 10

    url = f"https://www.vinted.fr/api/v2/catalog/items?search_text={search_text}&page={page}&per_page={per_page}"

    print("🕵️‍♂️ Going Stealth Mode with curl_cffi...")

    try:
        # THE MAGIC FIX: impersonate="chrome120"
        # This makes your Python script 'speak' exactly like Chrome during the handshake.
        response = requests.get(url, headers=HEADERS, impersonate="chrome120")

        if response.status_code == 200:
            print("✅ SUCCESS! 403 Bypassed.")
            data = response.json()
            print(f"🎉 Found {len(data.get('items', []))} items")

            # Save it immediately so you never have to scrape this again for testing
            with open("level1_win.json", "w") as f:
                json.dump(data, f, indent=4)

        else:
            print(f"❌ Status: {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"💥 Error: {e}")