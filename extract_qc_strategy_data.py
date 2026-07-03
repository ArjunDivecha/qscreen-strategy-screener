"""
=============================================================================
SCRIPT NAME: extract_qc_strategy_data.py
=============================================================================

INPUT FILES:
- /Users/arjundivecha/Dropbox/AAA Backup/A Complete/QScreen Original/qscreen/html_files/*.html
    Local QuantPedia strategy pages (1,069 files). Each contains a strategy
    metadata table (Markets Traded, Sharpe Ratio, Notes fields, etc.) and,
    for most strategies, an <iframe> pointing at a live QuantConnect embedded
    backtest results page.
- Live network resource (fetched, not local):
    https://www.quantconnect.com/terminal/quantpediaBacktestResult/embedded_backtest_<hash>.html
    One per strategy. Contains the QC "Overall Statistics" table and a link
    to a rendered equity-curve thumbnail PNG.

OUTPUT FILES:
- /Users/arjundivecha/Dropbox/AAA Backup/A Complete/QScreen Original/qscreen/qc_extracted_data/strategies.jsonl
    Incremental checkpoint. One JSON object per line, appended as each
    strategy finishes processing (crash-safe / resumable).
- /Users/arjundivecha/Dropbox/AAA Backup/A Complete/QScreen Original/qscreen/qc_extracted_data/charts/<safe_name>__<hash>.png
    The QuantConnect equity-curve chart image for each strategy that has one.
- /Users/arjundivecha/Dropbox/AAA Backup/A Complete/QScreen Original/qscreen/qc_extracted_data/strategies_master.xlsx
    Final combined table (one row per strategy, union of all columns seen),
    built from strategies.jsonl. Missing genuinely-undefined values render
    as an em dash "-" (never "n/a"), per project convention.
- /Users/arjundivecha/Dropbox/AAA Backup/A Complete/QScreen Original/qscreen/qc_extracted_data/extraction_log.log
    Per-file processing log (success/failure/reason).

VERSION: 1.1
LAST UPDATED: 2026-07-02
AUTHOR: Claude Code

DESCRIPTION:
For every QuantPedia strategy HTML file that links to a QuantConnect embedded
backtest, this script extracts:
  1. From the LOCAL html file body: all "strategy table" key/value metadata
     fields (Markets Traded, Backtest period from source paper, Confidence
     in anomaly's validity, Indicative Performance, Period of Rebalancing,
     Estimated Volatility, Number of Traded Instruments, Maximum Drawdown,
     Complexity Evaluation, Sharpe Ratio, Region, Financial instruments -
     plus every "Notes to ..." field for each of those), the Keywords tag
     list, and the "<complexity> trading strategy" description paragraph.
  2. From the LIVE QuantConnect embed page: every row of the "Overall
     Statistics" table (Total Orders, Sharpe Ratio, Drawdown, Alpha, Beta,
     etc. - whatever QC reports, captured dynamically), the rendered
     equity-curve chart downloaded as a PNG file, and the raw daily equity
     curve series (var equityChart in the embed's JS) used to compute true
     out-of-sample performance (see below).

TRUE OUT-OF-SAMPLE PERFORMANCE (the hard part):
  The "Backtest period from source paper" field (e.g. "1961-2018") states
  the years of data the ORIGINAL ACADEMIC PAPER used to discover the effect.
  The QuantConnect backtest, however, always simulates from 2000-01-01
  through whenever it was last generated (~2024-12). That means part of the
  QC curve overlaps years the paper's own data already covered (not a real
  out-of-sample test), and part of it covers years the paper never saw at
  all - a genuine, uncontaminated out-of-sample test of whether the effect
  persisted.

  For each strategy this script:
    a. Parses the LAST 4-digit year out of "Backtest period from source
       paper" (robust to "YYYY-YYYY", "YYYY - YYYY", en-dashes, etc.) as
       the paper's study end year.
    b. Splits the QC daily equity curve at Jan 1 of (end_year + 1).
    c. Computes, on the post-split ("true out-of-sample") segment only:
       total return %, CAGR %, max drawdown %, window length in years,
       and the segment's start/end dates.
    d. Also computes the same total-return figure for the pre-split
       ("in-sample-overlap") segment, purely as context - it is NOT a
       claim of validity, just what QC's own simulation did during years
       the paper's data already covered.
    e. Additionally computes trailing 1/3/5-year OOS figures measured from
       the OOS start date (fund fact-sheet style: 1Y total return, 3Y and
       5Y both as total return and annualized CAGR). A horizon is left
       blank when the OOS window doesn't reach that far - never estimated.
  If the paper's end year is at or after the last available QC data point
  (no OOS window exists) or the period field can't be parsed, the OOS
  fields are left blank (rendered as an em dash in the xlsx) with a note
  explaining why - never a fabricated number.

Results are written incrementally to a JSONL checkpoint file (one line per
strategy) so the process can be interrupted and resumed without re-fetching
completed strategies, and so partial results are inspectable at any time.
A final pass converts the JSONL into a single Excel workbook. The raw daily
equity curve itself is NOT persisted (only the derived OOS/in-sample summary
metrics) to keep output size manageable.

Supports a --limit N flag for pilot/testing runs on a small sample before
committing to the full batch, and skips any strategy already present in the
checkpoint file (resume behavior).

DEPENDENCIES:
- requests
- openpyxl
- (stdlib) re, os, sys, json, glob, argparse, logging, hashlib,
  concurrent.futures, urllib.parse, html

USAGE:
python extract_qc_strategy_data.py --limit 10      # pilot run, 10 strategies
python extract_qc_strategy_data.py                 # full run, all strategies
python extract_qc_strategy_data.py --build-xlsx    # only rebuild the xlsx
                                                     # from existing jsonl

NOTES:
- Network fetches run with a thread pool (default 8 workers) since each
  request is I/O-bound and QuantConnect's embed pages are large (~1-1.5 MB).
- Every completed strategy is appended to strategies.jsonl immediately; the
  script can be killed and re-run safely.
- No fabricated data: if a field is absent from the source HTML, it is
  recorded as an empty string / null. The xlsx builder renders those as an
  em dash "-", never "n/a".
=============================================================================
"""

