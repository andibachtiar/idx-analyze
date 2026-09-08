# Roadmap UI/UX & Fitur — IDX-BEI Investment Research Platform

> **Fase:** 25 — UI/UX Enhancement (iterasi selesai)
> **Diperbarui:** 2026-09-05
> **Status:** Dashboard & Stock Page (Iterasi 1) ✓ · Candlestick + Indikator + Routing (Iterasi 2) ✓ · Screener + Compare (Iterasi 3) ✓ · News UI + AI Chat + Export CSV (Iterasi 4) ✓ · Grafik Fundamental (Iterasi 5) ✓ · Screener AI (Iterasi 6) ✓ · Research Memory (Iterasi 7) ✓ · Watchlist + Alert Harga (Iterasi 8) ✓ · Candle/Line toggle ✓

> **Status data & screen:** semua preset screen (Buffett/Value/Growth/Quality/Dividend/Technical) berfungsi dengan data nyata setelah backfill harga + normalisasi unit.

## 1. Visi UI

Membangun antarmuka riset saham IDX yang menampilkan data **deterministik** lebih dulu
(harga, fundamental, teknis, valuasi) sebagai fondasi, lalu menambahkan interpretasi AI
di atasnya. UI harus menjawab:

> "Saham favorit saya naik/turun berapa hari ini? Apa fundamental & teknisnya?"

Bukan menggantikan keputusan investor, tapi menyediakan bukti yang bisa ditelusuri.

### Prinsip Desain

- **Data-first**: angka dari PostgreSQL, bukan dihitung di frontend atau dikarang AI.
- **Gradually disclose**: ringkasan → detail → analisis AI.
- **Dark, dense & readable**: cocok untuk layar analisis; hindari video-game aesthetic.
- **Responsif**: grid fleksibel, fallback 1 kolom di layar sempit.
- **No auth keamanan untuk sekarang**: dashboard internal; layering keamanan menyusul.

---

## 2. Halaman yang Sudah Dibangun (Iterasi 1)

### 2.1 Dashboard — `/`

Fitur:

| Bagian            | Deskripsi                                                                     | Sumber Data              |
| ----------------- | ----------------------------------------------------------------------------- | ------------------------ |
| Statistik Ringkas | Total emiten, yang punya harga, advancers, decliners                          | `/stocks`                |
| Saham Favorit     | Kartu favorit dengan harga & perubahan harian, klik → detail saham            | `/favorites` + `/stocks` |
| Semua Saham       | Tabel seluruh emiten (ticker, nama, sektor, harga, % change, volume, tanggal) | `/stocks`                |
| Pencarian         | Pencarian cepat header (Enter membuka halaman saham)                          | client-side              |
| Filter Sektor     | Filter chip berdasarkan sektor                                                | client-side              |

**Interaksi:**

- Klik baris / kartu → buka halaman per saham
- Klik ★ → toggle favorit (POST/DELETE `/favorites/{ticker}`)

### 2.2 Halaman Per Saham — tab di dalam dashboard (`openStock(ticker)`)

Satu halaman, 4 tab:

| Tab           | Konten                                                                     | API                             |
| ------------- | -------------------------------------------------------------------------- | ------------------------------- |
| **Harga**     | Grafik garis harga penutupan (Chart.js), kontrol rentang 3M/6M/1Y/2Y/Semua | `/stocks/{ticker}/prices`       |
| **Profil**    | Nama, sektor, industri, papan, tanggal listing                             | `/stocks/{ticker}`              |
| **Key Stats** | P/E, P/B, EV/EBITDA, ROE, margin, debt/equity, dll.                        | `/stocks/{ticker}` (`metrics`)  |
| **Analisa**   | Fundamental                                                                | `/stocks/{ticker}/fundamentals` |
|               | Technical                                                                  | `/stocks/{ticker}/technical`    |
|               | Valuation                                                                  | `/stocks/{ticker}/valuation`    |

Header detail menampilkan: ticker, nama, harga besar, tanggal + volume, tombol favorit.

### 2.3 Grafik Candlestick + Indikator (Iterasi 2)

- **Candlestick OHLC** menggantikan line chart (`chartjs-chart-financial` + `chartjs-adapter-date-fns`).
- **Overlay indikator** (dihitung client-side dari OHLCV):
  - SMA 20 / 50 / 200 (toggle)
  - Bollinger Bands (20, 2σ)
