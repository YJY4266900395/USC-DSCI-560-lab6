import argparse
import json
from pathlib import Path

import mysql.connector


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield line_no, json.loads(line)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"JSON decode error in {path} at line {line_no}: {e}") from e


def to_date(s):
    # Input is ISO 'YYYY-MM-DD' or None
    return s if s else None


def main():
    ap = argparse.ArgumentParser(description="Load Lab6 jsonl outputs into MySQL.")
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=3306)
    ap.add_argument("--user", required=True)
    ap.add_argument("--password", required=True)
    ap.add_argument("--database", default="lab6")

    ap.add_argument("--well_jsonl", required=True, help="Path to well_info.jsonl")
    ap.add_argument("--stim_jsonl", required=True, help="Path to stimulation_data.jsonl")

    ap.add_argument("--batch_size", type=int, default=500)
    ap.add_argument("--truncate", action="store_true", help="TRUNCATE tables before load (destructive)")
    args = ap.parse_args()

    conn = mysql.connector.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        autocommit=False,
    )
    cur = conn.cursor()

    if args.truncate:
        # FK requires order: stim first then well
        cur.execute("SET FOREIGN_KEY_CHECKS=0")
        cur.execute("TRUNCATE TABLE stimulation_data")
        cur.execute("TRUNCATE TABLE well_info")
        cur.execute("SET FOREIGN_KEY_CHECKS=1")
        conn.commit()

    # ---------- well_info upsert ----------
    well_sql = """
    INSERT INTO well_info (
      primary_id,
      operator, well_name, api, enesco_job, job_type, county_state, shl_location,
      latitude, longitude, datum,
      ndic_file_no, county, state, address,
      lat_raw, lon_raw, latlon_page, latlon_suspect, fig1_pages,
      source_pdf, relative_path, raw_text
    ) VALUES (
      %(primary_id)s,
      %(operator)s, %(well_name)s, %(api)s, %(enesco_job)s, %(job_type)s, %(county_state)s, %(shl_location)s,
      %(latitude)s, %(longitude)s, %(datum)s,
      %(ndic_file_no)s, %(county)s, %(state)s, %(address)s,
      %(lat_raw)s, %(lon_raw)s, %(latlon_page)s, %(latlon_suspect)s, %(fig1_pages)s,
      %(source_pdf)s, %(relative_path)s, %(raw_text)s
    )
    ON DUPLICATE KEY UPDATE
      operator=VALUES(operator),
      well_name=VALUES(well_name),
      api=VALUES(api),
      enesco_job=VALUES(enesco_job),
      job_type=VALUES(job_type),
      county_state=VALUES(county_state),
      shl_location=VALUES(shl_location),
      latitude=VALUES(latitude),
      longitude=VALUES(longitude),
      datum=VALUES(datum),
      ndic_file_no=VALUES(ndic_file_no),
      county=VALUES(county),
      state=VALUES(state),
      address=VALUES(address),
      lat_raw=VALUES(lat_raw),
      lon_raw=VALUES(lon_raw),
      latlon_page=VALUES(latlon_page),
      latlon_suspect=VALUES(latlon_suspect),
      fig1_pages=VALUES(fig1_pages),
      source_pdf=VALUES(source_pdf),
      relative_path=VALUES(relative_path),
      raw_text=VALUES(raw_text)
    """

    def norm_well(row: dict) -> dict:
        fig = row.get("fig1_pages")
        row["fig1_pages"] = json.dumps(fig, ensure_ascii=False) if fig is not None else None
        row["latlon_suspect"] = int(bool(row.get("latlon_suspect")))
        return row

    well_path = Path(args.well_jsonl)
    buf = []
    n_well = 0
    for _, row in iter_jsonl(well_path):
        buf.append(norm_well(row))
        if len(buf) >= args.batch_size:
            cur.executemany(well_sql, buf)
            conn.commit()
            n_well += len(buf)
            buf.clear()
    if buf:
        cur.executemany(well_sql, buf)
        conn.commit()
        n_well += len(buf)

    # ---------- stimulation_data insert/upsert ----------
    stim_sql = """
    INSERT INTO stimulation_data (
      primary_id,
      date_stimulated, stimulation_formation, top_ft, bottom_ft, stimulation_stages,
      volume, volume_units,
      treatment_type, acid_pct, lbs_proppant, max_treatment_pressure_psi, max_treatment_rate_bbl_min,
      details,
      stim_present, stim_has_fields,
      api, ndic_file_no,
      fig2_pages,
      source_pdf, relative_path,
      raw_text, raw_text_clean
    ) VALUES (
      %(primary_id)s,
      %(date_stimulated)s, %(stimulation_formation)s, %(top_ft)s, %(bottom_ft)s, %(stimulation_stages)s,
      %(volume)s, %(volume_units)s,
      %(treatment_type)s, %(acid_pct)s, %(lbs_proppant)s, %(max_treatment_pressure_psi)s, %(max_treatment_rate_bbl_min)s,
      %(details)s,
      %(stim_present)s, %(stim_has_fields)s,
      %(api)s, %(ndic_file_no)s,
      %(fig2_pages)s,
      %(source_pdf)s, %(relative_path)s,
      %(raw_text)s, %(raw_text_clean)s
    )
    ON DUPLICATE KEY UPDATE
      stimulation_formation=VALUES(stimulation_formation),
      stimulation_stages=VALUES(stimulation_stages),
      volume=VALUES(volume),
      volume_units=VALUES(volume_units),
      treatment_type=VALUES(treatment_type),
      acid_pct=VALUES(acid_pct),
      lbs_proppant=VALUES(lbs_proppant),
      max_treatment_pressure_psi=VALUES(max_treatment_pressure_psi),
      max_treatment_rate_bbl_min=VALUES(max_treatment_rate_bbl_min),
      details=VALUES(details),
      stim_present=VALUES(stim_present),
      stim_has_fields=VALUES(stim_has_fields),
      api=VALUES(api),
      ndic_file_no=VALUES(ndic_file_no),
      fig2_pages=VALUES(fig2_pages),
      source_pdf=VALUES(source_pdf),
      relative_path=VALUES(relative_path),
      raw_text=VALUES(raw_text),
      raw_text_clean=VALUES(raw_text_clean)
    """

    def norm_stim(row: dict) -> dict:
        row["date_stimulated"] = to_date(row.get("date_stimulated"))
        row["stim_present"] = int(bool(row.get("stim_present")))
        row["stim_has_fields"] = int(bool(row.get("stim_has_fields")))
        fig = row.get("fig2_pages")
        row["fig2_pages"] = json.dumps(fig, ensure_ascii=False) if fig is not None else None
        return row

    stim_path = Path(args.stim_jsonl)
    buf = []
    n_stim = 0
    for _, row in iter_jsonl(stim_path):
        buf.append(norm_stim(row))
        if len(buf) >= args.batch_size:
            cur.executemany(stim_sql, buf)
            conn.commit()
            n_stim += len(buf)
            buf.clear()
    if buf:
        cur.executemany(stim_sql, buf)
        conn.commit()
        n_stim += len(buf)

    cur.close()
    conn.close()

    print(f"Loaded well_info rows: {n_well}")
    print(f"Loaded stimulation_data rows: {n_stim}")
    print("Done.")


if __name__ == "__main__":
    main()
