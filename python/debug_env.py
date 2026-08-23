"""Debug script to check environment configuration."""
import os
import sys
from pathlib import Path

# Check .env file locations
print("Checking for .env files...")
env_paths = [
    Path.cwd() / ".env",  # current directory
    Path(__file__).parent / ".env",  # same directory as this script
    Path(__file__).parent.parent / ".env",  # parent directory
]

for env_path in env_paths:
    if env_path.exists():
        print(f"  Found: {env_path}")
        with open(env_path) as f:
            content = f.read()
            # Show only non-secret lines
            for line in content.split('\n'):
                if 'KEY' not in line.upper() and 'SECRET' not in line.upper():
                    print(f"    {line}")
                elif 'KEY' in line.upper() or 'SECRET' in line.upper():
                    # Show key name but mask value
                    if '=' in line:
                        key = line.split('=')[0]
                        print(f"    {key}=***MASKED***")
    else:
        print(f"  Not found: {env_path}")

# Check environment variables
print("\nCurrent environment variables:")
print(f"  OPENAI_API_KEY: {'SET' if os.environ.get('OPENAI_API_KEY') else 'NOT SET'}")
print(f"  OPENAI_BASE_URL: {os.environ.get('OPENAI_BASE_URL', 'NOT SET')}")
print(f"  OPENAI_MODEL: {os.environ.get('OPENAI_MODEL', 'NOT SET')}")

# Try to load dotenv
try:
    from dotenv import load_dotenv
    loaded = load_dotenv()
    print(f"\ndotenv load result: {loaded}")
except ImportError:
    print("\ndotenv not installed")

# Check if we can create OpenAI client
print("\nTesting OpenAI client initialization...")
try:
    from openai import OpenAI
    api_key = os.environ.get('OPENAI_API_KEY', '')
    base_url = os.environ.get('OPENAI_BASE_URL', '')
    model = os.environ.get('OPENAI_MODEL', 'gpt-4o')

    print(f"  API Key: {'SET' if api_key else 'NOT SET'}")
    print(f"  Base URL: {base_url or 'https://api.openai.com/v1'}")
    print(f"  Model: {model}")

    if api_key:
        try:
            client = OpenAI(api_key=api_key, base_url=base_url or None)
            print("  Client initialized successfully!")
        except Exception as e:
            print(f"  Client initialization failed: {e}")
    else:
        print("  Skipping client init - no API key")

except ImportError:
    print("  OpenAI package not installed")

print("\nDone!")