- **Volume sub-chart** di bawah grafik, warna bar hijau/merah mengikuti arah hari.
- **Toggle indikator** di `#indicatorControls`; rentang 3M/6M/1Y/2Y/Semua tetap ada.

### 2.4 Routing URL (Iterasi 2)

- Halaman saham kini memiliki URL canonical `/stock/{ticker}` (bisa di-bookmark/share).
- Backend menyajikan SPA untuk `/stock/{ticker}` agar refresh langsung aman (route baru).
- Back/forward browser bekerja lewat History API (`pushState` + `popstate`).

### 2.5 Stock Screener UI (Iterasi 3)

- Panel **Screener** (nav header) dengan:
  - Tombol preset: Buffett, Value, Growth, Quality, Dividend.
  - Form filter cepat: ROE, P/E, Net Margin, Debt/Equity (`>`/`<`).
  - Tabel hasil: ticker + tanda lolos per filter + score; klik baris → halaman saham.
- `POST /screen` kini mengisi `stocks` dari `list_stock_metrics()` (PostgreSQL), bukan dict kosong.

### 2.6 Perbandingan Saham UI (Iterasi 3)

- Panel **Bandingkan** (nav header): input 2–4 ticker dipisah koma.
- Tabel side-by-side: harga, ROE, Net Margin, Debt/Eq, P/E, P/B, dividend.
- `GET /compare?tickers=...` menggabungkan profil + kuotasi + metrik dari DB.

### 2.7 News & Events Backend

- **Pengumpulan**: `scrape_idx_news.py` (IDX) → `news_articles` (2484 artikel).
  `scrape_company_news.py` (yfinance) dibaca dari DB `companies`; Yahoo news kosong
  untuk pasar IDX, jadi IDX feed adalah sumber utama.
- **Link ticker**: `enrich_news_tickers.py` mengisi `news_articles.ticker` dari kode
  saham UPPERCASE di judul/isi (799 artikel ter-link; stopword mencegah false-positive).
- **Event classifier**: `events/classif_news_records()` menjalankan `EventProcessor`
  atas berita → daftar `CorporateEvent` (dividend, acquisition, new_contract, earnings, dll.).
- **Endpoint**: `GET /news`, `GET /stocks/{ticker}/news`, `GET /stocks/{ticker}/events`.

---

## 3. API Pendukung

Endpoint baru yang ditambahkan untuk UI:

| Method | Path                                  | Deskripsi                                                                        |
| ------ | ------------------------------------- | -------------------------------------------------------------------------------- |
| GET    | `/stocks`                             | Semua saham + harga terakhir + ataubahan harian (`change`, `change_pct`)         |
| GET    | `/stocks/{ticker}/prices`             | Riwayat OHLCV (terurut, mendukung `start`/`end`/`limit`)                         |
| GET    | `/stocks/{ticker}/financials/history` | Riwayat multi-periode `financial_ratios` (oldest-first) untuk grafik fundamental |
| GET    | `/stocks/{ticker}`                    | Profil + kuotasi + key statistics                                                |
| POST   | `/screen`                             | Screener (preset atau filter kustom) dari data `financial_ratios` DB             |
| GET    | `/compare?tickers=...`                | Perbandingan metrik side-by-side (maks. 4 ticker)                                |
| GET    | `/news`                               | Berita terbaru (opsional filter `?ticker=`)                                      |
| POST   | `/ai/screen-analysis`                 | Screening deterministik + interpretasi LLM atas top-N hasil (tombol Analisis AI) |
| GET    | `/stocks/{ticker}/research-history`   | Riwayat laporan riset AI tersimpan (newest-first)                                |
| GET    | `/stocks/{ticker}/thesis-comparison`  | Perbandingan thesis antar laporan (confidence/verdict/key changes)               |
| GET    | `/stocks/{ticker}/news`               | Berita per saham                                                                 |
| GET    | `/stocks/{ticker}/events`             | Corporate event hasil klasifikasi dari berita saham                              |
| GET    | `/favorites`                          | Daftar ticker favorit                                                            |
| POST   | `/favorites/{ticker}`                 | Tambah favorit (idempoten)                                                       |
| DELETE | `/favorites/{ticker}`                 | Hapus favorit                                                                    |
| POST   | `/favorites/{ticker}/alert`           | Set alert harga (target + direction above/below, auto-add ke watchlist)          |
| DELETE | `/favorites/{ticker}/alert`           | Hapus alert harga                                                                |
| GET    | `/favorites/details`                  | Favorit + konfigurasi alert + harga terakhir                                     |
| GET    | `/favorites/alerts`                   | Alert yang targetnya sudah tersentuh                                             |

