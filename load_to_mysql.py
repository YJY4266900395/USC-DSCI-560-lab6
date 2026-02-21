"""
Loads well_info.jsonl, stimulation_data.jsonl, and production_data.jsonl
into the lab6 database.
Usage:
    python3 load_to_mysql.py \
        --user labuser --password labpass --database lab6 \
        --well_jsonl output/parsed/well_info.jsonl \
        --stim_jsonl output/parsed/stimulation_data.jsonl \
        --prod_jsonl output/parsed/production_data.jsonl \
        --truncate
"""

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
    return s if s else None


def main():
    ap = argparse.ArgumentParser(description="Load Lab6 JSONL outputs into MySQL.")
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=3306)
    ap.add_argument("--user", required=True)
    ap.add_argument("--password", required=True)
    ap.add_argument("--database", default="lab6")
    ap.add_argument("--well_jsonl", required=True)
    ap.add_argument("--stim_jsonl", required=True)
    ap.add_argument("--prod_jsonl", default="", help="Path to production_data.jsonl (optional)")
    ap.add_argument("--batch_size", type=int, default=500)
    ap.add_argument("--truncate", action="store_true")
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
        cur.execute("SET FOREIGN_KEY_CHECKS=0")
        cur.execute("TRUNCATE TABLE IF EXISTS production_data")
        cur.execute("TRUNCATE TABLE stimulation_data")
        cur.execute("TRUNCATE TABLE well_info")
        cur.execute("SET FOREIGN_KEY_CHECKS=1")
        conn.commit()

    # ==========================
    # well_info (api as PK)
    # ==========================
    well_sql = """
    INSERT INTO well_info (
      operator, well_name, api, enesco_job, job_type, county_state, shl_location,
      latitude, longitude, datum,
      ndic_file_no, county, state, address,
      lat_raw, lon_raw, latlon_page, latlon_suspect, fig1_pages, raw_text
    ) VALUES (
      %(operator)s, %(well_name)s, %(api)s, %(enesco_job)s, %(job_type)s, %(county_state)s, %(shl_location)s,
      %(latitude)s, %(longitude)s, %(datum)s,
      %(ndic_file_no)s, %(county)s, %(state)s, %(address)s,
      %(lat_raw)s, %(lon_raw)s, %(latlon_page)s, %(latlon_suspect)s, %(fig1_pages)s, %(raw_text)s
    )
    ON DUPLICATE KEY UPDATE
      operator=VALUES(operator),
      well_name=VALUES(well_name),
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
      raw_text=VALUES(raw_text)
    """

    def norm_well(row: dict):
        row["latlon_suspect"] = int(bool(row.get("latlon_suspect")))
        fig = row.get("fig1_pages")
        row["fig1_pages"] = json.dumps(fig) if fig else None
        return row

    n_well = 0
    buf = []
    for _, row in iter_jsonl(Path(args.well_jsonl)):
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

    print(f"Loaded well_info rows: {n_well}")

    # ==========================
    # stimulation_data (api FK)
    # ==========================
    stim_sql = """
    INSERT INTO stimulation_data (
      date_stimulated, stimulation_formation, top_ft, bottom_ft, stimulation_stages,
      volume, volume_units,
      treatment_type, acid_pct, lbs_proppant,
      max_treatment_pressure_psi, max_treatment_rate_bbl_min,
      details,
      api,
      stim_present, stim_has_fields,
      ndic_file_no, fig2_pages,
      raw_text, raw_text_clean
    ) VALUES (
      %(date_stimulated)s, %(stimulation_formation)s, %(top_ft)s, %(bottom_ft)s, %(stimulation_stages)s,
      %(volume)s, %(volume_units)s,
      %(treatment_type)s, %(acid_pct)s, %(lbs_proppant)s,
      %(max_treatment_pressure_psi)s, %(max_treatment_rate_bbl_min)s,
      %(details)s,
      %(api)s,
      %(stim_present)s, %(stim_has_fields)s,
      %(ndic_file_no)s, %(fig2_pages)s,
      %(raw_text)s, %(raw_text_clean)s
    )
    ON DUPLICATE KEY UPDATE
      stimulation_formation=VALUES(stimulation_formation),
      top_ft=VALUES(top_ft),
      bottom_ft=VALUES(bottom_ft),
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
      ndic_file_no=VALUES(ndic_file_no),
      fig2_pages=VALUES(fig2_pages),
      raw_text=VALUES(raw_text),
      raw_text_clean=VALUES(raw_text_clean)
    """

    def norm_stim(row: dict):
        row["date_stimulated"] = to_date(row.get("date_stimulated"))
        row["stim_present"] = int(bool(row.get("stim_present")))
        row["stim_has_fields"] = int(bool(row.get("stim_has_fields")))
        fig = row.get("fig2_pages")
        row["fig2_pages"] = json.dumps(fig) if fig else None
        return row

    n_stim = 0
    buf = []
    for _, row in iter_jsonl(Path(args.stim_jsonl)):
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

    print(f"Loaded stimulation_data rows: {n_stim}")

    # ==========================
    # production_data (api FK, web-scraped)
    # ==========================
    prod_jsonl = Path(args.prod_jsonl) if args.prod_jsonl else None
    n_prod = 0

    if prod_jsonl and prod_jsonl.exists():
        prod_sql = """
        INSERT INTO production_data (
            api, well_name, well_status, well_type, closest_city,
            operator, county_state, first_production_date, most_recent_production_date,
            oil_barrels, gas_mcf,
            drillingedge_url, scrape_success
        ) VALUES (
          %(api)s, %(well_name)s, %(well_status)s, %(well_type)s, %(closest_city)s,
                    %(operator)s, %(county_state)s, %(first_production_date)s, %(most_recent_production_date)s,
                    %(oil_barrels)s, %(gas_mcf)s,
                    %(drillingedge_url)s, %(scrape_success)s
        )
        ON DUPLICATE KEY UPDATE
            well_name=VALUES(well_name),
            well_status=VALUES(well_status),
            well_type=VALUES(well_type),
            closest_city=VALUES(closest_city),
            operator=VALUES(operator),
            county_state=VALUES(county_state),
            first_production_date=VALUES(first_production_date),
            most_recent_production_date=VALUES(most_recent_production_date),
            oil_barrels=VALUES(oil_barrels),
            gas_mcf=VALUES(gas_mcf),
            drillingedge_url=VALUES(drillingedge_url),
            scrape_success=VALUES(scrape_success)
        """

        def norm_prod(row: dict):
            # Ensure all expected keys exist to avoid KeyError during executemany
            expected_keys = [
                "api", "well_name", "well_status", "well_type", "closest_city",
                "field_name", "operator", "county_state", "first_production_date", "most_recent_production_date",
                "oil_barrels", "gas_mcf", "drillingedge_url", "scrape_success"
            ]
            for k in expected_keys:
                if k not in row:
                    row[k] = None

            row["scrape_success"] = int(bool(row.get("scrape_success")))
            # Ensure numeric types
            try:
                if row.get("oil_barrels") is not None:
                    row["oil_barrels"] = float(row["oil_barrels"])
            except (ValueError, TypeError):
                row["oil_barrels"] = None
            try:
                if row.get("gas_mcf") is not None:
                    row["gas_mcf"] = float(row["gas_mcf"])
            except (ValueError, TypeError):
                row["gas_mcf"] = None

            # Preserve production date strings (or None)
            row["first_production_date"] = to_date(row.get("first_production_date"))
            row["most_recent_production_date"] = to_date(row.get("most_recent_production_date"))

            # operator and county_state should be strings (preprocessed), but ensure None if missing
            row["operator"] = row.get("operator")
            row["county_state"] = row.get("county_state")

            return row

        buf = []
        for _, row in iter_jsonl(prod_jsonl):
            # Only load rows whose api exists in well_info
            if not row.get("api"):
                continue
            buf.append(norm_prod(row))
            if len(buf) >= args.batch_size:
                cur.executemany(prod_sql, buf)
                conn.commit()
                n_prod += len(buf)
                buf.clear()

        if buf:
            cur.executemany(prod_sql, buf)
            conn.commit()
            n_prod += len(buf)

        print(f"Loaded production_data rows: {n_prod}")
    else:
        if args.prod_jsonl:
            print(f"WARNING: production_data file not found: {args.prod_jsonl} — skipping.")
        else:
            print("No --prod_jsonl specified — skipping production_data.")

    cur.close()
    conn.close()

    print(f"\nDone. Total: well_info={n_well}, stimulation={n_stim}, production={n_prod}")


if __name__ == "__main__":
    main()
