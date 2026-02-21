"""
Cleans and normalizes data in JSONL files BEFORE loading into MySQL.
Applies to: well_info.jsonl, stimulation_data.jsonl, production_data.jsonl
Usage:
    python3 preprocess.py --data_dir output/parsed

This reads *.jsonl files in-place (backs up originals as *.jsonl.bak).
"""

import argparse
import json
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Any

# ── Regex patterns ───────────────────────────────────────────────────────────

RE_HTML_TAG = re.compile(r"<[^>]+>")
RE_MULTI_SPACE = re.compile(r"\s{2,}")
RE_OCR_JUNK = re.compile(r"[^\x20-\x7E\u00C0-\u024F\u0300-\u036F°'\".,;:\-/()&#+\n]")
RE_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f-\x9f]")
RE_NUMBER_ONLY = re.compile(r"^[\d,]+\.?\d*$")
RE_OCR_NO_SHORT = re.compile(r"(?i)\band\s*number\b")
RE_OCR_ANDNO = re.compile(r"(?i)\bAND\s*NO\.?\:?")

# State normalization
STATE_MAP = {
    "nd": "North Dakota",
    "north dakota": "North Dakota",
    "mt": "Montana",
    "montana": "Montana",
    "sd": "South Dakota",
    "south dakota": "South Dakota",
    "mn": "Minnesota",
    "minnesota": "Minnesota",
    "wy": "Wyoming",
    "wyoming": "Wyoming",
}

# ── Cleaning Functions ───────────────────────────────────────────────────────

def clean_string(s: Any) -> Optional[str]:
    """Clean a string value: strip HTML, OCR junk, normalize whitespace."""
    if s is None:
        return None
    s = str(s)
    # Remove HTML tags
    s = RE_HTML_TAG.sub("", s)
    # Remove control characters
    s = RE_CONTROL_CHARS.sub("", s)
    # Normalize unicode whitespace
    s = s.replace("\u00a0", " ").replace("\u200b", "")
    # Collapse multiple spaces
    s = RE_MULTI_SPACE.sub(" ", s).strip()
    # Return None if empty
    return s if s else None


def clean_well_name(s: Any) -> Optional[str]:
    """Clean well name and remove common OCR artifacts like 'and Number' or leading 'AND NO.:'.
    Returns None if the remaining name is empty or meaningless.
    """
    v = clean_string(s)
    if v is None:
        return None

    # If the entire string is just 'and Number' (OCR artifact), drop it
    if re.match(r"(?i)^\s*and\s*number\s*$", v):
        return None

    # Remove leading 'AND NO.:' variants (may appear before actual name)
    v = RE_OCR_ANDNO.sub("", v)

    # Remove stray 'and Number' tokens anywhere
    v = RE_OCR_NO_SHORT.sub("", v)

    # Clean up leftover punctuation and extra spaces
    v = re.sub(r"^[\s\-:]+", "", v)
    v = re.sub(r"[\s\-:]+$", "", v)
    v = RE_MULTI_SPACE.sub(" ", v).strip()

    return v if v else None


def clean_ocr_text(s: Any) -> Optional[str]:
    """Aggressive cleaning for raw OCR text fields."""
    if s is None:
        return None
    s = str(s)
    s = RE_HTML_TAG.sub("", s)
    s = RE_CONTROL_CHARS.sub("", s)
    s = s.replace("\u00a0", " ").replace("\u200b", "")
    # Remove common OCR artifacts
    s = s.replace("|", "I")  # pipe often misread as I
    s = re.sub(r"\b[Il]{3,}\b", "", s)  # strings of I/l
    s = RE_MULTI_SPACE.sub(" ", s).strip()
    return s if s else None


def normalize_state(s: Any) -> Optional[str]:
    """Normalize state name to full name."""
    if s is None:
        return None
    s = clean_string(s)
    if s is None:
        return None
    key = s.lower().strip()
    return STATE_MAP.get(key, s)


