import os
import re
from pathlib import Path
import mysql.connector

DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "",
    "database": "oil_wells",
    "port": 3306,
}

OUTPUTS_DIR = Path("outputs")

def normalize_text(s: str) -> str:
    s = s.replace("\u2019", "'").replace("\u2018", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("\ufb01", "fi").replace("\ufb02", "fl")
    s = re.sub(r"[ \t]+", " ", s)
    return s

def extract_number_with_unit(text, patterns):
    for rx, unit in patterns:
        m = re.search(rx, text, flags=re.IGNORECASE)
        if m:
            raw = m.group(1)
            raw = raw.replace(",", "").replace(" ", "")
            try:
                return float(raw), unit
            except Exception:
                pass
    return None, None

def detect_treatment_type(text):
    candidates = []
    m = re.search(r"treatment\s*type\s*[:\-]\s*([A-Za-z0-9 /&\-\(\)]+)", text, re.IGNORECASE)
    if m:
        candidates.append(m.group(1).strip())
    if re.search(r"hydraulic\s+fractur", text, re.IGNORECASE):
        candidates.append("Hydraulic Fracture")
    if re.search(r"\bfrac\b|\bfracture\b", text, re.IGNORECASE):
        candidates.append("Frac / Fracture Treatment")
    if re.search(r"stimulation", text, re.IGNORECASE):
        candidates.append("Stimulation")
    candidates = [c for c in candidates if c]
    if not candidates:
        return None
    candidates.sort(key=lambda x: len(x), reverse=True)
    return candidates[0][:255]

def parse_figure2_from_dir(well_dir: Path):
    hit_files = sorted(well_dir.glob("hit_*.txt"))
    if not hit_files:
        return None

    best = {
        "treatment_type": None,
        "total_proppant": None,
        "fluid_volume": None,
        "max_pressure": None,
        "score": 0,
    }

    proppant_patterns = [
        (r"proppant[^0-9]{0,40}([\d,]{2,})\s*(?:lb|lbs|#)\b", "lb"),
        (r"total\s*proppant[^0-9]{0,40}([\d,]{2,})\s*(?:lb|lbs|#)\b", "lb"),
        (r"proppant[^0-9]{0,40}([\d,]{2,})\s*ton\b", "ton"),
    ]
    fluid_patterns = [
        (r"fluid[^0-9]{0,40}([\d,]{2,})\s*bbl\b", "bbl"),
        (r"fluid\s*volume[^0-9]{0,40}([\d,]{2,})\s*bbl\b", "bbl"),
        (r"fluid[^0-9]{0,40}([\d,]{2,})\s*gal\b", "gal"),
    ]
    pressure_patterns = [
        (r"(?:max(?:imum)?\s*)?press(?:ure)?[^0-9]{0,40}([\d,]{2,})\s*psi\b", "psi"),
        (r"treat(?:ing)?\s*press(?:ure)?[^0-9]{0,40}([\d,]{2,})\s*psi\b", "psi"),
        (r"([\d,]{2,})\s*psi\s*(?:treat|treating|max)", "psi"),
    ]

    for fp in hit_files:
        try:
            txt = fp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        txt = normalize_text(txt)
        low = txt.lower()

        score = 0
        for kw in ["proppant", "treat", "treating", "pressure", "psi", "fluid", "bbl", "frac", "fracture", "stimulation"]:
            if kw in low:
                score += 1

        tt = detect_treatment_type(txt)
        prop_v, _ = extract_number_with_unit(txt, proppant_patterns)
        fluid_v, _ = extract_number_with_unit(txt, fluid_patterns)
        pres_v, _ = extract_number_with_unit(txt, pressure_patterns)

        filled = sum(x is not None for x in [tt, prop_v, fluid_v, pres_v])
        score += filled * 3

        if score > best["score"]:
            best.update(
                {
                    "treatment_type": tt,
                    "total_proppant": prop_v,
                    "fluid_volume": fluid_v,
                    "max_pressure": pres_v,
                    "score": score,
                }
            )

    if all(best[k] is None for k in ["treatment_type", "total_proppant", "fluid_volume", "max_pressure"]):
        return None

    return {
        "treatment_type": best["treatment_type"],
        "total_proppant": best["total_proppant"],
        "fluid_volume": best["fluid_volume"],
        "max_pressure": best["max_pressure"],
    }

def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT id, api_number, well_file_no FROM wells WHERE well_file_no IS NOT NULL;")
    wells = cur.fetchall()

    total = len(wells)
    ok = 0
    miss = 0

    for i, w in enumerate(wells, start=1):
        wid = w["id"]
        api = w["api_number"]
        wno = str(w["well_file_no"]).strip()
        well_dir = OUTPUTS_DIR / f"W{wno}"

        print(f"[{i}/{total}] {api} (W{wno})")

        if not well_dir.exists():
            miss += 1
            continue

        data = parse_figure2_from_dir(well_dir)
        if data is None:
            miss += 1
            continue

        cur.execute("DELETE FROM stimulation_data WHERE well_id = %s;", (wid,))
        cur.execute(
            """
            INSERT INTO stimulation_data (well_id, treatment_type, total_proppant, fluid_volume, max_pressure)
            VALUES (%s, %s, %s, %s, %s);
            """,
            (wid, data["treatment_type"], data["total_proppant"], data["fluid_volume"], data["max_pressure"]),
        )

        ok += 1
        if i % 10 == 0:
            conn.commit()

    conn.commit()
    cur.close()
    conn.close()

    print(f"DONE. ok={ok}, miss={miss}, total={total}")

if __name__ == "__main__":
    main()
