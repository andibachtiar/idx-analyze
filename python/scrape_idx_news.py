"""
Scraper for IDX news/headlines.

Fetches the latest market news from the IDX website.
"""

import json
import os

from curl_cffi import requests

# --- Configuration ---
BASE_URL = "https://www.idx.co.id"
NEWS_ENDPOINT = "/primary/home/content"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "Referer": "https://www.idx.co.id/id/berita/berita/"
}

# File Paths (relative to the python/ directory)
DATA_DIR = os.path.join(os.path.dirname(__file__), '../data')
OUTPUT_FILE = os.path.join(DATA_DIR, 'idx_news.json')

# --- Utility Functions ---

def ensure_data_dir():
    """Ensures the data directory exists."""
    os.makedirs(DATA_DIR, exist_ok=True)

def fetch_news():
    """Fetch news from IDX website."""
    url = f"{BASE_URL}{NEWS_ENDPOINT}"
    print(f"Fetching {url}...")

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            impersonate="chrome",
            timeout=30
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            try:
                data = response.json()
                print("Successfully parsed JSON.")

                # Save to file
                ensure_data_dir()
                with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                print(f"Data saved to {OUTPUT_FILE}")

                # Print a snippet to verify
                if isinstance(data, dict):
                    preview = json.dumps(data, indent=2)[:500]
                elif isinstance(data, list):
                    preview = json.dumps(data[:3], indent=2)[:500] if len(data) > 0 else "Empty list"
                else:
                    preview = str(data)[:500]
                print(f"Preview: {preview}...")

                return data
            except json.JSONDecodeError as e:
                print(f"Failed to decode JSON: {e}")
                print(f"Response text snippet: {response.text[:500]}")
                return None
        else:
            print(f"Request failed with status {response.status_code}")
            print(f"Response snippet: {response.text[:500]}")
            return None

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

if __name__ == "__main__":
    fetch_news()
