const API = "";
let stocks = [];
let favorites = new Set();
let favoritesDetails = {};
let triggeredAlerts = [];
let activeSectors = [];
let stocksPage = 1;
let stocksPageSize = 25;
let sortKey = "";
let sortDir = "asc";
let currentTicker = null;
let currentStockSector = "";
let priceChart = null;
let volumeChart = null;
let chartRange = 365;
let chartType = "line";
let fullPriceData = [];
let visibleIndicators = new Set(["sma20", "sma50"]);
// Fundamentals chart state
let fundamentalChart = null;
let fundamentalData = [];
let currentFundamentalMetric = "revenue";

// Export / screener / compare tracking state
let stocksView = [];
let lastScreenData = { results: [] };
let screenSortState = { key: "score", dir: "desc" };
let lastCompareData = { stocks: [], tickers: [] };
// AI chat state
let aiStreaming = false;
let aiHistory = [];

async function fetchJSON(path, opts) {
  const res = await fetch(API + path, opts);
  if (!res.ok) throw new Error("HTTP " + res.status);
  return res.json();
}

function fmtIDR(n) {
  if (n === null || n === undefined) return "—";
  return "Rp " + Number(n).toLocaleString("id-ID");
}
function fmtNum(n) {
  if (n === null || n === undefined) return "—";
  return Number(n).toLocaleString("id-ID");
}

// ---------- Dashboard ----------
async function loadDashboard() {
  showView("view-dashboard");
  try {
    const data = await fetchJSON("/stocks");
    stocks = data.stocks || [];
    renderDashboardStats();
    renderSectorFilters();
    renderStocksTable();
    await loadFavorites();
    if (favorites.size > 0) renderFavorites();
    loadMacroImpact();
  } catch (e) {
    showError("Gagal memuat data saham: " + e.message);
  }
}

function renderDashboardStats() {
  const priced = stocks.filter((s) => s.close != null);
  const advancers = priced.filter((s) => (s.change || 0) > 0).length;
  const decliners = priced.filter((s) => (s.change || 0) < 0).length;
  const totalUp = priced.reduce((a, s) => a + (s.change_pct || 0), 0);
  document.getElementById("dashboardStats").innerHTML =
    stat("Total Saham", stocks.length, "emiten IDX") +
    stat("Dengan Harga", priced.length, "memiliki data harga") +
    stat("Naik", advancers, "advancers", "up") +
    stat("Turun", decliners, "decliners", "down");
}
function stat(label, value, sub, cls) {
  return `<div class="stat-card"><div class="label">${label}</div><div class="value ${cls || ""}">${value}</div><div class="sub">${sub}</div></div>`;
}

// ---------- Macro Impact / Research Candidates (Dashboard) ----------
async function loadMacroImpact(force) {
  const el = document.getElementById("macroImpact");
  const meta = document.getElementById("macroMeta");
  const llmEl = document.getElementById("macroLLM");
  if (!el) return;
  if (!force) {
    el.innerHTML = '<div class="loading">Memuat dampak makro...</div>';
  }
  try {
    // Read the persisted daily candidates (deterministic sector/ticker list).
    const data = await fetchJSON("/research/candidates?hours=48");
    renderMacroImpact(data);
  } catch (e) {
    el.innerHTML = `<div class="loading">Gagal memuat dampak makro: ${e.message}</div>`;
    if (meta) meta.textContent = "";
  }
}

function renderMacroImpact(data) {
  const el = document.getElementById("macroImpact");
  const meta = document.getElementById("macroMeta");
  const llmEl = document.getElementById("macroLLM");
  if (!el) return;
  const cands = (data && data.candidates) || [];
  if (!cands.length) {
    el.innerHTML =
      '<div class="loading">Belum ada kandidat riset pada periode ini. Jalankan pipeline berita makro terlebih dahulu.</div>';
    if (meta) meta.textContent = "";
    if (llmEl) llmEl.style.display = "none";
    return;
  }
  // Only show the latest batch (hide older candidate_dates); a sector/ticker may
  // appear on several dates, keep only the most recent row per key.
  const latestDate =
    cands
      .map((c) => c.candidate_date)
      .filter(Boolean)
      .sort()
      .pop() || "";
  const latest = cands.filter((c) => c.candidate_date === latestDate);
  el.innerHTML = groupMacroCandidates(latest);
  if (meta) {
    const when = latestDate || "—";
    meta.textContent = `${latest.length} kandidat · ${data.hours || 48} jam · ${when}`;
  }
  if (llmEl) {
    const text = (data.llm_analysis || "").trim();
    if (text) {
      llmEl.style.display = "block";
      llmEl.innerHTML =
        '<div class="markdown-body"><strong>Interpretasi AI:</strong>' +
        mdToHtml(text) +
        "</div>";
    } else {
      llmEl.style.display = "none";
    }
  }
}

function macroCard(c) {
  const conf = c.confidence
    ? (Number(c.confidence) * 100).toFixed(0) + "%"
    : "—";
  const ticker = c.ticker;
  const title = ticker
    ? `<button class="macro-chip macro-chip-btn" onclick="openResearchCandidate('${ticker}')">${ticker}</button>`
    : `<span class="macro-chip">Sektor</span>`;
  // Latest price change for a ticker candidate (from the loaded `/stocks` list).
  let priceHtml = "";
  if (ticker) {
    const s = (stocks || []).find((x) => x.ticker === ticker);
    if (s) {
      const chg = s.change_pct;
      const chgCls =
        chg == null ? "muted" : chg > 0 ? "up" : chg < 0 ? "down" : "muted";
      const chgTxt =
        chg == null ? "—" : (chg > 0 ? "+" : "") + Number(chg).toFixed(2) + "%";
      priceHtml = `<div class="macro-price"><span>${fmtIDR(s.close)}</span><span class="${chgCls}">${chgTxt}</span></div>`;
    }
  }
  return `<div class="macro-card">
    <div class="macro-ticks">${title}</div>
    <div class="macro-counts">
      <span class="muted" style="font-size: 0.72rem">conf ${conf}</span>
    </div>
    ${priceHtml}
  </div>`;
}

function groupMacroCandidates(cands) {
  // Group by sector, preserving first-appearance order; ticker and sector-level
  // rows for the same sector are rendered under a single sector header.
  const groups = new Map();
  const order = [];
  cands.forEach((c) => {
    const s = c.sector || "Unknown";
    if (!groups.has(s)) {
      groups.set(s, []);
      order.push(s);
    }
    groups.get(s).push(c);
  });
  return order
    .map((sector) => {
      const items = groups.get(sector);
      // Sector header: dominant direction + net from the first (most relevant) row.
      const head = items[0] || {};
      const dir = head.direction || "neutral";
      const arrow = dir === "positive" ? "▲" : dir === "negative" ? "▼" : "•";
      const cls =
        dir === "positive" ? "up" : dir === "negative" ? "down" : "muted";
      const net = Number(head.net_strength || 0);
      // Only render ticker-level cards; the sector theme is already the group
      // header, so a bare sector-level (ticker=null) card would be an empty box.
      const tickerItems = items.filter((c) => c.ticker);
      const cards = tickerItems.map((c) => macroCard(c)).join("");
      return `<section class="macro-group">
        <div class="macro-group-head">
          <span class="macro-sector">${sector}</span>
          <span class="macro-net ${cls}">${arrow} ${net.toFixed(2)}</span>
          <span class="muted" style="font-size: 0.75rem">${dir === "positive" ? "Positif" : dir === "negative" ? "Negatif" : "Netral"} · ${tickerItems.length} saham</span>
        </div>
        <div class="macro-grid">${cards}</div>
      </section>`;
    })
    .join("");
}

async function openResearchCandidate(ticker) {
  await openStock(ticker);
  switchStockTab("research");
}

function renderSectorFilters() {
  const sectors = [...new Set(stocks.map((s) => s.sector).filter(Boolean))];
  const container = document.getElementById("sectorFilters");
  // Always render a clear-all ("Semua") chip plus each sector.
  const chip = (label, sel, click, extraCls) =>
    `<button class="${sel ? "active" : ""} ${extraCls || ""}" onclick="${click}">${label}</button>`;
  const allChip = chip("Semua", activeSectors.length === 0, "setSectorsAll()");
  const sectorChips = sectors
    .map((s) =>
      chip(
        s,
        activeSectors.includes(s),
        `toggleSector('${s.replace(/'/g, "\\'")}')`,
      ),
    )
    .join("");
  const hint =
    activeSectors.length >= 3
      ? '<span class="sector-hint">Maks 3 sektor</span>'
      : `<span class="sector-hint">${activeSectors.length}/3</span>`;
  container.innerHTML =
    `<div class="sector-filter">${allChip}${sectorChips}</div>` +
    `<div class="sector-hint-row">${hint}</div>`;
}

