"""
scrape_production.py — Step 3: Web Scraping (DrillingEdge)
==========================================================
Strategy (reliable, no fragile clicks):
  1. Load search results via direct GET URL with API# parameter
  2. Parse the results HTML to extract the well detail page href
  3. Navigate to that href directly (driver.get, not click)
  4. Parse the detail page for target fields

Usage:
    python3 scrape_production.py \
        --well_jsonl output/parsed/well_info.jsonl \
        --out_jsonl  output/parsed/production_data.jsonl

Optional:
    --delay 2.0          Seconds between page loads (default: 2.0)
    --headless           Run Chrome headless
    --resume             Skip wells already in output file
"""

import argparse
import json
import re
import time
import unicodedata
from pathlib import Path
from typing import Optional, Dict, List
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup

# ── Constants ────────────────────────────────────────────────────────────────

# From your screenshot: the search form submits as GET with these params
SEARCH_TPL = (
    "https://www.drillingedge.com/search"
    "?type=wells"
    "&operator_name="
    "&well_name="
    "&api_no={api}"
    "&lease_key="
    "&state="
    "&county="
    "&well_status="
    "&section="
    "&township="
    "&range="
    "&min_boe="
    "&max_boe="
    "&min_depth="
    "&max_depth="
    "&field_formation="
)

RE_SPACES = re.compile(r"\s+")
RE_MEMBERS = re.compile(r"Members\s*Only", re.I)

# ── Helpers ──────────────────────────────────────────────────────────────────

def norm(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = s.replace("\u00a0", " ").replace("\u200b", "")
    return RE_SPACES.sub(" ", s).strip()


def parse_num(s: str) -> Optional[float]:
    """'1.1 k' → 1100.0,  '303' → 303.0,  '2,200' → 2200.0"""
    if not s:
        return None
    s = norm(s)
    m = re.match(r"([\d,.]+)\s*k\b", s, re.I)
    if m:
        try: return float(m.group(1).replace(",", "")) * 1000
        except ValueError: pass
    m = re.match(r"([\d,.]+)\s*M\b", s, re.I)
    if m:
        try: return float(m.group(1).replace(",", "")) * 1_000_000
        except ValueError: pass
    m = re.search(r"[\d,]+\.?\d*", s.replace(",", ""))
    if m:
        try: return float(m.group(0))
        except ValueError: pass
    return None


def clean_val(v: str) -> Optional[str]:
    v = norm(v)
    if not v or RE_MEMBERS.search(v) or v.lower() in ("n/a", "na", "null", "none"):
        return None
    return v


def safe_name(name) -> str:
    """Return well name or '(no name)' if None."""
    if name is None:
        return "(no name)"
    return str(name)


# ── Browser ──────────────────────────────────────────────────────────────────

def make_driver(headless: bool = False) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])
    opts.add_argument("--log-level=3")
    driver = webdriver.Chrome(options=opts)
    driver.implicitly_wait(8)
    return driver


# ── Step 1: Search → get detail page URL ─────────────────────────────────────

def get_well_url(driver: webdriver.Chrome, api: str, delay: float) -> Optional[str]:
    """
    Load search results page for this API#,
    parse the HTML to find the well detail page link,
    return the full URL (not click, just extract href).
    """
    search_url = SEARCH_TPL.format(api=quote_plus(api))
    driver.get(search_url)
    time.sleep(delay)

    # Wait for table to appear
    try:
        WebDriverWait(driver, 12).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
        )
    except TimeoutException:
        return None

    time.sleep(1)

    # Parse with BS4 — much more reliable than Selenium element clicking
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Find all <a> inside <table> ... <td>
    for a in soup.select("table td a"):
        href = a.get("href", "")
        # Skip operator links
        if "/operators/" in href:
            continue
        # We want links like /north-dakota/mckenzie-county/wells/...
        if "/wells/" in href:
            print(href)
            if href.startswith("http"):
                return href
            return "https://www.drillingedge.com" + href

    # Fallback: any link with the API in it
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Match links containing the API number (with or without dashes)
        api_nodash = api.replace("-", "")
        if api in href or api_nodash in href:
            if "/operators/" in href:
                continue
            if href.startswith("http"):
                return href
            return "https://www.drillingedge.com" + href

    return None


# ── Step 2: Parse detail page ────────────────────────────────────────────────
default_data = {
        "api": None,
        "well_name": None,
        "well_status": None,
        "well_type": None,
        "closest_city": None,
        "oil_barrels": None,
        "gas_mcf": None,
        "operator": None,
        "county_state": None,
        "first_production_date": None,
        "most_recent_production_date": None,
        "drillingedge_url": None,
        "scrape_success": False
    }
