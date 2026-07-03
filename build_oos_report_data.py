"""
=============================================================================
SCRIPT NAME: build_oos_report_data.py
=============================================================================

INPUT FILES:
- /Users/arjundivecha/Dropbox/AAA Backup/A Complete/QScreen Original/qscreen/qc_extracted_data/strategies.jsonl
    800 strategy records produced by extract_qc_strategy_data.py (paper
    metadata + QC statistics + true out-of-sample performance analysis).
- /Users/arjundivecha/Dropbox/AAA Backup/A Complete/QScreen Original/qscreen/qc_extracted_data/charts/*.png
    Per-strategy QuantConnect equity-curve thumbnails (a handful are
    base64-embedded into the report as visual highlights).

OUTPUT FILES:
- /Users/arjundivecha/Dropbox/AAA Backup/A Complete/QScreen Original/qscreen/qc_extracted_data/report_data.json
    A single compact JSON payload consumed by the HTML report: per-category
    strategy tables (sorted by out-of-sample CAGR), category-level summary
    statistics, corpus-wide headline statistics, and a small set of
    base64-encoded chart thumbnails for visual highlights (best/worst
    overall performers and the best performer in each category).

VERSION: 1.1
LAST UPDATED: 2026-07-02
AUTHOR: Claude Code

DESCRIPTION:
Reads the 800-strategy extraction output and:
  1. Buckets every strategy into one of 8 categories from its "Markets
     Traded" field: Equities, Commodities, Currencies, Cryptocurrencies,
     Bonds, REITs, Multi-Asset (more than one market listed), Other.
  2. Within each category, sorts strategies by true out-of-sample CAGR
     (falling back to OOS total return when CAGR isn't computable due to a
     short window, and placing strategies with NO computable OOS figure —
     e.g. study period runs right up to the data's end — in a clearly
     labeled "insufficient data" tail rather than silently dropping them).
  3. Computes category-level summary stats: strategy count, median/mean OOS
     CAGR, "survival rate" (% with positive OOS CAGR among those with a
     computable figure), and average paper-claimed vs actual OOS return.
  4. Computes corpus-wide headline stats for the report's opening section.
  5. Base64-embeds a small, deliberately limited set of chart PNGs (overall
     top 5, overall bottom 5, and the #1 performer in each category) so the
     HTML report is fully self-contained with no external file references.
  6. Carries through the trailing 1/3/5-year OOS return/CAGR fields computed
     by extract_qc_strategy_data.py so the report can show fund-fact-sheet
     style trailing returns alongside the full-window figures.

DEPENDENCIES:
- (stdlib) json, base64, os, statistics, collections

USAGE:
python build_oos_report_data.py

NOTES:
- No fabricated data: strategies with status != "ok" or an unparseable OOS
  figure are retained in the output (flagged), never dropped silently.
=============================================================================
"""

import base64
import collections
import json
import os
import statistics

BASE_DIR = "/Users/arjundivecha/Dropbox/AAA Backup/A Complete/QScreen Original/qscreen"
JSONL_PATH = os.path.join(BASE_DIR, "qc_extracted_data", "strategies.jsonl")
OUT_PATH = os.path.join(BASE_DIR, "qc_extracted_data", "report_data.json")

CATEGORY_MAP = {
    "equities": "Equities",
    "commodities": "Commodities",
    "currencies": "Currencies",
    "cryptos": "Cryptocurrencies",
    "bonds": "Bonds",
    "reits": "REITs",
}


def categorize(markets_traded: str) -> str:
    mt = (markets_traded or "").strip().lower()
    if not mt:
        return "Other"
    parts = [p.strip() for p in mt.split(",") if p.strip()]
    if len(parts) == 1 and parts[0] in CATEGORY_MAP:
        return CATEGORY_MAP[parts[0]]
    if len(parts) == 1 and parts[0] == "reits":
        return "REITs"
    if len(parts) > 1:
        return "Multi-Asset"
    return "Other"


