"""
Web interface for idx-bei investment research platform.

This module is kept for backward compatibility.
The main application is in api/main.py with both API and web interface.
"""

from __future__ import annotations

# For backward compatibility, import the main app
from api.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
