# Integrasi Brave Search API — Berita (Fase A / MVP)

> **Status:** Fase A **terverifikasi live**, Fase B2 (macro) **built**, Fase B3 (**impact mapping**) **built**, Fase B4 (**AI interpretasi dampak**) **built**.
> **Tujuan:** mengisi `news_articles` dengan berita segar & luas per saham, mengatasi
> feed IDX yang basi (berita BBRI terakhir 2023).
> **Prinsip:** memakai API resmi (bukan scraping), **hemat biaya** (scope favorit/watchlist),
> **idempotent** (dedup via `news_code = sha1(url)`), **filter sumber berita via env** (`BRAVE_SOURCES`).

---

## 1. Ringkasan

Endpoint **Brave News Search** mengambil berita per ticker, dinormalisasi ke schema
`news_articles`, lalu diproses oleh `insert_news` (idempotent) dan `events` classifier
yang sudah ada. Ticker langsung diketahui (query per-ticker), jadi tidak perlu
`enrich_news_tickers`.

```
scrape_brave_news.py (per ticker)
   │  GET /res/v1/news/search   (header X-Subscription-Token)
   ▼
Brave API → {title, url, description, page_age, profile.name, meta_url.hostname}
   │  normalisasi
   ▼
{title, url, publishedAt=page_age, source=profile.name, ticker,
   newsCode=sha1(url), content=description}
   │
   ▼ store.insert_news(records)   ON CONFLICT (news_code) DO NOTHING
   │
   ▼ events.classif_news_records(news)
   │
   ▼ /news, /stocks/{ticker}/news, /stocks/{ticker}/events
```

---

## 2. Endpoint & Auth

- **URL:** `GET https://api.search.brave.com/res/v1/news/search`
- **Auth:** header `X-Subscription-Token: <BRAVE_API_KEY>` (dan `Accept: application/json`)
- **Query params yang dipakai (lihat §6 env):**

| Param         | Nilai                 | Keterangan                                       |
| ------------- | --------------------- | ------------------------------------------------ |
| `q`           | `"BBCA saham berita"` | query per ticker (wajib)                         |
| `count`       | `5`                   | jumlah hasil (1–50)                              |
| `country`     | `id`                  | negara — `id` **valid**                          |
| `search_lang` | (opsional)            | **jangan `id`** → HTTP 422; hanya kirim bila set |
| `freshness`   | (opsional)            | `pd`/`pw`/`pm`/`py` → hanya berita terbaru       |

> **Penting:** param `source` adalah milik _web search_, **bukan** news search →
> dikirim ke `/res/v1/news/search` akan HTTP 422. Begitu juga `search_lang=id`
> tidak ada di enum Brave. Keduanya sudah tidak dikirim oleh scraper.

**Response — `results[]` (tiap item):**

```json
{
  "title": "...",
  "url": "...",
  "description": "...",
  "extra_snippets": ["..."],
  "age": "1 day ago",              // string manusia — JANGAN simpan ke kolom datetime
  "page_age": "2026-09-04T07:26:36", // ISO datetime → dipakai sebagai publishedAt
  "profile": { "name": "CNBC Indonesia", "url": "https://..." },
  "meta_url": { "hostname": "cnbcindonesia.com", "netloc": "cnbcindonesia.com", "..." }
}
```

---

## 3. File & perubahan (Fase A)

| Item                              | Perubahan                                                                                                                                                |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`scrape_brave_news.py`** (baru) | CLI `--ticker` (repeatable) / `--limit` / `--offset` / `--delay` / `--countries`/`--lang`; query per ticker, panggil Brave, normalisasi → `insert_news`. |
| **`database/scraper_store.py`**   | Tidak berubah — reuse `insert_news`. Pastikan `newsCode=sha1(url)` (deterministik).                                                                      |
| **`.env`**                        | Tambah `BRAVE_API_KEY` (secret).                                                                                                                         |
| **`docs/roadmap.md`**             | Backlog row `news-brave` = **next phase**.                                                                                                               |
| **Test**                          | `tests/test_brave_news.py` (lihat §7).                                                                                                                   |

