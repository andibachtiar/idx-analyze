import json
import os
import sys
import time
from urllib.parse import urlencode

from curl_cffi import requests

from database.scraper_store import ScraperDatabase, save_raw_json

# --- Configuration ---
BASE_URL = "https://www.idx.co.id/primary/DigitalStatistic/GetApiDataPaginated"

QUERY_PARAMS = {
    "urlName": "LINK_FINANCIAL_DATA_RATIO",
    "periodQuarter": 4,
    "periodYear": 2024,
    "type": "yearly",
    "isPrint": "false",  # Must be string for URL encoding
    "cumulative": "false", # Must be string for URL encoding
    "pageSize": 100,
    "orderBy": "",
    "search": ""
}

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "referer": "https://www.idx.co.id/id/data-pasar/laporan-statistik/digital-statistic/monthly/financial-report-and-ratio-of-listed-companies/financial-data-and-ratio"
}

# File Paths (relative to the python/ directory)
DATA_DIR = os.path.join(os.path.dirname(__file__), '../data')
OUTPUT_FILE = os.path.join(DATA_DIR, 'financial_ratio.json')

# Rate limiting/error handling constants
SUCCESS_DELAY_SECONDS = 1
RATE_LIMIT_SLEEP_SECONDS = 30 # 30 seconds wait if rate limited (429)

# --- Utility Functions ---

def ensure_data_dir():
    """Ensures the data directory exists."""
    os.makedirs(DATA_DIR, exist_ok=True)

def build_url(page_number):
    """Combines BASE_URL with query parameters, including the dynamic page_number."""
    params = {
        **QUERY_PARAMS,
        "pageNumber": page_number
    }
    return f"{BASE_URL}?{urlencode(params)}"

def fetch_data(url):
    """Generic function to fetch data from a given URL using curl_cffi."""
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            impersonate="chrome",
            timeout=30
        )

        status_code = response.status_code

        if status_code == 200:
            try:
                data = response.json()
                print(f"Status: {status_code}. Successfully parsed JSON.")
                return data
            except json.JSONDecodeError:
                print(f"Status: {status_code}. Failed to decode JSON. Snippet: {response.text[:500]}")
        elif status_code == 429:
            print(f"Status: {status_code}. Rate limit hit.")
            raise requests.RequestsError("Rate Limit (429) Hit")
        else:
            print(f"Status: {status_code}. Request failed. Snippet: {response.text[:500]}")

    except requests.RequestsError as e:
        # Re-raise for the scraper to catch and handle rate limit separately
        if "Rate Limit (429) Hit" in str(e):
            raise
        print(f"A request error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    return None

def save_json(file_path, data):
    """Persist raw response only when SCRAPER_SAVE_JSON=true."""
    save_raw_json(file_path, data)
    if os.getenv("SCRAPER_SAVE_JSON", "false").lower() == "true":
        print(f"Raw data saved to {file_path}")

# --- Main Scraper ---

def scrape_financial_data():
    """Fetches all pages of financial ratio data and saves the combined result."""
    ensure_data_dir()

    page_number = 1
    has_more_data = True
    all_data = []

    print('Starting financial ratio data collection...')

    while has_more_data:
        try:
            print(f"Fetching page {page_number}...")
            url = build_url(page_number)

            data = fetch_data(url)

            if data and data.get('data') and len(data['data']) > 0:
                page_records = data['data']
                all_data.extend(page_records)
                print(f"Retrieved {len(page_records)} records from page {page_number}. Total collected: {len(all_data)}")
                page_number += 1

                # Add delay to respect rate limits
                time.sleep(SUCCESS_DELAY_SECONDS)
            else:
                has_more_data = False
                print('No more data available or fetch failed.')

        except requests.RequestsError:
            # Handle explicit rate limit hit (429)
            print(f"Rate limit hit. Waiting for {RATE_LIMIT_SLEEP_SECONDS} seconds before retrying...")
            time.sleep(RATE_LIMIT_SLEEP_SECONDS)
        except Exception as e:
            print(f"Fatal error during scraping: {e}")
            has_more_data = False # Stop on other unexpected errors

    # Save combined data outside the loop
    if all_data:
        combined_data = {
            "totalRecords": len(all_data),
            "data": all_data
        }
        save_json(OUTPUT_FILE, combined_data)
        try:
            with ScraperDatabase() as store:
                imported = store.upsert_financial_ratios(all_data)
            print(f"Persisted {imported} financial ratio records to PostgreSQL")
        except Exception as exc:
            print(f"PostgreSQL persistence failed: {exc}")
            raise
    else:
        print("No data was collected to save.")

if __name__ == "__main__":
    scrape_financial_data()
