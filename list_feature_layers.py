import requests

REST_ROOT = "https://gis.dmr.nd.gov/dmrpublicservices/rest/services"

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

def main():
    services = list_services()
    fs_urls = []
    for s in services:
        name = s.get("name")
        typ = s.get("type")
        if not name or typ not in ["MapServer", "FeatureServer"]:
            continue
        if typ == "FeatureServer":
            fs_urls.append((name, f"{REST_ROOT}/{name}/FeatureServer"))
        else:
            fs_urls.append((name, f"{REST_ROOT}/{name}/FeatureServer"))
    print(f"Total services scanned: {len(services)}")
    print(f"FeatureServer candidates: {len(fs_urls)}")

    keywords = ["prod", "production", "monthly", "oil", "gas", "stimul", "frac", "treat"]
    for name, fs in fs_urls:
        low = name.lower()
        if not any(k in low for k in keywords):
            continue
        try:
            meta = jget(fs, {"f": "pjson"})
        except Exception:
            continue
        layers = meta.get("layers", [])
        if not layers:
            continue
        print("=" * 80)
        print("SERVICE:", name)
        for lyr in layers[:10]:
            lid = lyr.get("id")
            lname = lyr.get("name")
            if lid is None:
                continue
            try:
                ldef = jget(f"{fs}/{lid}", {"f": "pjson"})
            except Exception:
                continue
            fields = [f.get("name") for f in (ldef.get("fields") or []) if f.get("name")]
            f_low = " | ".join([x.lower() for x in fields[:40]])
            hit = any(k in f_low for k in keywords)
            print(f"  layer {lid}: {lname}  fields={len(fields)}  keyword_hit={hit}")
            if hit:
                print("    sample_fields:", ", ".join(fields[:25]))

if __name__ == "__main__":
    main()