function toggleSector(s) {
  if (activeSectors.includes(s)) {
    activeSectors = activeSectors.filter((x) => x !== s);
  } else {
    if (activeSectors.length >= 3) {
      showError("Maksimal 3 sektor dapat dipilih sekaligus.");
      return;
    }
    activeSectors.push(s);
  }
  stocksPage = 1;
  renderSectorFilters();
  renderStocksTable();
}

function setSectorsAll() {
  activeSectors = [];
  stocksPage = 1;
  renderSectorFilters();
  renderStocksTable();
}

function renderStocksTable() {
  const q = (document.getElementById("stockFilter").value || "").toLowerCase();
  const filtered = stocks.filter(
    (s) =>
      (activeSectors.length === 0 || activeSectors.includes(s.sector)) &&
      (!q || (s.ticker + " " + s.name).toLowerCase().includes(q)),
  );
  // Sorting: click a header to toggle (none/asc/desc → next cycle).
  if (sortKey) {
    filtered.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      const an = Number(av);
      const bn = Number(bv);
      const useNum = !Number.isNaN(an) && !Number.isNaN(bn);
      if (useNum) return (an - bn) * (sortDir === "asc" ? 1 : -1);
      const cmp = String(av ?? "").localeCompare(String(bv ?? ""));
      return cmp * (sortDir === "asc" ? 1 : -1);
    });
  }
  stocksView = filtered;
  const total = filtered.length;
  const pages = Math.max(1, Math.ceil(total / stocksPageSize));
  stocksPage = Math.min(Math.max(1, stocksPage), pages);
  const start = (stocksPage - 1) * stocksPageSize;
  const pageRows = filtered.slice(start, start + stocksPageSize);
  const body = pageRows
    .map((s) => {
      const chg = s.change_pct;
      const cls = chg > 0 ? "up" : chg < 0 ? "down" : "muted";
      const chgTxt =
        chg == null ? "—" : (chg > 0 ? "+" : "") + chg.toFixed(2) + "%";
      const star = favorites.has(s.ticker) ? "★" : "☆";
      return `<tr onclick="openStock('${s.ticker}')">
                    <td><span class="star-row" onclick="event.stopPropagation(); toggleFavorite('${s.ticker}')">${star}</span></td>
                    <td><span class="ticker-badge">${s.ticker}</span></td>
                    <td>${s.name}</td>
                    <td class="muted">${s.sector || "—"}</td>
                    <td>${fmtIDR(s.close)}</td>
                    <td class="${cls}">${chgTxt}</td>
                    <td>${fmtNum(s.volume)}</td>
                    <td class="muted">${s.date || "—"}</td>
                </tr>`;
    })
    .join("");
  document.getElementById("stocksBody").innerHTML =
    body || '<tr><td colspan="8" class="loading">Tidak ada hasil</td></tr>';
  updateSortMarks();
  renderStocksPagination(total, pages);
}

function updateSortMarks() {
  document.querySelectorAll("#sub-market th.sortable").forEach((th) => {
    const mark = th.querySelector(".sort-mark");
    const key = th.dataset.key;
    th.classList.toggle("sorted", sortKey === key);
    if (mark) mark.textContent = sortArrow(key);
  });
}

function sortStocks(key) {
  if (sortKey === key) {
    // cycle: asc -> desc -> none
    if (sortDir === "asc") sortDir = "desc";
    else if (sortDir === "desc") {
      sortKey = "";
      sortDir = "asc";
    } else sortDir = "asc";
  } else {
    sortKey = key;
    sortDir = "asc";
  }
  renderStocksTable();
}

function sortArrow(key) {
  if (sortKey !== key) return "";
  return sortDir === "asc" ? " ▲" : " ▼";
}

function renderStocksPagination(total, pages) {
  const el = document.getElementById("stocksPagination");
  if (!el) return;
  const start = total === 0 ? 0 : (stocksPage - 1) * stocksPageSize + 1;
  const end = Math.min(stocksPage * stocksPageSize, total);
  const btn = (label, page, disabled, cls) =>
    `<button class="pag-btn ${cls || ""}" ${disabled ? "disabled" : ""} onclick="gotoStocksPage(${page})">${label}</button>`;
  el.innerHTML =
    `<div class="pagination">` +
    `<span class="pag-info">Menampilkan ${start}-${end} dari ${total} · hal ${stocksPage}/${pages}</span>` +
    `<div class="pag-controls">` +
    btn("«", 1, stocksPage === 1) +
    btn("‹", stocksPage - 1, stocksPage === 1) +
    btn(stocksPage, stocksPage, true, "active") +
    btn("›", stocksPage + 1, stocksPage >= pages) +
    btn("»", pages, stocksPage >= pages) +
    `</div></div>`;
}

function gotoStocksPage(page) {
  stocksPage = page;
  renderStocksTable();
}

async function loadFavorites() {
  try {
    const d = await fetchJSON("/favorites");
    favorites = new Set(d.tickers || []);
  } catch (e) {
    favorites = new Set();
  }
  await Promise.all([loadFavoritesDetails(), loadAlerts()]);
  renderFavorites();
}

async function loadFavoritesDetails() {
  try {
    const d = await fetchJSON("/favorites/details");
    favoritesDetails = {};
    (d.favorites || []).forEach((f) => (favoritesDetails[f.ticker] = f));
  } catch (e) {
    favoritesDetails = {};
  }
}

async function loadAlerts() {
  try {
    const d = await fetchJSON("/favorites/alerts");
    triggeredAlerts = d.alerts || [];
  } catch (e) {
    triggeredAlerts = [];
  }
  const banner = document.getElementById("alertsBanner");
  if (!banner) return;
  if (!triggeredAlerts.length) {
    banner.style.display = "none";
    return;
  }
  banner.style.display = "block";
  banner.innerHTML =
    "<strong>" +
    triggeredAlerts.length +
    " alert harga tersentuh:</strong> " +
    triggeredAlerts
      .map(
        (a) =>
          '<span class="alert-chip" onclick="openStock(\'' +
          a.ticker +
          "')\">" +
          a.ticker +
          " " +
          fmtIDR(a.alert_price) +
          "</span>",
      )
      .join(" ");
}

async function setAlert(tickerArg) {
  const t = (tickerArg || currentTicker || "").toUpperCase();
  const input = document.getElementById("alertInput-" + t);
  const val = input ? input.value.replace(/[^\d.]/g, "") : "";
  const price = Number(val);
  if (!price || price <= 0) {
    showError("Masukkan target harga yang valid.");
    return;
  }
  const dir = document.getElementById("alertDir-" + t);
  const direction = dir ? dir.value : "above";
  try {
    await fetchJSON("/favorites/" + t + "/alert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ alert_price: price, direction }),
    });
    favorites.add(t);
    await loadFavorites();
  } catch (e) {
    showError("Gagal set alert: " + e.message);
  }
}

async function clearAlert(tickerArg) {
  const t = (tickerArg || "").toUpperCase();
  try {
    await fetchJSON("/favorites/" + t + "/alert", { method: "DELETE" });
    await loadFavorites();
  } catch (e) {
    showError("Gagal hapus alert: " + e.message);
  }
}

async function renderFavorites() {
  const grid = document.getElementById("favoritesGrid");
  const favStocks = stocks.filter((s) => favorites.has(s.ticker));
  grid.innerHTML =
    favStocks
      .map((s) => {
        const chg = s.change_pct;
        const cls = chg > 0 ? "up" : chg < 0 ? "down" : "muted";
        const det = favoritesDetails[s.ticker] || {};
        const hasAlert = det.alert_enabled && det.alert_price;
        const dirVal = det.alert_direction || "above";
        const alertCtl = hasAlert
          ? '<div class="alert-ctl"><span class="alert-on">🔔 ' +
            fmtIDR(det.alert_price) +
            " (" +
            det.alert_direction +
            ')</span><button class="alert-btn" onclick="event.stopPropagation(); clearAlert(\'' +
            s.ticker +
            "')\">×</button></div>"
          : '<div class="alert-ctl"><input id="alertInput-' +
            s.ticker +
            '" type="text" placeholder="target" inputmode="decimal"><select id="alertDir-' +
            s.ticker +
            '"><option value="above">≥</option><option value="below">≤</option></select><button class="alert-btn" onclick="event.stopPropagation(); setAlert(\'' +
            s.ticker +
            "')\">🔔</button></div>";
        return `<div class="fav-card" onclick="openStock('${s.ticker}')">
                    <span class="star on" onclick="event.stopPropagation(); toggleFavorite('${s.ticker}')">★</span>
                    <div class="ticker">${s.ticker}</div>
                    <div class="name">${s.name || ""}</div>
                    <div class="price-row"><span class="price">${fmtIDR(s.close)}</span><span class="change ${cls}">${chg == null ? "—" : (chg > 0 ? "+" : "") + chg.toFixed(2) + "%"}</span></div>
                    <div class="muted" style="font-size:.78rem">${s.sector || ""}</div>
                    ${alertCtl}
                </div>`;
      })
      .join("") ||
    '<div class="muted">Belum ada favorit. Klik ☆ pada saham untuk menambahkan.</div>';
}