def parse_detail(driver: webdriver.Chrome, data: dict = default_data) -> Dict:
    """Extract fields from the well detail page."""

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # ── KV pairs from the "Well Details" table ──
    # Rows have paired cells: [key, value, key, value, ...]
    kv: Dict[str, str] = {}
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            for i in range(0, len(cells) - 1, 2):
                k = norm(cells[i].get_text(" ", strip=True))
                v = norm(cells[i + 1].get_text(" ", strip=True))
                if k and v:
                    kv[k] = v

    # Map some target fields from the details table
    # We'll also extract well_name, operator and county
    for k, v in kv.items():
        kl = k.strip().lower()
        if (data.get("well_name") is None or data.get("well_name") == "and Number") and kl == "well name":
            data["well_name"] = clean_val(v)
            continue
        if data.get("operator") is None and kl == "operator":
            data["operator"] = clean_val(v)
            continue
        if data.get("county_state") is None and kl.startswith("county"):
            # value often like 'McKenzie County, ND'
            data["county_state"] = clean_val(v)
            continue
        if data.get("well_status") is None and kl == "well status":
            data["well_status"] = clean_val(v)
            continue
        if data.get("well_type") is None and kl == "well type":
            data["well_type"] = clean_val(v)
            continue
        if data.get("closest_city") is None and kl == "closest city":
            data["closest_city"] = clean_val(v)
            continue
        # Production dates in the details table
        if data.get("first_production_date") is None and "first production" in kl:
            data["first_production_date"] = clean_val(v)
            continue
        if data.get("most_recent_production_date") is None and ("most recent" in kl or "most recent production" in kl):
            data["most_recent_production_date"] = clean_val(v)
            continue

    # ── Production badges from Well Summary ──
    # "1.1 k  Barrels of Oil Produced in Dec 2025"
    # "303    Barrels of Oil Produced in May 2023"
    page_text = soup.get_text(" ", strip=True)

    m = re.search(r"([\d,.]+\s*k?)\s*Barrels?\s*(?:of\s*)?Oil\s*Produced", page_text, re.I)
    if m:
        data["oil_barrels"] = parse_num(m.group(1))

    m = re.search(r"([\d,.]+\s*k?)\s*MCF\s*(?:of\s*)?Gas\s*Produced", page_text, re.I)
    if m:
        data["gas_mcf"] = parse_num(m.group(1))

    # ── Fallback: monthly prod columns in the details table ──
    for k, v in kv.items():
        kl = k.lower()
        if "oil prod" in kl and data["oil_barrels"] is None:
            cv = clean_val(v)
            if cv:
                data["oil_barrels"] = parse_num(cv)
        if "gas prod" in kl and data["gas_mcf"] is None:
            cv = clean_val(v)
            if cv:
                data["gas_mcf"] = parse_num(cv)

    # normalize empty strings to None
    for kk in list(data.keys()):
        if isinstance(data[kk], str):
            data[kk] = clean_val(data[kk])

    return data


# ── JSONL I/O ────────────────────────────────────────────────────────────────

def read_jsonl(path: Path) -> List[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def append_jsonl(row: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Scrape DrillingEdge using Selenium.")
    ap.add_argument("--well_jsonl", required=True)
    ap.add_argument("--out_jsonl", required=True)
    ap.add_argument("--delay", type=float, default=2.0)
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    well_jsonl = Path(args.well_jsonl)
    out_jsonl = Path(args.out_jsonl)

    if not well_jsonl.exists():
        print(f"ERROR: {well_jsonl} not found")
        return

    wells = read_jsonl(well_jsonl)
    print(f"Loaded {len(wells)} wells from {well_jsonl}")

    # Resume
    done_apis = set()
    if args.resume and out_jsonl.exists():
        for row in read_jsonl(out_jsonl):
            if row.get("api"):
                done_apis.add(row["api"])
        print(f"Resume: {len(done_apis)} already done, skipping.")
    else:
        if out_jsonl.exists():
            out_jsonl.unlink()

    print(f"Starting Chrome (headless={args.headless})...")
    driver = make_driver(headless=args.headless)

    success = 0
    failed = 0
    skipped = 0

    try:
        for i, well in enumerate(wells, 1):
            api = well.get("api")
            if not api:
                skipped += 1
                continue
            if api in done_apis:
                skipped += 1
                continue

            name = safe_name(well.get("well_name", "null"))
            print(f"[{i}/{len(wells)}] {api}  {name[:45]:<45s}", end="  ", flush=True)

            row = {
                "api": api,
                "well_name": well.get("well_name"),
                "well_status": None,
                "well_type": None,
                "closest_city": None,
                "oil_barrels": None,
                "gas_mcf": None,
                "operator": well.get("operator"),
                "county_state": well.get("county_state"),
                "first_production_date": None,
                "most_recent_production_date": None,
                "drillingedge_url": None,
                "scrape_success": False
                }

            try:
                # Step 1: search → extract detail URL from results HTML
                detail_url = get_well_url(driver, api, args.delay)
                if not detail_url:
                    print("FAIL (no link in results)")
                    failed += 1
                    append_jsonl(row, out_jsonl)
                    continue

                # Step 2: navigate to detail page directly
                driver.get(detail_url)
                time.sleep(args.delay)

                # Verify it's a real detail page
                src = driver.page_source
                if "Well Summary" not in src and "Well Details" not in src:
                    print("FAIL (not a detail page)")
                    failed += 1
                    append_jsonl(row, out_jsonl)
                    continue

                # Step 3: parse
                page_data = parse_detail(driver, row)
                row.update(page_data)
                row["drillingedge_url"] = detail_url
                row["scrape_success"] = True
                success += 1

                s = page_data.get("well_status") or "?"
                o = page_data.get("oil_barrels") or "?"
                g = page_data.get("gas_mcf") or "?"
                print(f"OK  status={s}  oil={o}  gas={g}")

            except Exception as e:
                print(f"ERROR {type(e).__name__}: {e}")
                failed += 1

            append_jsonl(row, out_jsonl)
            time.sleep(args.delay * 0.5)

    except KeyboardInterrupt:
        print("\n\nInterrupted! Progress saved.")
    finally:
        driver.quit()
        print(f"\nDone. success={success}  failed={failed}  skipped={skipped}")
        print(f"Output: {out_jsonl}")
        if failed > 0:
            print("Tip: re-run with --resume to retry failed ones won't help (they stay).")
            print("     Delete output and re-run to retry all.")


if __name__ == "__main__":
    main()