import argparse
import glob
import html
import json
import logging
import math
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone

import requests

# -----------------------------------------------------------------------
# Paths (all absolute, per project convention)
# -----------------------------------------------------------------------
BASE_DIR = "/Users/arjundivecha/Dropbox/AAA Backup/A Complete/QScreen Original/qscreen"
HTML_DIR = os.path.join(BASE_DIR, "html_files")
OUT_DIR = os.path.join(BASE_DIR, "qc_extracted_data")
CHARTS_DIR = os.path.join(OUT_DIR, "charts")
JSONL_PATH = os.path.join(OUT_DIR, "strategies.jsonl")
XLSX_PATH = os.path.join(OUT_DIR, "strategies_master.xlsx")
LOG_PATH = os.path.join(OUT_DIR, "extraction_log.log")

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15"
REQUEST_TIMEOUT = 30

os.makedirs(CHARTS_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()],
)
log = logging.getLogger(__name__)


# -----------------------------------------------------------------------
# Local HTML parsing
# -----------------------------------------------------------------------
def strip_tags(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def parse_local_html(path: str) -> dict:
    """Extract strategy metadata fields from a local QuantPedia HTML file."""
    with open(path, encoding="utf-8", errors="replace") as f:
        raw = f.read()

    data = {"source_html_path": path}

    def find1(pattern, default=""):
        m = re.search(pattern, raw)
        return html.unescape(m.group(1)).strip() if m else default

    data["title"] = find1(r'<meta property="og:title" content="([^"]+)"')
    data["quantpedia_url"] = find1(r'<link rel="canonical" href="([^"]+strategies[^"]+)"')
    data["published_date"] = find1(r'article:published_time" content="([^"]+)"')
    data["modified_date"] = find1(r'article:modified_time" content="([^"]+)"')

    hash_match = re.search(r"embedded_backtest_([0-9a-f]+)\.html", raw)
    data["qc_hash"] = hash_match.group(1) if hash_match else ""
    data["qc_embed_url"] = (
        f"https://www.quantconnect.com/terminal/quantpediaBacktestResult/"
        f"embedded_backtest_{data['qc_hash']}.html"
        if data["qc_hash"]
        else ""
    )

    # Strategy-table key/value rows: <div class="...first">KEY</div><div class="...second">VALUE</div>
    pairs = re.findall(
        r'"medium-6 small-12 first">([^<]+)</div>\s*'
        r'<div class="medium-6 small-12 second">(.*?)</div>\s*</div>\s*<hr>',
        raw,
        re.S,
    )
    field_map = {}
    for key, val in pairs:
        key = strip_tags(key)
        val = strip_tags(val)
        field_map[key] = val
    data["strategy_fields"] = field_map

    # Keywords
    data["keywords"] = re.findall(r'class="keyword">([^<]+)</a>', raw)

    # "<X> trading strategy" description block: <div class="subtitle">...trading strategy</div><p>...</p>
    desc_match = re.search(
        r'<div class="subtitle">([^<]*trading strategy)</div>\s*<p>(.*?)</p>',
        raw,
        re.I | re.S,
    )
    if desc_match:
        data["strategy_description_title"] = strip_tags(desc_match.group(1))
        data["strategy_description_text"] = strip_tags(desc_match.group(2))
    else:
        data["strategy_description_title"] = ""
        data["strategy_description_text"] = ""

    return data


# -----------------------------------------------------------------------
# Live QuantConnect embed parsing
# -----------------------------------------------------------------------
def fetch_qc_embed(embed_url: str) -> str:
    resp = requests.get(
        embed_url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT
    )
    resp.raise_for_status()
    return resp.text


def parse_qc_statistics(raw: str) -> dict:
    """Extract every Overall Statistics row: dynamic, whatever QC reports."""
    stats = {}
    for name, val in re.findall(
        r'statistic-name"[^>]*>([^<]+)</div>\s*'
        r'<div class="statistic-grid statistic-value"[^>]*>([^<]*)</div>',
        raw,
    ):
        stats[strip_tags(name)] = strip_tags(val)
    return stats


def get_qc_thumbnail_url(raw: str) -> str:
    m = re.search(r'name="thumbnail" content="([^"]+)"', raw)
    return m.group(1) if m else ""


def parse_equity_curve(raw: str):
    """Extract the raw daily equity curve from the QC embed's JS.

    Returns a list of (date, close_value) tuples sorted by date, or an
    empty list if the embed has no equityChart variable (no backtest ran).
    """
    m = re.search(r"var equityChart = (\{.*?\});", raw, re.S)
    if not m:
        return []
    try:
        obj = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []
    points = []
    for row in obj.get("data", []):
        if len(row) >= 5:
            # OHLC candlestick row: [timestamp_ms, open, high, low, close]
            ts_ms, close = row[0], row[4]
        elif len(row) == 2:
            # Plain line-series row: [timestamp_ms, value]
            ts_ms, close = row[0], row[1]
        else:
            continue
        d = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).date()
        points.append((d, float(close)))
    points.sort(key=lambda p: p[0])
    return points


