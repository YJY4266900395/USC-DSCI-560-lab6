import requests
import re

REST_ROOT = "https://gis.dmr.nd.gov/dmrpublicservices/rest/services"

KEYWORDS = [
    "oil", "gas", "mcf", "bbl", "prod", "product", "production", "monthly", "month",
    "stimul", "stimulation", "frac", "fract", "treat", "treatment",
    "propp", "proppant", "fluid", "pressure", "psi", "stage"
]

def jget(url, params=None):
    r = requests.get(url, params=params or {}, timeout=30)
    r.raise_for_status()
    return r.json()

def list_services():
    root = jget(REST_ROOT, {"f": "pjson"})
    services = list(root.get("services", []))
    for folder in root.get("folders", []):
        data = jget(f"{REST_ROOT}/{folder}", {"f": "pjson"})
        services.extend(data.get("services", []))
    return services

def normalize_fs_url(name, typ):
    if not name:
        return None
    if typ == "FeatureServer":
        return f"{REST_ROOT}/{name}/FeatureServer"
    if typ == "MapServer":
        return f"{REST_ROOT}/{name}/FeatureServer"
    return None

def hit(fields):
    low = " ".join([f.lower() for f in fields])
    return [k for k in KEYWORDS if k in low]

def main():
    services = list_services()
    fs_urls = []
    for s in services:
        url = normalize_fs_url(s.get("name"), s.get("type"))
        if url:
            fs_urls.append((s.get("name"), url))

    print(f"Total services scanned: {len(services)}")
    print(f"FeatureServer candidates: {len(fs_urls)}")

    seen = set()
    found = 0

    for name, fs in fs_urls:
        if fs in seen:
            continue
        seen.add(fs)

        try:
            meta = jget(fs, {"f": "pjson"})
        except Exception:
            continue

        layers = meta.get("layers", [])
        if not layers:
            continue

        for lyr in layers:
            lid = lyr.get("id")
            lname = lyr.get("name")
            if lid is None:
                continue

            layer_url = f"{fs}/{lid}"
            try:
                ldef = jget(layer_url, {"f": "pjson"})
            except Exception:
                continue

            fields = [f.get("name") for f in (ldef.get("fields") or []) if f.get("name")]
            if not fields:
                continue

            hits = hit(fields)
            if hits:
                found += 1
                print("=" * 90)
                print("SERVICE:", name)
                print("LAYER:", lid, lname)
                print("LAYER_URL:", layer_url)
                print("HITS:", hits[:12])
                print("SAMPLE_FIELDS:", ", ".join(fields[:35]))

    print(f"\nDONE. matched_layers={found}")

if __name__ == "__main__":
    main()