---

## 4. Fungsi utama `scrape_brave_news.py`

```python
def build_query(ticker: str, country: str = "id", lang: str = "id") -> str
    # -> f"{ticker} saham berita"; param country/search_lang untuk country=id/search_lang=id

def fetch_brave_news(query: str, count: int = 5) -> list[dict]
    # GET /res/v1/news/search, header X-Subscription-Token, timeout, return raw items

def normalize_item(item: dict, ticker: str) -> dict
    # -> {ticker, title, url, publishedAt, source=source.publisher, content=description,
    #     newsCode=sha1(url)}  (published_at fallback ke size)

def scrape_brave_news(tickers, count, delay, offset, limit) -> int
    # loop ticker → fetch → normalize → store.insert_news
```

**Normalisasi field (ke schema `news_articles`):**

| Field `news_articles` | Dari response                                |
| --------------------- | -------------------------------------------- |
| `ticker`              | `ticker` (argumen query)                     |
| `title`               | `item["title"]`                              |
| `url`                 | `item["url"]`                                |
| `content`             | `item["description"]`                        |
| `source`              | `item["profile"]["name"]` (publisher)        |
| `published_at`        | `item["page_age"]` (fallback `published_at`) |
| `news_code`           | `sha1(url)`                                  |

> `insert_news` membaca key `title`/`url`/`content`/`source`/`publishedAt`/`newsCode`/`ticker`.
> Jangan pakai `age` (string "X ago") → akan gagal disimpan ke kolom datetime.

> `insert_news` membaca key `title`/`url`/`content`/`source`/`publishedAt`/`newsCode`/`ticker`.

---

## 5. Scope & biaya (kunci)

- **Free tier Brave:** ± **2.000 request/bulan, 1 request/detik** (1 request = 1 query).
- **Scope awal (hemat biaya):** hanya **saham favorit + watchlist** (~5–20 ticker), bukan 973.
- **Rate-limit:** `delay ≥ 1s` antar query + `--limit`/`--offset` untuk batch.
- **Jadwal:** sekali/hari (atau interval) via `scheduler.py`, bukan tiap request.
- Bisa diperluas bertahap (daftar ticker yang lebih besar) bila kuota mencukupi.

---

## 6. Konfigurasi env (termasuk filter sumber)

```env
BRAVE_API_KEY=BSA_xxxxxxxx          # wajib
BRAVE_URL=https://api.search.brave.com/res/v1/news/search  # opsional
BRAVE_COUNT=5                       # hasil per query (1–50)
BRAVE_COUNTRY=id                    # valid (2-char atau ALL)
# BRAVE_LANG=            # biarkan kosong — search_lang=id → HTTP 422
# BRAVE_FRESHNESS=pm     # opsional: pd/pw/pm/py — batasi ke berita terbaru
# Filter sumber (allowlist, koma) — HANYA berita dari sumber ini yang diambil.
# Kosong = terima semua (tidak disarankan). Cocok pada publisher name ATAU domain url.
# Kurasikan: hanya media/publisher tepercaya & relevan (finansial/ekonomi/politik/komoditas).
BRAVE_SOURCES=cnbcindonesia.com,katadata.co.id,antaranews.com,bisnis.com,kompas.com,investor.id,journalarta.com,liputan6.com,fxstreet-id.com,bloombergtechnoz.com,kabarbursa.com,mediaindonesia.com,kontan.co.id,detik.com,tempo.co,republika.co.id,thejakartapost.com,idxchannel.com,harianenergi.com,ekon.go.id,suara.com,merdeka.com,cnnindonesia.com,viva.co.id,investing.com,mongabay.com
# Query makro (koma) untuk mode --macro; disimpan dengan ticker=NULL.
BRAVE_MACRO_QUERIES=ekonomi indonesia,bi suku bunga,ihsg hari ini,harga batubara,harga cpo,kenaikan suku bunga bank indonesia,penurunan suku bunga bank indonesia,harga minyak dunia naik,inflasi indonesia,politik indonesia
```

