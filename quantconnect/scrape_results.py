"""
Loop through the QuantConnect embed URLs in urls.json, render each one
with a headless browser, and save the rendered stats/text/screenshot for
each strategy under results/<strategy_name>/.

The QuantConnect embed is a JS single-page terminal, not static HTML, so
plain requests.get() won't see the numbers - this uses Playwright to let
the page load before scraping.

Usage:
    pip install -r requirements.txt
    playwright install chromium   # skip if a browser is already installed
    python scrape_results.py [--limit N] [--delay SECONDS] [--retries N]

Output per strategy (results/<strategy_name>/):
    text.txt        - all visible text on the rendered page
    stats.json      - key/value pairs parsed out of common QC stat labels
    screenshot.png  - full-page screenshot, for anything the parser misses
"""

import argparse
import json
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

HERE = Path(__file__).resolve().parent
URLS_FILE = HERE / "urls.json"
RESULTS_DIR = HERE / "results"

# Statistic labels as they commonly appear in QuantConnect backtest reports.
# The parser looks for "<label>" followed shortly after by a numeric-looking value.
STAT_LABELS = [
    "Sharpe Ratio",
    "Compounding Annual Return",
    "Drawdown",
    "Net Profit",
    "Total Trades",
    "Win Rate",
    "Loss Rate",
    "Annual Standard Deviation",
    "Annual Variance",
    "Alpha",
    "Beta",
    "Information Ratio",
    "Tracking Error",
    "Treynor Ratio",
]


def parse_stats(page_text):
    """Best-effort extraction of labeled statistics from the page's plain text."""
    stats = {}
    for label in STAT_LABELS:
        # Look for the label, then the nearest number/percentage within ~50 chars after it.
        pattern = re.compile(re.escape(label) + r"\s*[:\-]?\s*(-?[\d,]+\.?\d*\s*%?)", re.IGNORECASE)
        match = pattern.search(page_text)
        if match:
            stats[label] = match.group(1).strip()
    return stats


def scrape_one(page, strategy_name, url, retries):
    out_dir = RESULTS_DIR / strategy_name
    out_dir.mkdir(parents=True, exist_ok=True)

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            # Give the terminal's JS a moment to finish rendering stats/charts.
            page.wait_for_timeout(3000)

            text = page.inner_text("body")
            (out_dir / "text.txt").write_text(text, encoding="utf-8")

            stats = parse_stats(text)
            (out_dir / "stats.json").write_text(
                json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8"
            )

            page.screenshot(path=str(out_dir / "screenshot.png"), full_page=True)
            return True, None
        except PlaywrightTimeoutError as e:
            last_error = str(e)
            time.sleep(2 * attempt)
        except Exception as e:
            last_error = str(e)
            break

    (out_dir / "error.txt").write_text(last_error or "unknown error", encoding="utf-8")
    return False, last_error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N strategies (for testing)")
    parser.add_argument("--delay", type=float, default=2.0, help="Seconds to wait between requests")
    parser.add_argument("--retries", type=int, default=2, help="Retries per URL on timeout")
    parser.add_argument("--skip-existing", action="store_true", help="Skip strategies that already have a stats.json")
    args = parser.parse_args()

    if not URLS_FILE.exists():
        raise SystemExit("urls.json not found - run extract_urls.py first")

    mapping = json.loads(URLS_FILE.read_text(encoding="utf-8"))
    items = list(mapping.items())
    if args.limit:
        items = items[: args.limit]

    RESULTS_DIR.mkdir(exist_ok=True)

    ok_count = 0
    fail_count = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for i, (strategy_name, url) in enumerate(items, start=1):
            if args.skip_existing and (RESULTS_DIR / strategy_name / "stats.json").exists():
                print(f"[{i}/{len(items)}] {strategy_name}: skipped (already scraped)")
                continue

            print(f"[{i}/{len(items)}] {strategy_name}: fetching...")
            success, error = scrape_one(page, strategy_name, url, args.retries)
            if success:
                ok_count += 1
                print(f"[{i}/{len(items)}] {strategy_name}: done")
            else:
                fail_count += 1
                print(f"[{i}/{len(items)}] {strategy_name}: FAILED - {error}")

            time.sleep(args.delay)

        browser.close()

    print(f"\nDone. {ok_count} succeeded, {fail_count} failed. Results in {RESULTS_DIR}")


if __name__ == "__main__":
    main()
