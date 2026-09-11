# Data Pipeline — IDX-BEI Investment Research Platform

> **Mengapa file ini ada:** sejak Phase 24–26, **scraping data tidak lagi
> dilakukan secara manual satu per satu**. Semua pengumpulan data dijalankan oleh
> **pipeline** (`run_pipeline.py`), yang bisa dijalankan sekali atau dijadwalkan
> otomatis (`scheduler.py`). File ini mendokumentasikan alur, perintah, dan
> konfigurasinya.

---

## 1. Prinsip: scraping = pipeline

Sumber data (IDX, Yahoo Finance, berita) hanya boleh disentuh oleh **pipeline**.
Aplikasi (FastAPI) hanya **membaca** dari PostgreSQL dan di-cache sebentar
(TTL) agar tidak membebani DB saat banyak permintaan. Jangan memanggil scraper
secara manual di luar pipeline kecuali untuk debugging/disaster-recovery.

```
        scraper scripts  ─┐
        scraper scripts  ─┼── run_pipeline.py ──> PostgreSQL ──> API (read + cache)
        scraper scripts  ─┘          ▲
                                     │
                            scheduler.py (jadwal otomatis)
```

---

## 2. Menjalankan pipeline

Satu command, urut sesuai dependency (perusahaan dulu agar FK aman):

```bash
uv run python run_pipeline.py --all
```

Urutan langkah:

| Step                  | Script                                         | Fungsi                                                                                                                   |
| --------------------- | ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `companies`           | `scrape_company_profiles.py`                   | Master + detail perusahaan (universe untuk FK)                                                                           |
| `prices`              | `scrape_stock_prices.py`                       | Harga OHLCV harian (incremental; hanya tanggal yang hilang)                                                              |
| `financial_ratio`     | `scrape_financial_ratio.py`                    | Rasio keuangan terbaru dari IDX                                                                                          |
| `yfinance`            | `scrape_yahoo_financial_fields.py`             | Enrichment: dividend_yield/current_ratio/payout_ratio/CAGR                                                               |
| `financial_history`   | `backfill_financial_history.py`                | Riwayat multi-tahun dari yfinance (untuk grafik fundamental)                                                             |
| `news_brave`          | `scrape_brave_news.py --macro`                 | Feed makro/ekonomi/politik via Brave (`ticker=NULL`, filter sumber)                                                      |
| `news_impacts`        | `enrich_news_impacts.py`                       | Tag dampak sektor/ticker deterministic (B3)                                                                              |
| `research_candidates` | `generate_research_candidates.py`              | Kandidat riset deterministic dari snapshot (B5) + LLM interpretation                                                     |
| `research_analyze`    | `auto_analyze.py --source research_candidates` | Analisis menyeluruh (AI) untuk ticker kandidat riset (recency-guarded, capped `RESEARCH_ANALYZE_MAX_TICKERS` default 20) |

> **Sumber berita harian = Brave (makro saja).** Feed IDX (`scrape_idx_news`), per-ticker
> Yahoo (`scrape_company_news`), dan per-ticker Brave **tidak lagi** dijalankan di pipeline.
> Berita makro diambil via **Brave Search API** (filter `BRAVE_SOURCES`); berita
> **per-ticker kini di-fetch on-demand** saat user klik “generate analisis menyeluruh”.

#### Sumber Berita (Brave-only)

Pipeline harian hanya mengambil **berita makro** via satu mode:

| Mode      | Step                     | Query                                                                                        | Ticker di tabel                                         |
| --------- | ------------------------ | -------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| **Makro** | `news_brave` (`--macro`) | `BRAVE_MACRO_QUERIES` (ekonomi/politik umum, mis. "ekonomi indonesia, ihsg, harga batubara") | `NULL` → dipetakan ke sektor/ticker oleh `news_impacts` |

**Aturan scope:**

- `news_brave` `--macro` hanya menjalankan `BRAVE_MACRO_QUERIES` (bukan per-ticker),
  dan hasilnya disimpan dengan `ticker=NULL`. Pelink-an ke sektor/emiten dilakukan
  **deterministik** oleh `enrich_news_impacts.py` (B3).
