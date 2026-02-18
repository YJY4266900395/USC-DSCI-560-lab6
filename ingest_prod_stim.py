import csv
import json
from pathlib import Path
import mysql.connector

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "oil_wells",
}

BASE_DIR = Path(__file__).resolve().parent
PROD_DIR = BASE_DIR / "production_data"
STIM_DIR = BASE_DIR / "stimulation_data"

def norm_api(s):
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    s = s.replace("–", "-").replace("—", "-")
    s = s.replace(" ", "")
    return s

def get_conn():
    return mysql.connector.connect(**DB_CONFIG)

def table_columns(cur, table):
    cur.execute(f"SHOW COLUMNS FROM {table}")
    return [r[0] for r in cur.fetchall()]

def iter_files(folder):
    if not folder.exists():
        return []
    files = []
    files += sorted(folder.glob("*.csv"))
    files += sorted(folder.glob("*.json"))
    files += sorted(folder.glob("*.jsonl"))
    return files

def read_rows(path):
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
    elif path.suffix.lower() in [".json", ".jsonl"]:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            txt = f.read().strip()
            if not txt:
                return
            if path.suffix.lower() == ".jsonl":
                for line in txt.splitlines():
                    line = line.strip()
                    if line:
                        yield json.loads(line)
            else:
                obj = json.loads(txt)
                if isinstance(obj, list):
                    for row in obj:
                        yield row
                elif isinstance(obj, dict) and "data" in obj and isinstance(obj["data"], list):
                    for row in obj["data"]:
                        yield row
                else:
                    yield obj

def parse_float(x):
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    if not s or s.lower() in ["null", "none", "nan"]:
        return None
    s = s.replace(",", "")
    try:
        return float(s)
    except:
        return None

def lookup_well_id(cur, api_number=None, well_file_no=None):
    if api_number:
        cur.execute("SELECT id FROM wells WHERE api_number=%s LIMIT 1", (api_number,))
        r = cur.fetchone()
        if r:
            return int(r[0])
    if well_file_no:
        cur.execute("SELECT id FROM wells WHERE well_file_no=%s LIMIT 1", (str(well_file_no),))
        r = cur.fetchone()
        if r:
            return int(r[0])
    return None

def upsert_row(cur, table, cols, data):
    use_cols = [c for c in cols if c in data and data[c] is not None and c != "id"]
    if "well_id" not in use_cols and "well_id" in cols and "well_id" in data and data["well_id"] is not None:
        use_cols = ["well_id"] + use_cols
    if not use_cols:
        return False
    placeholders = ",".join(["%s"] * len(use_cols))
    col_list = ",".join(use_cols)
    update_cols = [c for c in use_cols if c not in ["id", "well_id"]]
    if update_cols:
        update_sql = ",".join([f"{c}=VALUES({c})" for c in update_cols])
    else:
        update_sql = "well_id=VALUES(well_id)"
    sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_sql}"
    vals = [data[c] for c in use_cols]
    cur.execute(sql, vals)
    return True

def ingest_production():
    print(f"PROD_DIR={PROD_DIR}")
    conn = get_conn()
    cur = conn.cursor()
    cols = table_columns(cur, "production_data")
    files = iter_files(PROD_DIR)
    if not files:
        print("No files found in production_data/")
        conn.close()
        return
    inserted = 0
    skipped = 0
    total = 0
    for fp in files:
        for row in read_rows(fp):
            total += 1
            api = norm_api(row.get("api_number") or row.get("api") or row.get("API") or row.get("API_NUMBER"))
            wfile = row.get("well_file_no") or row.get("well_file") or row.get("wellfileno") or row.get("WELL_FILE_NO")
            well_id = lookup_well_id(cur, api_number=api, well_file_no=wfile)
            if well_id is None:
                skipped += 1
                continue
            data = {"well_id": well_id}
            if "well_status" in cols:
                data["well_status"] = row.get("well_status") or row.get("status") or row.get("WELL_STATUS")
            if "well_type" in cols:
                data["well_type"] = row.get("well_type") or row.get("type") or row.get("WELL_TYPE")
            if "closest_city" in cols:
                data["closest_city"] = row.get("closest_city") or row.get("city") or row.get("CLOSEST_CITY")
            if "oil_barrels" in cols:
                data["oil_barrels"] = parse_float(row.get("oil_barrels") or row.get("oil") or row.get("OIL_BARRELS"))
            if "gas_mcf" in cols:
                data["gas_mcf"] = parse_float(row.get("gas_mcf") or row.get("gas") or row.get("GAS_MCF"))
            ok = upsert_row(cur, "production_data", cols, data)
            if ok:
                inserted += 1
            if inserted % 200 == 0:
                conn.commit()
    conn.commit()
    conn.close()
    print(f"production_data DONE. total_rows={total}, upserted={inserted}, skipped_no_well={skipped}")

def ingest_stimulation():
    print(f"STIM_DIR={STIM_DIR}")
    conn = get_conn()
    cur = conn.cursor()
    cols = table_columns(cur, "stimulation_data")
    files = iter_files(STIM_DIR)
    if not files:
        print("No files found in stimulation_data/")
        conn.close()
        return
    inserted = 0
    skipped = 0
    total = 0
    for fp in files:
        for row in read_rows(fp):
            total += 1
            api = norm_api(row.get("api_number") or row.get("api") or row.get("API") or row.get("API_NUMBER"))
            wfile = row.get("well_file_no") or row.get("well_file") or row.get("wellfileno") or row.get("WELL_FILE_NO")
            well_id = lookup_well_id(cur, api_number=api, well_file_no=wfile)
            if well_id is None:
                skipped += 1
                continue
            data = {"well_id": well_id}
            for k in cols:
                if k in ["id", "well_id"]:
                    continue
                if k in row and row[k] not in [None, ""]:
                    v = row[k]
                    if isinstance(v, str):
                        v = v.strip()
                    data[k] = v
            ok = upsert_row(cur, "stimulation_data", cols, data)
            if ok:
                inserted += 1
            if inserted % 200 == 0:
                conn.commit()
    conn.commit()
    conn.close()
    print(f"stimulation_data DONE. total_rows={total}, upserted={inserted}, skipped_no_well={skipped}")

if __name__ == "__main__":
    ingest_production()
    ingest_stimulation()