> **Catatan kuota & kualitas:** pernah diuji dengan allowlist sempit (5–8 sumber) →
> hanya ~1–2/5 artikel makro yang lolos. Setelah diperluas ke sumber tepercaya di
> atas → ~3–5/5 lolos. Jangan sekadar menambah banyak domain: sumber generik
> (mis. "Informasi") & non-finansial (mis. "Portal Islam") **sengaja ditolak** agar
> feed tetap relevan. Scraper mencetak `dropped sources` untuk membantu kurasi.

- `source_allowed()` mencocokkan allowlist terhadap **nama publisher** (`profile.name`)
  dan **domain url** (`meta_url.hostname`) dari item — jadi entri bisa berupa domain atau nama.
  Bila href/sumber tidak diketahui, item dibuang saat filter aktif.
- `BRAVE_FRESHNESS` opsional → hanya berita terbaru (mis. `pw` = past week) bila diisi; default kosong = tanpa batas umur.

---

## 5b. Mode Makro (Fase B2) — berita ekonomi/politik umum

Selain query per-ticker, scraper bisa mengambil **berita makro** dengan `--macro`.
Berita ini disimpan ke `news_articles` dengan **`ticker = NULL`** (general), tetap
ter-filter `BRAVE_SOURCES`, dan idempotent. Tujuannya jadi bahan pemetaan dampak
industri/saham (Fase B3).

```bash
uv run python scrape_brave_news.py --macro                    # pakai BRAVE_MACRO_QUERIES
uv run python scrape_brave_news.py --macro --macro-queries "ekonomi indonesia,ihsg"
uv run python scrape_brave_news.py --macro --limit 2 --count 5  # batch kecil
```

| Argumen           | Peran                                                       |
| ----------------- | ----------------------------------------------------------- |
| `--macro`         | jalankan mode makro (bukan per-ticker)                      |
| `--macro-queries` | override daftar query (koma), menimpa `BRAVE_MACRO_QUERIES` |
| `--limit`         | batasi jumlah query (hemat kuota / pengujian)               |
| `--count`         | hasil per query (default env)                               |

> **Biaya:** 1 query makro = 1 request. Scope ke ~5–10 query per run, **bukan** 973 ticker.
> Berita makro yang menyebut ticker bisa di-`enrich_news_tickers` di fase lanjut.

> CLI override: `--source cnbcindonesia.com,katadata.co.id` (menimpa env).

### 5c. Impact Tagging Deterministic (Fase B3)

`enrich_news_impacts.py` menandai tiap berita dengan **sektor terdampak + arah**
(positif/negatif) + **confidence** memakai lexicon keyword. Output ditulis ke tabel
`news_impacts` (migrasi `202609050012`), idempotent via
`UNIQUE (news_id, sector, ticker, direction)`.

```bash
uv run python enrich_news_impacts.py                 # default: sektor-level (ticker=NULL)
uv run python enrich_news_impacts.py --expand        # juga materialisasi 1 baris/company di sektor
uv run python enrich_news_impacts.py --limit 100     # batch kecil
```

| Argumen    | Peran                                                                        |
| ---------- | ---------------------------------------------------------------------------- |
| (default)  | 1 baris sektor (`ticker=NULL`) + 1 baris per ticker yang disebut di artikel  |
| `--expand` | tambah 1 baris per company pada sektor terdampak (untuk daftar saham), noisy |
| `--limit`  | proses hanya N artikel pertama (pengujian)                                   |

**Lexicon** (`IMPACT_RULES`) contoh: `"menaikkan suku bunga"` → `Keuangan: positive`
dan `Properti & Real Estat: negative`; `"harga minyak dunia naik"` → `Energi: positive`.
Confidence deterministic: `0.6 + 0.1 * (jumlah signal - 1)`, cap `0.95`.

