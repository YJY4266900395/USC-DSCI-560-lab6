import os
import re
import sys
import time
import unicodedata
from typing import Optional, Tuple, List, Dict

import requests
import mysql.connector
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DB", "oil_wells"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
}
MYSQL_UNIX_SOCKET = os.getenv("MYSQL_UNIX_SOCKET", "").strip()

RE_SPACES = re.compile(r"\s+")
RE_NON_ALNUM = re.compile(r"[^a-z0-9]+")
RE_API = re.compile(r"\b\d{2}-\d{3}-\d{5}\b", re.IGNORECASE)
RE_MEMBERS_ONLY = re.compile(r"\bMembers Only\b", re.IGNORECASE)

LABEL_CANDIDATES_STATUS = ["Well Status", "Status"]
LABEL_CANDIDATES_FIELD = ["Field / Formation", "Field", "Formation", "Pool", "Play", "Basin"]

def norm_text(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = s.replace("\u00a0", " ")
    s = RE_SPACES.sub(" ", s).strip()
    return s

def slugify(s: str) -> str:
    s = norm_text(s).lower()
    s = s.replace("&", " and ").replace("/", " ")
    s = s.replace("’", "").replace("'", "").replace('"', "")
    s = RE_NON_ALNUM.sub("-", s)
    s = s.strip("-")
    s = re.sub(r"-{2,}", "-", s)
    return s

def norm_county(county: str) -> str:
    c = norm_text(county).lower()
    c = c.replace("county", " ")
    c = c.replace("state", " ")
    c = re.sub(r"\b(in|of|the|and)\b", " ", c)
    c = re.sub(r"[^a-z ]+", " ", c)
    c = RE_SPACES.sub(" ", c).strip()
    c = c.replace(" ", "-").strip("-")
    c = re.sub(r"-{2,}", "-", c)
    return c

def looks_bad_url(url: str) -> bool:
    u = url.lower()
    if "drillingedge.com" not in u:
        return True
    if "/north-dakota/" not in u or "/wells/" not in u:
        return True
    if "/north-dakota/state-" in u:
        return True
    if "/north-dakota/in-" in u:
        return True
    return False

def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    })
    try:
        s.get("https://www.drillingedge.com/", timeout=(6, 14))
    except Exception:
        pass
    return s

def fetch_html(session: requests.Session, url: str, timeout=(10, 26), tries: int = 3) -> Optional[str]:
    for i in range(tries):
        try:
            r = session.get(
                url,
                timeout=timeout,
                allow_redirects=True,
                headers={"Referer": "https://www.drillingedge.com/"},
            )
            if r.status_code == 200 and r.text:
                return r.text
            if r.status_code in (403, 429, 500, 502, 503, 504):
                time.sleep(1.0 * (i + 1))
                continue
        except Exception:
            time.sleep(1.0 * (i + 1))
            continue
    return None

def extract_kv_from_details_table(soup: BeautifulSoup) -> Dict[str, str]:
    kv: Dict[str, str] = {}
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            tds = tr.find_all(["td", "th"])
            if len(tds) >= 2:
                k = norm_text(tds[0].get_text(" ", strip=True))
                v = norm_text(tds[1].get_text(" ", strip=True))
                if k and v:
                    kv[k] = v
    return kv

def pick_value_by_labels(kv: Dict[str, str], labels: List[str]) -> Optional[str]:
    low = {k.lower(): v for k, v in kv.items()}
    for lab in labels:
        if lab.lower() in low:
            v = norm_text(low[lab.lower()])
            if not v:
                return None
            if RE_MEMBERS_ONLY.search(v):
                return None
            if v.lower() in ("n/a", "na", "null"):
                return None
            return v
    for k, v in kv.items():
        for lab in labels:
            if lab.lower() in k.lower():
                vv = norm_text(v)
                if not vv or RE_MEMBERS_ONLY.search(vv) or vv.lower() in ("n/a", "na", "null"):
                    return None
                return vv
    return None

def parse_well_page(html: str) -> Tuple[Optional[str], Optional[str]]:
    soup = BeautifulSoup(html, "html.parser")
    kv = extract_kv_from_details_table(soup)
    status = pick_value_by_labels(kv, LABEL_CANDIDATES_STATUS)
    field = pick_value_by_labels(kv, LABEL_CANDIDATES_FIELD)
    if field and field.lower() in ("well status", "status"):
        field = None
    return status, field