- **Berita per-ticker tidak lagi** di-scrape harian untuk favorit/watchlist. Ia di-fetch
  **on-demand** saat analisis menyeluruh berjalan (lihat `_fetch_fresh_ticker_news` di
  `api/main.py`), lalu disimpan ke `news_articles` dan dipakai sebagai bahan analisa.
- **Guard kesegaran:** scrape per-ticker saat analisis menyeluruh hanya terjadi bila
  **belum ada berita terbaru** untuk ticker itu (berita terbaru lebih tua dari
  `NEWS_FRESHNESS_HOURS`, default 24 jam). Jika sudah ada berita segar, API Brave tidak
  dipanggil dan analisis memakai data yang ada — menghemat kuota API.
- Setelah scrape on-demand berhasil, cache baca data-loader dibersihkan agar analisis
  langsung memakai baris berita yang baru disimpan.
- Bila ingin menjalankan per-ticker secara manual kapan saja:
  `uv run python scrape_brave_news.py --ticker BBCA --ticker BBRI`.

**Kendali biaya/rate-limit:** pipeline harian = 1 request per query `BRAVE_MACRO_QUERIES`
(biasanya ~5–10), **bukan** 973 ticker. Berita per-ticker di-fetch hanya saat diminta
(user klik analisis) = 1 request per ticker yang dianalisa. Sumber difilter oleh
`BRAVE_SOURCES` (allowlist domain/publisher); hasil di luar allowlist dibuang.

**Ticker per artikel:**

- Makro → `ticker=NULL`; pelink-an ke sektor/ticker dilakukan **deterministik** oleh
  `enrich_news_impacts.py` (B3, lexicon keyword → sektor/direksi/confidence), lalu
  `news_impacts` → `research_candidates` (B5).
- Per-ticker (on-demand) → `ticker` **eksplisit** dari query (paling andal, tanpa tebakan);
  disimpan saat analisis menyeluruh berjalan.

### Alur harian: scraping → interpretasi → kandidat riset

```
news_brave (makro, ticker=NULL) ─→ news_impacts (tag sektor/direksi) → research_candidates
                                  (sector + affected_tickers)
                                └─ LLM interpretasi bukti yang sama (opsional --use-llm)
```

Kandidat **tidak pernah dikarang LLM** (Opsi A): hanya `sector` + `affected_tickers`
yang muncul dari snapshot deterministic `news_impacts`. LLM hanya memberi narasi
interpretasi. Hasil disimpan idempotent per tanggal (`research_candidates`, unique
index `COALESCE(ticker,'')` agar sektor-level tidak duplikat). Saat ini kandidat
**hanya ditampilkan** di dashboard & tab Research; klik ticker membuka Research
tab untuk dianalisa manual (belum auto-analyze).

**Geo domestik/global (P2):** setiap tag `news_impacts` diklasifikasikan
`domestic`/`global`/`mixed` via `classify_geo()` (dari judul, deterministik).
Snapshot & prompt LLM menyertakan `Dom/Glb` per sektor, dan guidance meminta LLM
menandai transmisi global ke IDX sebagai _indirect/lagged_ — mencegah
over-claim dampak langsung berita global (ECB/Fed) ke saham Indonesia.

**Bobot geo (P2b):** `net_strength` kini geo-weighted (`GEO_WEIGHTS`: domestic
1.0, mixed 0.75, global 0.5), sehingga sinyal domestik berbobot lebih besar saat
ranking. `positive_count`/`negative_count` & avg confidence tetap mentah agar
transparan; bobot per tag terlihat di snapshot (`geo_weight`, `domestic_share`).

**Transparansi keyword (P3):** `matched_keywords` diteruskan ke snapshot & prompt
LLM (kolom `keywords` + section `## Keyword transparency`), jadi interpretasi
menyebut frase pemicu persis (mis. _"kenaikan suku bunga"_) dan bisa dilacak, bukan
black-box. Karena sinyal global di-halve, default `RESEARCH_CANDIDATES_MIN_NET`
diturunkan menjadi `0.25` agar satu sinyal makro yang bermakna tetap lolos menjadi
kandidat.

