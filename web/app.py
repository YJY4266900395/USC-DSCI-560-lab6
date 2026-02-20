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
    "user": "root",
    "password": "",
    "database": "oil_wells",
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

    cur.execute("""
        SELECT
            w.id,
            w.api_number,
            w.well_name,
            w.operator,
            w.latitude,
            w.longitude,
            w.address,
            w.county,
            w.state,
            w.well_file_no,
            w.plss_quarter,
            w.section_no,
            w.township_code,
            w.range_code,
            w.state_code,
            w.status AS well_status_code,

            s.treatment_type,
            s.total_proppant,
            s.fluid_volume,
            s.max_pressure,

            p.well_status,
            p.well_type,
            p.closest_city,
            p.oil_barrels,
            p.gas_mcf
        FROM wells w
        LEFT JOIN stimulation_data s ON s.well_id = w.id
        LEFT JOIN production_data  p ON p.well_id = w.id
        ORDER BY w.id
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