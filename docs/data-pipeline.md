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

| Step                  | Script                             | Fungsi                                                               |
| --------------------- | ---------------------------------- | -------------------------------------------------------------------- |
| `companies`           | `scrape_company_profiles.py`       | Master + detail perusahaan (universe untuk FK)                       |
| `prices`              | `scrape_stock_prices.py`           | Harga OHLCV harian (incremental; hanya tanggal yang hilang)          |
| `financial_ratio`     | `scrape_financial_ratio.py`        | Rasio keuangan terbaru dari IDX                                      |
| `yfinance`            | `scrape_yahoo_financial_fields.py` | Enrichment: dividend_yield/current_ratio/payout_ratio/CAGR           |
| `financial_history`   | `backfill_financial_history.py`    | Riwayat multi-tahun dari yfinance (untuk grafik fundamental)         |
| `news`                | `scrape_idx_news.py`               | Feed berita IDX (dedup via NewsCode)                                 |
| `news_link`           | `enrich_news_tickers.py`           | Menautkan berita ke ticker IDX                                       |
| `company_news`        | `scrape_company_news.py`           | Berita per-ticker dari Yahoo (dedup deterministik SHA-1)             |
| `news_brave`          | `scrape_brave_news.py --macro`     | Feed makro/ekonomi/politik via Brave (`ticker=NULL`, filter sumber)  |
| `news_impacts`        | `enrich_news_impacts.py`           | Tag dampak sektor/ticker deterministic (B3)                          |
| `research_candidates` | `generate_research_candidates.py`  | Kandidat riset deterministic dari snapshot (B5) + LLM interpretation |

### Alur harian: scraping → interpretasi → kandidat riset

```
news_brave (makro) ─┐
company/news (ticker)─┤→ news_impacts (tag sektor/direksi) → research_candidates
                     │                                       (sector + affected_tickers)
                     │
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
