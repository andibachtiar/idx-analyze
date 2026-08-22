"""
Web interface for idx-bei investment research platform.

Simple HTML/JS frontend for stock analysis.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Mount static files
import os

static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    """Main page with stock analysis interface."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IDX-BEI Investment Research Platform</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            color: #333;
        }
        .header {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 2rem;
            text-align: center;
        }
        .header h1 { font-size: 2rem; margin-bottom: 0.5rem; }
        .header p { opacity: 0.9; }
        .container { max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }
        .card {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }
        .card h2 { margin-bottom: 1rem; color: #1e3c72; }
        .form-group { margin-bottom: 1rem; }
        .form-group label { display: block; margin-bottom: 0.5rem; font-weight: 500; }
        .form-group input, .form-group select, .form-group textarea {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 1rem;
        }
        .btn {
            background: #2a5298;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 1rem;
            transition: background 0.2s;
        }
        .btn:hover { background: #1e3c72; }
        .results { margin-top: 1.5rem; }
        .results pre {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 4px;
            overflow-x: auto;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }
        .stat-card {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 4px;
            text-align: center;
        }
        .stat-card .value { font-size: 1.5rem; font-weight: bold; color: #2a5298; }
        .stat-card .label { font-size: 0.875rem; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <h1>IDX-BEI Investment Research Platform</h1>
        <p>AI-powered stock analysis for Indonesian stocks</p>
    </div>

    <div class="container">
        <div class="stats">
            <div class="stat-card">
                <div class="value">15</div>
                <div class="label">Phases Complete</div>
            </div>
            <div class="stat-card">
                <div class="value">600+</div>
                <div class="label">Test Cases</div>
            </div>
            <div class="stat-card">
                <div class="value">50+</div>
                <div class="label">API Endpoints</div>
            </div>
        </div>

        <div class="card">
            <h2>Stock Analysis</h2>
            <div class="form-group">
                <label for="ticker">Ticker Symbol</label>
                <input type="text" id="ticker" placeholder="e.g., BBCA, BBRI, ASII">
            </div>
            <div class="form-group">
                <label for="question">Research Question</label>
                <textarea id="question" rows="3" placeholder="What would you like to know about this stock?"></textarea>
            </div>
            <button class="btn" onclick="analyzeStock()">Analyze Stock</button>
            <div id="results" class="results"></div>
        </div>

        <div class="card">
            <h2>Available Features</h2>
            <ul style="margin-left: 1.5rem; line-height: 2;">
                <li><strong>Fundamental Analysis</strong> - ROE, margins, growth rates</li>
                <li><strong>Technical Analysis</strong> - SMA, RSI, MACD, Bollinger Bands</li>
                <li><strong>Valuation</strong> - P/E, P/B, EV/EBITDA with historical context</li>
                <li><strong>Historical Analysis</strong> - YoY growth, trends, CAGR</li>
                <li><strong>Stock Screening</strong> - Buffett, Growth, Value, Quality screens</li>
                <li><strong>Backtesting</strong> - Strategy simulation with look-ahead bias prevention</li>
                <li><strong>AI Research</strong> - LLM-powered analysis with structured reports</li>
                <li><strong>Vector Search</strong> - Semantic search over documents</li>
            </ul>
        </div>

        <div class="card">
            <h2>API Documentation</h2>
            <p>Interactive API documentation is available at:</p>
            <ul style="margin-left: 1.5rem; margin-top: 0.5rem;">
                <li><a href="/docs">Swagger UI</a></li>
                <li><a href="/redoc">ReDoc</a></li>
            </ul>
        </div>
    </div>

    <script>
        async function analyzeStock() {
            const ticker = document.getElementById('ticker').value.toUpperCase();
            const question = document.getElementById('question').value;

            if (!ticker) {
                alert('Please enter a ticker symbol');
                return;
            }

            const resultsDiv = document.getElementById('results');
            resultsDiv.innerHTML = '<p>Analyzing...</p>';

            try {
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ticker, question})
                });

                const data = await response.json();
                resultsDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
            } catch (error) {
                resultsDiv.innerHTML = '<p class="error">Error: ' + error.message + '</p>';
            }
        }
    </script>
</body>
</html>
    """


@app.get("/api/health")
async def api_health():
    """API health check."""
    return {"status": "healthy", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.web:app", host="0.0.0.0", port=8001, reload=True)