async function toggleFavorite(tickerArg) {
  const t = tickerArg || currentTicker;
  const isFav = favorites.has(t);
  const method = isFav ? "DELETE" : "POST";
  try {
    await fetchJSON("/favorites/" + t, { method: method });
    await loadFavorites();
    renderStocksTable();
    if (currentTicker) updateFavButton();
    renderFavorites();
  } catch (e) {
    showError("Gagal update favorit: " + e.message);
  }
}

function updateFavButton() {
  const btn = document.getElementById("favToggle");
  btn.textContent = favorites.has(currentTicker) ? "★ Favorit" : "☆ Tambahkan";
  btn.style.color = favorites.has(currentTicker) ? "#facc15" : "inherit";
}

let searchIdx = -1;

function searchSuggestions(q) {
  const list = stocks || [];
  const query = (q || "").trim().toLowerCase();
  if (!query) return list.slice(0, 8);
  const exact = list.filter(
    (s) => s.ticker && s.ticker.toLowerCase() === query,
  );
  const tickerPrefix = list.filter(
    (s) => s.ticker && s.ticker.toLowerCase().startsWith(query),
  );
  const namePrefix = list.filter((s) =>
    (s.name || "").toLowerCase().startsWith(query),
  );
  const nameSub = list.filter((s) =>
    (s.name || "").toLowerCase().includes(query),
  );
  const seen = new Set();
  const out = [];
  [...exact, ...tickerPrefix, ...namePrefix, ...nameSub].forEach((s) => {
    if (!seen.has(s.ticker)) {
      seen.add(s.ticker);
      out.push(s);
    }
  });
  return out.slice(0, 8);
}

function renderSearchDropdown() {
  const dd = document.getElementById("searchDropdown");
  if (!dd) return;
  const sugg = searchSuggestions(document.getElementById("globalSearch").value);
  if (!sugg.length) {
    dd.style.display = "none";
    return;
  }
  if (searchIdx >= sugg.length) searchIdx = sugg.length - 1;
  dd.style.display = "block";
  dd.innerHTML = sugg
    .map((s, i) => {
      const cls = i === searchIdx ? "active" : "";
      const meta = [s.sector, s.industry].filter(Boolean).join(" · ");
      return `<div class="search-item ${cls}" onclick="pickSearchSuggestion('${s.ticker}')">
        <span class="search-item-ticker">${s.ticker}</span>
        <span class="search-item-body">
          <span class="search-item-name">${s.name}</span>
          <span class="search-item-meta">${meta || ""}</span>
        </span>
      </div>`;
    })
    .join("");
}

function showSearchSuggestions() {
  searchIdx = -1;
  renderSearchDropdown();
}

function pickSearchSuggestion(ticker) {
  const input = document.getElementById("globalSearch");
  if (input) input.blur();
  hideSearchDropdown();
  openStock(ticker);
}

function hideSearchDropdown() {
  const dd = document.getElementById("searchDropdown");
  if (dd) dd.style.display = "none";
  searchIdx = -1;
}

function maybeOpenStock(e) {
  if (e.key === "Enter") {
    e.preventDefault();
    const sugg = searchSuggestions(
      document.getElementById("globalSearch").value,
    );
    const pick = sugg[searchIdx >= 0 ? searchIdx : 0];
    if (pick && pick.ticker) {
      pickSearchSuggestion(pick.ticker);
    } else {
      showError("Saham tidak ditemukan.");
    }
  } else if (e.key === "ArrowDown") {
    e.preventDefault();
    const sugg = searchSuggestions(
      document.getElementById("globalSearch").value,
    );
    if (sugg.length) {
      searchIdx = (searchIdx + 1) % sugg.length;
      renderSearchDropdown();
    }
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    const sugg = searchSuggestions(
      document.getElementById("globalSearch").value,
    );
    if (sugg.length) {
      searchIdx = (searchIdx - 1 + sugg.length) % sugg.length;
      renderSearchDropdown();
    }
  } else if (e.key === "Escape") {
    hideSearchDropdown();
  } else {
    renderSearchDropdown();
  }
}

// ---------- Stock Detail ----------
async function openStock(ticker) {
  currentTicker = ticker.toUpperCase();
  currentStockSector = "";
  history.pushState({ ticker: currentTicker }, "", "/stock/" + currentTicker);
  showView("view-stock");
  document.getElementById("dTicker").textContent = currentTicker;
  document.getElementById("dName").textContent = "Memuat...";
  document.getElementById("dPrice").textContent = "—";
  document.getElementById("dPriceMeta").textContent = "—";
  updateFavButton();
  switchStockTab("chart");
  aiHistory = [];
  aiStreaming = false;

  try {
    const data = await fetchJSON("/stocks/" + currentTicker);
    const p = data.profile || {};
    document.getElementById("dName").textContent = p.name || data.ticker;
    document.getElementById("dTicker").textContent = data.ticker;
    const q = data.quote || {};
    document.getElementById("dPrice").textContent = fmtIDR(q.price);
    document.getElementById("dPriceMeta").textContent =
      (q.as_of ? "per " + q.as_of : "") +
      (q.volume ? " · Vol " + fmtNum(q.volume) : "");
    renderProfile(p);
    renderMetrics(data.metrics || {});
    currentStockSector = p.sector || "";
  } catch (e) {
    showError("Gagal memuat detail: " + e.message);
  }

  loadPriceChart();
  loadAnalysis();
  loadNews();
  loadFundamentalHistory();
  loadResearchHistory();
  loadResearchCandidates();
}

function renderProfile(p) {
  const items = [
    ["Nama", p.name],
    ["Ticker", p.ticker],
    ["Sektor", p.sector],
    ["Industri", p.industry],
    ["Papan", p.board],
    ["Tanggal Listing", p.listing_date],
  ];
  document.getElementById("profileGrid").innerHTML =
    items
      .filter((i) => i[1])
      .map(
        (i) =>
          `<div class="profile-item"><div class="k">${i[0]}</div><div class="v">${i[1]}</div></div>`,
      )
      .join("") || '<div class="muted">Data profil belum tersedia.</div>';
}

const METRIC_LABELS = {
  pe_ratio: "P/E Ratio",
  pb_ratio: "P/B Ratio",
  ev_ebitda: "EV/EBITDA",
  dividend_yield: "Dividend Yield",
  roe: "ROE",
  roa: "ROA",
  roic: "ROIC",
  gross_margin: "Gross Margin",
  operating_margin: "Operating Margin",
  net_margin: "Net Margin",
  debt_to_equity: "Debt / Equity",
  current_ratio: "Current Ratio",
  interest_coverage: "Interest Coverage",
  revenue: "Revenue",
  net_income: "Net Income",
  eps: "EPS",
  total_assets: "Total Assets",
};
function fmtMetric(k, v) {
  if (v == null) return "—";
  const n = Number(v);
  const pctKeys = [
    "roe",
    "roa",
    "roic",
    "gross_margin",
    "operating_margin",
    "net_margin",
    "dividend_yield",
  ];
  if (pctKeys.includes(k)) return n.toFixed(2) + "%";
  if (["revenue", "net_income", "total_assets", "eps"].includes(k))
    return fmtIDR(n);
  return n.toLocaleString("id-ID", { maximumFractionDigits: 2 });
}
function renderMetrics(m) {
  const entries = Object.entries(m).filter(
    ([k, v]) => METRIC_LABELS[k] && v != null,
  );
  document.getElementById("metricGrid").innerHTML =
    entries
      .map(
        ([k, v]) =>
          `<div class="metric"><div class="k">${METRIC_LABELS[k]}</div><div class="v">${fmtMetric(k, v)}</div></div>`,
      )
      .join("") ||
    '<div class="muted">Data fundamental belum tersedia untuk saham ini.</div>';
}

// ---------- Chart ----------
async function loadPriceChart() {
  try {
    const data = await fetchJSON(`/stocks/${currentTicker}/prices?limit=5000`);
    fullPriceData = data.prices || [];
    renderChart();
  } catch (e) {
    showError("Gagal memuat grafik: " + e.message);
  }
}
function setChartRange(days) {
  chartRange = days;
  document
    .querySelectorAll("#chartControls button")
    .forEach((b) =>
      b.classList.toggle("active", Number(b.dataset.days) === days),
    );
  renderChart();
}

function setChartType(type) {
  chartType = type;
  document
    .querySelectorAll("#chartTypeControls button")
    .forEach((b) => b.classList.toggle("active", b.dataset.chart === type));
  renderChart();
}