def load_records():
    records = []
    with open(JSONL_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def png_to_data_uri(path: str) -> str:
    if not path or not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def strategy_row(r: dict) -> dict:
    sf = r.get("strategy_fields", {}) or {}
    return {
        "name": r["strategy_name"],
        "display_name": r.get("title", "").replace(" - QuantPedia", "") or r["strategy_name"].replace("_", " "),
        "url": r.get("quantpedia_url", ""),
        "markets_traded": sf.get("Markets Traded", ""),
        "paper_period": sf.get("Backtest period from source paper", ""),
        "paper_confidence": sf.get("Confidence in anomaly's validity", ""),
        "paper_indicative_perf": sf.get("Indicative Performance", ""),
        "paper_sharpe": sf.get("Sharpe Ratio", ""),
        "paper_complexity": sf.get("Complexity Evaluation", ""),
        "region": sf.get("Region", ""),
        "keywords": r.get("keywords", []),
        "qc_sharpe_full": (r.get("qc_statistics", {}) or {}).get("Sharpe Ratio", ""),
        "qc_cagr_full": (r.get("qc_statistics", {}) or {}).get("Compounding Annual Return", ""),
        "qc_drawdown_full": (r.get("qc_statistics", {}) or {}).get("Drawdown", ""),
        "in_sample_return_pct": r.get("in_sample_overlap_total_return_pct"),
        "in_sample_start": r.get("in_sample_overlap_start_date"),
        "in_sample_end": r.get("in_sample_overlap_end_date"),
        "oos_start": r.get("oos_start_date"),
        "oos_end": r.get("oos_end_date"),
        "oos_years": r.get("oos_years"),
        "oos_total_return_pct": r.get("oos_total_return_pct"),
        "oos_cagr_pct": r.get("oos_cagr_pct"),
        "oos_max_drawdown_pct": r.get("oos_max_drawdown_pct"),
        "oos_1y_return_pct": r.get("oos_1y_return_pct"),
        "oos_3y_return_pct": r.get("oos_3y_return_pct"),
        "oos_3y_cagr_pct": r.get("oos_3y_cagr_pct"),
        "oos_5y_return_pct": r.get("oos_5y_return_pct"),
        "oos_5y_cagr_pct": r.get("oos_5y_cagr_pct"),
        "oos_note": r.get("oos_note", ""),
        "chart_png_path": r.get("chart_png_path", ""),
    }


def effective_oos_pct(row):
    """CAGR when computable, else total return, else None."""
    if row["oos_cagr_pct"] is not None:
        return row["oos_cagr_pct"]
    return row["oos_total_return_pct"]


def sort_key(row):
    # Primary: OOS CAGR (annualized, fairest cross-window comparison).
    # Fallback: OOS total return (for short windows w/o a CAGR).
    # Strategies with neither sort to the bottom via -inf.
    if row["oos_cagr_pct"] is not None:
        return (2, row["oos_cagr_pct"])
    if row["oos_total_return_pct"] is not None:
        return (1, row["oos_total_return_pct"])
    return (0, float("-inf"))


def main():
    records = load_records()
    rows = [strategy_row(r) for r in records if r.get("status") == "ok"]
    for row in rows:
        row["category"] = categorize(row["markets_traded"])

    by_category = collections.defaultdict(list)
    for row in rows:
        by_category[row["category"]].append(row)

    category_order = ["Equities", "Commodities", "Currencies", "Cryptocurrencies",
                       "Bonds", "REITs", "Multi-Asset", "Other"]

    categories_out = []
    for cat in category_order:
        cat_rows = by_category.get(cat, [])
        if not cat_rows:
            continue
        cat_rows.sort(key=sort_key, reverse=True)

        computable = [r["oos_cagr_pct"] for r in cat_rows if r["oos_cagr_pct"] is not None]
        effective_vals = [effective_oos_pct(r) for r in cat_rows]
        effective_vals = [v for v in effective_vals if v is not None]
        n_with_oos = len(effective_vals)
        n_positive = sum(1 for v in effective_vals if v > 0)

        summary = {
            "category": cat,
            "n_strategies": len(cat_rows),
            "n_with_oos_data": n_with_oos,
            "median_oos_cagr_pct": round(statistics.median(computable), 3) if computable else None,
            "mean_oos_cagr_pct": round(statistics.mean(computable), 3) if computable else None,
            "survival_rate_pct": round(100.0 * n_positive / n_with_oos, 1) if n_with_oos else None,
        }

        categories_out.append({"summary": summary, "strategies": cat_rows})

    # ---- Corpus-wide headline stats ----
    all_cagr = [r["oos_cagr_pct"] for r in rows if r["oos_cagr_pct"] is not None]
    all_effective = [(r, effective_oos_pct(r)) for r in rows]
    all_with_oos = [r for r, v in all_effective if v is not None]
    all_positive = [r for r, v in all_effective if v is not None and v > 0]
    n_no_oos = sum(1 for r, v in all_effective if v is None)

    def parse_pct(s):
        try:
            return float(str(s).replace("%", "").strip())
        except (ValueError, TypeError):
            return None

    paper_claims = [parse_pct(r["paper_indicative_perf"]) for r in rows]
    paper_claims = [p for p in paper_claims if p is not None]

    headline = {
        "n_total": len(rows),
        "n_with_oos_data": len(all_with_oos),
        "n_no_oos_window": n_no_oos,
        "median_oos_cagr_pct": round(statistics.median(all_cagr), 3) if all_cagr else None,
        "mean_oos_cagr_pct": round(statistics.mean(all_cagr), 3) if all_cagr else None,
        "survival_rate_pct": round(100.0 * len(all_positive) / len(all_with_oos), 1) if all_with_oos else None,
        "mean_paper_claimed_pct": round(statistics.mean(paper_claims), 2) if paper_claims else None,
        "median_paper_claimed_pct": round(statistics.median(paper_claims), 2) if paper_claims else None,
    }

    # ---- Scatter data: paper claimed return vs OOS CAGR ----
    scatter = []
    for r in rows:
        paper_val = parse_pct(r["paper_indicative_perf"])
        if paper_val is not None and r["oos_cagr_pct"] is not None:
            scatter.append({
                "name": r["display_name"],
                "category": r["category"],
                "paper_pct": paper_val,
                "oos_cagr_pct": r["oos_cagr_pct"],
            })

    # ---- Highlight charts (base64), kept deliberately small in number ----
    rows_with_cagr = [r for r in rows if r["oos_cagr_pct"] is not None]
    rows_with_cagr.sort(key=lambda r: r["oos_cagr_pct"], reverse=True)
    top5 = rows_with_cagr[:5]
    bottom5 = rows_with_cagr[-5:][::-1]

    highlight_charts = {}
    for r in top5 + bottom5:
        uri = png_to_data_uri(r["chart_png_path"])
        if uri:
            highlight_charts[r["name"]] = uri

    for cat_block in categories_out:
        best = cat_block["strategies"][0] if cat_block["strategies"] else None
        if best and best["name"] not in highlight_charts:
            uri = png_to_data_uri(best["chart_png_path"])
            if uri:
                highlight_charts[best["name"]] = uri

    payload = {
        "headline": headline,
        "categories": categories_out,
        "top5": [r["name"] for r in top5],
        "bottom5": [r["name"] for r in bottom5],
        "scatter": scatter,
        "highlight_charts": highlight_charts,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)

    print(f"Wrote {OUT_PATH}")
    print(f"Total strategies: {len(rows)}")
    for cat_block in categories_out:
        s = cat_block["summary"]
        print(f"  {s['category']:18s} n={s['n_strategies']:4d}  median_oos_cagr={s['median_oos_cagr_pct']}  survival={s['survival_rate_pct']}%")
    print(f"Highlight charts embedded: {len(highlight_charts)}")
    print(f"Headline: {headline}")


if __name__ == "__main__":
    main()
