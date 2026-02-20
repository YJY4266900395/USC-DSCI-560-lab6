# Oil Wells Map - Flask Backend
# APIs:
# GET / - serves the main map page (index.html)
# GET /api/wells - JSON array of all wells, stimulation, production data

from flask import Flask, jsonify, send_from_directory
import mysql.connector
import os

# all files in web folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    static_folder=BASE_DIR,
    static_url_path="/static",
)

# MySQL connection config 
DB_CONFIG = {
    "host": "localhost",
    "user": "labuser",
    "password": "labpass",
    "database": "dsci560_lab6",
    "port": 3306,
}


def get_db():
    # Return a fresh MySQL connection
    return mysql.connector.connect(**DB_CONFIG)


######################## Routes ########################

@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/api/wells")
def api_wells():
    # Return every well joined with its stimulation and production data.
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    # New schema: well_info + stimulation_data (no production_data table)
    cur.execute("""
        SELECT
            w.well_id,
            w.api,
            w.ndic_file_no,
            w.well_name,
            w.operator,
            w.county,
            w.state,
            w.shl_location,
            w.latitude,
            w.longitude,
            w.latitude_raw,
            w.longitude_raw,
            w.datum,

            s.stim_date,
            s.stimulated_formation,
            s.top_ft,
            s.bottom_ft,
            s.stimulation_stages,
            s.volume,
            s.volume_units,
            s.type_treatment,
            s.acid_pct,
            s.lbs_proppant,
            s.max_treat_pressure_psi,
            s.max_treat_rate,
            s.max_treat_rate_units,
            s.details
        FROM well_info w
        LEFT JOIN stimulation_data s ON s.well_id = w.well_id
        ORDER BY w.well_id
    """)
    # Use LEFT JOIN so wells without stimulation/production records still appear

    rows = cur.fetchall()
    cur.close()
    conn.close()

    # Ensure JSON-safe types
    for r in rows:
        for k, v in r.items():
            if v is None:
                continue
            if not isinstance(v, (int, float, str, bool)):
                r[k] = str(v)

    return jsonify(rows)


######################## Entry point ########################
if __name__ == "__main__":
    # Bind to 127.0.0.1 only, Apache will proxy public traffic here
    app.run(host="127.0.0.1", port=5000, debug=False)