function toggleIndicator(ind) {
  if (visibleIndicators.has(ind)) visibleIndicators.delete(ind);
  else visibleIndicators.add(ind);
  document
    .querySelectorAll("#indicatorControls button")
    .forEach((b) =>
      b.classList.toggle("active", visibleIndicators.has(b.dataset.ind)),
    );
  renderChart();
}

function rgba(hex, a) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

function sma(data, period) {
  const out = data.map(() => null);
  let sum = 0;
  for (let i = 0; i < data.length; i++) {
    sum += data[i];
    if (i >= period) sum -= data[i - period];
    if (i >= period - 1) out[i] = sum / period;
  }
  return out;
}

function bollinger(data, period, mult) {
  const mid = sma(data, period);
  const upper = data.map(() => null);
  const lower = data.map(() => null);
  for (let i = period - 1; i < data.length; i++) {
    let sumSq = 0;
    for (let j = i - period + 1; j <= i; j++) {
      const diff = data[j] - mid[i];
      sumSq += diff * diff;
    }
    const sd = Math.sqrt(sumSq / period);
    upper[i] = mid[i] + mult * sd;
    lower[i] = mid[i] - mult * sd;
  }
  return { mid, upper, lower };
}

function renderVolumeChart(labels, data) {
  const cv = document.getElementById("volumeChart");
  if (!cv) return;
  if (volumeChart) volumeChart.destroy();
  volumeChart = new Chart(cv, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          data: data.volume,
          backgroundColor: data.volume.map((v, i) =>
            v && data.close[i] >= data.open[i]
              ? "rgba(34,197,94,0.5)"
              : "rgba(239,68,68,0.5)",
          ),
          borderWidth: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { display: false, grid: { display: false } },
        y: {
          ticks: { color: "#9aa3b5", maxTicksLimit: 4 },
          grid: { color: "rgba(158,170,190,.08)" },
        },
      },
    },
  });
}

// Draw candlesticks manually over a standard line chart (category x-axis).
// This avoids the fragile chartjs-chart-financial controller whose timeseries
// + parsing:false setup left an empty 0-1 chart.
const CandlePlugin = {
  id: "candle",
  afterDatasetsDraw(chart) {
    const candles = chart.$candles;
    if (!candles || !candles.length) return;
    const { ctx, scales } = chart;
    const xScale = scales.x;
    const yScale = scales.y;
    const meta = chart.getDatasetMeta(0); // base invisible line gives x positions
    const bw = Math.max(
      1.5,
      (meta.data[0] ? meta.data[0].width || 2 : 2) * 0.7,
    );
    ctx.save();
    candles.forEach((d, i) => {
      const el = meta.data[i];
      if (!el || el.x == null) return;
      const x = el.x;
      const o = yScale.getPixelForValue(d.open);
      const h = yScale.getPixelForValue(d.high);
      const l = yScale.getPixelForValue(d.low);
      const c = yScale.getPixelForValue(d.close);
      const up = c < o; // close < open -> green (idx convention: green = down? default)
      const color = d.close >= d.open ? "#26a69a" : "#ef5350";
      ctx.strokeStyle = color;
      ctx.fillStyle = color;
      ctx.lineWidth = 1;
      // Wick
      ctx.beginPath();
      ctx.moveTo(x, h);
      ctx.lineTo(x, l);
      ctx.stroke();
      // Body
      const top = Math.min(o, c);
      const height = Math.max(Math.abs(o - c), 1);
      ctx.fillRect(x - bw / 2, top, bw, height);
      ctx.strokeRect(x - bw / 2, top, bw, height);
    });
    ctx.restore();
  },
};
if (typeof Chart !== "undefined") Chart.register(CandlePlugin);

function renderChart() {
  const canvas = document.getElementById("priceChart");
  if (!fullPriceData.length) return;
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - chartRange);
  const series = fullPriceData.filter((d) => new Date(d.date) >= cutoff);
  const labels = series.map((d) => d.date);
  const closes = series.map((d) => d.close);
  const volume = series.map((d) => d.volume);
  const open = series.map((d) => d.open);
  const isCandle = chartType === "candlestick";

  // Price dataset: line (default, guaranteed to show movement). In candlestick
  // mode we keep an invisible line base so the standard category axis works and
  // the CandlePlugin draws OHLC bodies/wicks on top.
  const datasets = [
    isCandle
      ? {
          type: "line",
          label: "OHLC",
          data: closes,
          borderWidth: 0,
          pointRadius: 0,
          fill: false,
        }
      : {
          type: "line",
          label: "Harga",
          data: closes,
          borderColor: "#4f7cff",
          backgroundColor: "rgba(79,124,255,0.08)",
          borderWidth: 1.8,
          pointRadius: 0,
          fill: true,
          tension: 0.1,
        },
  ];

  // Indicator overlays are plain number arrays on the category axis in both modes.
  const addLine = (label, data, color, width) => {
    datasets.push({
      type: "line",
      label,
      data,
      borderColor: color,
      borderWidth: width,
      pointRadius: 0,
      fill: false,
    });
  };

  if (visibleIndicators.has("sma20"))
    addLine("SMA 20", sma(closes, 20), "#4f7cff", 1.4);
  if (visibleIndicators.has("sma50"))
    addLine("SMA 50", sma(closes, 50), "#22d3ee", 1.4);
  if (visibleIndicators.has("sma200"))
    addLine("SMA 200", sma(closes, 200), "#facc15", 1.4);
  if (visibleIndicators.has("bollinger")) {
    const bb = bollinger(closes, 20, 2);
    addLine("BB Upper", bb.upper, "rgba(167,139,250,0.7)", 1);
    datasets.push({
      type: "line",
      label: "BB Lower",
      data: bb.lower,
      borderColor: "rgba(167,139,250,0.7)",
      borderWidth: 1,
      pointRadius: 0,
      fill: "-1",
      backgroundColor: "rgba(167,139,250,0.08)",
    });
  }

  if (priceChart) priceChart.destroy();
  priceChart = new Chart(canvas, {
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          labels: { color: "#9aa3b5", boxWidth: 12, font: { size: 11 } },
        },
      },
      scales: {
        x: {
          type: "category",
          ticks: { color: "#9aa3b5", maxTicksLimit: 8 },
          grid: { color: "rgba(158,170,190,.08)" },
        },
        y: {
          ticks: { color: "#9aa3b5" },
          grid: { color: "rgba(158,170,190,.08)" },
          ...(isCandle && series.length
            ? {
                suggestedMin: Math.min(...series.map((d) => d.low ?? d.close)),
                suggestedMax: Math.max(...series.map((d) => d.high ?? d.close)),
              }
            : {}),
        },
      },
    },
  });
  // Hand the raw OHLC series to the manual candle renderer (category axis).
  if (isCandle) priceChart.$candles = series;

  renderVolumeChart(labels, { volume, close: closes, open });
}

