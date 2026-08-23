"""
Application Configuration Loader.

Loads and validates all configuration at startup.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment variables
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"Loaded environment from: {env_file}")
else:
    # Try parent directory
    parent_env = project_root.parent / ".env"
    if parent_env.exists():
        load_dotenv(parent_env)
        print(f"Loaded environment from: {parent_env}")
    else:
        print("Warning: No .env file found. Using default values.")

# Import and initialize configuration
from ai.config import get_config, load_and_validate, print_config_summary


def initialize_config():
    """Initialize and validate application configuration."""
    issues = load_and_validate()

    if issues:
        print("\n⚠️  Configuration Issues:")
        for issue in issues:
            print(f"   {issue}")

    return issues

if __name__ == "__main__":
    initialize_config()
    print_config_summary()
