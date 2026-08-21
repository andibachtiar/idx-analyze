import asyncio
import json
import os
import sys
import time

from curl_cffi import requests
from curl_cffi.requests import AsyncSession

# Configuration
BASE_URL = "https://www.idx.co.id/primary"
COMPANY_PROFILES_ENDPOINT = "/ListedCompany/GetCompanyProfiles"
COMPANY_DETAIL_ENDPOINT = "/ListedCompany/GetCompanyProfilesDetail"

# Headers
headers = {
    "accept": "application/json, text/plain, */*",
    "Referer": "https://www.idx.co.id/id/perusahaan-tercatat/profil-perusahaan/"
}

# File Paths (relative to the python/ directory)
DATA_DIR = os.path.join(os.path.dirname(__file__), '../data')
ALL_COMPANIES_FILE = os.path.join(DATA_DIR, 'allCompanies.json')
COMPANY_DETAILS_FILE = os.path.join(DATA_DIR, 'companyDetailsByKodeEmiten.json')

# Rate limiting/error handling constants
REQUEST_DELAY_SECONDS = 1  # Delay between successful requests to prevent hammering
ERROR_SLEEP_SECONDS = 5 * 60 # 5 minutes sleep on error, following JS example structure
CONCURRENCY_LIMIT = 5 # Number of concurrent requests

def ensure_data_dir():
    """Ensures the data directory exists."""
    os.makedirs(DATA_DIR, exist_ok=True)

async def fetch_data(session, url):
    """Generic function to fetch data from a given URL."""
    print(f"Fetching {url}...")
    try:
        # impersonate="chrome" is usually sufficient to bypass basic Cloudflare checks
        response = await session.get(
            url,
            headers=headers,
            impersonate="chrome",
            timeout=30
        )

        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Status: {response.status_code}. Successfully parsed JSON.")
                # print(json.dumps(data, indent=2)[:500] + "...")
                return data
            except json.JSONDecodeError:
                print(f"Status: {response.status_code}. Failed to decode JSON. Snippet: {response.text[:500]}")
        else:
            print(f"Status: {response.status_code}. Request failed for {url}. Snippet: {response.text[:500]}")

    except Exception as e:
        print(f"An error occurred fetching {url}: {e}")

    return None

def fetch_all_company_profiles_sync():
    """Fetches a list of all listed companies synchronously."""
    url = f"{BASE_URL}{COMPANY_PROFILES_ENDPOINT}?start=0&length=9999"
    print(f"Fetching {url}...")
    try:
        response = requests.get(
            url,
            headers=headers,
            impersonate="chrome",
            timeout=30
        )

        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Status: {response.status_code}. Successfully parsed JSON.")
                return data
            except json.JSONDecodeError:
                print(f"Status: {response.status_code}. Failed to decode JSON. Snippet: {response.text[:500]}")
        else:
            print(f"Status: {response.status_code}. Request failed. Snippet: {response.text[:500]}")

    except Exception as e:
        print(f"An error occurred: {e}")

    return None

async def fetch_company_profile_detail(session, kode_emiten, language='id-id'):
    """Fetches the company profile details for a given KodeEmiten."""
    url = f"{BASE_URL}{COMPANY_DETAIL_ENDPOINT}?KodeEmiten={kode_emiten}&language={language}"
    return await fetch_data(session, url)

def load_or_initialize_json(file_path, default_value=None):
    if default_value is None:
        default_value = {}
    """Loads JSON data from a file or returns a default value if the file does not exist."""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return json.loads(content) if content else default_value
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading {file_path}. Initializing with default. Error: {e}")
            return default_value
    return default_value