// ---------- Analysis ----------
async function loadAnalysis() {
  const f = document.getElementById("analysisFundamental");
  const t = document.getElementById("analysisTechnical");
  const v = document.getElementById("analysisValuation");
  f.innerHTML = '<div class="loading">Memuat fundamental...</div>';
  t.innerHTML = '<div class="loading">Memuat technical...</div>';
  v.innerHTML = '<div class="loading">Memuat valuation...</div>';

  fetchJSON("/stocks/" + currentTicker + "/fundamentals")
    .then((d) => {
      f.innerHTML = renderAnalysisRows(d);
    })
    .catch(
      () =>
        (f.innerHTML =
          '<div class="muted">Data fundamental tidak tersedia.</div>'),
    );

  fetchJSON("/stocks/" + currentTicker + "/technical")
    .then((d) => {
      t.innerHTML = renderAnalysisRows(d);
    })
    .catch(
      () =>
        (t.innerHTML =
          '<div class="muted">Data technical tidak tersedia.</div>'),
    );

  fetchJSON("/stocks/" + currentTicker + "/valuation")
    .then((d) => {
      v.innerHTML = renderAnalysisRows(d);
    })
    .catch(
      () =>
        (v.innerHTML =
          '<div class="muted">Data valuation tidak tersedia.</div>'),
    );
}
function renderAnalysisRows(d) {
  if (!d) return '<div class="muted">Tidak ada data.</div>';
  const skipKeys = new Set([
    "ticker",
    "calculated_at",
    "source",
    "as_of",
    "notes",
    "currency",
    "unit",
  ]);
  const human = (k) => String(k).replace(/_/g, " ");
  const html = (v) => {
    if (v === null || v === undefined) return "—";
    if (typeof v === "boolean") return v ? "✓" : "✗";
    if (typeof v === "number")
      return Number.isFinite(v)
        ? v.toLocaleString(undefined, { maximumFractionDigits: 4 })
        : "—";
    return escapeHtml(String(v));
  };
  // Render a single dict entry: if it has derived fields (value/signal) show them inline.
  const renderEntry = (key, val) => {
    if (val && typeof val === "object" && !Array.isArray(val) && val !== null) {
      // A structured metric dict (value + signal + is_available) -> one row.
      if ("value" in val || "metric_name" in val || "is_available" in val) {
        const detail = [];
        if ("value" in val) detail.push(html(val.value));
        if ("signal" in val && val.signal)
          detail.push("<em>" + escapeHtml(String(val.signal)) + "</em>");
        if ("is_available" in val && val.is_available === false)
          detail.push("<span class='muted'>unavailable</span>");
        return (
          '<div class="row"><span class="label">' +
          escapeHtml(human(key)) +
          "</span><span>" +
          (detail.join(" · ") || "—") +
          "</span></div>"
        );
      }
      // Otherwise render as a sub-group (nested dict, e.g. inputs / historical_comparison).
      const children = Object.entries(val)
        .filter(([k2, v2]) => typeof v2 !== "function")
        .map(([k2, v2]) => renderEntry(k2, v2))
        .join("");
      return children
        ? '<div class="row label">' +
            escapeHtml(human(key)) +
            "</div>" +
            children
        : '<div class="row"><span class="label">' +
            escapeHtml(human(key)) +
            "</span><span>—</span></div>";
    }
    if (Array.isArray(val)) {
      return (
        '<div class="row"><span class="label">' +
        escapeHtml(human(key)) +
        "</span><span>" +
        val.map(html).join(", ") +
        "</span></div>"
      );
    }
    return (
      '<div class="row"><span class="label">' +
      escapeHtml(human(key)) +
      "</span><span>" +
      html(val) +
      "</span></div>"
    );
  };
  const entries = Object.entries(d).filter(
    ([k, val]) => !skipKeys.has(k) && val != null && typeof val !== "function",
  );
  if (!entries.length)
    return (
      '<div class="muted">' +
      escapeHtml(d.notes || "Tidak ada data.") +
      "</div>"
    );
  return entries.map(([k, v]) => renderEntry(k, v)).join("");
}

// ---------- Fundamentals chart (multi-period) ----------
const FUNDAMENTAL_LABELS = {
  revenue: "Revenue",
  net_income: "Laba Bersih",
  operating_income: "Laba Operasi",
  net_margin: "Net Margin",
  gross_margin: "Gross Margin",
  roe: "ROE",
  debt_to_equity: "Debt/Eq",
};

async function loadFundamentalHistory() {
  const el = document.getElementById("fundamentalChart");
  if (!el) return;
  try {
    const d = await fetchJSON(
      "/stocks/" + currentTicker + "/financials/history",
    );
    fundamentalData = d.series || [];
    renderFundamentalChart();
  } catch (e) {
    showError("Gagal memuat grafik fundamental: " + e.message);
  }
}

function isPercentageMetric(key) {
  return ["net_margin", "gross_margin", "roe"].includes(key);
}

function setFundamentalMetric(key) {
  currentFundamentalMetric = key;
  document
    .querySelectorAll("#fundamentalControls button")
    .forEach((b) => b.classList.toggle("active", b.dataset.fmetric === key));
  renderFundamentalChart();
}

function renderFundamentalChart() {
  const el = document.getElementById("fundamentalChart");
  if (!el) return;
  const key = currentFundamentalMetric;
  const pct = isPercentageMetric(key);
  const labels = fundamentalData.map((r) =>
    r.period_end ? r.period_end.slice(0, 7) : r.fiscal_year || "",
  );
  const values = fundamentalData.map((r) => r[key] ?? null);
  if (fundamentalChart) fundamentalChart.destroy();
  fundamentalChart = new Chart(el, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: FUNDAMENTAL_LABELS[key] || key,
          data: values,
          borderColor: "#4fc3f7",
          backgroundColor: "rgba(79, 195, 247, 0.1)",
          fill: true,
          tension: 0.3,
          pointRadius: 4,
          pointBackgroundColor: "#4fc3f7",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: true, labels: { color: "#ced4da" } },
        tooltip: {
          callbacks: {
            label: (ctx) =>
              pct
                ? (ctx.parsed.y ?? 0).toFixed(2) + "%"
                : fmtIDR(ctx.parsed.y ?? 0),
          },
        },
      },
      scales: {
        x: {
          ticks: { color: "#ced4da", maxTicksLimit: 12 },
          grid: { color: "rgba(255,255,255,0.05)" },
        },
        y: {
          ticks: {
            color: "#ced4da",
            callback: (v) => (pct ? v + "%" : fmtIDR(v)),
          },
          grid: { color: "rgba(255,255,255,0.05)" },
        },
      },
    },
  });
}

// ---------- Navigation / tabs ----------
function showView(id) {
  document
    .querySelectorAll(".view")
    .forEach((v) => v.classList.remove("active"));
  document.getElementById(id).classList.add("active");
  if (id === "view-dashboard") document.getElementById("globalSearch").focus();
}
function showDashboard() {
  history.pushState({ ticker: null }, "", "/");
  loadDashboard();
}

async function loadResearchHistory() {
  const el = document.getElementById("researchHistory");
  if (!el) return;
  el.innerHTML = '<div class="loading">Memuat riwayat research...</div>';
  try {
    const d = await fetchJSON(
      "/stocks/" + currentTicker + "/research-history?limit=5",
    );
    const reports = d.reports || [];
    if (!reports.length) {
      el.innerHTML =
        '<p class="muted">Belum ada riset tersimpan untuk saham ini. Jalankan “AI Analisa Chat” untuk membuat thesis pertama.</p>';
      return;
    }
    el.innerHTML = reports
      .map((r, i) => {
        const sections = r.sections || {};
        const conf = r.confidence_score;
        const confTxt =
          typeof conf === "number" ? (conf * 100).toFixed(0) + "%" : "—";
        const verdict = r.overall_verdict || "—";
        const date = (r.generated_at || r.saved_at || "").slice(0, 16);
        const q = r.question
          ? '<div class="research-q">Pertanyaan: ' +
            escapeHtml(r.question) +
            "</div>"
          : "";
        // Render every non-empty section (the LLM writes the report content into
        // various sections, not always executive_summary/conclusion).
        const sectionOrder = [
          "executive_summary",
          "business_quality",
          "growth_analysis",
          "profitability",
          "financial_health",
          "valuation",
          "technical_position",
          "recent_events",
          "risks",
          "bull_case",
          "base_case",
          "bear_case",
          "conclusion",
        ];
        const contentBlocks = sectionOrder
          .filter((k) => sections[k])
          .map((k) => {
            const head = k.replace(/_/g, " ");
            return (
              '<div class="research-sec"><div class="research-sec-title">' +
              escapeHtml(head) +
              '</div><div class="research-sec-body">' +
              mdToHtml(sections[k]) +
              "</div></div>"
            );
          })
          .join("");
        return `<div class="research-item">
                <div class="research-head">
                  <div class="research-date">${date || "#" + (i + 1)}</div>
                  <div class="research-verdict">${escapeHtml(String(verdict))}</div>
                  <div class="research-conf">Confidence ${confTxt}</div>
                </div>
                ${q}
                ${
                  contentBlocks
                    ? '<details class="research-detail"><summary>Lihat analisis lengkap</summary>' +
                      contentBlocks +
                      "</details>"
                    : '<div class="muted">Tidak ada isi analisis tersimpan.</div>'
                }
              </div>`;
      })
      .join("");
  } catch (e) {
    el.innerHTML =
      '<p class="muted">Gagal memuat riwayat: ' +
      escapeHtml(e.message) +
      "</p>";
  }
}

async function loadResearchCandidates(force) {
  const el = document.getElementById("researchCandidateList");
  const llmEl = document.getElementById("researchCandidateLLM");
  if (!el) return;
  if (!force) el.innerHTML = '<div class="loading">Memuat kandidat...</div>';
  try {
    // Only show candidates related to the open ticker's own industry/sector.
    const fromList =
      (stocks || []).find((s) => s.ticker === currentTicker) || {};
    const sector = currentStockSector || fromList.sector || "";
    const params = new URLSearchParams({ hours: "48" });
    if (currentTicker) params.set("ticker", currentTicker);
    if (sector) params.set("sector", sector);
    const d = await fetchJSON("/research/candidates?" + params.toString());
    renderResearchCandidates(d, sector || currentTicker);
  } catch (e) {
    el.innerHTML =
      '<p class="muted">Gagal memuat kandidat: ' +
      escapeHtml(e.message) +
      "</p>";
  }
}

