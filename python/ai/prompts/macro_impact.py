"""Macro/impact interpretation (Fase B4) - deterministic-first.

Turns the deterministic news_impacts tags (sector/direction/confidence from B3)
into a structured macro snapshot: per-sector positive/negative pressure,
confidence-weighted ranking, and affected tickers. The LLM is only asked to
interpret and rank the tags - it never invents the sector/direction map, which is
already computed deterministically by enrich_news_impacts.

Everything the LLM says must be traceable to a supplied tag; the prompt carries
the evidence (news title + URL) so interpretations are grounded, not fabricated.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ai.data_loader_pg import get_data_loader

_NL = chr(10)

# Deterministic geo classification (Fase B5 P2): helps the interpreter distinguish
# domestic (transmission to IDX is direct) from global (indirect / lagged) macro.
_DOMESTIC_HINTS = (
    "ihsg", "bank indonesia", "bank sentral indonesia", "bi ", "gubernur bi",
    "rupiah", "idr", "ekonomi indonesia", "pemerintah indonesia", "menkeu",
    "kementerian keuangan", "ojk", "bursa efek indonesia", "saham indonesia",
    "jakarta", "pertumbuhan ekonomi indonesia", "inflasi indonesia",
    "suku bunga indonesia", "sukuk", "obligasi negara", "apbn",
)
_GLOBAL_HINTS = (
    "ecb", "bank sentral eropa", "the fed", "federal reserve", "fed ", "boj",
    "bank of england", "bank of japan", "reserve bank", "the fed menaikkan",
    "wall street", "saham eropa", "saham asia", "ekonomi global", "pasar global",
    "european central bank", "yield obligasi global", "the fed ", "ecb ",
    "amerika serikat", "ekonomi amerika", "ekonomi eropa", "ekonomi tiongkok",
)


def classify_geo(title: str, source: str | None = None) -> str:
    """Return 'domestic' | 'global' | 'mixed' | 'unknown' deterministically."""
    text = (title or "").lower()
    dom = any(h in text for h in _DOMESTIC_HINTS)
    glo = any(h in text for h in _GLOBAL_HINTS)
    if dom and glo:
        return "mixed"
    if dom:
        return "domestic"
    if glo:
        return "global"
    return "unknown"


# Fase B5 P2b: geo weighting so domestic macro signals (direct transmission to
# IDX) count for more than global signals (indirect/lagged) when ranking sector
# pressure. Deterministic and exposed in the snapshot for transparency.
GEO_WEIGHTS: dict[str, float] = {
    "domestic": 1.0,
    "mixed": 0.75,
    "global": 0.5,
    "unknown": 1.0,
}


def geo_weight(geo: str | None) -> float:
    """Return the deterministic weight for a geo label."""
    return GEO_WEIGHTS.get(geo or "unknown", 1.0)


def load_impacts(hours: int = 48, limit: int = 200) -> list[dict[str, Any]]:
    """Read deterministic impact tags within the last ``hours``, enriched with geo."""
    impacts = get_data_loader().get_news_impacts(hours=hours, limit=limit)
    for imp in impacts:
        imp["geo"] = classify_geo(imp.get("title") or "", imp.get("source"))
    return impacts


def _percentile(values: list[float], p: float) -> float:
    """Nearest-rank percentile (0-100)."""
    if not values:
        return 0.0
    vals = sorted(values)
    idx = max(0, min(len(vals) - 1, int(round((p / 100.0) * (len(vals) - 1)))))
    return vals[idx]


def compute_net_baselines(
    history: list[dict[str, Any]],
    current_sectors: dict[str, float] | None = None,
    min_sample_days: int = 5,
) -> dict[str, dict[str, Any]]:
    """Deterministic per-sector net_strength baseline from historical impacts.

    Groups the geo-weighted daily net_strength per sector, then returns the
    distribution (median, p75, p90, max, min, sample_days) so the current value
    can be compared to "normal". ``current_sectors`` maps sector -> current
    geo-weighted net_strength (from the live snapshot) for the ``current`` field.

    ``min_sample_days`` is the number of distinct days below which the baseline is
    considered unreliable: ``sample_sufficient`` is True when there are at least
    that many days, and ``baseline_confidence`` (0..1) rises linearly toward 1 as
    ``sample_days`` grows up to ``min_sample_days``.
    """
    per_day: dict[str, dict[str, float]] = {}
    for imp in history:
        sector = imp.get("sector") or "Unknown"
        direction = imp.get("direction") or "neutral"
        conf = float(imp.get("confidence") or 0.0)
        w = geo_weight(imp.get("geo"))
        day = str(imp.get("published_at") or "")[:10]
        if not day:
            continue
        bucket = per_day.setdefault(sector, {})
        sign = 1.0 if direction == "positive" else -1.0 if direction == "negative" else 0.0
        bucket[day] = bucket.get(day, 0.0) + sign * conf * w

    baselines: dict[str, dict[str, Any]] = {}
    for sector, day_map in per_day.items():
        values = list(day_map.values())
        if not values:
            continue
        sample_days = len(values)
        sample_sufficient = sample_days >= min_sample_days
        baseline_confidence = round(min(1.0, sample_days / min_sample_days), 3)
        baselines[sector] = {
            "median": round(_percentile(values, 50), 3),
            "p75": round(_percentile(values, 75), 3),
            "p90": round(_percentile(values, 90), 3),
            "max": round(max(values), 3),
            "min": round(min(values), 3),
            "sample_days": sample_days,
            "sample_sufficient": sample_sufficient,
            "baseline_confidence": baseline_confidence,
            "current": round(float((current_sectors or {}).get(sector, 0.0)), 3),
        }
    return baselines


def attach_baselines(
    snapshot: dict[str, Any],
    baselines: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Attach deterministic baseline stats to each sector in the snapshot (in-place)."""
    for s in snapshot.get("sectors", []):
        b = baselines.get(s["sector"])
        if b:
            s["baseline"] = b
    return snapshot