def save_json(file_path, data):
    """Saves data to a JSON file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"Successfully saved data to {os.path.basename(file_path)}")
    except IOError as e:
        print(f"Error saving data to {file_path}: {e}")

async def process_company(session, semaphore, company, index, total, kode_emiten_json):
    kode_emiten = company.get('KodeEmiten')
    nama_emiten = company.get('NamaEmiten', 'N/A')

    if not kode_emiten:
        print(f"Skipping record {index} due to missing KodeEmiten.")
        return None

    if kode_emiten in kode_emiten_json:
        print(f"[{index+1}/{total}] Skipping already processed {kode_emiten} ({nama_emiten}).")
        return None

    async with semaphore:
        print(f"[{index+1}/{total}] Fetching details for {kode_emiten} ({nama_emiten})...")
        try:
            details = await fetch_company_profile_detail(session, kode_emiten)

            if details:
                # Apply rate limit delay after a successful request to avoid hammering
                if REQUEST_DELAY_SECONDS > 0:
                    print(f"Waiting for {REQUEST_DELAY_SECONDS} seconds...")
                    await asyncio.sleep(REQUEST_DELAY_SECONDS)
                return (kode_emiten, details)
            else:
                print(f"Failed to retrieve company details for {kode_emiten}.")
                raise Exception("Failed to retrieve company details.")

        except Exception as company_error:
            print(f"Error processing {kode_emiten}: {company_error}")
            print(f"Sleeping for {ERROR_SLEEP_SECONDS/60} minutes due to error at {time.ctime()}...")
            await asyncio.sleep(ERROR_SLEEP_SECONDS)
            print(f"Woke up at {time.ctime()}. Resuming.")
            return None

async def process_companies_async(companies_to_process, kode_emiten_json):
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    processed_count = 0

    async with AsyncSession() as session:
        tasks = []
        for i, company in enumerate(companies_to_process):
            task = asyncio.create_task(process_company(session, semaphore, company, i, len(companies_to_process), kode_emiten_json))
            tasks.append(task)

        for future in asyncio.as_completed(tasks):
            result = await future
            if result:
                kode_emiten, details = result
                kode_emiten_json[kode_emiten] = details
                # Save incrementally inside the loop to ensure we don't lose progress if it crashes
                save_json(COMPANY_DETAILS_FILE, kode_emiten_json)
                processed_count += 1
                print("-----------------------------------")

    return processed_count

def scrape_company_data():
    """Orchestrates the scraping, loading, and saving of company data."""
    ensure_data_dir()

    # 1. Fetch or load all companies list
    print("--- Step 1: Fetching all company profiles list ---")
    all_companies_data = load_or_initialize_json(ALL_COMPANIES_FILE)

    if not all_companies_data or 'data' not in all_companies_data:
        # If file doesn't exist or is empty, fetch it
        all_companies_data = fetch_all_company_profiles_sync()
        if not all_companies_data or 'data' not in all_companies_data:
            print("Failed to fetch all company profiles. Aborting.")
            return

        print(f"Found {all_companies_data.get('recordsTotal', len(all_companies_data['data']))} total companies.")
        save_json(ALL_COMPANIES_FILE, all_companies_data)
    else:
        print(f"Loaded {all_companies_data.get('recordsTotal', len(all_companies_data['data']))} existing company records from {os.path.basename(ALL_COMPANIES_FILE)}")


    # 2. Fetch company details incrementally
    print("\n--- Step 2: Fetching individual company details ---")
    kode_emiten_json = load_or_initialize_json(COMPANY_DETAILS_FILE)
    companies_to_process = all_companies_data.get('data', [])

    print(f"Loaded {len(kode_emiten_json)} existing company details from {os.path.basename(COMPANY_DETAILS_FILE)}")
    print(f"Total companies in list: {len(companies_to_process)}")

    # Run the async loop
    try:
        processed_count = asyncio.run(process_companies_async(companies_to_process, kode_emiten_json))
    except Exception as e:
        print(f"An error occurred during async processing: {e}")
        processed_count = 0

    print(f"\nData collection completed. {processed_count} new companies processed.")

if __name__ == "__main__":
    scrape_company_data()