function renderResearchCandidates(data, scope) {
  const el = document.getElementById("researchCandidateList");
  const llmEl = document.getElementById("researchCandidateLLM");
  if (!el) return;
  const cands = (data && data.candidates) || [];
  if (!cands.length) {
    el.innerHTML =
      '<p class="muted">Tidak ada kandidat makro untuk ' +
      escapeHtml(String(scope || currentTicker || "saham ini")) +
      " (sektor/industrinya) pada 48 jam terakhir.</p>";
    if (llmEl) llmEl.style.display = "none";
    return;
  }
  el.innerHTML = cands
    .map((c) => {
      const dir = c.direction || "neutral";
      const arrow = dir === "positive" ? "▲" : dir === "negative" ? "▼" : "•";
      const cls =
        dir === "positive" ? "up" : dir === "negative" ? "down" : "muted";
      const conf = c.confidence
        ? (Number(c.confidence) * 100).toFixed(0) + "%"
        : "—";
      const ticker = c.ticker;
      const action = ticker
        ? `<div class="research-cand-action"><button class="back-btn" onclick="openStock('${ticker}')">Buka ${ticker}</button></div>`
        : "";
      return `<div class="research-cand">
        <div class="research-cand-head">
          <span class="research-cand-sector">${escapeHtml(c.sector)}</span>
          <span class="research-cand-ticker">${ticker ? escapeHtml(ticker) : "Sektor"}</span>
          <span class="research-cand-dir ${cls}">${arrow} ${dir === "positive" ? "Positif" : dir === "negative" ? "Negatif" : "Netral"}</span>
        </div>
        <div class="research-cand-meta">
          <span class="muted">conf ${conf}</span>
          <span class="muted">net ${Number(c.net_strength || 0).toFixed(2)}</span>
          <span class="muted">${escapeHtml(c.candidate_date || "")}</span>
        </div>
        ${c.reason ? `<div class="research-cand-reason">${escapeHtml(c.reason)}</div>` : ""}
        ${action}
      </div>`;
    })
    .join("");
  if (llmEl) {
    const text = (data.llm_analysis || "").trim();
    if (text) {
      llmEl.style.display = "block";
      llmEl.innerHTML =
        '<div class="markdown-body"><strong>Interpretasi AI (makro):</strong>' +
        mdToHtml(text) +
        "</div>";
    } else {
      llmEl.style.display = "none";
    }
  }
}

async function generateResearch() {
  const btn = document.getElementById("researchGenerateBtn");
  const status = document.getElementById("researchStatus");
  if (!currentTicker) {
    showError("Pilih saham terlebih dahulu.");
    return;
  }
  if (btn) btn.disabled = true;
  if (status) status.textContent = "Menganalisis menyeluruh...";
  try {
    const d = await fetchJSON(
      "/stocks/" + currentTicker + "/research/analyze?min_hours=24",
      { method: "POST" },
    );
    if (d.status === "skipped") {
      if (status)
        status.textContent =
          "Sudah ada analisis " +
          d.age_hours +
          " jam lalu. Regenerate setelah " +
          d.min_hours +
          " jam.";
    } else {
      if (status) status.textContent = "Analisis baru berhasil dibuat.";
    }
    await loadResearchHistory();
  } catch (e) {
    if (status) status.textContent = "";
    showError("Gagal generate analisis: " + e.message);
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function loadNews() {
  const feed = document.getElementById("newsFeed");
  if (!feed) return;
  feed.innerHTML = '<div class="loading">Memuat berita...</div>';
  try {
    const [newsRes, eventsRes] = await Promise.all([
      fetchJSON("/stocks/" + currentTicker + "/news?limit=20"),
      fetchJSON("/stocks/" + currentTicker + "/events?limit=20"),
    ]);
    const news = newsRes.news || [];
    const events = eventsRes.events || [];
    const eventByTitle = {};
    events.forEach((ev) => (eventByTitle[ev.title] = ev));
    if (!news.length) {
      feed.innerHTML = '<p class="muted">Belum ada berita untuk saham ini.</p>';
      return;
    }
    feed.innerHTML = news
      .map((n) => {
        const ev = eventByTitle[n.title];
        const badges = ev
          ? `<span class="event-badge ${ev.event_type}">${ev.event_type.replace(/_/g, " ")}</span>`
          : "";
        const url = n.url
          ? ` href="${n.url}" target="_blank" rel="noopener"`
          : "";
        const date = n.published_at ? n.published_at.slice(0, 10) : "";
        return `<div class="news-item">
                <div class="news-date">${date}</div>
                <div class="news-body">
                  <div class="news-title"><a${url}>${n.title || ""}</a></div>
                  <div class="news-meta">${n.source || ""} ${badges}</div>
                </div>
              </div>`;
      })
      .join("");
  } catch (e) {
    feed.innerHTML =
      '<p class="muted">Gagal memuat berita: ' + e.message + "</p>";
  }
}

async function switchStockTab(tab) {
  document
    .querySelectorAll(".tabs button")
    .forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
  document
    .querySelectorAll(".analysis-section")
    .forEach((s) => s.classList.remove("active"));
  // 'chart' uses tab-chart id; others use tab-<name>
  document.getElementById("tab-" + tab).classList.add("active");
  if (tab === "ai") populateAiChat();
  if (tab === "research") {
    loadResearchCandidates();
    loadResearchHistory();
  }
}

// ---------- AI Chat (streaming) ----------
function addChatMsg(role, text) {
  const log = document.getElementById("aiChatLog");
  const el = document.createElement("div");
  el.className = "chat-msg " + role;
  // Bot messages carry markdown (bold/lists) -> render; user messages are plain.
  el.innerHTML = role === "bot" ? mdToHtml(text) : escapeHtml(text || "");
  log.appendChild(el);
  log.scrollTop = log.scrollHeight;
  return el;
}

function populateAiChat() {
  const stockEl = document.getElementById("aiChatStock");
  if (stockEl) stockEl.textContent = currentTicker || "saham ini";
  const log = document.getElementById("aiChatLog");
  // Keep only the welcome message + conversation history
  log.innerHTML = `<div class="chat-msg bot">Halo! Tanyakan apa saja tentang <strong>${currentTicker || "saham ini"}</strong>, misalnya “Bagaimana prospek valuasi?” atau “Apa risiko utamanya?”</div>`;
  aiHistory.forEach((m) => addChatMsg(m.role, m.text));
  log.scrollTop = log.scrollHeight;
  const input = document.getElementById("aiChatInput");
  if (input) input.focus();
}

function onAiInputKey(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendAiMessage();
  }
}

async function sendAiMessage() {
  const input = document.getElementById("aiChatInput");
  const text = (input.value || "").trim();
  if (!text || aiStreaming) return;
  if (!currentTicker) {
    showError("Pilih saham terlebih dahulu.");
    return;
  }
  input.value = "";
  aiHistory.push({ role: "user", text });
  addChatMsg("user", text);
  const botEl = addChatMsg("bot", "Mengetik...");
  aiStreaming = true;
  try {
    const res = await fetch("/ai/analyze-stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticker: currentTicker, question: text }),
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    let acc = "";
    let started = false;
    let phaseMsg = "Mengetik...";

    const render = () => {
      botEl.innerHTML = started ? mdToHtml(acc) : escapeHtml(phaseMsg);
      document.getElementById("aiChatLog").scrollTop =
        document.getElementById("aiChatLog").scrollHeight;
    };
    const handleBlock = (block) => {
      let event = null;
      const dataLines = [];
      block.split("\n").forEach((line) => {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
      });
      if (!dataLines.length) return;
      const raw = dataLines.join("\n");
      let data = {};
      try {
        data = JSON.parse(raw);
      } catch (e) {
        data = { text: raw };
      }
      if (event === "status") {
        phaseMsg = data.message || phaseMsg;
        render();
      } else if (event === "chunk") {
        if (!started) {
          started = true;
          acc = "";
        }
        acc += data.text || "";
        render();
      } else if (event === "done") {
        return;
      } else if (event === "error") {
        botEl.innerHTML = escapeHtml(data.message || "Error");
        aiHistory.push({ role: "bot", text: data.message || "Error" });
        throw new Error(data.message || "Error");
      }
    };

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buf.indexOf("\n\n")) !== -1) {
        handleBlock(buf.slice(0, idx));
        buf = buf.slice(idx + 2);
      }
    }
    if (buf.trim()) handleBlock(buf);
    acc = acc || "(Tidak ada respon)";
    botEl.innerHTML = mdToHtml(acc);
    aiHistory.push({ role: "bot", text: acc });
  } catch (e) {
    if (botEl.textContent === "Mengetik..." || !botEl.textContent) {
      botEl.textContent = "Error: " + e.message;
    }
    if (!aiHistory.length || aiHistory[aiHistory.length - 1].role !== "bot") {
      aiHistory.push({ role: "bot", text: "Error: " + e.message });
    }
  } finally {
    aiStreaming = false;
  }
}

function showError(msg) {
  const el = document.getElementById("errorBanner");
  el.textContent = msg;
  el.style.display = "block";
  setTimeout(() => (el.style.display = "none"), 5000);
}