def parse_paper_end_year(period_str: str):
    """Robustly pull the study's END year out of a 'Backtest period from
    source paper' string, e.g. '1961-2018', '1993–2013', '1994 -2020'."""
    if not period_str:
        return None
    years = re.findall(r"\d{4}", period_str)
    if not years:
        return None
    return int(years[-1])


def compute_segment_metrics(points, seg_start=None, seg_end=None):
    """Given a list of (date, close) points, restrict to [seg_start, seg_end]
    (inclusive, either bound may be None for open-ended) and compute total
    return %, CAGR %, and max drawdown % on that slice.

    Returns None if fewer than 2 points fall in the requested window.
    """
    seg = [p for p in points if (seg_start is None or p[0] >= seg_start) and (seg_end is None or p[0] <= seg_end)]
    if len(seg) < 2:
        return None

    start_date, start_val = seg[0]
    end_date, end_val = seg[-1]
    if start_val <= 0:
        return None

    years = (end_date - start_date).days / 365.25
    total_return_pct = (end_val / start_val - 1.0) * 100.0

    cagr_pct = None
    if years >= 0.5:
        cagr_pct = ((end_val / start_val) ** (1.0 / years) - 1.0) * 100.0

    # Max drawdown on close-to-close values within the segment.
    peak = seg[0][1]
    max_dd = 0.0
    for _d, v in seg:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (v - peak) / peak * 100.0
            if dd < max_dd:
                max_dd = dd

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "years": round(years, 2),
        "n_points": len(seg),
        "total_return_pct": round(total_return_pct, 3),
        "cagr_pct": round(cagr_pct, 3) if cagr_pct is not None else None,
        "max_drawdown_pct": round(max_dd, 3),
    }


