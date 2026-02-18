import os
import re
import time
import json
import mysql.connector
import requests

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DB", "oil_wells"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
}

REST_ROOT = os.getenv("GIS_REST_ROOT", "https://gis.dmr.nd.gov/dmrpublicservices/rest/services")
TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "30"))
SLEEP = float(os.getenv("HTTP_SLEEP", "0"))
BATCH_COMMIT = int(os.getenv("BATCH_COMMIT", "10"))

def get_conn():
    return mysql.connector.connect(**DB_CONFIG)

def http_get(url, params=None):
    r = requests.get(url, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def list_services():
    root = http_get(f"{REST_ROOT}", {"f": "pjson"})
    folders = root.get("folders", [])
    services = root.get("services", [])
    for folder in folders:
        data = http_get(f"{REST_ROOT}/{folder}", {"f": "pjson"})
        for s in data.get("services", []):
            services.append(s)
    return services

def service_to_featureserver_url(svc):
    name = svc.get("name")
    typ = svc.get("type")
    if not name or typ != "MapServer":
        return None
    return f"{REST_ROOT}/{name}/FeatureServer"

def list_layers(feature_url):
    data = http_get(feature_url, {"f": "pjson"})
    return data.get("layers", []), data

def score_layer(layer):
    fields = [f.get("name", "").lower() for f in layer.get("fields", [])]
    fieldset = set(fields)
    prod_keys = [
        "oil", "oil_bbl", "oil_barrels", "oil_bbls", "gas", "gas_mcf",
        "well_status", "status", "well_type", "type", "closest_city", "city"
    ]
    stim_keys = [
        "treatment", "treatment_type", "frac", "stimulation",
        "proppant", "total_proppant", "fluid", "fluid_volume",
        "pressure", "max_pressure"
    ]
    api_keys = ["api_no", "api", "api_number", "api14", "api_14"]

    prod = sum(any(k in f for f in fields) for k in prod_keys)
    stim = sum(any(k in f for f in fields) for k in stim_keys)
    api = [k for k in api_keys if k in fieldset]
    return prod, stim, api

def pick_best_layers():
    services = list_services()
    candidates = []
    for svc in services:
        furl = service_to_featureserver_url(svc)
        if not furl:
            continue
        try:
            layers, meta = list_layers(furl)
        except Exception:
            continue
        for lyr in layers:
            layer_id = lyr.get("id")
            if layer_id is None:
                continue
            layer_url = f"{furl}/{layer_id}"
            try:
                layer_def = http_get(layer_url, {"f": "pjson"})
            except Exception:
                continue
            prod_score, stim_score, api_fields = score_layer(layer_def)
            if not api_fields:
                continue
            candidates.append({
                "service": svc.get("name"),
                "layer_id": layer_id,
                "layer_url": layer_url,
                "prod_score": prod_score,
                "stim_score": stim_score,
                "api_fields": api_fields,
                "fields": [f.get("name") for f in layer_def.get("fields", [])],
            })

    candidates.sort(key=lambda x: (max(x["prod_score"], x["stim_score"]), x["prod_score"], x["stim_score"]), reverse=True)

    prod_layer = None
    stim_layer = None

    for c in candidates:
        if prod_layer is None and c["prod_score"] >= 3:
            prod_layer = c
        if stim_layer is None and c["stim_score"] >= 3:
            stim_layer = c
        if prod_layer and stim_layer:
            break

    return prod_layer, stim_layer, candidates[:12]

def norm_api(api):
    s = str(api).strip()
    s = re.sub(r"\s+", "", s)
    s = s.replace("–", "-").replace("—", "-")
    if re.fullmatch(r"\d{14}", s):
        return f"{s[0:2]}-{s[2:5]}-{s[5:10]}"
    if re.fullmatch(r"\d{2}-\d{3}-\d{5}", s):
        return s
    m = re.search(r"(\d{2})\D*(\d{3})\D*(\d{5})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return s

def gis_query_one(layer_url, api_field, api_number):
    where = f"{api_field}='{api_number}'"
    params = {
        "f": "json",
        "where": where,
        "outFields": "*",
        "returnGeometry": "false"
    }
    data = http_get(f"{layer_url}/query", params)
    feats = data.get("features", [])
    if not feats:
        where2 = f"{api_field}='{api_number.replace('-', '')}'"
        params["where"] = where2
        data = http_get(f"{layer_url}/query", params)
        feats = data.get("features", [])
    if not feats:
        return None
    return feats[0].get("attributes", {})

def upsert_production(cur, well_id, attrs):
    if attrs is None:
        return False
    keys = {k.lower(): k for k in attrs.keys()}

    def pick(*names):
        for n in names:
            k = keys.get(n.lower())
            if k is not None:
                v = attrs.get(k)
                if v is not None and v != "":
                    return v
        return None

    well_status = pick("well_status", "status", "WELL_STATUS", "STATUS")
    well_type = pick("well_type", "type", "WELL_TYPE", "TYPE")
    closest_city = pick("closest_city", "city", "CLOSEST_CITY", "CITY")
    oil = pick("oil_barrels", "oil_bbl", "oil", "OIL", "OIL_BBL", "OIL_BARRELS")
    gas = pick("gas_mcf", "gas", "GAS", "GAS_MCF")

    cur.execute(
        "INSERT INTO production_data (well_id, well_status, well_type, closest_city, oil_barrels, gas_mcf) "
        "VALUES (%s,%s,%s,%s,%s,%s) "
        "ON DUPLICATE KEY UPDATE well_status=VALUES(well_status), well_type=VALUES(well_type), "
        "closest_city=VALUES(closest_city), oil_barrels=VALUES(oil_barrels), gas_mcf=VALUES(gas_mcf)",
        (well_id, well_status, well_type, closest_city, oil, gas)
    )
    return True

def upsert_stimulation(cur, well_id, attrs):
    if attrs is None:
        return False
    keys = {k.lower(): k for k in attrs.keys()}

    def pick(*names):
        for n in names:
            k = keys.get(n.lower())
            if k is not None:
                v = attrs.get(k)
                if v is not None and v != "":
                    return v
        return None

    treatment_type = pick("treatment_type", "treatment", "frac_type", "TREATMENT_TYPE", "TREATMENT")
    total_proppant = pick("total_proppant", "proppant", "PROPPANT", "TOTAL_PROPPANT")
    fluid_volume = pick("fluid_volume", "fluid", "FLUID", "FLUID_VOLUME")
    max_pressure = pick("max_pressure", "pressure", "PRESSURE", "MAX_PRESSURE")

    cur.execute(
        "INSERT INTO stimulation_data (well_id, treatment_type, total_proppant, fluid_volume, max_pressure) "
        "VALUES (%s,%s,%s,%s,%s) "
        "ON DUPLICATE KEY UPDATE treatment_type=VALUES(treatment_type), total_proppant=VALUES(total_proppant), "
        "fluid_volume=VALUES(fluid_volume), max_pressure=VALUES(max_pressure)",
        (well_id, treatment_type, total_proppant, fluid_volume, max_pressure)
    )
    return True

def ensure_unique_well_id(cur, table):
    cur.execute(f"SHOW INDEX FROM {table} WHERE Key_name='uq_{table}_well'")
    if cur.fetchone() is None:
        cur.execute(f"ALTER TABLE {table} ADD UNIQUE KEY uq_{table}_well (well_id)")

def main():
    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT id, api_number FROM wells WHERE api_number IS NOT NULL AND api_number<>'' ORDER BY id")
    wells = cur.fetchall()
    print(f"Total wells in DB: {len(wells)}")

    ensure_unique_well_id(cur, "production_data")
    ensure_unique_well_id(cur, "stimulation_data")
    conn.commit()

    prod_layer, stim_layer, preview = pick_best_layers()
    print("Detected layers (top 8):")
    for i, c in enumerate(preview[:8]):
        print(f"  layer {i}: prod_score={c['prod_score']}, stim_score={c['stim_score']}, api_field={c['api_fields'][0]} service={c['service']} id={c['layer_id']}")

    prod_url = prod_layer["layer_url"] if prod_layer else None
    prod_api_field = prod_layer["api_fields"][0] if prod_layer else None
    stim_url = stim_layer["layer_url"] if stim_layer else None
    stim_api_field = stim_layer["api_fields"][0] if stim_layer else None

    print("Using production layer:", prod_url, "api_field:", prod_api_field)
    print("Using stimulation layer:", stim_url, "api_field:", stim_api_field)

    prod_written = 0
    stim_written = 0
    missed_prod = 0
    missed_stim = 0

    for i, w in enumerate(wells, start=1):
        api = norm_api(w["api_number"])
        wid = w["id"]
        print(f"[{i}/{len(wells)}] {api}")

        if prod_url and prod_api_field:
            try:
                attrs = gis_query_one(prod_url, prod_api_field, api)
                if attrs is None:
                    missed_prod += 1
                else:
                    if upsert_production(cur, wid, attrs):
                        prod_written += 1
            except Exception:
                missed_prod += 1

        if stim_url and stim_api_field:
            try:
                attrs = gis_query_one(stim_url, stim_api_field, api)
                if attrs is None:
                    missed_stim += 1
                else:
                    if upsert_stimulation(cur, wid, attrs):
                        stim_written += 1
            except Exception:
                missed_stim += 1

        if i % BATCH_COMMIT == 0:
            conn.commit()
            print("  commit")

        if SLEEP > 0:
            time.sleep(SLEEP)

    conn.commit()
    cur.close()
    conn.close()

    print(f"DONE. prod_written={prod_written}, stim_written={stim_written}, missed_prod={missed_prod}, missed_stim={missed_stim}, total={len(wells)}")

if __name__ == "__main__":
    main()
