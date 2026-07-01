"""
Scan html_files/*.html for embedded QuantConnect backtest iframes and
write a strategy -> URL mapping to urls.json.

Usage:
    python extract_urls.py
"""

import json
import re
from pathlib import Path

HTML_DIR = Path(__file__).resolve().parent.parent / "html_files"
OUTPUT_FILE = Path(__file__).resolve().parent / "urls.json"

IFRAME_PATTERN = re.compile(r'<iframe src="([^"]+quantconnect\.com[^"]*)"', re.IGNORECASE)


def extract_urls():
    mapping = {}
    for html_file in sorted(HTML_DIR.glob("*.html")):
        strategy_name = html_file.stem
        text = html_file.read_text(encoding="utf-8", errors="ignore")
        match = IFRAME_PATTERN.search(text)
        if match:
            mapping[strategy_name] = match.group(1)
    return mapping


if __name__ == "__main__":
    mapping = extract_urls()
    OUTPUT_FILE.write_text(json.dumps(mapping, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Found {len(mapping)} strategies with a QuantConnect embed out of "
          f"{len(list(HTML_DIR.glob('*.html')))} total HTML files.")
    print(f"Wrote mapping to {OUTPUT_FILE}")