def add_years(d: date, n: int) -> date:
    """Calendar-year addition, clamping Feb 29 -> Feb 28 in non-leap target years."""
    try:
        return d.replace(year=d.year + n)
    except ValueError:
        return d.replace(year=d.year + n, day=28)


OOS_HORIZON_YEARS = [1, 3, 5]


def compute_oos_horizon_metrics(points, oos_start_date, curve_last_date):
    """Trailing 1/3/5-year returns measured from the OOS start date, fund
    fact-sheet style: 1Y is a simple total return (equivalent to its own
    CAGR), 3Y and 5Y report both total return and annualized (CAGR).
    A horizon is left entirely blank (None) when the OOS window doesn't
    reach that far yet - never estimated or extrapolated.
    """
    out = {}
    for n in OOS_HORIZON_YEARS:
        target_date = add_years(oos_start_date, n)
        key_prefix = f"oos_{n}y"
        if target_date > curve_last_date:
            out[f"{key_prefix}_return_pct"] = None
            if n > 1:
                out[f"{key_prefix}_cagr_pct"] = None
            continue
        seg = compute_segment_metrics(points, seg_start=oos_start_date, seg_end=target_date)
        if seg is None:
            out[f"{key_prefix}_return_pct"] = None
            if n > 1:
                out[f"{key_prefix}_cagr_pct"] = None
            continue
        out[f"{key_prefix}_return_pct"] = seg["total_return_pct"]
        if n > 1:
            out[f"{key_prefix}_cagr_pct"] = seg["cagr_pct"]
    return out


def compute_oos_analysis(points, paper_end_year):
    """Split the equity curve at Jan 1 of (paper_end_year + 1) and compute
    metrics for both the pre-split (in-sample-overlap) and post-split
    (true out-of-sample) segments. Returns a flat dict of result fields;
    values are None (rendered as an em dash downstream) when not computable.
    """
    result = {
        "oos_paper_end_year": paper_end_year,
        "oos_split_date": None,
        "oos_note": "",
        "in_sample_overlap_start_date": None,
        "in_sample_overlap_end_date": None,
        "in_sample_overlap_years": None,
        "in_sample_overlap_total_return_pct": None,
        "oos_start_date": None,
        "oos_end_date": None,
        "oos_years": None,
        "oos_total_return_pct": None,
        "oos_cagr_pct": None,
        "oos_max_drawdown_pct": None,
        "oos_1y_return_pct": None,
        "oos_3y_return_pct": None,
        "oos_3y_cagr_pct": None,
        "oos_5y_return_pct": None,
        "oos_5y_cagr_pct": None,
    }

    if paper_end_year is None:
        result["oos_note"] = "Backtest period from source paper missing/unparseable"
        return result

    if not points:
        result["oos_note"] = "no equity curve data in QC embed"
        return result

    split_date = date(paper_end_year + 1, 1, 1)
    result["oos_split_date"] = split_date.isoformat()

    curve_first_date = points[0][0]
    curve_last_date = points[-1][0]

    if split_date > curve_last_date:
        result["oos_note"] = (
            f"study period end year ({paper_end_year}) is at/after the last "
            f"available QC backtest data ({curve_last_date.isoformat()}) - "
            f"no out-of-sample window exists"
        )
        # Still report the in-sample-overlap segment (the whole curve).
        overlap = compute_segment_metrics(points, seg_end=curve_last_date)
        if overlap:
            result["in_sample_overlap_start_date"] = overlap["start_date"]
            result["in_sample_overlap_end_date"] = overlap["end_date"]
            result["in_sample_overlap_years"] = overlap["years"]
            result["in_sample_overlap_total_return_pct"] = overlap["total_return_pct"]
        return result

    overlap = compute_segment_metrics(points, seg_end=date(paper_end_year, 12, 31))
    if overlap:
        result["in_sample_overlap_start_date"] = overlap["start_date"]
        result["in_sample_overlap_end_date"] = overlap["end_date"]
        result["in_sample_overlap_years"] = overlap["years"]
        result["in_sample_overlap_total_return_pct"] = overlap["total_return_pct"]

    oos = compute_segment_metrics(points, seg_start=split_date)
    if oos is None:
        result["oos_note"] = "fewer than 2 data points after study period end"
        return result

    result["oos_start_date"] = oos["start_date"]
    result["oos_end_date"] = oos["end_date"]
    result["oos_years"] = oos["years"]
    result["oos_total_return_pct"] = oos["total_return_pct"]
    result["oos_cagr_pct"] = oos["cagr_pct"]
    result["oos_max_drawdown_pct"] = oos["max_drawdown_pct"]

    oos_start_date_obj = date.fromisoformat(oos["start_date"])
    result.update(compute_oos_horizon_metrics(points, oos_start_date_obj, curve_last_date))

    if oos["years"] < 0.5:
        result["oos_note"] = f"short OOS window ({oos['years']:.2f}y) - CAGR not annualized"
    if curve_first_date > split_date:
        result["oos_note"] = (result["oos_note"] + "; " if result["oos_note"] else "") + (
            f"note: QC backtest itself only starts {curve_first_date.isoformat()}, "
            f"after the requested split date"
        )

    return result


