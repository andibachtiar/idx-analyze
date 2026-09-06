# API Reference — IDX-BEI Research Platform

FastAPI backend di `python/api/main.py`. Base URL lokal: `http://localhost:8000`.

> Ringkasan endpoint berdasarkan kode aktual. Untuk format request/response lengkap,
> lihat `python/api/schemas.py`.

---

## Health & SPA

| Method | Path              | Deskripsi                                     |
| ------ | ----------------- | --------------------------------------------- |
| GET    | `/health`         | Status layanan + fase yang selesai            |
| GET    | `/`               | SPA dashboard (HTML)                          |
| GET    | `/stock/{ticker}` | SPA halaman saham (dapat di-bookmark/refresh) |

## Pasar & Saham

| Method | Path                      | Deskripsi                                         |
| ------ | ------------------------- | ------------------------------------------------- |
| GET    | `/stocks`                 | Semua saham + harga terakhir + perubahan harian   |
| GET    | `/stocks/{ticker}`        | Profil + kuotasi + key statistics                 |
| GET    | `/stocks/{ticker}/price`  | Harga terakhir                                    |
| GET    | `/stocks/{ticker}/prices` | Riwayat OHLCV (mendukung `start`/`end`/`limit`)   |
| GET    | `/compare?tickers=...`    | Perbandingan metrik side-by-side (maks. 4 ticker) |

## Analisa (tab di halaman saham)

| Method | Path                                  | Deskripsi                                                     |
| ------ | ------------------------------------- | ------------------------------------------------------------- |
| GET    | `/stocks/{ticker}/fundamentals`       | Analisis fundamental deterministik                            |
| GET    | `/stocks/{ticker}/technical`          | Indikator teknis (SMA/EMA/RSI/MACD/Bollinger)                 |
| GET    | `/stocks/{ticker}/valuation`          | Valuasi (P/E, P/B, dst.) + harga real                         |
| GET    | `/stocks/{ticker}/historical`         | Analisis historis                                             |
| GET    | `/stocks/{ticker}/financials/history` | Riwayat `financial_ratios` multi-periode (grafik fundamental) |

## News & Event

| Method | Path                      | Deskripsi                            |
| ------ | ------------------------- | ------------------------------------ |
| GET    | `/news`                   | Berita terbaru (opsional `?ticker=`) |
| GET    | `/stocks/{ticker}/news`   | Berita per saham                     |
| GET    | `/stocks/{ticker}/events` | Corporate event hasil klasifikasi    |

## Favorit & Watchlist Alert

| Method | Path                        | Deskripsi                                                |
| ------ | --------------------------- | -------------------------------------------------------- |
| GET    | `/favorites`                | Daftar ticker favorit                                    |
| POST   | `/favorites/{ticker}`       | Tambah favorit (idempoten)                               |
| DELETE | `/favorites/{ticker}`       | Hapus favorit                                            |
| GET    | `/favorites/details`        | Favorit + konfigurasi alert + harga terakhir             |
| GET    | `/favorites/alerts`         | Alert yang targetnya tersentuh                           |
| POST   | `/favorites/{ticker}/alert` | Set alert harga (`alert_price`, `direction` above/below) |
| DELETE | `/favorites/{ticker}/alert` | Hapus alert harga                                        |

## Screener & Backtest

| Method | Path                  | Deskripsi                                         |
| ------ | --------------------- | ------------------------------------------------- |
| POST   | `/screen`             | Screener (preset atau filter kustom) dari data DB |
| POST   | `/ai/screen-analysis` | Screening deterministik + interpretasi LLM        |
| POST   | `/backtest`           | Backtest strategi                                 |

## AI / Prompt

| Method | Path                          | Deskripsi                                                           |
| ------ | ----------------------------- | ------------------------------------------------------------------- |
| POST   | `/ai/analyze`                 | Laporan riset lengkap (AIResearcher)                                |
| POST   | `/ai/analyze-stream`          | Chat streaming per-saham (SSE: `status` → `chunk` → `done`/`error`) |
| POST   | `/ai/compare`                 | Perbandingan AI antar saham                                         |
| POST   | `/ai/valuation`               | Valuasi multi-metode                                                |
| POST   | `/ai/technical`               | Interpretasi teknis (LLM)                                           |
| POST   | `/ai/fundamental`             | Snapshot fundamental + Signal Output (opsional LLM)                 |
| POST   | `/ai/catalyst`                | Katalis/event                                                       |
| POST   | `/ai/competitor`              | Analisis kompetitor (moat, Five Forces)                             |
| POST   | `/ai/institutional-ownership` | Kepemilikan institusional                                           |
| POST   | `/ai/industry-map`            | Peta industri / value chain                                         |
| POST   | `/ai/financial-report`        | Analisis laporan keuangan                                           |
| POST   | `/ai/validate-thesis`         | Validasi thesis                                                     |

## Dokumen / RAG

| Method | Path                | Deskripsi                      |
| ------ | ------------------- | ------------------------------ |
| POST   | `/documents/add`    | Tambah dokumen ke vector store |
| POST   | `/documents/search` | Cari dokumen (RAG)             |

---

## Catatan

- **Data-correctness**: angka dimuat dari PostgreSQL (deterministik), AI hanya menginterpretasi.
- **Cache**: metode baca loader di-cache TTL (`DATA_CACHE_TTL`); `scheduler.py` memanggil `clear_cache()` setelah pipeline.
- **Streaming AI (`/ai/analyze-stream`)**: Server-Sent Events `event: status` (fase `preparing`/`collecting`/`generating`) → `event: chunk` (token) → `event: done`/`event: error`. Frontend mem-parsing ini untuk menampilkan proses berpikir AI secara real-time.
- **Respons**: banyak endpoint melewati `_json_safe()` untuk menormalkan `date`/`Decimal`/`NaN`.
