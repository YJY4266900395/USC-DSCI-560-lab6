"""
Oil Wells Map - Flask Backend
Runs behind Apache reverse proxy on 127.0.0.1:5000.

Routes:
  GET /            → serves index.html
  GET /static/<f>  → serves style.css / app.js
  GET /api/wells   → JSON: all well + stimulation + production data
"""

import os
from flask import Flask, jsonify, send_from_directory
import mysql.connector

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=BASE_DIR, static_url_path="/static")

#  MySQL config 
DB_CONFIG = {
    "host": "localhost",
    "user": "labuser",
    "password": "labpass",
    "database": "lab6",
    "port": 3306,
}


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/api/wells")
def api_wells():
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT
            /*  well_info (base)  */
            w.api,
            w.enesco_job,
            w.job_type,
            w.shl_location,
            w.latitude,
            w.longitude,
            w.datum,
            w.ndic_file_no,
            w.county,
            w.state,
            w.address,

            /*  overlapping fields: prefer production (scraped) over well_info (OCR)  */
            COALESCE(p.well_name,    w.well_name)    AS well_name,
            COALESCE(p.operator,     w.operator)     AS operator,
            COALESCE(p.county_state, w.county_state) AS county_state,

            /*  stimulation_data  */
            s.date_stimulated,
            s.stimulation_formation,
            s.top_ft,
            s.bottom_ft,
            s.stimulation_stages,
            s.volume,
            s.volume_units,
            s.treatment_type,
            s.acid_pct,
            s.lbs_proppant,
            s.max_treatment_pressure_psi,
            s.max_treatment_rate_bbl_min,
            s.details,

            /*  production_data (web-scraped)  */
            p.well_status,
            p.well_type,
            p.closest_city,
            p.oil_barrels,
            p.gas_mcf,
            p.first_production_date,
            p.most_recent_production_date,
            p.drillingedge_url

        FROM well_info w
        LEFT JOIN stimulation_data  s ON s.api = w.api
        LEFT JOIN production_data   p ON p.api = w.api
        ORDER BY w.api
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    for r in rows:
        for k, v in r.items():
            if v is not None and not isinstance(v, (int, float, str, bool)):
                r[k] = str(v)

    return jsonify(rows)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)