### Skema DB baru

- Tabel `favorites` (migrasi `202609040009_create_favorites_table`):
  - `ticker` (PK/fk → companies), `position`, `created_at`.
  - **Deduplication** via `UNIQUE(ticker)`, posisi dihitung otomatis (MAX+1).

---

## 4. Peta Jalan (Roadmap) — Iterasi Berikutnya

Iterasi 1 (selesai) hanya meletakkan kerangka. Fitur lanjutan diurutkan berdasarkan nilai vs. biaya:

### Prioritas Rendah/Menengah (tinggi nilai, cepat)

| #   | Fitur                        | Deskripsi                                                                                    | Target Iterasi |
| --- | ---------------------------- | -------------------------------------------------------------------------------------------- | -------------- |
| 1   | **Candlestick chart**        | Line chart diganti candlestick OHLC (plugin `chartjs-chart-financial`)                       | Iterasi 2 ✅   |
| 2   | **Indicator overlay**        | SMA 20/50/200, Bollinger, volume sub-chart (dihitung client-side dari OHLCV)                 | Iterasi 2 ✅   |
| 3   | **Routing URL**              | `/stock/{ticker}` via HTML5 History API (bookmark/share, refresh aman)                       | Iterasi 2 ✅   |
| 4   | **Persist favorit per-user** | Ditunda — butuh auth (user + login/session); desain terpisah                                 | Iterasi 3 🔜   |
| 5   | **Screening UI**             | Form 5-factor screener (ROE, growth, P/E, dividend) → tabel hasil                            | Iterasi 3 ✅   |
| 6   | **Perbandingan saham**       | Side-by-side metrik antar 2–4 ticker (harga, ROE, margin, P/E, dividend)                     | Iterasi 3 ✅   |
| 7   | **Enrichment yfinance**      | `dividend_yield`/`current_ratio`/`payout_ratio` dari Yahoo (aktifkan Value/Quality/Dividend) | Iterasi 3 ✅   |
| 7   | **News & Events UI**         | Feed berita per saham; backend+classifier aktif, tab Berita di halaman saham                 | Iterasi 4 ✅   |
| 8   | **AI analisis chat**         | Streaming `POST /ai/analyze-stream` → panel chat dalam halaman saham                         | Iterasi 4 ✅   |
| 9   | **Export CSV**               | Ekspor tabel harga/screener/compare untuk analisis eksternal                                 | Iterasi 4 ✅   |

### Prioritas Tinggi (butuh data/infra — tunggu fase data)

| #   | Fitur                                                             | Prasyarat                                                                        | Status       |
| --- | ----------------------------------------------------------------- | -------------------------------------------------------------------------------- | ------------ |
| 10  | Real-time quotes (harga intraday, polling/socket)                 | Data pipeline real-time (Phase 26)                                               | 🔵 Backlog   |
| 11  | Screener AI & interpretasi LLM                                    | Prompt screener stabil (Phase 18 ✅)                                             | Iterasi 6 ✅ |
| 12  | Watchlist dengan alert harga                                      | Stateless alert + notification                                                   | Iterasi 8 ✅ |
| 13  | Histori research memory (tampilkan thesis terdahulu vs. sekarang) | Research memory (Phase 13 ✅)                                                    | Iterasi 7 ✅ |
| 14  | Grafik fundamental (revenue/earnings/margin multi-tahun)          | `financial_ratios` sejarah + backfill yfinance (`backfill_financial_history.py`) | Iterasi 5 ✅ |
| 15  | **Growth screen aktif** (revenue/earnings CAGR)                   | CAGR dihitung dari yfinance `financials` multi-tahun                             | Iterasi 3 ✅ |

### Backlog Masa Depan