def fix_longitude(lon: Any) -> Any:
    """
    North Dakota longitudes should be negative (western hemisphere).
    Fix common OCR/parsing errors where sign is dropped.
    """
    if lon is None:
        return None
    try:
        lon = float(lon)
    except (ValueError, TypeError):
        return lon
    # ND longitude range: roughly -97 to -104
    if 97 <= lon <= 110:
        return -lon
    return lon


def fix_latitude(lat: Any) -> Any:
    """Validate latitude is reasonable for ND (roughly 45.9 to 49)."""
    if lat is None:
        return None
    try:
        lat = float(lat)
    except (ValueError, TypeError):
        return lat
    # Reasonable range for ND
    if -90 <= lat <= 90:
        return lat
    return None


def normalize_date(s: Any) -> Optional[str]:
    """Try to parse and normalize a date string to YYYY-MM-DD."""
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    # Already in good format
    # If already ISO full date
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s

    # Try full-date formats -> return ISO YYYY-MM-DD
    full_formats = [
        "%m/%d/%Y", "%m-%d-%Y", "%Y/%m/%d",
        "%m/%d/%y", "%m-%d-%y",
        "%B %d, %Y", "%b %d, %Y",
        "%d-%b-%Y", "%d-%B-%Y",
    ]
    for fmt in full_formats:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Try month-year formats and return as 'Month YYYY' (e.g. 'September 2019')
    month_year_formats = ["%B %Y", "%b %Y", "%Y %B", "%Y %b"]
    for fmt in month_year_formats:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%B %Y")
        except ValueError:
            continue

    return s  # Return original if can't parse


def to_int(v: Any) -> Optional[int]:
    """Convert a value to int, handling commas and whitespace."""
    if v is None:
        return None
    try:
        s = str(v).replace(",", "").strip()
        if not s:
            return None
        return int(float(s))
    except (ValueError, TypeError):
        return None


def to_float(v: Any) -> Optional[float]:
    """Convert a value to float, handling commas and whitespace."""
    if v is None:
        return None
    try:
        s = str(v).replace(",", "").strip()
        if not s:
            return None
        return float(s)
    except (ValueError, TypeError):
        return None


# ── Per-table Preprocessing ──────────────────────────────────────────────────

def preprocess_well(row: dict) -> dict:
    """Clean a well_info record."""
    row["operator"] = clean_string(row.get("operator"))
    row["well_name"] = clean_well_name(row.get("well_name"))
    row["api"] = clean_string(row.get("api"))
    row["enesco_job"] = clean_string(row.get("enesco_job"))
    row["job_type"] = clean_string(row.get("job_type"))
    # Normalize county_state: keep 'County' name and normalize state to full
    cs = clean_string(row.get("county_state"))
    if cs and "," in cs:
        parts = [p.strip() for p in cs.split(",", 1)]
        county = parts[0]
        state = normalize_state(parts[1])
        row["county_state"] = f"{county}, {state}" if state else county
    else:
        row["county_state"] = cs
    row["shl_location"] = clean_string(row.get("shl_location"))
    row["datum"] = clean_string(row.get("datum"))
    row["county"] = clean_string(row.get("county"))
    row["address"] = clean_string(row.get("address"))

    # Normalize state
    row["state"] = normalize_state(row.get("state"))

    # Fix coordinates
    row["latitude"] = fix_latitude(row.get("latitude"))
    row["longitude"] = fix_longitude(row.get("longitude"))

    # Clean raw text fields (keep but clean)
    row["lat_raw"] = clean_ocr_text(row.get("lat_raw"))
    row["lon_raw"] = clean_ocr_text(row.get("lon_raw"))
    row["raw_text"] = clean_ocr_text(row.get("raw_text"))

    return row