def download_chart_png(thumb_url: str, dest_path: str) -> bool:
    try:
        resp = requests.get(
            thumb_url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(resp.content)
        return True
    except Exception as e:
        log.warning(f"  chart download failed for {thumb_url}: {e}")
        return False


def safe_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)[:150]


# -----------------------------------------------------------------------
# Per-strategy pipeline
# -----------------------------------------------------------------------
def process_one(html_path: str) -> dict:
    strategy_name = os.path.splitext(os.path.basename(html_path))[0]
    result = {"strategy_name": strategy_name, "status": "pending"}

    try:
        local = parse_local_html(html_path)
        result.update(local)

        if not local["qc_hash"]:
            result["status"] = "no_qc_link"
            return result

        raw = fetch_qc_embed(local["qc_embed_url"])
        result["qc_statistics"] = parse_qc_statistics(raw)

        thumb_url = get_qc_thumbnail_url(raw)
        result["qc_thumbnail_url"] = thumb_url

        chart_path = ""
        if thumb_url:
            fname = f"{safe_filename(strategy_name)}__{local['qc_hash']}.png"
            dest = os.path.join(CHARTS_DIR, fname)
            if download_chart_png(thumb_url, dest):
                chart_path = dest
        result["chart_png_path"] = chart_path

        equity_points = parse_equity_curve(raw)
        paper_end_year = parse_paper_end_year(local["strategy_fields"].get("Backtest period from source paper", ""))
        oos = compute_oos_analysis(equity_points, paper_end_year)
        result.update(oos)

        result["status"] = "ok"
        log.info(
            f"OK: {strategy_name}  ({len(result['qc_statistics'])} stats, chart={'yes' if chart_path else 'no'}, "
            f"oos_return={oos.get('oos_total_return_pct')})"
        )

    except requests.exceptions.RequestException as e:
        result["status"] = "fetch_error"
        result["error"] = str(e)
        log.error(f"FETCH ERROR: {strategy_name}: {e}")
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        log.error(f"ERROR: {strategy_name}: {e}")

    return result


