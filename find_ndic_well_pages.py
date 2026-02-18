import re
import time
import requests

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
BASES = ["https://www.dmr.nd.gov", "https://dmr.nd.gov"]

CANDIDATE_PATHS = [
    "/oilgas/well_srch.asp?api={api}",
    "/oilgas/well_srch.asp?APINo={api}",
    "/oilgas/weleq.asp?api={api}",
    "/oilgas/weleq.asp?Api={api}",
    "/oilgas/weleq.asp?APINo={api}",
    "/oilgas/weleq.asp?api_no={api14}",
    "/oilgas/weleq.asp?api={api14}",

    "/oilgas/well_production.asp?api={api}",
    "/oilgas/well_production.asp?api={api14}",
    "/oilgas/wellprod.asp?api={api}",
    "/oilgas/wellprod.asp?api={api14}",

    "/oilgas/well.asp?api={api}",
    "/oilgas/well.asp?api={api14}",
    "/oilgas/wellinfo.asp?api={api}",
    "/oilgas/wellinfo.asp?api={api14}",

    "/Oil-and-Gas/Well-Information?api={api}",
    "/Oil-and-Gas/Well-Information?api={api14}",
    "/Oil-and-Gas/Well-Search?api={api}",
    "/Oil-and-Gas/Well-Search?api={api14}",
]

def norm_api(api: str) -> str:
    s = (api or "").strip().replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", "", s)
    m = re.search(r"(\d{2})\D*(\d{3})\D*(\d{5})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return s

def digits_only(s: str) -> str:
    return re.sub(r"\D+", "", s or "")

def fetch(session, url):
    r = session.get(url, headers={"User-Agent": UA}, timeout=(10, 30), allow_redirects=True)
    txt = r.text or ""
    head = txt[:4000].lower()
    return r.status_code, head, url, r.url

def main():
    apis = [
        "33-053-02148",
        "33-053-02102",
        "33-105-02720",
    ]

    s = requests.Session()
    out = []

    for api in apis:
        api = norm_api(api)
        api14 = digits_only(api)
        found = False
        for base in BASES:
            for p in CANDIDATE_PATHS:
                url = base + p.format(api=api, api14=api14)
                try:
                    code, head, orig, final = fetch(s, url)
                except Exception:
                    continue
                if code != 200:
                    continue
                if "access denied" in head or "forbidden" in head:
                    continue
                if "not found" in head and "well" not in head:
                    continue
                if api.replace("-", "") in head or api in head:
                    print("HIT:", api, "=>", final)
                    out.append(f"{api}\t{final}")
                    found = True
                    break
            if found:
                break
        if not found:
            print("MISS:", api)
        time.sleep(0.2)

    with open("ndic_url_hits.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(out) + ("\n" if out else ""))

    print("saved: ndic_url_hits.txt")

if __name__ == "__main__":
    main()