> **Prinsip:** arah & sektor dijamin deterministic (di code), bukan dari LLM.
> LLM (Fase B4) hanya boleh merangkum/mengurutkan dari tag ini sebagai bukti.
> `--expand` sengaja tidak default — menandai ~100 bank utk 1 artikel makro = noise.

### 6b. Idempotency & dedup

- `newsCode = sha1(url)` → `insert_news` `ON CONFLICT (news_code) DO NOTHING` → re-run tidak duplikat.
- Ticker sudah ada (query per-ticker) → tidak perlu `enrich_news_tickers`.
- `published_at` kadang tidak ada/akurat → tetap insert (ticker/title/url cukup) agar feed tetap terisi.

---

## 7. Tests (`tests/test_brave_news.py`)

- `test_build_query`: `q` berisi ticker + "saham berita".
- `test_normalize_item`: field response (`profile.name`/`meta_url.hostname`/`page_age`) → field `news_articles`.
- `test_news_code_deterministic`: `sha1(url)` stabil, tidak `hash()` (anti-duplikat antar proses).
- `test_fetch_brave_news_mocked`: mock `requests.get` → header `X-Subscription-Token` ada, URL benar, **tidak kirim `source`**.
- `test_fetch_omits_search_lang_when_empty`: `search_lang` tidak dikirim bila kosong (hindari 422).
- `test_fetch_sends_freshness_only_when_set`: `freshness` opsional & hanya dikirim bila diisi.
- `test_source_allowed`: cocok domain (`meta_url.hostname`) & nama publisher; tolak item tanpa sumber saat filter ON.
- `test_insert_idempotent`: via fake store → `ON CONFLICT (news_code)`.

---

## 8. Keputusan & risiko

| Aspek                     | Catatan                                                                 |
| ------------------------- | ----------------------------------------------------------------------- |
| **Biaya / rate-limit**    | Paling penting → scope kecil (favorit/watchlist), delay, batch, jadwal. |
| **Kualitas hasil**        | Campur sumber; perlu filter relevansi + stopword.                       |
| **`published_at`**        | Tidak selalu akurat → fallback/None; tetap insert.                      |
| **Tidak menyentuh harga** | Murni `news_articles`; tidak mengubah `stock_prices`.                   |
| **Legal**                 | API resmi (bukan scraping) — lebih aman.                                |

---

## 9. Fase berikutnya (setelah MVP)

- **Fase B (integrasi pipeline):** ✅ `news_brave` + `news_impacts` kini step di
  `run_pipeline.py` (`--all` atau `--steps news_brave,news_impacts`), jadi berita
  makro & impact tag ter-refresh otomatis di tiap siklus.
- **Fase C (jadwal):** ✅ `scheduler.py` menjalankan `run_pipeline.py --all` pada
  `SCRAPE_SCHEDULE_TIME` / `SCRAPE_INTERVAL_HOURS`, lalu `clear_cache()`. Karena
  `--all` sudah memuat `news_brave`/`news_impacts`, berita makro & impact tag ikut
  terjadwal otomatis (lihat `docs/data-pipeline.md` §3).
- **Fase B5 (per-ticker Brave):** ✅ `news_brave_ticker` kini step pipeline
  (`scrape_brave_news.py` tanpa arg) — berita **per-ticker** untuk **favorit/watchlist**
  saja, `ticker` diisi eksplisit dari query. Feed IDX (`scrape_idx_news`) & per-ticker
  Yahoo (`scrape_company_news`) **tidak lagi** dijalankan pipeline; sumber berita
  kini **Brave-only** (lihat `docs/data-pipeline.md` §2).
- **Fase D:** perluas daftar ticker (mis. hasil screen) sesuai kuota.
- **Fase B4:** ✅ `ai/prompts/macro_impact.py` + endpoint `POST /ai/macro-impact` —
  snapshot/ranking sektor & ticker terdampak **deterministic** dari `news_impacts`;
  LLM hanya menginterpretasi bukti. Lihat `docs/roadmap.md` #18d.