| #   | Fitur                                              | Deskripsi                                                                                                                                                                                                                                                                            | Status           |
| --- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------- |
| 16  | **Generate analisis menyeluruh (tombol Research)** | Tombol di tab Research → `POST /stocks/{ticker}/research/analyze`; **debounce recency** (skip bila laporan < `min_hours`, default 24) agar tidak spam LLM.                                                                                                                           | ✅ Dibangun      |
| 16b | **Struktur laporan terisi**                        | `ResearchReport` kini punya `overall_verdict` (derived dari teks LLM) + `executive_summary` fallback; parser section tahan header bernomor (`## 4. Valuation`).                                                                                                                      | ✅ Dibangun      |
| 17  | **Auto-analyze berkala** (scheduled research)      | `auto_analyze.py` — AI otomatis menganalisa ticker target (favorit/env `AUTO_ANALYZE_TICKERS`) secara berkala via `scheduler.py`, guard recency `AUTO_ANALYZE_MIN_HOURS` (default 24) agar tidak spam LLM, disimpan ke research memory. Aktifkan dengan `AUTO_ANALYZE_ENABLED=true`. | ✅ Fase 17 built |

### Data Completeness Riset (gap dari laporan AKRA)

Gap teridentifikasi saat memeriksa `data/research_memory/AKRA_20260906_233955_080085.json` — beberapa bagian laporan kosong karena data belum dikumpulkan / belum disambungkan.

| #   | Item                                                  | Deskripsi                                                                                                                                                                                                                                                                        | Status   |
| --- | ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| D1  | **Surface Growth & Current Ratio dari DB**            | `calculate_all_metrics` kini memakai `revenue_cagr`/`earnings_cagr`/`current_ratio` yang sudah tersimpan (sebelumnya dihitung ulang lalu hilang). Growth & current ratio laporan langsung terisi.                                                                                | ✅ Fixed |
| D2  | **Fix urutan histori harga teknis**                   | `get_historical_prices` kini mengembalikan **ASC (oldest→newest)** untuk `days` hari terbaru; `price_vs_sma_200`/SMA kini konsisten dengan harga (AKRA: +4.13% above SMA, bukan -4.40%).                                                                                         | ✅ Fixed |
| D3  | **Enrichment yfinance: income statement + cash flow** | Perluas `scrape_yahoo_financial_fields.py` → `gross_profit`, `cash_and_equivalents`, `interest_expense`, `operating_cash_flow`, `capital_expenditures` (migrasi `202609050015`). Engine kini menghitung `gross_margin`, `interest_coverage`, `net_debt_to_ebitda`, `fcf_margin`. | ✅ Fixed |
| D4  | **Sambungkan berita → recent_events & risks**         | `AIResearcher._fill_news_sections` mengisi `recent_events` (classifier event + headline) & `risks` (sentimen negatif/keyword) dari `news_articles` bila section kosong; `company_news` masuk `data_sources`.                                                                     | ✅ Fixed |
| D5  | **Historical valuation comparison (P/E & P/B 5Y)**    | `get_valuation` membangun riwayat P/E & P/B dari harga + EPS/equity per tahun (`_build_historical_valuations`); `_metrics_from_db` menurunkan shares/BVPS sehingga `pb_ratio` terhitung. `historical_comparison` terisi (median_5y, percentile, is_expensive/cheap).             | ✅ Fixed |
| D6  | **Business quality synthesis**                        | `AIResearcher._fill_business_quality` menyintesis `business_quality` (tabel Dimensi/Nilai/Penilaian + kesimpulan) dari ROE/ROA/ROIC/margin + D/E & current ratio secara deterministik.                                                                                           | ✅ Fixed |

### ➡️ Next Phase

