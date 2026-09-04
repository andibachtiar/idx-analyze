"""
Scraper for IDX news.

Fetches news/announcements from the IDX NewsAnnouncement API and persists
them to PostgreSQL. Raw JSON is kept only when SCRAPER_SAVE_JSON=true.
"""

from __future__ import annotations

import json
import os
from urllib.parse import urlencode

from curl_cffi import requests

from database.scraper_store import ScraperDatabase, save_raw_json

# --- Configuration ---
# Endpoint and parameters captured from the idx.com news page (fetch network).
BASE_URL = "https://idx.co.id"
NEWS_ENDPOINT = "/primary/NewsAnnouncement/GetNewsSearch"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "referer": "https://idx.co.id/id/berita/berita/",
}

# File Paths (relative to the python/ directory)
DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")
OUTPUT_FILE = os.path.join(DATA_DIR, "idx_news.json")

# How many records to request per page.
PAGE_SIZE = 100


def build_url(page_number: int = 1) -> str:
    """Build the news search URL with the IDX fetch-network parameters."""
    params = {
        "locale": "id-id",
        "pageNumber": page_number,
        "pageSize": PAGE_SIZE,
        "isHeadline": 0,
    }
    return f"{BASE_URL}{NEWS_ENDPOINT}?{urlencode(params)}"


def fetch_page(page_number: int = 1) -> dict | None:
    """Fetch one page of news records."""
    url = build_url(page_number)
    print(f"Fetching {url}...")

    response = requests.get(url, headers=HEADERS, impersonate="chrome", timeout=30)
    print(f"Status Code: {response.status_code}")

    if response.status_code != 200:
        print(f"Request failed with status {response.status_code}")
        print(f"Response snippet: {response.text[:500]}")
        return None

    try:
        return response.json()
    except json.JSONDecodeError as exc:
        print(f"Failed to decode JSON: {exc}")
        print(f"Response text snippet: {response.text[:500]}")
        return None


def extract_url(item: dict) -> str | None:
    """Derive the news URL from the Links[].Href field if present."""
    links = item.get("Links")
    if isinstance(links, list):
        for link in links:
            if isinstance(link, dict):
                href = link.get("Href")
                if href:
                    return str(href)
    return None


def fetch_news() -> list:
    """Fetch all news pages and persist them to PostgreSQL."""
    all_records = []
    page = 1

    while True:
        data = fetch_page(page)
        if not data:
            break

        # The GetNewsSearch response wraps records under the "Items" key.
        records = data.get("Items") if isinstance(data, dict) else None
        if not isinstance(records, list) or not records:
            # Diagnostic fallback: reveal the shape when the container changes.
            if isinstance(data, dict):
                print(f"  Response top-level keys: {list(data.keys())}")
                for key, value in data.items():
                    if isinstance(value, list):
                        print(f"  List field '{key}' with {len(value)} items")
            print("No more news records in the response.")
            break

        all_records.extend(records)
        print(f"Retrieved {len(records)} records from page {page} (total collected: {len(all_records)})")

        # Stop when the returned page has fewer items than requested (last page).
        if len(records) < PAGE_SIZE:
            break
        page += 1

    if not all_records:
        print("No news records were collected.")
        return []

    # Keep raw response as backup only when explicitly enabled.
    save_raw_json(OUTPUT_FILE, {"Items": all_records})

    try:
        with ScraperDatabase() as store:
            imported = store.insert_news(all_records)
        print(f"Persisted {imported} news records to PostgreSQL")
    except Exception as exc:
        print(f"PostgreSQL persistence failed: {exc}")
        raise

    return all_records


if __name__ == "__main__":
    fetch_news()
