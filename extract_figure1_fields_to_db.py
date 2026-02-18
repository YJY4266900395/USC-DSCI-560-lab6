import re
from pathlib import Path
import mysql.connector

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "oil_wells",
}

OUT_DIR = Path("outputs")

API_RE = re.compile(r"\b(\d{2})\D?(\d{3})\D?(\d{5})\b")
WELL_FILE_RE = re.compile(r"(Well\s*File\s*No\.?|Well\s*File\s*#)\s*[:#]?\s*([0-9]{3,10})", re.IGNORECASE)
PLSS_RE = re.compile(r"\b([NSEW]{1,2}\s*[NSEW]{1,2})\b", re.IGNORECASE)
SECTION_RE = re.compile(r"\bSec(?:tion)?\.?\s*[:#]?\s*(\d{1,2})\b", re.IGNORECASE)
TWP_RE = re.compile(r"\bT(?:ownship)?\s*[:#]?\s*(\d{1,3})\s*([NS])\b", re.IGNORECASE)
RNG_RE = re.compile(r"\bR(?:ange)?\s*[:#]?\s*(\d{1,3})\s*([EW])\b", re.IGNORECASE)
COUNTY_RE = re.compile(r"\b([A-Z][A-Z ]+?)\s+COUNTY\b", re.IGNORECASE)
STATE_RE = re.compile(r"\b(ND|NORTH\s+DAKOTA)\b", re.IGNORECASE)

def norm_api(s):
    m = API_RE.search(s or "")
    if not m:
        return None
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

def pick_best_plss(text):
    cands = []
    for m in PLSS_RE.finditer(text):
        v = re.sub(r"\s+", "", m.group(1).upper())
        if v in ("NWNE","NWNW","NENW","NENE","SWNE","SWNW","SENW","SENE","NWSW","NWSE","NESW","NESE","SWSW","SWSE","SESW","SESE"):
            cands.append(v)
    return cands[0] if cands else None

def pick_county(text):
    ms = list(COUNTY_RE.finditer(text))
    if not ms:
        return None
    v = ms[0].group(1).strip()
    v = re.sub(r"\s{2,}", " ", v)
    return v.title()

def extract_fields(text):
    api = norm_api(text)
    well_file_no = None
    m = WELL_FILE_RE.search(text)
    if m:
        well_file_no = m.group(2)

    plss = pick_best_plss(text)

    section_no = None
    m = SECTION_RE.search(text)
    if m:
        try:
            section_no = int(m.group(1))
        except:
            section_no = None

    township_code = None
    m = TWP_RE.search(text)
    if m:
        township_code = f"{m.group(1)}{m.group(2).upper()}"

    range_code = None
    m = RNG_RE.search(text)
    if m:
        range_code = f"{m.group(1)}{m.group(2).upper()}"

    county = pick_county(text)

    state_code = None
    m = STATE_RE.search(text)
    if m:
        state_code = "ND"

    return {
        "api_number": api,
        "well_file_no": well_file_no,
        "plss_quarter": plss,
        "section_no": section_no,
        "township_code": township_code,
        "range_code": range_code,
        "county": county,
        "state_code": state_code,
    }

def merge_nonempty(a, b):
    out = dict(a)
    for k, v in b.items():
        if k == "api_number":
            continue
        if v is not None and v != "":
            if out.get(k) in (None, ""):
                out[k] = v
    return out

def read_dir_texts(wdir: Path):
    texts = []
    for p in sorted(wdir.glob("hit_*.txt")):
        try:
            texts.append(p.read_text(errors="ignore"))
        except:
            pass
    if not texts:
        for p in sorted(wdir.glob("*.txt")):
            try:
                texts.append(p.read_text(errors="ignore"))
            except:
                pass
    return texts

def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()

    wdirs = [p for p in OUT_DIR.iterdir() if p.is_dir() and p.name.startswith("W")]
    wdirs.sort(key=lambda x: x.name)

    updated = 0
    skipped = 0
    missing_api = 0

    for i, wdir in enumerate(wdirs, 1):
        texts = read_dir_texts(wdir)
        if not texts:
            skipped += 1
            continue

        agg = {"api_number": None}
        api = None

        for t in texts:
            f = extract_fields(t)
            if not api and f["api_number"]:
                api = f["api_number"]
                agg["api_number"] = api
            agg = merge_nonempty(agg, f)

        if not api:
            missing_api += 1
            continue

        sets = []
        vals = []

        for col in ("well_file_no","plss_quarter","section_no","township_code","range_code","state_code","county"):
            v = agg.get(col)
            if v is None or v == "":
                continue
            sets.append(f"{col}=%s")
            vals.append(v)

        if not sets:
            skipped += 1
            continue

        vals.append(api)
        sql = f"UPDATE wells SET {', '.join(sets)} WHERE api_number=%s"
        cur.execute(sql, vals)
        if cur.rowcount > 0:
            updated += 1

        if i % 50 == 0:
            conn.commit()

    conn.commit()
    cur.close()
    conn.close()
    print(f"DONE. updated={updated}, skipped={skipped}, missing_api={missing_api}, total_dirs={len(wdirs)}")

if __name__ == "__main__":
    main()