def preprocess_stim(row: dict) -> dict:
    """Clean a stimulation_data record."""
    row["date_stimulated"] = normalize_date(row.get("date_stimulated"))
    row["stimulation_formation"] = clean_string(row.get("stimulation_formation"))
    row["treatment_type"] = clean_string(row.get("treatment_type"))
    row["volume_units"] = clean_string(row.get("volume_units"))
    row["details"] = clean_string(row.get("details"))
    row["api"] = clean_string(row.get("api"))

    # Ensure numeric fields
    row["top_ft"] = to_int(row.get("top_ft"))
    row["bottom_ft"] = to_int(row.get("bottom_ft"))
    row["stimulation_stages"] = to_int(row.get("stimulation_stages"))
    row["volume"] = to_float(row.get("volume"))
    row["acid_pct"] = to_float(row.get("acid_pct"))
    row["lbs_proppant"] = to_int(row.get("lbs_proppant"))
    row["max_treatment_pressure_psi"] = to_int(row.get("max_treatment_pressure_psi"))
    row["max_treatment_rate_bbl_min"] = to_float(row.get("max_treatment_rate_bbl_min"))

    # Clean raw text
    row["raw_text"] = clean_ocr_text(row.get("raw_text"))
    row["raw_text_clean"] = clean_ocr_text(row.get("raw_text_clean"))

    return row


def preprocess_production(row: dict) -> dict:
    """Clean a production_data record."""
    row["api"] = clean_string(row.get("api"))
    row["well_name"] = clean_well_name(row.get("well_name"))
    row["well_status"] = clean_string(row.get("well_status"))
    row["well_type"] = clean_string(row.get("well_type"))
    row["closest_city"] = clean_string(row.get("closest_city"))
    # row["field_name"] = clean_string(row.get("field_name"))
    row["drillingedge_url"] = clean_string(row.get("drillingedge_url"))

    # New scraped fields
    row["operator"] = clean_string(row.get("operator"))
    # Normalize county_state similar to well preprocessing
    cs = clean_string(row.get("county_state"))
    if cs and "," in cs:
        parts = [p.strip() for p in cs.split(",", 1)]
        county = parts[0]
        state = normalize_state(parts[1])
        row["county_state"] = f"{county}, {state}" if state else county
    else:
        row["county_state"] = cs

    # Normalize month-year style production dates (keep as text like 'September 2019')
    row["first_production_date"] = normalize_date(row.get("first_production_date"))
    row["most_recent_production_date"] = normalize_date(row.get("most_recent_production_date"))

    # Ensure numeric
    row["oil_barrels"] = to_float(row.get("oil_barrels"))
    row["gas_mcf"] = to_float(row.get("gas_mcf"))

    return row


# ── File Processing ──────────────────────────────────────────────────────────

def process_jsonl(path: Path, preprocess_fn, label: str) -> int:
    """Read a JSONL file, apply preprocessing, write back. Returns row count."""
    if not path.exists():
        print(f"  [{label}] SKIP — file not found: {path}")
        return 0

    # Backup original
    bak = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, bak)

    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    cleaned = [preprocess_fn(row) for row in rows]

    # Write back
    with path.open("w", encoding="utf-8") as f:
        for row in cleaned:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"  [{label}] Processed {len(cleaned)} rows (backup: {bak.name})")
    return len(cleaned)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Preprocess JSONL data before MySQL import.")
    ap.add_argument("--data_dir", required=True, help="Directory containing JSONL files")
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"ERROR: {data_dir} not found")
        return

    print(f"Preprocessing data in: {data_dir}\n")

    total = 0
    total += process_jsonl(data_dir / "well_info.jsonl", preprocess_well, "well_info")
    total += process_jsonl(data_dir / "stimulation_data.jsonl", preprocess_stim, "stimulation_data")
    total += process_jsonl(data_dir / "production_data.jsonl", preprocess_production, "production_data")

    print(f"\nDone. Total rows preprocessed: {total}")


if __name__ == "__main__":
    main()
