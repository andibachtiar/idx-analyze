"""
Scraper for IDX index summary data.

Fetches daily trading summary and index performance from the IDX website.
"""

import json
import os

from curl_cffi import requests

# --- Configuration ---
BASE_URL = "https://www.idx.co.id"
INDEX_SUMMARY_ENDPOINT = "/primary/TradingSummary/GetIndexSummary"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
}

# File Paths (relative to the python/ directory)
DATA_DIR = os.path.join(os.path.dirname(__file__), '../data')
OUTPUT_FILE = os.path.join(DATA_DIR, 'index_summary.json')

# --- Utility Functions ---

def ensure_data_dir():
    """Ensures the data directory exists."""
    os.makedirs(DATA_DIR, exist_ok=True)

def fetch_index_summary():
    """Fetch index summary data from IDX website."""
    params = "length=9999&start=0"
    url = f"{BASE_URL}{INDEX_SUMMARY_ENDPOINT}?{params}"
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

                # Save to file in data directory
                ensure_data_dir()
                with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                print(f"Data saved to {OUTPUT_FILE}")

                # Print a snippet to verify
                preview = str(data)[:200]
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
    fetch_index_summary()