| #   | Fitur                                             | Deskripsi                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Status                                |
| --- | ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| 18  | **Integrasi Brave Search API untuk berita (MVP)** | **Fase A verified** `scrape_brave_news.py` → `news_articles` (idempotent `newsCode=sha1(url)`), **filter sumber via `BRAVE_SOURCES`** (allowlist), scope favorit/watchlist. Terverifikasi live → 5 berita/ticker, tanpa duplikat. Desain: [`docs/news-brave.md`](news-brave.md).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | ✅ Fase A verified                    |
| 18b | **Brave Macro News (B2)**                         | **Fase B2 built** `--macro` → query ekonomi/politik umum (`BRAVE_MACRO_QUERIES`), disimpan dengan `ticker=NULL`, tetap difilter `BRAVE_SOURCES`, idempotent. Fondasi untuk impact mapping (B3).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | ✅ Fase B2 built                      |
| 18c | **News → Sector/Impact tag (B3)**                 | **Fase B3 built** `enrich_news_impacts.py` — lexicon deterministic `keyword → sector + direction (positif/negatif) + confidence`; sektor-level default (`ticker=NULL`), `--expand` opsional untuk materialisasi per-ticker (bisa noisy). Tabel `news_impacts` (migrasi `202609050012`). **Terintegrasi pipeline** (`--steps news_brave,news_impacts`) + jadwal tiap scrape. Terverifikasi live → rate-hike = Keuangan↑/Properti↓, oil = Energi↑.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | ✅ Fase B3 built                      |
| 18d | **AI interpretasi dampak makro (B4)**             | **Fase B4 built** `ai/prompts/macro_impact.py` + endpoint `POST /ai/macro-impact` — snapshot/ranking sektor & ticker terdampak **deterministic** dari `news_impacts`; LLM hanya menginterpretasi bukti (tidak mengarang mapping). `get_news_impacts()` di data loader. Terverifikasi live → 10 tag / 2 sektor, endpoint HTTP 200.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | ✅ Fase B4 built                      |
| 18e | **Pipeline + Jadwal Brave news (B/C)**            | `news_brave` + `news_impacts` jadi step `run_pipeline.py`; `scheduler.py` (`--all` + `clear_cache()`) menjadwalkan tiap `SCRAPE_INTERVAL_HOURS`. Berita makro & impact tag auto-refresh, idempotent. [data-pipeline.md](data-pipeline.md) §3.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | ✅ Fase B/C done                      |
| 18f | **Research Candidates (B5)**                      | **Fase B5 built** `generate_research_candidates.py` — kandidat riset **deterministik** dari snapshot `news_impacts` (Opsi A, LLM tidak mengarang ticker), disimpan idempotent per tanggal ke `research_candidates` (migrasi `202609050013`, unique index `COALESCE(ticker,'')`). Pipeline step `research_candidates` setelah `news_impacts`; LLM hanya menginterpretasi bukti (opsional `--use-llm`). Endpoint `GET /research/candidates`; dashboard + tab Research menampilkan kandidat & klik ticker membuka Research. **P0 fix dedup:** migrasi `202609050014` mengganti UNIQUE NULL-buggy dengan expression index `COALESCE(ticker,'')` — artikel yang sama tidak lagi dihitung berulang. **P1 expand ke ticker:** sektor terdampak diperluas ke emiten paling likuid (`get_sector_tickers`, capped `RESEARCH_CANDIDATES_MAX_TICKERS_PER_SECTOR` default 5). **P2 geo domestik/global:** `classify_geo()` menandai tiap tag sebagai `domestic`/`global`/`mixed`; snapshot & prompt kini menyertakan `Dom/Glb` per sektor + guidance agar LLM menandai transmisi global ke IDX sebagai _indirect/lagged_ dan tidak over-claim. **P2b bobot geo:** `net_strength` kini geo-weighted (`GEO_WEIGHTS`: domestic 1.0 / mixed 0.75 / global 0.5) sehingga sinyal domestik berbobot lebih besar saat ranking; count & avg confidence tetap mentah (transparan). **P3 transparansi keyword:** `matched_keywords` kini diteruskan ke snapshot→prompt (kolom `keywords` + section `## Keyword transparency`), sehingga LLM menyebut frase pemicu persis; default `min_abs_net` diturunkan ke 0.25 agar sejalan skala bobot geo (sinyal global di-halve). **P4 baseline historis:** `compute_net_baselines()` menghitung distribusi `net_strength` per sektor (geo-weighted harian) selama 30 hari — median/p75/p90; snapshot & prompt menyertakan `Baseline(med/p90)` sehingga interpretasi menyebut apakah tekanan `above/at/below` normal. Baseline juga membawa `sample_sufficient`/`baseline_confidence` (min 5 hari) — bila kurang, prompt menandai `~` & meminta LLM menyebut perbandingan historis terbatas, tidak overstate. **Saat ini hanya tampil** (tidak auto-analyze). | ✅ Fase B5 built (P0+P1+P2+P2b+P3+P4) |

