import json
import os
from pathlib import Path
import mysql.connector

# ====== 只需要改这里 ======
MYSQL_HOST = "localhost"
MYSQL_USER = "labuser"
MYSQL_PASS = "labpass"
MYSQL_DB   = "dsci560_lab6"

WELL_JSONL = Path("/mnt/e/Jupyter Notebook file/560/lab6/output/parsed/well_info.jsonl")
STIM_JSONL = Path("/mnt/e/Jupyter Notebook file/560/lab6/output/parsed/stimulation_data.jsonl")

# ===========================

def connect():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASS,
        database=MYSQL_DB,
        autocommit=False,
    )

def norm_api(api: str | None):
    if not api:
        return None
    return api.strip() or None

def norm_str(s: str | None):
    if s is None:
        return None
    s = str(s).strip()
    return s if s else None

def load_wells(cur):
    inserted = 0
    updated = 0
    skipped = 0

    sql = """
    INSERT INTO well_info (
      api, ndic_file_no, well_name, operator, address, county, state,
      shl_location, datum,
      latitude, longitude, latitude_raw, longitude_raw,
      source_pdf, relative_path
    )
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    ON DUPLICATE KEY UPDATE
      well_name=VALUES(well_name),
      operator=VALUES(operator),
      address=VALUES(address),
      county=VALUES(county),
      state=VALUES(state),
      shl_location=VALUES(shl_location),
      datum=VALUES(datum),
      latitude=VALUES(latitude),
      longitude=VALUES(longitude),
      latitude_raw=VALUES(latitude_raw),
      longitude_raw=VALUES(longitude_raw),
      source_pdf=VALUES(source_pdf),
      relative_path=VALUES(relative_path);
    """

    with WELL_JSONL.open(encoding="utf-8") as f:
        for ln in f:
            r = json.loads(ln)

            api  = norm_api(r.get("api"))
            ndic = norm_str(r.get("ndic_file_no"))

            # 至少要有一个业务键（你统计 missing api AND ndic = 0）
            if not api and not ndic:
                skipped += 1
                continue

            vals = (
                api, ndic,
                norm_str(r.get("well_name")),
                norm_str(r.get("operator")),
                norm_str(r.get("address")),
                norm_str(r.get("county")),
                norm_str(r.get("state")),
                norm_str(r.get("well_surface_location") or r.get("shl_location")),
                norm_str(r.get("datum")),
                r.get("latitude"),
                r.get("longitude"),
                norm_str(r.get("lat_raw") or r.get("latitude_raw")),
                norm_str(r.get("lon_raw") or r.get("longitude_raw")),
                norm_str(r.get("source_pdf")),
                norm_str(r.get("relative_path")),
            )

            cur.execute(sql, vals)

            # mysql-connector：rowcount 对 upsert 不总可靠，这里用“是否已有记录”不划算
            # 简化：统计执行次数
            inserted += 1

    return inserted, updated, skipped

def lookup_well_id(cur, api, ndic):
    if api:
        cur.execute("SELECT well_id FROM well_info WHERE api=%s", (api,))
        row = cur.fetchone()
        if row:
            return row[0]
    if ndic:
        cur.execute("SELECT well_id FROM well_info WHERE ndic_file_no=%s", (ndic,))
        row = cur.fetchone()
        if row:
            return row[0]
    return None

def load_stims(cur):
    inserted = 0
    skipped_no_well = 0

    sql = """
    INSERT INTO stimulation_data (
      well_id, stim_date, stimulated_formation, top_ft, bottom_ft, stimulation_stages,
      volume, volume_units,
      type_treatment, acid_pct, lbs_proppant,
      max_treat_pressure_psi, max_treat_rate, max_treat_rate_units,
      details, raw_text, source_pdf
    )
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    ON DUPLICATE KEY UPDATE
      stimulated_formation=VALUES(stimulated_formation),
      stimulation_stages=VALUES(stimulation_stages),
      volume=VALUES(volume),
      volume_units=VALUES(volume_units),
      type_treatment=VALUES(type_treatment),
      acid_pct=VALUES(acid_pct),
      lbs_proppant=VALUES(lbs_proppant),
      max_treat_pressure_psi=VALUES(max_treat_pressure_psi),
      max_treat_rate=VALUES(max_treat_rate),
      max_treat_rate_units=VALUES(max_treat_rate_units),
      details=VALUES(details),
      raw_text=VALUES(raw_text),
      source_pdf=VALUES(source_pdf);
    """

    with STIM_JSONL.open(encoding="utf-8") as f:
        for ln in f:
            r = json.loads(ln)

            api  = norm_api(r.get("api"))
            ndic = norm_str(r.get("ndic_file_no"))

            well_id = lookup_well_id(cur, api, ndic)
            if not well_id:
                skipped_no_well += 1
                continue

            vals = (
                well_id,
                r.get("date_stimulated") or r.get("stim_date"),
                norm_str(r.get("stimulation_formation") or r.get("stimulated_formation")),
                r.get("top_ft"),
                r.get("bottom_ft"),
                r.get("stimulation_stages"),
                r.get("volume"),
                norm_str(r.get("volume_units")),
                norm_str(r.get("treatment_type") or r.get("type_treatment")),
                r.get("acid_pct"),
                r.get("lbs_proppant"),
                r.get("max_treatment_pressure_psi") or r.get("max_treat_pressure_psi"),
                r.get("max_treatment_rate_bbl_min") or r.get("max_treat_rate"),
                norm_str(r.get("max_treat_rate_units") or "BBLS/Min"),
                norm_str(r.get("details")),
                norm_str(r.get("raw_text")),
                norm_str(r.get("source_pdf")),
            )

            cur.execute(sql, vals)
            inserted += 1

    return inserted, skipped_no_well

def main():
    assert WELL_JSONL.exists(), f"Missing {WELL_JSONL}"
    assert STIM_JSONL.exists(), f"Missing {STIM_JSONL}"

    conn = connect()
    cur = conn.cursor()

    try:
        w_ins, w_upd, w_skip = load_wells(cur)
        conn.commit()

        s_ins, s_skip = load_stims(cur)
        conn.commit()

        print("=== LOAD DONE ===")
        print(f"wells inserted/processed: {w_ins}  skipped(no api&ndic): {w_skip}")
        print(f"stims inserted/processed: {s_ins}  skipped(no matching well): {s_skip}")

        # quick checks
        cur.execute("SELECT COUNT(*) FROM well_info")
        print("well_info count:", cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM stimulation_data")
        print("stimulation_data count:", cur.fetchone()[0])

        cur.execute("SELECT COUNT(*) FROM well_info WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
        print("wells with lat/lon:", cur.fetchone()[0])

    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()