def find_wells_links_with_api(html: str, api: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/wells/" in href and api in href:
            if href.startswith("http"):
                out.append(href)
            else:
                out.append("https://www.drillingedge.com" + href)
    out = list(dict.fromkeys(out))
    out.sort(key=len)
    return out

def search_fallback_url(session: requests.Session, api: str) -> Optional[str]:
    q = api.strip()
    search_urls = [
        f"https://www.drillingedge.com/search?search={q}",
        f"https://www.drillingedge.com/search?query={q}",
        f"https://www.drillingedge.com/search?q={q}",
    ]
    for su in search_urls:
        html = fetch_html(session, su)
        if not html:
            continue
        links = find_wells_links_with_api(html, api)
        if links:
            return links[0]
    return None

def candidate_urls(api: str, county: str, well_name: str) -> List[str]:
    c = norm_county(county)
    name_slug = slugify(well_name)
    cands: List[str] = []
    if c and name_slug:
        cands.append(f"https://www.drillingedge.com/north-dakota/{c}-county/wells/{name_slug}/{api}")
    if c:
        cands.append(f"https://www.drillingedge.com/north-dakota/{c}-county/wells/{api}")
    if name_slug:
        loose = re.sub(r"-\d+[a-z]?$", "", name_slug)
        if loose and loose != name_slug and c:
            cands.append(f"https://www.drillingedge.com/north-dakota/{c}-county/wells/{loose}/{api}")
    return list(dict.fromkeys(cands))

def connect_db():
    cfg = dict(DB_CONFIG)
    if MYSQL_UNIX_SOCKET:
        cfg.pop("host", None)
        cfg.pop("port", None)
        cfg["unix_socket"] = MYSQL_UNIX_SOCKET
    return mysql.connector.connect(**cfg)

def db_summary(cur):
    cur.execute("SELECT COUNT(*) FROM wells")
    total = int(cur.fetchone()[0])
    cur.execute("SELECT COUNT(*) FROM wells WHERE status IS NULL")
    status_null = int(cur.fetchone()[0])
    cur.execute("SELECT COUNT(*) FROM wells WHERE field_name IS NULL")
    field_null = int(cur.fetchone()[0])
    cur.execute("SELECT COUNT(*) FROM wells WHERE drillingedge_url IS NULL")
    url_null = int(cur.fetchone()[0])
    cur.execute("SELECT status, COUNT(*) FROM wells GROUP BY status ORDER BY COUNT(*) DESC")
    dist = cur.fetchall()
    cur.execute("SELECT api_number FROM wells WHERE field_name IS NULL ORDER BY api_number")
    still_field_null = [r[0] for r in cur.fetchall()]
    return total, status_null, field_null, url_null, dist, still_field_null

def main():
    inp = sys.argv[1] if len(sys.argv) > 1 else None

    conn = connect_db()
    cur = conn.cursor()

    cur.execute("SELECT id, api_number, county, well_name, status, field_name, drillingedge_url FROM wells")
    all_rows = cur.fetchall()

    row_map = {r[1]: r for r in all_rows}

    targets = []
    if inp:
        with open(inp, "r", encoding="utf-8") as f:
            for line in f:
                m = RE_API.search(line)
                if m:
                    api = m.group(0)
                    if api in row_map:
                        targets.append(api)
    else:
        for r in all_rows:
            _, api, _, _, status, field, _ = r
            if status is None or field is None:
                targets.append(api)

    targets = list(dict.fromkeys(targets))
    rows_to_process = [row_map[a] for a in targets]

    print(f"Rows to process: {len(rows_to_process)}")

    session = make_session()

    updated = 0
    failed = 0
    skipped = 0

    for (wid, api, county, well_name, status0, field0, url0) in rows_to_process:
        ok = False
        used_url = None
        new_status = status0
        new_field = field0
        last_try = None

        url_candidates: List[str] = []
        if url0 and (not looks_bad_url(url0)):
            url_candidates.append(url0)
        url_candidates.extend(candidate_urls(api, county or "", well_name or ""))

        for url in list(dict.fromkeys(url_candidates)):
            last_try = url
            html = fetch_html(session, url)
            if not html:
                continue
            st, fd = parse_well_page(html)
            if st:
                new_status = st
            if fd:
                new_field = fd
            used_url = url
            ok = True
            break

        if not ok:
            fb = search_fallback_url(session, api)
            if fb:
                last_try = fb
                html = fetch_html(session, fb)
                if html:
                    st, fd = parse_well_page(html)
                    if st:
                        new_status = st
                    if fd:
                        new_field = fd
                    used_url = fb
                    ok = True

        if not ok:
            failed += 1
            if last_try:
                print(f"{api} FAIL {last_try}")
            else:
                print(f"{api} FAIL")
            continue

        if used_url is None:
            used_url = url0

        cur.execute(
            "UPDATE wells SET status=%s, field_name=%s, drillingedge_url=%s WHERE id=%s",
            (new_status, new_field, used_url, wid),
        )
        conn.commit()
        updated += 1
        print(f"{api} UPDATED status={new_status if new_status else 'NULL'} field={new_field if new_field else 'NULL'}")

    print(f"\nDONE updated={updated} failed={failed} skipped={skipped}\n")

    total, status_null, field_null, url_null, dist, still_field_null = db_summary(cur)

    print("DB SUMMARY:")
    print(f"- total rows: {total}")
    print(f"- status IS NULL: {status_null}")
    print(f"- field_name IS NULL: {field_null}")
    print(f"- drillingedge_url IS NULL: {url_null}\n")

    print("STATUS DISTRIBUTION:")
    for st, cnt in dist:
        print(f"- {st if st else 'NULL'}: {cnt}")

    if still_field_null:
        print("\nFIELD_NAME STILL NULL (likely missing on page / gated):")
        for a in still_field_null:
            print(f"- {a}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()