| 18g | **Perluas cakupan per-ticker Brave (A)** | Aktifkan per-ticker Brave di luar favorit, **scope = hasil screener** dengan batas top-N configurable (env), mis. `BRAVE_TICKER_SCOPE=screen`, `BRAVE_TICKER_SCREEN_TYPE=quality`, `BRAVE_TICKER_SCREEN_N=15` (bisa diturunkan ke 3). Menarik top-N ticker dari preset screener (default `quality`) lalu query Brave per-ticker; `ticker` tetap diisi eksplisit. **Keputusan:** pakai subset screener terkendali (bukan `all` 973) demi biaya/rate-limit; top 3 dianggap terlalu kecil, N default 15 (env-tunable). | 🔵 Backlog (design settled) |
| 18h | **Perkuat pelink-an makro→ticker (B)** | ✅ **Selesai.** Perkaya lexicon `IMPACT_RULES` (`enrich_news_impacts.py`): tambah sektor `Utilitas` (listrik/EBT) + varian keyword pendek berarah (baja/pupuk/nikel/emas/CPO/tembaga, travel/hotel, pangan/El Nino, 5G, BPJS, smelter, punggung) sehingga berita makro lebih banyak ter-link. Default `max_tickers_per_sector` dinaikkan **5 → 8** (`RESEARCH_CANDIDATES_MAX_TICKERS_PER_SECTOR`). | ✅ Done |
| 18i | **Cadence pipeline (daily/weekly/monthly)** | Tiap step diberi `cadence` (daily: companies/prices/financial_ratio/news_*, weekly: `yfinance`, monthly: `financial_history`). `run_pipeline.py --cadence <c>` menjalankan subset per cadence; `scheduler.py` kini menjalankan cadence yang **jatuh tempo** (state `data/scheduler_cadence_state.json`, daily ≥1 hari / weekly ≥7 / monthly ≥30), bukan selalu `--all`. `--steps` & `--all` tetap. | ✅ Done |
| 18j | **Analisis menyeluruh untuk kandidat riset** | Step `research_analyze` (`auto_analyze.py --source research_candidates`) menjalankan analisis AI menyeluruh untuk ticker kandidat riset (recency-guarded, cap `RESEARCH_ANALYZE_MAX_TICKERS` default 20), disimpan ke research memory. | ✅ Done |
| 18k | **Compare hasil AI untuk menyaring kandidat (future)** | Setelah tiap kandidat dianalisis, bandingkan laporan (mis. `overall_verdict`, `confidence_score`, skor data) dari research memory untuk **meranking/menyaring** kandidat — mis. prioritaskan yang bullish + confidence tinggi + data lengkap; tandai yang bearish/data kosong. Deterministic filter + narasi LLM. | 🔵 Backlog (future) |

> **Catatan:** Growth screen kini berfungsi — `revenue_cagr`/`earnings_cagr` dihitung dari
> riwayat multi-tahun yfinance (`compute_cagr`) dan disimpan di `financial_ratios`,
> dibaca oleh `list_stock_metrics()`. Value, Quality, Dividend juga aktif lewat
> enrichment yfinance (dividen/current ratio/payout ratio). Cakupan hasil tergantung
> jumlah ticker yang sudah di-scrape (jalankan `scrape_yahoo_financial_fields.py` penuh).

---

## 5. Keputusan Teknis

| Keputusan      | Pilihan                                      | Alasan                                           |
| -------------- | -------------------------------------------- | ------------------------------------------------ |
| Charting       | Chart.js (+ chartjs-chart-financial) via CDN | Ringan; candlestick + indikator tanpa build step |
| SSA vs MPA     | SPA (single index.html)                      | Ringan, tanpa build step, mudah di-iterasi       |
| Data flow      | JSON API → fetch                             | Terpisah dari backend, mudah dimigrasikan        |
| Static serving | FastAPI `GET /` membaca file                 | Selaras pola lama, tidak perlu build tooling     |
| Favorit        | Tabel PostgreSQL                             | Persisten, source-of-truth                       |

### TODO / Perbaikan Berikutnya

- [ ] Ganti `!!`/`!important` bila ada di CSS; rapikan responsif mobile.
- [ ] Tambah fallback jika `/stocks` 973 baris terlalu besar (pagination 100/request).
- [ ] Ubah `renderAnalysisRows` agar menampilkan data `signals`/`indicators` secara terstruktur, bukan raw JSON.
- [ ] Tambah file `web/app.js` & `web/style.css` terpisah bila mulai membengkak.