// ---------- Screener & Compare (Iterasi 3) ----------
function switchNav(nav) {
  if (
    nav === "market" ||
    nav === "screener" ||
    nav === "compare" ||
    nav === "macro"
  ) {
    document
      .querySelectorAll(".top-nav button")
      .forEach((b) => b.classList.toggle("active", b.dataset.nav === nav));
    showView("view-dashboard");
    document
      .querySelectorAll(".sub-view")
      .forEach((s) => s.classList.remove("active"));
    document.getElementById("sub-" + nav).classList.add("active");
    if (nav === "compare")
      runCompare(
        document.getElementById("compareInput").value || "BBCA,BBRI,TLKM",
      );
    if (nav === "macro") loadMacroImpact();
  }
}

const PRESET_INFO = {
  buffett:
    "Buffett: kualitas + valuasi murah (ROE tinggi, P/E rendah, utang rendah)",
  value: "Value: saham murah relatif laba/aset (P/E & P/B rendah)",
  growth: "Growth: pertumbuhan laba & revenue tinggi",
  quality:
    "Quality: profitabilitas & kesehatan balance sheet tinggi (margin, utang rendah)",
  dividend: "Dividend: hasil dividen tinggi & payout wajar",
  technical: "Technical: momentum harga (vs SMA200, RSI, volume)",
};

function updatePresetDesc(screenType) {
  const el = document.getElementById("screenerPresetDesc");
  if (!el) return;
  el.textContent =
    PRESET_INFO[screenType] || "Pilih preset atau atur filter di bawah.";
}

function setScreenPresetActive(screenType) {
  document
    .querySelectorAll(".screener-actions [data-preset]")
    .forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.preset === screenType);
    });
  updatePresetDesc(screenType);
}

async function runScreenType(screenType) {
  setScreenPresetActive(screenType);
  const body = document.getElementById("screenBody");
  const cols = screenType === "technical" ? 7 : 8;
  body.innerHTML =
    '<tr><td colspan="' +
    cols +
    '" class="loading">Menjalankan screener...</td></tr>';
  try {
    const d = await fetchJSON("/screen", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ screen_type: screenType }),
    });
    lastScreenData.screen_type = screenType;
    lastScreenData.filters = null;
    renderScreenResults(d);
  } catch (e) {
    body.innerHTML =
      '<tr><td colspan="8" class="muted">Gagal: ' + e.message + "</td></tr>";
  }
}

function readFilter(selMetric, op) {
  const el = document.getElementById(selMetric);
  const val = el.value;
  if (!val) return null;
  const m = val.match(/^([<>]=?)(\d+)$/);
  if (!m) return null;
  let value = Number(m[2]);
  // Metrics stored as percent in the DB are normalised to decimals in the
  // screening map, so convert the user's percent input (e.g. "roe > 10" -> 0.10).
  if (op === "roe" || op === "net_margin") {
    value = value / 100;
  }
  return { metric: op, operator: m[1], value };
}

async function runCustomScreen() {
  const filters = [
    readFilter("f_roe", "roe"),
    readFilter("f_pe", "pe_ratio"),
    readFilter("f_npm", "net_margin"),
    readFilter("f_de", "debt_to_equity"),
  ].filter(Boolean);
  if (!filters.length) {
    showError("Pilih minimal satu filter.");
    return;
  }
  const body = document.getElementById("screenBody");
  body.innerHTML =
    '<tr><td colspan="8" class="loading">Menjalankan screener...</td></tr>';
  try {
    const d = await fetchJSON("/screen", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filters }),
    });
    lastScreenData.screen_type = null;
    lastScreenData.filters = filters;
    renderScreenResults(d);
  } catch (e) {
    body.innerHTML =
      '<tr><td colspan="8" class="muted">Gagal: ' + e.message + "</td></tr>";
  }
}

function updateScreenSortIndicator() {
  const ind = document.getElementById("screenSortInd");
  if (!ind) return;
  if (screenSortState.key !== "score") {
    ind.textContent = "";
    return;
  }
  ind.textContent = screenSortState.dir === "desc" ? " ▼" : " ▲";
}

function toggleScreenSort() {
  if (screenSortState.key === "score") {
    screenSortState.dir = screenSortState.dir === "desc" ? "asc" : "desc";
  } else {
    screenSortState.key = "score";
    screenSortState.dir = "desc";
  }
  renderScreenResults(lastScreenData);
}

function screenHeaderRow(isTechnical) {
  const scoreTh =
    '<th class="sortable" onclick="toggleScreenSort()">Score<span id="screenSortInd"></span></th>';
  if (isTechnical) {
    return (
      "<tr>" +
      "<th>Ticker</th>" +
      "<th>Nama</th>" +
      "<th>Harga</th>" +
      "<th>vs SMA200</th>" +
      "<th>RSI 14</th>" +
      "<th>Volume</th>" +
      scoreTh +
      "</tr>"
    );
  }
  return (
    "<tr>" +
    "<th>Ticker</th>" +
    "<th>Nama</th>" +
    "<th>ROE</th>" +
    "<th>P/E</th>" +
    "<th>Net Margin</th>" +
    "<th>Debt/Eq</th>" +
    "<th>Dividend</th>" +
    scoreTh +
    "</tr>"
  );
}

function screenRowHtml(r, isTechnical) {
  const mv = r.metric_values || {};
  const scoreTd = r.score == null ? "" : Number(r.score).toFixed(3);
  if (isTechnical) {
    const pv = mv.price_vs_sma_200;
    const rsi = mv.rsi_14;
    const vol = mv.volume_ratio;
    const pvsCls = pv == null ? "" : pv > 0 ? "up" : pv < 0 ? "down" : "";
    const pvs =
      pv == null
        ? "—"
        : (pv >= 0 ? "+" : "") + (Number(pv) * 100).toFixed(1) + "%";
    const pvsTd = pvsCls ? `<span class="${pvsCls}">${pvs}</span>` : pvs;
    return `<tr onclick="openStock('${r.ticker}')">
                <td><span class="ticker-badge">${r.ticker}</span></td>
                <td>${escapeHtml(r.name || "—")}</td>
                <td>${mv.close == null ? "—" : fmtIDR(mv.close)}</td>
                <td>${pvsTd}</td>
                <td>${rsi == null ? "—" : Number(rsi).toFixed(1)}</td>
                <td>${vol == null ? "—" : Number(vol).toFixed(2) + "x"}</td>
                <td>${scoreTd}</td>
              </tr>`;
  }
  return `<tr onclick="openStock('${r.ticker}')">
                <td><span class="ticker-badge">${r.ticker}</span></td>
                <td>${escapeHtml(r.name || "—")}</td>
                <td>${r.filter_results?.roe?.passed ? "✓" : "—"}</td>
                <td>${r.filter_results?.pe_ratio?.passed ? "✓" : "—"}</td>
                <td>${r.filter_results?.net_margin?.passed ? "✓" : "—"}</td>
                <td>${r.filter_results?.debt_to_equity?.passed ? "✓" : "—"}</td>
                <td>${r.filter_results?.dividend_yield?.passed ? "✓" : "—"}</td>
                <td>${scoreTd}</td>
              </tr>`;
}

function renderScreenResults(d) {
  const body = document.getElementById("screenBody");
  const head = document.getElementById("screenHead");
  // Preserve the active screen type across renders (sorting / toggle re-renders).
  const stype = lastScreenData.screen_type;
  const isTechnical = stype === "technical";
  const cols = isTechnical ? 7 : 8;
  let rows = (d.results || []).slice();
  if (screenSortState.key) {
    const dir = screenSortState.dir === "desc" ? -1 : 1;
    rows.sort((a, b) => {
      const av = a[screenSortState.key];
      const bv = b[screenSortState.key];
      return (
        ((av == null ? -Infinity : av) - (bv == null ? -Infinity : bv)) * dir
      );
    });
  }
  rows = rows.slice(0, 100);
  lastScreenData = {
    results: rows,
    screen_type: stype,
    filters: lastScreenData.filters,
  };
  if (head) head.innerHTML = screenHeaderRow(isTechnical);
  if (!rows.length) {
    body.innerHTML =
      '<tr><td colspan="' +
      cols +
      '" class="muted">Tidak ada saham yang lolos filter.</td></tr>';
    return;
  }
  updateScreenSortIndicator();
  body.innerHTML = rows.map((r) => screenRowHtml(r, isTechnical)).join("");
}