# -----------------------------------------------------------------------
# Incremental JSONL I/O
# -----------------------------------------------------------------------
def load_completed_names(jsonl_path: str) -> set:
    done = set()
    if os.path.exists(jsonl_path):
        with open(jsonl_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    done.add(rec.get("strategy_name"))
                except json.JSONDecodeError:
                    continue
    return done


def append_jsonl(jsonl_path: str, record: dict) -> None:
    with open(jsonl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# -----------------------------------------------------------------------
# XLSX builder
# -----------------------------------------------------------------------
def build_xlsx(jsonl_path: str, xlsx_path: str) -> None:
    from openpyxl import Workbook

    records = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    if not records:
        log.warning("No records to write to xlsx.")
        return

    fixed_cols = [
        "strategy_name", "status", "title", "quantpedia_url",
        "published_date", "modified_date", "qc_hash", "qc_embed_url",
        "strategy_description_title", "strategy_description_text",
        "keywords", "chart_png_path", "error",
        # True out-of-sample analysis (computed from the QC equity curve).
        "oos_paper_end_year", "oos_split_date",
        "in_sample_overlap_start_date", "in_sample_overlap_end_date",
        "in_sample_overlap_years", "in_sample_overlap_total_return_pct",
        "oos_start_date", "oos_end_date", "oos_years",
        "oos_total_return_pct", "oos_cagr_pct", "oos_max_drawdown_pct",
        # Trailing 1/3/5-year out-of-sample returns, measured from oos_start_date.
        # Blank (never fabricated) when the OOS window doesn't reach that far.
        "oos_1y_return_pct",
        "oos_3y_return_pct", "oos_3y_cagr_pct",
        "oos_5y_return_pct", "oos_5y_cagr_pct",
        "oos_note",
    ]

    strategy_field_keys = []
    stat_keys = []
    for rec in records:
        for k in rec.get("strategy_fields", {}) or {}:
            if k not in strategy_field_keys:
                strategy_field_keys.append(k)
        for k in rec.get("qc_statistics", {}) or {}:
            if k not in stat_keys:
                stat_keys.append(k)

    columns = fixed_cols + [f"field: {k}" for k in strategy_field_keys] + [f"stat: {k}" for k in stat_keys]

    wb = Workbook()
    ws = wb.active
    ws.title = "strategies"
    ws.append(columns)

    EM_DASH = "—"

    def cellval(rec, col):
        if col in fixed_cols:
            v = rec.get(col, "")
            if col == "keywords":
                v = "; ".join(v) if isinstance(v, list) else v
            return v if v not in (None, "") else EM_DASH
        if col.startswith("field: "):
            v = (rec.get("strategy_fields", {}) or {}).get(col[len("field: "):], "")
            return v if v not in (None, "") else EM_DASH
        if col.startswith("stat: "):
            v = (rec.get("qc_statistics", {}) or {}).get(col[len("stat: "):], "")
            return v if v not in (None, "") else EM_DASH
        return EM_DASH

    for rec in records:
        ws.append([cellval(rec, c) for c in columns])

    wb.save(xlsx_path)
    log.info(f"Wrote xlsx: {xlsx_path} ({len(records)} rows, {len(columns)} columns)")


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Process only first N files (pilot run)")
    parser.add_argument("--workers", type=int, default=8, help="Thread pool size for network fetches")
    parser.add_argument("--build-xlsx", action="store_true", help="Only rebuild xlsx from existing jsonl")
    args = parser.parse_args()

    if args.build_xlsx:
        build_xlsx(JSONL_PATH, XLSX_PATH)
        return

    all_html = sorted(glob.glob(os.path.join(HTML_DIR, "*.html")))
    # Only files that actually contain a QC embed link
    candidates = []
    for p in all_html:
        with open(p, encoding="utf-8", errors="replace") as f:
            head = f.read()
        if "embedded_backtest_" in head:
            candidates.append(p)

    if args.limit:
        candidates = candidates[: args.limit]

    already_done = load_completed_names(JSONL_PATH)
    todo = [p for p in candidates if os.path.splitext(os.path.basename(p))[0] not in already_done]

    log.info(f"Total candidates: {len(candidates)}  Already done: {len(already_done)}  To process: {len(todo)}")

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(process_one, p): p for p in todo}
        for i, fut in enumerate(as_completed(futures), 1):
            record = fut.result()
            append_jsonl(JSONL_PATH, record)
            if i % 25 == 0:
                log.info(f"Progress: {i}/{len(todo)}")

    build_xlsx(JSONL_PATH, XLSX_PATH)


if __name__ == "__main__":
    main()
