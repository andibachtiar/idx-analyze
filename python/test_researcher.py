"""Test script to debug researcher initialization."""
import os
import sys
from pathlib import Path

print("=" * 60)
print("Testing Researcher Initialization")
print("=" * 60)

# Check current directory
print(f"\nCurrent working directory: {Path.cwd()}")

# Check if .env exists in various locations
env_paths = [
    Path.cwd() / ".env",
    Path.cwd().parent / ".env",
    Path(__file__).parent / ".env",
    Path(__file__).parent.parent / ".env",
]

print("\nChecking for .env files:")
for p in env_paths:
    exists = p.exists()
    print(f"  {p}: {'EXISTS' if exists else 'NOT FOUND'}")
    if exists:
        print(f"    -> Will use this path")

# Try to import and create researcher
print("\n" + "=" * 60)
print("Importing AIResearcher...")
print("=" * 60)

try:
    from ai.researcher import AIResearcher

    print("\nCreating researcher instance...")
    researcher = AIResearcher()

    print(f"\nResearcher state:")
    print(f"  api_key: {'SET' if researcher.api_key else 'NOT SET'}")
    print(f"  model: {researcher.model}")
    print(f"  base_url: {researcher.base_url}")
    print(f"  client: {researcher.client}")
    print(f"  client is None: {researcher.client is None}")

    if researcher.client is not None:
        print("\n✓ Client initialized successfully!")
        print(f"  Model: {researcher.model}")
        print(f"  Base URL: {researcher.base_url}")
    else:
        print("\n✗ Client is None - will use mock responses")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test complete")
print("=" * 60)