**Baseline historis (P4):** `compute_net_baselines()` menghitung distribusi
`net_strength` per sektor dari riwayat `news_impacts` (geo-weighted per hari)
selama `RESEARCH_CANDIDATES_BASELINE_DAYS` (default 30) → median/p75/p90.
Snapshot & prompt menyertakan `Baseline(med/p90)` sehingga interpretasi menyebut
apakah tekanan saat ini _above/at/below_ normal — bukan sekadar angka tanpa
konteks. Baseline juga membawa **`sample_sufficient`**/ **`baseline_confidence`**
(min 5 hari): bila kurang, prompt menandai `~` dan meminta LLM menyebut
perbandingan historis terbatas, agar tidak overstate.

**Pemilihan emiten per sektor (P5):** saat memperluas kandidat sektor ke level
saham, `RESEARCH_CANDIDATES_TICKER_RANK` memilih cara peringkatnya:

- `technical` (default) — `get_sector_technical_tickers` memilih emiten
  **teknis terbaik dengan syarat likuiditas minimum**: pertama filter emiten yang
  likuiditasnya (close × volume) ≥ **persentil 40%** sektor
  (`RESEARCH_CANDIDATES_LIQUIDITY_PERCENTILE`, default 0.40), lalu peringkat
  komposit berbobot:
  - trend (`price_vs_sma_200`) bobot **0.5** — 30% di atas SMA200 = skor 1
  - RSI sehat (~55) bobot **0.3**
  - volume ratio bobot **0.2** (2× volume = skor 1)
- `liquidity` — `get_sector_tickers` memilih emiten **paling likuid** (close × volume).
- **Pemetaan nama sektor:** lexicon memakai nama Indonesia ("Keuangan") sementara
  `companies.sector` memakai IDX Inggris ("Financials"); `_sector_names()`
  menerjemahkan keduanya sehingga ekspansi mencapai anggota sektor sebenarnya
  (mis. "Keuangan" → 104 Financials, bukan hanya 3 ticker bernama Indonesia).
- Batas per sektor via `RESEARCH_CANDIDATES_MAX_TICKERS_PER_SECTOR` (default 8).

Jalankan kandidat dengan LLM: `uv run python generate_research_candidates.py --use-llm`
(atau set `RESEARCH_CANDIDATES_USE_LLM=true` di `.env`).

### Opsi berguna

```bash
uv run python run_pipeline.py --steps prices,news      # subset
uv run python run_pipeline.py --all --backfill         # tarik 5t harga tiap run
uv run python run_pipeline.py --all --retries 3 --delay 1.0
```

Hasil & kegagalan tiap step dicatat di:

- Log: `logs/pipeline.log`
- Failure ledger: `data/pipeline_ledger.jsonl`

---

## 3. Menjadwalkan pipeline otomatis

```bash
uv run python scheduler.py                 # daemon, setiap SCRAPE_INTERVAL_HOURS (default 24)
uv run python scheduler.py --interval 6    # tiap 6 jam
uv run python scheduler.py --now           # jalankan sekali sekarang & keluar
uv run python scheduler.py --dry-run       # cetak jadwal berikutnya lalu keluar
```

Konfigurasi via environment:

| Variabel                | Default        | Arti                                                  |
| ----------------------- | -------------- | ----------------------------------------------------- |
| `SCRAPE_SCHEDULE_TIME`  | (kosong)       | Jam harian `HH:MM` di Asia/Jakarta                    |
| `SCRAPE_INTERVAL_HOURS` | `24`           | Interval dalam jam (dipakai bila waktu harian kosong) |
| `SCRAPE_TIMEZONE`       | `Asia/Jakarta` | Zona waktu jadwal                                     |

Setelah pipeline selesai, `scheduler.py` memanggil `clear_cache()` agar endpoint
API langsung menyajikan data baru (tidak menunggu TTL).

### Cadence (daily / weekly / monthly) — default otomatis

Tiap step punya **cadence** (frekuensi refresh) yang sesuai karakter datanya.
Scheduler menjalankan step yang **jatuh tempo** (dilacak via
`data/scheduler_cadence_state.json`), bukan selalu `--all`:

