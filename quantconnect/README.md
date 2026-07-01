# QuantConnect Backtest Scraper

Extracts the embedded QuantConnect backtest results referenced in `html_files/*.html`
(800 of the 1069 strategies have one) and saves the rendered output for each.

The embed at each URL is a QuantConnect terminal single-page app, not static HTML,
so the numbers only appear after its JavaScript runs. `scrape_results.py` uses
Playwright (headless Chromium) to render each page before scraping.

## Steps

1. **Extract the embed URLs** (no network needed, reads local HTML files):

   ```bash
   python extract_urls.py
   ```

   Writes `urls.json`: `{ "<strategy_name>": "<quantconnect embed url>", ... }`.
   Already generated and committed - re-run only if `html_files/` changes.

2. **Scrape each URL** (needs internet access to quantconnect.com):

   ```bash
   pip install -r requirements.txt
   playwright install chromium   # one-time browser download
   python scrape_results.py
   ```

   Useful flags:
   - `--limit N` - only process the first N strategies, for a quick test run
   - `--delay SECONDS` - pause between requests (default 2s, be polite to QC's servers)
   - `--retries N` - retry attempts per URL on timeout (default 2)
   - `--skip-existing` - resume a partial run without re-scraping strategies already done

## Output

For each strategy, `results/<strategy_name>/` contains:

- `text.txt` - all visible text from the rendered page
- `stats.json` - best-effort parse of labeled statistics (Sharpe Ratio, Compounding
  Annual Return, Drawdown, etc.) found in the page text
- `screenshot.png` - full-page screenshot, useful for anything the text parser missed
  or for visually confirming the chart rendered
- `error.txt` - written instead of the above if all retries failed for that strategy

## Notes

- This was written and generated in a sandboxed cloud environment whose network
  policy blocks `quantconnect.com` (confirmed via a direct request that failed with
  a 403 at the proxy). The scraper itself has not been run end-to-end against a
  live QuantConnect page - run a small test first with `--limit 3` and check the
  screenshots/stats.json before doing a full 800-strategy run.
- `stats.json` extraction is regex-based against common QuantConnect report labels
  and may miss stats if QC changes its report layout - the full `text.txt` and
  `screenshot.png` are kept per strategy as a fallback for anything not captured.
- 800 sequential page loads is meaningful load on QuantConnect's servers - keep the
  default delay (or increase it) and check QuantConnect's terms of service if running
  this at full scale repeatedly.
