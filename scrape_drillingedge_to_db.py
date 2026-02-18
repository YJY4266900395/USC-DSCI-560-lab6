import re
import time
import random
import mysql.connector
import requests
from bs4 import BeautifulSoup

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "oil_wells",
}

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

def slugify(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("&", "and")
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-{2,}", "-", s)
    return s.strip("-")

def digits_only(s: str) -> str:
    return re.sub(r"\D+", "", s or "")

def norm_api(api: str) -> str:
    s = (api or "").strip().replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", "", s)
    m = re.search(r"(\d{2})\D*(\d{3})\D*(\d{5})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    if re.fullmatch(r"\d{14}", s):
        return f"{s[0:2]}-{s[2:5]}-{s[5:10]}"
    return s

def parse_scaled_number(num_str: str, suffix: str) -> float:
    x = float(num_str)
    suf = (suffix or "").strip().lower()
    if suf == "k":
        return x * 1000.0
    if suf == "m":
        return x * 1000000.0
    return x

def build_drillingedge_url(api: str, well_name: str, county: str, state_code: str) -> str:
    state_map = {
        "ND": "north-dakota",
        "NORTH DAKOTA": "north-dakota",
    }
    st = state_map.get((state_code or "").strip().upper(), "north-dakota")
    c = (county or "").strip()
    c = c.replace("County", "").strip()
    county_slug = slugify(c) + "-county"
    well_slug = slugify(well_name)
    return f"https://www.drillingedge.com/{st}/{county_slug}/wells/{well_slug}/{api}"

def fetch_html(url: str) -> str:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=25, allow_redirects=True)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}")
    return r.text

def extract_fields(html: str):
    soup = BeautifulSoup(html, "html.parser")
    txt = soup.get_text(" ", strip=True)
    txt = re.sub(r"\s+", " ", txt)

    m_status = re.search(r"Well Status\s+(.+?)\s+Well Type", txt, re.IGNORECASE)
    m_type = re.search(r"Well Type\s+(.+?)\s+(Township|County|Field)", txt, re.IGNORECASE)
    m_city = re.search(r"Closest City\s+(.+?)\s+(Latitude\s*/\s*Longitude|Lat\s*/\s*Long)", txt, re.IGNORECASE)

    status = (m_status.group(1).strip() if m_status else "")
    wtype = (m_type.group(1).strip() if m_type else "")
    city = (m_city.group(1).strip() if m_city else "")

    m_oil = re.search(r"([\d.]+)\s*([kKmM]?)\s*Barrels of Oil Produced in\s+([A-Za-z]{3}\s+\d{4})", txt)
    m_gas = re.search(r"([\d.]+)\s*([kKmM]?)\s*MCF of Gas Produced in\s+([A-Za-z]{3}\s+\d{4})", txt)

    oil = parse_scaled_number(m_oil.group(1), m_oil.group(2)) if m_oil else None
    gas = parse_scaled_number(m_gas.group(1), m_gas.group(2)) if m_gas else None

    return status, wtype, city, oil, gas

def get_conn():
    return mysql.connector.connect(**DB_CONFIG)

def pick(row, *keys):
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return row[k]
    return None

def ensure_tables(cur):
    cur.execute("""
    CREATE TABLE IF NOT EXISTS production_data (
        id INT AUTO_INCREMENT PRIMARY KEY,
        well_id INT,
        well_status VARCHAR(100),
        well_type VARCHAR(100),
        closest_city VARCHAR(255),
        oil_barrels DOUBLE,
        gas_mcf DOUBLE,
        UNIQUE KEY uq_prod_well (well_id),
        FOREIGN KEY (well_id) REFERENCES wells(id)
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS stimulation_data (
        id INT AUTO_INCREMENT PRIMARY KEY,
        well_id INT,
        treatment_type VARCHAR(255),
        total_proppant DOUBLE,
        fluid_volume DOUBLE,
        max_pressure DOUBLE,
        UNIQUE KEY uq_stim_well (well_id),
        FOREIGN KEY (well_id) REFERENCES wells(id)
    )
    """)

def main():
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    ensure_tables(conn.cursor())
    conn.commit()

    cur.execute("SELECT * FROM wells")
    rows = cur.fetchall()
    total = len(rows)
    print(f"Total wells in DB: {total}")

    upd = conn.cursor()
    ok = 0
    miss = 0

    for i, r in enumerate(rows, 1):
        wid = r.get("id")

        api = pick(r, "api_no", "api_number", "api", "api14")
        well_name = pick(r, "well_name", "well", "name")
        county = pick(r, "county")
        state_code = pick(r, "state_code", "state", "state_abbr")

        api = norm_api(str(api or ""))

        if not (wid and api and well_name and county):
            miss += 1
            print(f"[{i}/{total}] MISS meta: id={wid} api={bool(api)} name={bool(well_name)} county={bool(county)}")
            continue

        url = build_drillingedge_url(api, str(well_name), str(county), str(state_code or "ND"))
        print(f"[{i}/{total}] {api}")

        try:
            html = fetch_html(url)
            status, wtype, city, oil, gas = extract_fields(html)

            if not status:
                status = None
            if not wtype:
                wtype = None
            if not city:
                city = None

            upd.execute(
                """
                INSERT INTO production_data (well_id, well_status, well_type, closest_city, oil_barrels, gas_mcf)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  well_status=VALUES(well_status),
                  well_type=VALUES(well_type),
                  closest_city=VALUES(closest_city),
                  oil_barrels=VALUES(oil_barrels),
                  gas_mcf=VALUES(gas_mcf)
                """,
                (wid, status, wtype, city, oil, gas)
            )
            ok += 1

        except Exception as e:
            miss += 1
            print(f"  FAIL: {e}")

        if i % 10 == 0:
            conn.commit()
            print("  commit")

        time.sleep(random.uniform(0.4, 0.9))

    conn.commit()
    cur.close()
    upd.close()
    conn.close()
    print(f"DONE. ok={ok}, miss={miss}, total={total}")

if __name__ == "__main__":
    main()