| Cadence   | Step yang dijalankan                                                                          | Alasan                          |
| --------- | --------------------------------------------------------------------------------------------- | ------------------------------- |
| `daily`   | `companies`, `prices`, `financial_ratio`, `news_brave`, `news_impacts`, `research_candidates` | Harga/rasio/berita makro harian |
| `weekly`  | `yfinance`                                                                                    | Rate-limited & mahal (~30 mnt)  |
| `monthly` | `financial_history`                                                                           | Backfill multi-tahun, berat     |

Jalankan manual per cadence:

```bash
uv run python run_pipeline.py --cadence daily
uv run python run_pipeline.py --cadence weekly
uv run python run_pipeline.py --cadence monthly
uv run python run_pipeline.py --cadence all   # semua step (perilaku --all)
```

`--steps` tetap tersedia untuk subset eksplisit; `--all` = semua step. Default
`scheduler.py` kini berjalan **per cadence yang jatuh tempo**
(daily ≥1 hari, weekly ≥7 hari, monthly ≥30 hari), sehingga step berat tidak
dihambat tiap siklus sementara berita/harga tetap harian.

### Jadwal & interval tiap scrape

- **Setiap siklus jadwal** (sekali pada `SCRAPE_SCHEDULE_TIME`, atau tiap
  `SCRAPE_INTERVAL_HOURS`) menjalankan **pipeline lengkap** `--all`: termasuk
  `news_brave` (berita makro Brave) lalu `news_impacts` (tag dampak
  sektor/ticker). Jadi berita & impact tag makro ikut ter-refresh setiap siklus,
  bukan hanya sekali jalan.
- Karena `news_brave`/`news_impacts` **idempotent** (dedup via `news_code` +
  `UNIQUE(news_id, sector, ticker, direction)`), re-run tiap interval **tidak
  menduplikat** berita maupun impact tag.
- Interval lebih rapat (mis. `--interval 6`) = berita makro lebih segar, tapi
  memakai **lebih banyak kuota Brave** (1 request per query makro per siklus;
  10 query default ≈ 10 request). Sesuaikan sejumlah query makro
  (`BRAVE_MACRO_QUERIES`) & `BRAVE_COUNT` (hasil per query) dengan kuota Anda.

---

## 4. Caching baca (API / `PostgreSQLDataLoader`)

Metode baca yang sering dipanggil di-cache dalam proses selama **TTL**:

| Method                                        | Dipakai oleh                  |
| --------------------------------------------- | ----------------------------- |
| `list_stocks` / `list_stock_metrics`          | Dashboard, Screener, Compare  |
| `get_price_history` / `get_historical_prices` | Grafik harga                  |
| `get_news`                                    | Feed berita                   |
| `get_financial_ratios` / `..._history`        | Key stats, Grafik fundamental |

- Variabel: `DATA_CACHE_TTL` (detik, default `60`, `0` = mati).
- Invalidasi: `clear_cache()` (dipanggil scheduler, atau manual via `python -c "from ai.data_loader_pg import clear_cache; clear_cache()"`).

---

## 5. Catatan data-correctness

- **Dedup berita deterministik** (SHA-1) agar re-run tidak menduplikat artikel.
- **`_number` menolak NaN/Inf** agar kolom numerik tidak tercemar.
- **Unit dinormalisasi**: backfill yfinance → konvensi IDX (moneter ÷ 1e9, margin × 100).
- **`dividend_yield` dinormalisasi ke persen**: fraksi (≤1) ×100, nilai yang sudah persen (>1) dibiarkan, dan di-clamp maks 100% — mencegah skala ganda (sebelumnya 1810% untuk 18.10%).
- **Metrik persen untuk screener dinormalisasi ke desimal di `list_stock_metrics`**: `roe`/`roa`/`roic`/`gross_margin`/`operating_margin`/`net_margin` dibagi 100 agar cocok dengan threshold screen (`roe >= 0.15`, `net_margin >= 0.10`). `dividend_yield` tetap persen, `payout_ratio`/`cagr` tetap desimal. UI kustom (`readFilter`) mengonversi input persen → desimal untuk `roe`/`net_margin`.
- Harga **incremental** via `stored_dates` (hanya fetch tanggal yang belum ada).

> Jangan memanggil scraper langsung dari kode aplikasi; selalu lewat
> pipeline. Scraper dianggap _write-path_; API hanya _read-path_ (+ cache).