def build_snapshot(impacts: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate deterministic impact tags into a per-sector macro snapshot.

    For each sector we track positive and negative pressure:
      positive_count / negative_count - number of articles biasing that direction,
      positive_confidence / negative_confidence - mean confidence of those tags,
      net_strength - count weighted by confidence (positive minus negative).
    affected_tickers are explicitly-tagged tickers (company-specific news);
    sector-level (ticker=None) hits stay at sector granularity.
    """
    sectors: dict[str, dict[str, Any]] = {}
    for imp in impacts:
        sector = imp.get("sector") or "Unknown"
        direction = imp.get("direction") or "neutral"
        conf = float(imp.get("confidence") or 0.0)
        s = sectors.setdefault(
            sector,
            {
                "sector": sector,
                "positive": {"count": 0, "conf_sum": 0.0, "wconf_sum": 0.0},
                "negative": {"count": 0, "conf_sum": 0.0, "wconf_sum": 0.0},
                "news": [],
                "affected_tickers": set(),
                "domestic_count": 0,
                "global_count": 0,
            },
        )
        geo = imp.get("geo") or "unknown"
        w = geo_weight(geo)
        if direction == "positive":
            s["positive"]["count"] += 1
            s["positive"]["conf_sum"] += conf
            s["positive"]["wconf_sum"] += conf * w
        elif direction == "negative":
            s["negative"]["count"] += 1
            s["negative"]["conf_sum"] += conf
            s["negative"]["wconf_sum"] += conf * w
        if geo == "domestic":
            s["domestic_count"] += 1
        elif geo == "global":
            s["global_count"] += 1
        ticker = imp.get("ticker")
        if ticker:
            s["affected_tickers"].add(ticker)
        s["news"].append(
            {
                "title": imp.get("title"),
                "url": imp.get("url"),
                "source": imp.get("source"),
                "direction": direction,
                "confidence": conf,
                "geo": geo,
                "geo_weight": w,
                "matched_keywords": imp.get("matched_keywords"),
            }
        )

    snapshot: list[dict[str, Any]] = []
    for sector, s in sectors.items():
        pos_c = s["positive"]["count"]
        neg_c = s["negative"]["count"]
        pos = round(s["positive"]["conf_sum"] / pos_c, 3) if pos_c else 0.0
        neg = round(s["negative"]["conf_sum"] / neg_c, 3) if neg_c else 0.0
        # net_strength is geo-weighted (domestic weighs more than global), while
        # counts and average confidence stay raw for transparency.
        pos_w = s["positive"]["wconf_sum"]
        neg_w = s["negative"]["wconf_sum"]
        net = round(pos_w - neg_w, 3)
        domestic = s["domestic_count"]
        global_ = s["global_count"]
        total_geo = domestic + global_
        snapshot.append(
            {
                "sector": sector,
                "positive_count": pos_c,
                "negative_count": neg_c,
                "positive_confidence": pos,
                "negative_confidence": neg,
                "net_strength": net,
                "affected_tickers": sorted(s["affected_tickers"]),
                "domestic_count": domestic,
                "global_count": global_,
                "domestic_share": round(domestic / total_geo, 2) if total_geo else None,
                "news": s["news"][:12],
            }
        )

    snapshot.sort(
        key=lambda x: (
            abs(float(x["net_strength"])),
            float(x["positive_count"]) + float(x["negative_count"]),
        ),
        reverse=True,
    )
    return {"generated_at": datetime.now().isoformat(), "sectors": snapshot}


def build_candidates(
    snapshot: dict[str, Any],
    min_abs_net: float = 0.25,
    sector_tickers: dict[str, list[str]] | None = None,
    max_tickers_per_sector: int = 5,
) -> list[dict[str, Any]]:
    """Derive deterministic research candidates from a macro snapshot (Option A).

    Candidates are never invented by the LLM. For each sector with meaningful
    pressure (|net_strength| >= ``min_abs_net``) we emit:
      - a sector-level candidate (ticker=None), and
      - one candidate per affected/tagged company in that sector.
    When ``sector_tickers`` is supplied, a sector-level theme is also expanded to
    the most liquid companies in that sector (capped by ``max_tickers_per_sector``)
    so the Research tab gets stock-level candidates without bloating news_impacts.
    The dominant direction is the sign of ``net_strength``; confidence is the mean
    confidence of that direction.
    """
    candidates: list[dict[str, Any]] = []
    for s in snapshot.get("sectors", []):
        net = float(s.get("net_strength") or 0.0)
        if abs(net) < min_abs_net:
            continue
        direction = "positive" if net >= 0 else "negative"
        confidence = (
            float(s.get("positive_confidence") or 0.0)
            if direction == "positive"
            else float(s.get("negative_confidence") or 0.0)
        )
        pos = int(s.get("positive_count") or 0)
        neg = int(s.get("negative_count") or 0)
        reason = (
            f"{pos} positif / {neg} negatif tag dalam 48 jam; "
            f"net pressure {net:+.2f} ({direction})"
        )
        # Real tagged tickers first, then (optionally) the sector's liquid names.
        tickers: list[str] = []
        for t in s.get("affected_tickers") or []:
            if t not in tickers:
                tickers.append(t)
        for t in (sector_tickers or {}).get(s["sector"], []):
            if t not in tickers:
                tickers.append(t)
        tickers = tickers[: max(1, max_tickers_per_sector)]
        # Sector-level candidate first (so a pure sector theme is visible even
        # when no individual company was explicitly tagged).
        candidates.append(
            {
                "sector": s["sector"],
                "ticker": None,
                "direction": direction,
                "confidence": confidence,
                "net_strength": round(abs(net), 3),
                "reason": reason,
            }
        )
        for t in sorted(set(tickers)):
            candidates.append(
                {
                    "sector": s["sector"],
                    "ticker": t,
                    "direction": direction,
                    "confidence": confidence,
                    "net_strength": round(abs(net), 3),
                    "reason": f"{t} di sektor {s['sector']} {direction} ({pos}/{neg} tag)",
                }
            )
    return candidates


def generate_research_candidates(
    hours: int = 48,
    top_sectors: int = 10,
    min_abs_net: float = 0.25,
    use_llm: bool = False,
    llm_client=None,
    max_tickers_per_sector: int = 5,
    expand_tickers: bool = True,
    baseline_days: int = 30,
    min_sample_days: int = 5,
) -> dict[str, Any]:
    """Produce deterministic research candidates + optional LLM interpretation.

    The candidate list (sector/ticker/direction/confidence/net strength) is
    purely deterministic from news_impacts. When ``expand_tickers`` is True a
    pressured sector is expanded to its most liquid companies (capped) so the
    Research tab can offer per-stock analysis. The LLM is only asked for a
    narrative interpretation of the same evidence; it can never add or remove a
    candidate. Returns the full snapshot for the pipeline to persist.
    """
    result = analyze_macro_impacts(
        hours=hours,
        top_sectors=top_sectors,
        focus="",
        use_llm=use_llm,
        llm_client=llm_client,
        baseline_days=baseline_days,
        min_sample_days=min_sample_days,
    )
    sector_tickers: dict[str, list[str]] = {}
    if expand_tickers:
        loader = get_data_loader()
        sector_tickers = {
            s["sector"]: loader.get_sector_tickers(s["sector"], limit=max_tickers_per_sector)
            for s in result.get("sectors", [])
        }
    result["candidates"] = build_candidates(
        result,
        min_abs_net=min_abs_net,
        sector_tickers=sector_tickers,
        max_tickers_per_sector=max_tickers_per_sector,
    )
    return result


def build_prompt(snapshot: dict[str, Any], top_sectors: int = 10, focus: str = "") -> str:
    """Build the LLM prompt carrying ONLY the deterministic evidence."""
    lines = [
        "# Macro Impact - Deterministic Signals (do not invent any)",
        "Generated: " + snapshot["generated_at"],
        "",
        "## Sector impact tags (from deterministic lexicon)",
        "",
        "| Sector | +n/-n | +Conf | -Conf | NetPressure | Dom/Glb | Baseline(med/p90) | Affected tickers |",
        "|--------|-------|-------|-------|-------------|---------|------------------|------------------|",
    ]
    for s in snapshot["sectors"][: max(1, top_sectors)]:
        b = s.get("baseline") or {}
        if b:
            suff = "~" if not b.get("sample_sufficient", True) else ""
            base_txt = f"{b.get('median', 0):+.2f}/{b.get('p90', 0):+.2f}{suff}"
        else:
            base_txt = "n/a"
        lines.append(
            "| {sector} | {pos}/{neg} | {pc:.2f} | {nc:.2f} | {net:+.2f} | {dg} | {base} | {ticks} |".format(
                sector=s["sector"],
                pos=s["positive_count"],
                neg=s["negative_count"],
                pc=s["positive_confidence"],
                nc=s["negative_confidence"],
                net=s["net_strength"],
                dg=f"{s.get('domestic_count', 0)}/{s.get('global_count', 0)}",
                base=base_txt,
                ticks=", ".join(s["affected_tickers"]) or "-",
            )
        )
    lines.append("")
    lines.append("## Supporting evidence")
    lines.append("")
    for s in snapshot["sectors"][: max(1, top_sectors)]:
        for n in s["news"][:4]:
            kw = n.get("matched_keywords")
            kw_txt = f" | keywords: {kw}" if kw else ""
            lines.append(
                "- [{geo} {dir} conf {conf:.2f}]{kw_txt} {title} ({src})".format(
                    geo=n.get("geo") or "?",
                    dir=n["direction"],
                    conf=n["confidence"],
                    kw_txt=kw_txt,
                    title=n["title"],
                    src=n.get("source") or "",
                )
            )
    lines.append("")
    lines.append("## Keyword transparency")
    lines.append(
        "The 'keywords' above are the exact deterministic phrases that triggered each "
        "sector/direction tag (from the curated lexicon). When interpreting, cite the "
        "specific keyword(s) that drove a sector's pressure so the reasoning is "
        "traceable; do not invent other/abstract drivers beyond these keywords."
    )
    lines.append("")
    lines.append("## Historical baseline (deterministic)")
    lines.append(
        "'Baseline(med/p90)' shows the sector's geo-weighted daily net_strength "
        "distribution over the last 30 days (median and 90th percentile). A trailing "
        "'~' means the sample is insufficient (fewer than the minimum distinct days), "
        "so the baseline is unreliable. Compare the current NetPressure against these "
        "numbers: if it exceeds the p90 the pressure is unusual/high; if it is near "
        "the median it is ordinary. If a baseline is marked '~' or has low "
        "baseline_confidence, say the historical comparison is limited and do NOT "
        "overstate that the current value is above/below normal. Do not compute or "
        "criticise the baseline yourself."
    )
    lines.append("")
    lines.append("## Guidance on geographic origin (deterministic, do not invent)")
    lines.append(
        "The 'geo' tag marks each signal as domestic (Indonesia) or global (foreign "
        "central banks / global markets). If a sector's pressure is dominated by "
        "global signals (Dom/Glb skews to the global side), note that transmission "
        "to IDX/Indonesian stocks is likely indirect and may lag; do NOT claim a "
        "direct, immediate impact on Indonesian stocks unless the signal is "
        "domestic. Be explicit about this in the risks / what-would-change-the-view."
    )
    if focus:
        lines.append("")
        lines.append("Focus question: " + focus)
    return _NL.join(lines)


def rank_sectors(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the deterministic ranking (already sorted by net pressure)."""
    return list(snapshot.get("sectors", []))


def analyze_macro_impacts(
    hours: int = 48,
    top_sectors: int = 10,
    focus: str = "",
    use_llm: bool = False,
    llm_client=None,
    baseline_days: int = 30,
    min_sample_days: int = 5,
) -> dict[str, Any]:
    """Compute a deterministic macro snapshot, optionally interpret it with the LLM.

    The sectors, directions, confidence, affected tickers, and ranking are all
    deterministic (from news_impacts). A per-sector net_strength baseline over
    ``baseline_days`` is attached so the current value has historical context;
    ``min_sample_days`` sets the minimum distinct days for the baseline to be
    considered reliable. The LLM only interprets that evidence.
    """
    impacts = load_impacts(hours=hours)
    snapshot = build_snapshot(impacts)
    ranking = rank_sectors(snapshot)

    # Deterministic baseline over a longer window (geo-weighted daily nets).
    baseline_impacts = load_impacts(hours=baseline_days * 24, limit=5000)
    current_nets = {s["sector"]: float(s["net_strength"]) for s in ranking}
    baselines = compute_net_baselines(
        baseline_impacts, current_sectors=current_nets, min_sample_days=min_sample_days
    )
    attach_baselines(snapshot, baselines)

    result = {
        "generated_at": snapshot["generated_at"],
        "hours": hours,
        "baseline_days": baseline_days,
        "min_sample_days": min_sample_days,
        "total_impact_tags": len(impacts),
        "sectors": ranking,
        "llm_used": False,
        "llm_analysis": "",
    }

    if use_llm and llm_client and llm_client.is_available and ranking:
        prompt = build_prompt(snapshot, top_sectors=top_sectors, focus=focus)
        llm_result = llm_client.analyze_with_prompt(
            prompt=prompt,
            system_message=(
                "You are a macro analyst for Indonesian stocks (IDX/BEI). Interpret "
                "the deterministic sector impact tags, ranking the most positively and "
                "negatively pressured sectors and noting which tickers are exposed. Base "
                "every claim on the provided tags; never invent a sector/direction map, "
                "number, or news item. Separate FACT, INTERPRETATION, ASSUMPTION and "
                "SPECULATION."
            ),
            output_format=(
                "Markdown: (1) Top positive/negative sector pressures, (2) key drivers, "
                "(3) affected tickers, (4) risks, (5) what would change the view."
            ),
        )
        result["llm_analysis"] = llm_result.get("content") or llm_result.get("error") or ""
        result["llm_used"] = True

    return result
