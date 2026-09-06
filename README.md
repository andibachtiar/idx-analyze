# IDX-BEI Investment Research Platform

Platform riset investasi saham **Indonesia (IDX/BEI)** — Python + FastAPI + PostgreSQL + Neo4j.
Mengumpulkan data dari IDX/Yahoo, menganalisis secara **deterministik** (fundamental, teknis, valuasi, screener), lalu menambahkan interpretasi AI — semua angka bersumber dari database, bukan karangan LLM.

> 📚 **Semua dokumentasi kini terpusat di [`docs/`](docs/README.md).**
> Mulai dari [dokumentasi](docs/README.md) → [quickstart](docs/quickstart.md) → [arxivitektur](docs/architecture.md).

---

## Fitur inti

- **Data pipeline** (`run_pipeline.py`): scraping idempotent & incremental ke PostgreSQL, terjadwal via `scheduler.py`, cache read TTL.
- **Analisis deterministik**: fundamental, teknis (SMA/EMA/RSI/MACD/Bollinger), valuasi, screener (Buffett/Value/Growth/Quality/Dividend/Technical), backtest.
- **AI layered**: tools + researcher + report + research memory + RAG + prompt integration (fundamental, technical, screener, valuation, catalyst, competitor, institutional, industry-map, financial-report).
- **UI/UX (Phase 25)**: dashboard, halaman per saham (grafik harga candle/line dengan indikator, profil, key stats, fundamental chart, analisa, berita, AI chat, research memory), screener, compare, watchlist + alert harga, export CSV.
- **Relasi**: Neo4j untuk company/director/shareholder graph.

## Tech stack

Python 3.13 · FastAPI · PostgreSQL · Neo4j (opsional) · yfinance · pandas · Chart.js (CDN) · `uv`.

## Mulai cepat

```bash
cd python
uv sync
# jalankan pipeline (perusahaan → harga → rasio → enrichment → berita)
uv run python run_pipeline.py --all
# kunjungi API & UI
uv run python -m uvicorn api.main:app --reload --port 8000
```

Buka `http://localhost:8000`. Detail lengkap di [docs/quickstart.md](docs/quickstart.md).

## Struktur singkat

| Path        | Isi                                                            |
| ----------- | -------------------------------------------------------------- |
| `python/`   | Backend (scrapers, analysis, ai, api, database, web)           |
| `docs/`     | **Semua dokumentasi** (lihat [docs/README.md](docs/README.md)) |
| `prompt/`   | Spesifikasi prompt (sumber)                                    |
| `AGENTS.md` | Aturan & roadmap kerja untuk agent AI                          |

## Lisensi & disclaimer

Edukasi & riset saja. **Bukan nasihat investasi.** Semua angka dari data, keputusan akhir di tangan pengguna.