async function analyzeScreenAI() {
  const out = document.getElementById("screenAIOutput");
  const btn = document.getElementById("screenAIButton");
  if (!out) return;
  const rows = lastScreenData.results || [];
  if (!rows.length) {
    showError("Jalankan screener terlebih dahulu.");
    return;
  }
  out.innerHTML =
    '<div class="loading">AI menganalisis hasil screener...</div>';
  if (btn) btn.disabled = true;
  try {
    const d = await fetchJSON("/ai/screen-analysis", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        screen_type: lastScreenData.screen_type || undefined,
        filters: lastScreenData.filters || undefined,
        top_n: 10,
      }),
    });
    const md = d.llm_analysis || "";
    if (!md || md.startsWith("Error")) {
      out.innerHTML =
        '<p class="muted">Analisis AI tidak tersedia (LLM belum dikonfigurasi). ' +
        "Sedikit hasil screener tetap ditampilkan di tabel.</p>";
    } else {
      out.innerHTML =
        '<div class="ai-analysis markdown-body"><h3>Interpretasi AI</h3>' +
        mdToHtml(md) +
        "</div>";
    }
  } catch (e) {
    out.innerHTML =
      '<div class="muted">Gagal: ' + escapeHtml(e.message) + "</div>";
  } finally {
    if (btn) btn.disabled = false;
  }
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function convertTables(s) {
  // Convert markdown tables (| a | b | ...) into <table> HTML. A block is a table
  // when at least two consecutive pipe-lines exist and the second is a separator
  // row (contains only | - : and spaces). Runs after escapeHtml so cell content
  // still gets bold/code processed by the later passes.
  const lines = String(s || "").split("\n");
  let out = [];
  let i = 0;
  const isPipe = (l) => l.trimStart().startsWith("|");
  const isSep = (l) => /^\|\s*:?-{2,}\s*(\|\s*:?-{2,}\s*)*\|?$/.test(l.trim());
  const cells = (l) =>
    l
      .trim()
      .replace(/^\|/, "")
      .replace(/\|$/, "")
      .split("|")
      .map((c) => c.trim());
  while (i < lines.length) {
    if (isPipe(lines[i])) {
      // Collect the pipe run.
      let j = i;
      while (j < lines.length && (isPipe(lines[j]) || lines[j].trim() === "")) {
        if (lines[j].trim() === "") break; // stop at blank line
        j++;
      }
      const run = lines.slice(i, j);
      const isTable = run.length >= 2 && isSep(run[1]);
      if (isTable) {
        const header = cells(run[0]);
        const rows = run
          .slice(2)
          .filter((l) => l.trim())
          .map(cells);
        const th = header.map((c) => `<th>${c}</th>`).join("");
        const tb = rows
          .map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`)
          .join("");
        out.push(
          `<table><thead><tr>${th}</tr></thead><tbody>${tb}</tbody></table>`,
        );
        i = j;
        continue;
      }
    }
    out.push(lines[i]);
    i++;
  }
  return out.join("\n");
}

function mdToHtml(s) {
  // Lightweight markdown -> HTML for chat bot messages.
  let html = escapeHtml(s || "");
  html = convertTables(html);
  html = html.replace(/^#{1,6}\s*(.+)$/gm, "<strong>$1</strong>");
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  html = html.replace(/^[-*]\s+(.+)$/gm, "• $1");
  html = html.replace(/^(\d+)\.\s+(.+)$/gm, "<div>$1. $2</div>");
  html = html.replace(/(^|\n)\s*---\s*(\n|$)/gm, "$1<hr>$2");
  html = html.replace(/\n\n/g, "<br><br>");
  html = html.replace(/\n/g, "<br>");
  return html;
}

async function runCompare(text) {
  const tickers = (text || "")
    .split(",")
    .map((t) => t.trim().toUpperCase())
    .filter(Boolean)
    .slice(0, 4);
  const out = document.getElementById("compareOutput");
  if (!tickers.length) {
    out.innerHTML = '<p class="muted">Masukkan 2–4 ticker dipisah koma.</p>';
    return;
  }
  out.innerHTML = '<p class="loading">Memuat perbandingan...</p>';
  try {
    const d = await fetchJSON(
      "/compare?tickers=" + encodeURIComponent(tickers.join(",")),
    );
    renderCompare(d.stocks, tickers);
  } catch (e) {
    out.innerHTML = '<p class="muted">Gagal: ' + e.message + "</p>";
  }
}

const COMPARE_ROWS = [
  ["price", "Harga"],
  ["roe", "ROE %"],
  ["net_margin", "Net Margin %"],
  ["debt_to_equity", "Debt/Eq"],
  ["pe_ratio", "P/E"],
  ["pb_ratio", "P/B"],
  ["dividend_yield", "Dividend %"],
];
function renderCompare(stocks, tickers) {
  const out = document.getElementById("compareOutput");
  const byTicker = {};
  stocks.forEach((s) => (byTicker[s.ticker] = s));
  const rows = COMPARE_ROWS.map(([key, label]) => {
    const cells = tickers.map((t) => {
      const s = byTicker[t] || {};
      const val =
        key === "price"
          ? s.quote?.price
          : s.metrics
            ? s.metrics[key]
            : undefined;
      return `<td>${val == null ? "—" : key === "price" ? fmtIDR(val) : typeof val === "number" ? val.toLocaleString("id-ID", { maximumFractionDigits: 2 }) : val}</td>`;
    });
    return `<tr><td class="muted">${label}</td>${cells.join("")}</tr>`;
  });
  const head = tickers.map((t) => `<th>${t}</th>`).join("");
  out.innerHTML = `<div class="table-wrap"><table><thead><tr><th>Metrik</th>${head}</tr></thead><tbody>${rows.join("")}</tbody></table></div>`;
  lastCompareData = { stocks: stocks || [], tickers: tickers || [] };
}

// ---------- CSV Export ----------
function csvCell(v) {
  if (v === null || v === undefined) return "";
  const s = String(v);
  return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}
function exportCSV(filename, headers, rows) {
  const lines = [headers.map(csvCell).join(",")];
  rows.forEach((r) => lines.push(r.map(csvCell).join(",")));
  const blob = new Blob(["\uFEFF" + lines.join("\n")], {
    type: "text/csv;charset=utf-8;",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function exportStocksCSV() {
  exportCSV(
    "saham_harga.csv",
    ["Ticker", "Nama", "Sektor", "Harga", "Perubahan %", "Volume", "Tanggal"],
    stocksView.map((s) => [
      s.ticker,
      s.name,
      s.sector || "",
      s.close ?? "",
      s.change_pct ?? "",
      s.volume ?? "",
      s.date || "",
    ]),
  );
}

function exportScreenCSV() {
  const rows = lastScreenData.results || [];
  exportCSV(
    "screener_results.csv",
    [
      "Ticker",
      "Nama",
      "ROE",
      "P/E",
      "Net Margin",
      "Debt/Eq",
      "Dividend",
      "Score",
    ],
    rows.map((r) => [
      r.ticker,
      r.name || "",
      r.filter_results?.roe?.passed ? "✓" : "",
      r.filter_results?.pe_ratio?.passed ? "✓" : "",
      r.filter_results?.net_margin?.passed ? "✓" : "",
      r.filter_results?.debt_to_equity?.passed ? "✓" : "",
      r.filter_results?.dividend_yield?.passed ? "✓" : "",
      r.score == null ? "" : Number(r.score).toFixed(3),
    ]),
  );
}

function exportCompareCSV() {
  const { stocks: data, tickers } = lastCompareData;
  const byTicker = {};
  (data || []).forEach((s) => (byTicker[s.ticker] = s));
  const headers = ["Metrik", ...(tickers || [])];
  const rows = COMPARE_ROWS.map(([key, label]) => {
    const cells = (tickers || []).map((t) => {
      const s = byTicker[t] || {};
      return key === "price"
        ? (s.quote?.price ?? "")
        : (s.metrics?.[key] ?? "");
    });
    return [label, ...cells];
  });
  exportCSV("perbandingan_saham.csv", headers, rows);
}

// ---------- Client-side routing ----------
function routeFromPath() {
  const m = location.pathname.match(/^\/stock\/([^/]+)$/);
  if (m) {
    openStock(decodeURIComponent(m[1]));
  } else {
    loadDashboard();
  }
}
window.addEventListener("popstate", () => {
  const m = location.pathname.match(/^\/stock\/([^/]+)$/);
  if (m) openStock(decodeURIComponent(m[1]));
  else loadDashboard();
});

document.getElementById("stockFilter").addEventListener("input", () => {
  stocksPage = 1;
  renderStocksTable();
});
// Search autocomplete: hide on blur (allow suggestion click) and on outside click.
document
  .getElementById("globalSearch")
  .addEventListener("blur", () => setTimeout(hideSearchDropdown, 120));
document.addEventListener("click", (e) => {
  const dd = document.getElementById("searchDropdown");
  const input = document.getElementById("globalSearch");
  if (dd && input && !dd.contains(e.target) && e.target !== input) {
    hideSearchDropdown();
  }
});
routeFromPath();
// Show the default screener preset description on first load.
updatePresetDesc("");
