# 📚 Dokumentasi Proyek — IDX-BEI Research Platform

Seluruh dokumentasi dirapikan ke satu folder `docs/` agar mudah dinavigasi.
Indeks di bawah adalah pintu masuk utama.

> **Status proyek:** Fase 0–26 selesai. Phase 25 (UI/UX) Iterasi 1–8 selesai.

---

## Konten (`docs/`)

| File                                             | Isi                                                                      | Untuk siapa          |
| ------------------------------------------------ | ------------------------------------------------------------------------ | -------------------- |
| [README.md](README.md)                           | **Indeks ini** — peta semua dokumentasi                                  | Semua                |
| [quickstart.md](quickstart.md)                   | Install, jalankan scraper/pipeline, jalankan web server                  | Developer baru       |
| [architecture.md](architecture.md)               | Arsitektur sistem, alur data, modul utama                                | Developer            |
| [data-pipeline.md](data-pipeline.md)             | Scraping oleh pipeline (`run_pipeline.py`), jadwal, caching              | Ops / Data           |
| [data-flow.md](data-flow.md)                     | **Alur data & analisa otomatis (scheduling) — diagram, untuk user awam** | Semua / User         |
| [usage-guide.md](usage-guide.md)                 | Panduan pemakaian modul & API dengan contoh                              | User / Developer     |
| [api.md](api.md)                                 | Referensi endpoint REST                                                  | Frontend / Integrasi |
| [roadmap.md](roadmap.md)                         | Roadmap UI/UX & fitur (fase, iterasi, status)                            | Product              |
| [troubleshooting.md](troubleshooting.md)         | Masalah umum & solusi                                                    | Semua                |
| [database-setup.md](database-setup.md)           | Setup PostgreSQL                                                         | Ops                  |
| [database-migrations.md](database-migrations.md) | Migrasi schema DB                                                        | Developer            |
| [llm-configuration.md](llm-configuration.md)     | Konfigurasi LLM (OpenAI/Ollama/vLLM)                                     | AI                   |
| [news-brave.md](news-brave.md)                   | **Desain integrasi Brave Search untuk berita (Next Phase / MVP)**        | Data / Product       |
| [action-plan.md](action-plan.md)                 | Rencana aksi / langkah pengembangan                                      | Maintainer           |
| [progress-log.md](progress-log.md)               | Log progres per fase                                                     | Maintainer           |

> **Prompt spec (sumber, bukan dokumentasi):** file `.md` di `prompt/` (`stock-valuation.md`,
> `technical-analysis.md`, `stock-screener.md`, dst.) adalah spesifikasi prompt yang diimplementasikan
> di `ai/prompts/*.py`. Lihat [AGENTS.md → Prompt Integration Roadmap](../AGENTS.md).

---

## Alur baca yang disarankan

1. **Baru di proyek?** → mulai dari [quickstart.md](quickstart.md).
2. **Paham alur otomatis?** → [data-flow.md](data-flow.md) (diagram, untuk semua) lalu [architecture.md](architecture.md) / [data-pipeline.md](data-pipeline.md).
3. **Pakai API / UI?** → [api.md](api.md) dan [roadmap.md](roadmap.md).
4. **Masalah saat setup/run?** → [troubleshooting.md](troubleshooting.md).

---

## Ringkasan status fitur (per fase)

| Fase | Deskripsi                                                                                                                                        | Status |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ------ |
| 0–23 | Deterministik: model, fundamental, teknis, valuasi, screener, Neo4j, news/event, backtest, AI tools, researcher, report, memory, RAG, prompt API | ✅     |
| 24   | Data pipeline (scraper → PostgreSQL → AI tools)                                                                                                  | ✅     |
| 25   | UI/UX (dashboard, halaman saham, screener, compare, news, AI chat, export, grafik fundamental, screener AI, research memory, watchlist+alert)    | ✅     |
| 26   | Real-time updates (pipeline terjadwal + cache TTL)                                                                                               | ✅     |

---

## Catatan struktur repo

- `python/` — kode backend (scrapers, analysis, ai, api, database, web).
- `prompt/` — spesifikasi prompt (sumber).
- `docs/` — semua dokumentasi (folder ini).
- `AGENTS.md` — aturan & roadmap kerja untuk agent AI (jangan dihapus).
