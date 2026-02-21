import argparse, json, re
from pathlib import Path
from datetime import datetime, timezone

# ===================== IO =====================
def rjson(p): return json.loads(Path(p).read_text(encoding="utf-8"))

def wjson(obj, p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def append_jsonl(rows, p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def iters(dirp: Path, suffix: str):
    return sorted([p for p in dirp.rglob(f"*{suffix}") if p.is_file()])

def norm_space(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").replace("\u00a0", " ")).strip()

def trunc(t: str, n: int) -> str:
    t = "" if t is None else t
    return t if n <= 0 or len(t) <= n else (t[:n] + "\n...[TRUNCATED]...")

# ===================== helpers =====================
def rx_list(lst): return [re.compile(x, re.I) for x in lst]
def rx_groups(groups): return [[re.compile(x, re.I) for x in g] for g in groups]
def anyhit(rxs, text): return any(r.search(text or "") for r in rxs)

def clean_line(v):
    if v is None: return None
    v = re.sub(r"\s{2,}", " ", v.strip())
    return v or None

def first(rex, text):
    m = rex.search(text or "")
    return clean_line(m.group(1)) if m else None

def _to_int(s):
    if not s: return None
    try: return int(re.sub(r"[^\d]", "", str(s)))
    except: return None

def _to_flt(s):
    if not s: return None
    try: return float(re.sub(r"[^0-9.]", "", str(s)))
    except: return None

# ===================== OCR cleanup =====================
CID_RE  = re.compile(r"\(cid:\d+\)")

# 修复点：不要清掉 \t \n \r（否则 label-based 提取全失效）
CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")

def ocr_cleanup(t: str) -> str:
    t = (t or "").replace("\u00a0", " ")
    t = CID_RE.sub(" ", t)
    t = CTRL_RE.sub(" ", t)
    t = t.replace("’","'").replace("‘","'").replace("”",'"').replace("“",'"').replace("″", '"').replace("′", "'")
    t = t.replace("__", " ")
    t = re.sub(r"[_]{1,}", " ", t)
    return re.sub(r"[ \f\v]{2,}", " ", t)  # 不合并换行，只合并空格类

# ===================== robust label extraction =====================
BAD_VALUE_RX = re.compile(
    r"(24-?HOUR|PRODUCTION\s+RATE|Telephone\s+Number|City\s+State\s+Zip|"
    r"Qtr-?Qtr|Section|Township|Range|County|Spacing\s+Unit|Description|"
    r"Field\b|Operator\b\s*Telephone|Zip\s*Code)",
    re.I
)

def fix_stim_ocr(t: str) -> str:
    t = ocr_cleanup(t or "")

    # ---- Fix common OCR damage around stimulation tables ----
    t = re.sub(r"\bDa\W*e\b", "Date", t, flags=re.I)
    t = re.sub(r"\bDe\W*ails\b", "Details", t, flags=re.I)
    t = re.sub(r"\bS\s*ecific\b", "Specific", t, flags=re.I)
    t = re.sub(r"\bSa11d\b", "Sand", t)

    # 1/2()/2014 -> 1/20/2014 (0 read as ()), keep conservative
    t = re.sub(r"/(\d)\(\)/(?=\d{4}\b)", r"/\g<1>0/", t)
    return t

def lines_clean(text: str):
    # 保留换行结构，才能按行找 label
    return [ln.replace("\u00a0", " ").rstrip() for ln in (text or "").splitlines() if ln is not None]

def find_value_after_label(text: str, label: str, *, max_lookahead_lines: int = 3):
    if not text or not label: return None
    lbl = label.lower().strip()
    ls = lines_clean(text)
    for i, ln in enumerate(ls):
        l = (ln or "").strip()
        if not l: continue
        if l.lower().startswith(lbl):
            tail = l[len(label):].strip().lstrip(":#").strip()
            if tail:
                return re.sub(r"\s{2,}", " ", tail).strip() or None
            for j in range(1, max_lookahead_lines + 1):
                if i + j >= len(ls): break
                nxt = (ls[i + j] or "").strip()
                if nxt:
                    return re.sub(r"\s{2,}", " ", nxt).strip() or None
    return None

def pick_label_value(joined: str, labels):
    for lab in labels:
        v = find_value_after_label(joined, lab)
        if v and not BAD_VALUE_RX.search(v):
            return v
    return None

# ===================== FIG detection =====================
FIG1_GROUPS = rx_groups([
    [r"\bAPI\b", r"\bAPI\s*#\b", r"\bAPI\s*NO\b", r"\bAPI\s*NUMBER\b"],
    [r"\bLatitude\b", r"\bLongitude\b", r"\bGrid\s*(Northing|Easting)\b", r"\bN\d{1,2}\b", r"\bW\d{2,3}\b"],
    [r"\bWell\s*Name\b", r"\bWell\s*Name\s*and\s*Number\b", r"\bWELL\s*:\b", r"\bWell\s*File\s*No\b", r"\bNDIC\s*File\s*Number\b"],
    [r"\bQtr-Qtr\b", r"\bTownship\b", r"\bRange\b", r"\bSection\b", r"\bSurface\s*Location\b", r"\bSURFACE\s+LOCATION\b", r"\bCOUNTY\b"],
])
FIG1_NEG   = rx_list([r"\bMINIMUM\s+CURVATURE\b", r"\bRECORD\s+OF\s+SURVEY\b"])
FIG1_PRIOR = rx_list([
    r"\bWELL\s*DATA\s*SUMMARY\b",
    r"\bSURFACE\s*LOCATION\b",
    r"\bBOTTOM\s*HOLE\s*LOCATION\b",
    r"\bWell\s*Name\s*and\s*Number\b",
    r"\bWell\s*File\s*No\b",
    r"\bNDIC\s*File\s*Number\b"
])

FIG2_STRONG = rx_list([
    r"\bSpecific\s+Stimulations\b",
    r"\bWELL\s*SPECIFIC\s*STIMULATIONS\b",
    r"\bDATE\s*STIMULATED\b",
    r"\bACID,\s*SHOT,\s*FRAC\b",
    r"\bSTIMULATION\s+FORMATION\b"
])
FIG2_GROUPS = rx_groups([
    [r"\bWELL\s*SPECIFIC\s*STIMULATIONS\b", r"\bDATE\s*STIMULATED\b", r"\bACID,\s*SHOT,\s*FRAC\b"],
    [r"\bStimulation\s*Formation\b", r"\bProppant\b", r"\bStages\b"],
    [r"\bTop\b", r"\bBottom\b", r"\bVolume\b", r"\bPressure\b", r"\bRate\b"],
])
FIG2_PRIOR = rx_list([
    r"\bWELL\s*SPECIFIC\s*STIMULATIONS\b",
    r"\bDATE\s*STIMULATED\b",
    r"\bACID,\s*SHOT,\s*FRAC\b",
    r"\bPROPPANT\b",
    r"\bSTAGES\b",
    r"\bTOP\b",
    r"\bBOTTOM\b"
])

# ===================== API + NDIC =====================
RE_API_10 = re.compile(r"\bAPI\s*[:#]?\s*([0-9]{2}-[0-9]{3}-[0-9]{5})\b", re.I)
RE_API_14 = re.compile(r"\bAPI\s*[:#]?\s*([0-9]{2}-[0-9]{3}-[0-9]{5}-[0-9]{2})\b", re.I)
RX_API_14D = re.compile(r"\b(\d{2}-\d{3}-\d{5}-\d{2})\b")
RX_API_10D = re.compile(r"\b(\d{2}-\d{3}-\d{5})\b")
RX_API_SPLIT = re.compile(r"\b(\d{2})\D{0,3}(\d{3})\D{0,3}(\d{5})\b")
RX_API_DIG = re.compile(r"\b(\d{10,14})\b")

RE_NDIC1 = re.compile(r"\bWell\s*File\s*No\.?\s*[:#]?\s*(\d{3,8})\b", re.I)
RE_NDIC2 = re.compile(r"\bNDIC\s*File\s*Number\s*[:#]?\s*(\d{3,8})\b", re.I)

API_BAD_CTX = re.compile(
    r"(CTB\s+with\s+common\s+ownership|for\s+the\s+following\s+wells|"
    r"LIST\s+OF\s+ATTACHMENTS|ATTACHMENTS\b|PRODUCTION\b|DISPOSITION\b)",
    re.I
)

def normalize_api(s: str):
    s = (s or "").strip()
    if not s: return None
    m = RX_API_14D.search(s)
    if m: return "-".join(m.group(1).split("-")[:3])
    m = RX_API_10D.search(s)
    if m: return m.group(1)
    m = RX_API_SPLIT.search(s)
    if m: return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    digits = re.sub(r"\D", "", s)
    if len(digits) >= 12 and digits[:2] == digits[2:4]:
        digits = digits[2:]
    if len(digits) >= 10:
        core = digits[:10]
        return f"{core[:2]}-{core[2:5]}-{core[5:10]}"
    return None

def extract_api_from_text(text: str):
    if not text: return None
    t = (text or "").replace("\u00a0", " ").replace("API¥", "API#").replace("API¥#", "API#")
    idx = t.lower().find("api")
    if idx != -1:
        w = t[max(0, idx-300): idx+900]
        m = (RE_API_14.search(w) or RE_API_10.search(w) or RX_API_14D.search(w) or RX_API_10D.search(w) or RX_API_SPLIT.search(w) or RX_API_DIG.search(w))
        if m: return normalize_api(m.group(1))
    m = (RE_API_14.search(t) or RE_API_10.search(t) or RX_API_14D.search(t) or RX_API_10D.search(t) or RX_API_SPLIT.search(t))
    if m: return normalize_api(m.group(1))
    md = RX_API_DIG.search(t)
    if md and re.search(r"\bAPI\b", t, re.I):
        return normalize_api(md.group(1))
    return None

def extract_ndic_from_text(text: str):
    if not text: return None
    m = RE_NDIC1.search(text) or RE_NDIC2.search(text)
    return m.group(1) if m else None

def extract_api_from_pages(pages):
    if not pages: return None
    for p in pages:
        tx = p.get("text") or ""
        if re.search(r"\bAPI\b", tx, re.I) and not API_BAD_CTX.search(tx):
            v = extract_api_from_text(tx)
            if v: return v
    for p in pages:
        tx = p.get("text") or ""
        if API_BAD_CTX.search(tx): continue
        v = extract_api_from_text(tx)
        if v: return v
    return None

def extract_ndic_from_pages(pages):
    if not pages: return None
    for p in pages[:30]:
        v = extract_ndic_from_text(p.get("text") or "")
        if v: return v
    for p in pages:
        v = extract_ndic_from_text(p.get("text") or "")
        if v: return v
    return None

def ndic_from_filename(rel_path: str):
    m = re.search(r"(?:^|/|\\)W(\d{3,8})\.pdf\b", rel_path or "", re.I)
    return m.group(1) if m else None

# ===================== County/State =====================
RE_COUNTY_STATE = re.compile(r"\bCounty,\s*State\s*[:#]?\s*([^\n\r]{1,120})", re.I)

def split_county_state(county_state: str):
    if not county_state: return None, None
    s = county_state.strip()
    parts = [x.strip() for x in s.split(",") if x.strip()]
    if len(parts) >= 2: return parts[0], parts[1]
    m = re.match(r"^(.+?)\s{2,}(.+)$", s)
    return (m.group(1).strip(), m.group(2).strip()) if m else (None, None)

# ===================== FIG1 extras: datum/shl/enesco/job_type =====================
RE_DATUM_ANY = re.compile(
    r"\bDat(?:u|v|r)n\s*[:#]?\s*([A-Za-z0-9][A-Za-z0-9 \-_/]{1,40})\b"
    r"|\bDatum\s*[:#]?\s*([A-Za-z0-9][A-Za-z0-9 \-_/]{1,40})\b",
    re.I
)

RE_SHL_ANY = re.compile(
    r"\b(?:Well\s*Surface\s*Hole\s*Location\s*\(SHL\)|Well\s*Surface\s*Hole\s*Location|"
    r"Surface\s*Hole\s*Location|Well\s*Surface\s*Location|Surface\s*Location)\b\s*[:#]?\s*"
    r"([^\n\r]{1,220})",
    re.I
)

RE_ENESCO_JOB = re.compile(
    r"\bEnesco\s*Job\s*(?:#|No\.?|Number|Job#)?\s*[:#]?\s*([A-Za-z0-9][A-Za-z0-9\-_/]{2,40})\b",
    re.I
)

RE_JOB_TYPE = re.compile(
    r"\bJob\s*Type\b\s*[:#]?\s*([A-Za-z][A-Za-z0-9 &/\-]{1,60})",
    re.I
)
RE_JOB_TYPE_LOOSE = re.compile(
    r"\bJob\s*Type\b\s+([A-Za-z][A-Za-z0-9 &/\-]{1,60})",
    re.I
)

def extract_enesco_job(text: str):
    if not text: return None
    t = ocr_cleanup(text)
    m = RE_ENESCO_JOB.search(t)
    if m: return clean_line(m.group(1))
    v = find_value_after_label(t, "Enesco Job#") or find_value_after_label(t, "Enesco Job")
    return clean_line(v)

def extract_job_type(text: str):
    if not text: return None
    t = ocr_cleanup(text)
    m = RE_JOB_TYPE.search(t) or RE_JOB_TYPE_LOOSE.search(t)
    if m:
        v = clean_line(m.group(1))
        if v:
            v = re.split(r"\bCounty\b|\bState\b|\bCounty,\s*State\b", v, maxsplit=1, flags=re.I)[0].strip() or None
        return v
    v = find_value_after_label(t, "Job Type")
    return clean_line(v)

def extract_datum_any(text: str):
    if not text: return None
    t = ocr_cleanup(text)
    m = RE_DATUM_ANY.search(t)
    if m:
        v = clean_line(m.group(1) or m.group(2))
        if v:
            v = v.replace("Nad", "NAD").replace("nad", "NAD")
            v = re.sub(r"\bNAD\s*83\b", "NAD83", v, flags=re.I)
        return v
    v = find_value_after_label(t, "Datum") or find_value_after_label(t, "Daturn")
    return clean_line(v)

def extract_shl_any(text: str):
    if not text: return None
    t = ocr_cleanup(text)
    m = RE_SHL_ANY.search(t)
    if m:
        v = clean_line(m.group(1))
        return None if (v and BAD_VALUE_RX.search(v)) else v
    v = (
        find_value_after_label(t, "Well Surface Hole Location (SHL)") or
        find_value_after_label(t, "Well Surface Hole Location") or
        find_value_after_label(t, "Surface Location")
    )
    v = clean_line(v)
    return None if (v and BAD_VALUE_RX.search(v)) else v

def scan_pages_for(pattern_rx, pages, *, window_kw=None, max_pages=160):
    if not pages: return None
    scanned = 0
    for p in pages:
        tx = p.get("text") or ""
        if not tx: continue
        t = ocr_cleanup(tx)
        if window_kw and (re.search(window_kw, t, re.I) is None):
            continue
        m = pattern_rx.search(t)
        if m:
            for g in m.groups():
                if g:
                    return clean_line(g)
        scanned += 1
        if scanned >= max_pages:
            break
    return None

# ===================== Coords =====================
def ocr_fix_keyword_confusions(t: str) -> str:
    t = t or ""
    t = re.sub(r"\bL0ngitude\b", "Longitude", t, flags=re.I)
    t = re.sub(r"\bLat1tude\b", "Latitude", t, flags=re.I)
    t = re.sub(r"\bL0n\b", "Lon", t, flags=re.I)
    t = re.sub(r"Lon\s*gitude", "Longitude", t, flags=re.I)
    t = re.sub(r"Lat\s*itude", "Latitude", t, flags=re.I)
    return t

def norm_coord(t: str) -> str:
    t = ocr_fix_keyword_confusions(ocr_cleanup(t))
    t = re.sub(r"\bNorth\b","N",t,flags=re.I); t = re.sub(r"\bSouth\b","S",t,flags=re.I)
    t = re.sub(r"\bEast\b","E",t,flags=re.I);  t = re.sub(r"\bWest\b","W",t,flags=re.I)
    return re.sub(r"(\d)\.\s+(\d)", r"\1.\2", t)

RE_LAT_DEC = re.compile(r"\b(?:Latitude|Lat)\s*[:#]?\s*(-?\d{1,3}\.\d+)\b", re.I)
RE_LON_DEC = re.compile(r"\b(?:Longitude|Lon)\s*[:#]?\s*(-?\d{1,3}\.\d+)\b", re.I)
RE_PAIR_DMS_SUFFIX = re.compile(
    r"\b(\d{1,2})\s*[°ºo]\s*(\d{1,2})\s*['’′]\s*([0-9.]+)\s*(?:\"|”|″)?\s*([NS])\s*[,;/ ]+\s*"
    r"(\d{1,3})\s*[°ºo]\s*(\d{1,2})\s*['’′]\s*([0-9.]+)\s*(?:\"|”|″)?\s*([EW])\b", re.I
)
RE_DMS_PREFIX_N = re.compile(r"\bN\D*(\d{1,2})\D+(\d{1,2})\D+([0-9]{1,2}(?:\.[0-9]+)?)\b", re.I)
RE_DMS_PREFIX_W = re.compile(r"\bW\D*(\d{2,3})\D+(\d{1,2})\D+([0-9]{1,2}(?:\.[0-9]+)?)\b", re.I)
RE_LAT_DMS_LABELED = re.compile(r"\b(?:Latitude|Lat)\s*[:#]?\s*(\d{1,2})\s*[°ºo]\s*(\d{1,2})\s*['’′]\s*([0-9.]+)\s*(?:\"|”|″)?\s*([NS])?\b", re.I)
RE_LON_DMS_LABELED = re.compile(r"\b(?:Longitude|Lon)\s*[:#]?\s*(\d{1,3})\s*[°ºo]\s*(\d{1,2})\s*['’′]\s*([0-9.]+)\s*(?:\"|”|″)?\s*([EW])?\b", re.I)
RE_PAIR_DEC_ANY = re.compile(r"\b(-?\d{1,2}\.\d{4,})\s*[,;/ ]+\s*(-?\d{1,3}\.\d{4,})\b")

RE_PAIR_DMS_NOSYM = re.compile(
    r"\bN\D*(\d{1,2})\D+(\d{1,2})\D+([0-9]{1,2}(?:\.[0-9]+)?)\b.*?"
    r"\bW\D*(\d{2,3})\D+(\d{1,2})\D+([0-9]{1,2}(?:\.[0-9]+)?)\b",
    re.I | re.S
)
RE_DMS_PREFIX_N_GLUE = re.compile(r"\bN\D*(\d{1,2})\D+(\d{3}\.\d+)\b", re.I)
RE_DMS_PREFIX_W_GLUE = re.compile(r"\bW\D*(\d{2,3})\D+(\d{3}\.\d+)\b", re.I)

def split_ms_maybe(x: str):
    s = re.sub(r"[^\d.]", "", x or "")
    if re.match(r"^\d{3}\.\d+$", s):
        mm, ss = int(s[:2]), float(s[2:])
        if 0 <= mm <= 59 and 0 <= ss < 60: return mm, ss
    return None

def dms(d, m, s, h):
    v = float(d) + float(m)/60.0 + float(s)/3600.0
    return -v if (h and h.upper() in ("S","W")) else v

def _valid_latlon(lat, lon):
    return lat is not None and lon is not None and abs(lat) <= 90 and abs(lon) <= 180

# 增强：ND 数据优先使用 ND bbox（即使没有 api）
ND_BBOX = (45.5, 49.5, -105.5, -96.0)
USA_BBOX = (24.0, 50.0, -125.0, -66.0)

def bbox_for(api10, ndic_file_no):
    if ndic_file_no:
        return ND_BBOX
    if api10 and str(api10).startswith("33-"):
        return ND_BBOX
    return USA_BBOX

def in_bbox(lat, lon, bbox):
    latmin, latmax, lonmin, lonmax = bbox
    return latmin <= lat <= latmax and lonmin <= lon <= lonmax

def coord_window(text: str, span=1200):
    t = text or ""
    m = re.search(r"(Latitude|Longitude|Lat|Lon)\b", t, re.I)
    if m:
        a = max(0, m.start()-250); b = min(len(t), m.end()+span)
        return t[a:b]
    m2 = re.search(r"\bN\D*\d{1,2}\D+\d{1,2}\D+\d{1,2}", t, re.I) or re.search(r"\bW\D*\d{2,3}\D+\d{1,2}\D+\d{1,2}", t, re.I)
    if m2:
        a = max(0, m2.start()-250); b = min(len(t), m2.end()+span)
        return t[a:b]
    return t[:span]

def parse_lat_lon(text: str, api10, ndic_file_no):
    bbox = bbox_for(api10, ndic_file_no)
    t = coord_window(norm_coord(text or ""), span=1200)
    lat = lon = None
    lat_raw = lon_raw = None

    m = RE_LAT_DEC.search(t)
    if m:
        try: lat = float(m.group(1)); lat_raw = m.group(1)
        except: pass
    m = RE_LON_DEC.search(t)
    if m:
        try: lon = float(m.group(1)); lon_raw = m.group(1)
        except: pass
    if _valid_latlon(lat, lon):
        return (lat, lon, lat_raw, lon_raw, False) if in_bbox(lat, lon, bbox) else (None, None, lat_raw, lon_raw, True)

    m = RE_PAIR_DMS_SUFFIX.search(t)
    if m:
        la = dms(m.group(1), m.group(2), m.group(3), m.group(4))
        lo = dms(m.group(5), m.group(6), m.group(7), m.group(8))
        lr = f"{m.group(1)} {m.group(2)} {m.group(3)} {m.group(4)}"
        orr = f"{m.group(5)} {m.group(6)} {m.group(7)} {m.group(8)}"
        if _valid_latlon(la, lo):
            return (la, lo, lr, orr, False) if in_bbox(la, lo, bbox) else (None, None, lr, orr, True)

    mlat, mlon = RE_LAT_DMS_LABELED.search(t), RE_LON_DMS_LABELED.search(t)
    if mlat and mlon:
        la = dms(mlat.group(1), mlat.group(2), mlat.group(3), (mlat.group(4) or "N"))
        lo = dms(mlon.group(1), mlon.group(2), mlon.group(3), (mlon.group(4) or "W"))
        if _valid_latlon(la, lo):
            return (la, lo, mlat.group(0), mlon.group(0), False) if in_bbox(la, lo, bbox) else (None, None, mlat.group(0), mlon.group(0), True)

    m = RE_PAIR_DMS_NOSYM.search(t)
    if m:
        la = dms(m.group(1), m.group(2), m.group(3), "N")
        lo = dms(m.group(4), m.group(5), m.group(6), "W")
        if _valid_latlon(la, lo):
            return (la, lo, m.group(0), m.group(0), False) if in_bbox(la, lo, bbox) else (None, None, m.group(0), m.group(0), True)

    mng, mwg = RE_DMS_PREFIX_N_GLUE.search(t), RE_DMS_PREFIX_W_GLUE.search(t)
    if mng and mwg:
        ms_lat, ms_lon = split_ms_maybe(mng.group(2)), split_ms_maybe(mwg.group(2))
        if ms_lat and ms_lon:
            la = dms(mng.group(1), ms_lat[0], ms_lat[1], "N")
            lo = dms(mwg.group(1), ms_lon[0], ms_lon[1], "W")
            if _valid_latlon(la, lo):
                return (la, lo, mng.group(0), mwg.group(0), False) if in_bbox(la, lo, bbox) else (None, None, mng.group(0), mwg.group(0), True)

    mn, mw = RE_DMS_PREFIX_N.search(t), RE_DMS_PREFIX_W.search(t)
    if mn and mw:
        try:
            deg_lat, deg_lon = int(mn.group(1)), int(mw.group(1))
            if not (30 <= deg_lat <= 80 and 60 <= deg_lon <= 170):
                return None, None, mn.group(0), mw.group(0), True
            la = dms(mn.group(1), mn.group(2), mn.group(3), "N")
            lo = dms(mw.group(1), mw.group(2), mw.group(3), "W")
            if _valid_latlon(la, lo):
                return (la, lo, mn.group(0), mw.group(0), False) if in_bbox(la, lo, bbox) else (None, None, mn.group(0), mw.group(0), True)
        except:
            return None, None, mn.group(0), mw.group(0), True

    if "$" not in t:
        m = RE_PAIR_DEC_ANY.search(t)
        if m:
            try:
                la, lo = float(m.group(1)), float(m.group(2))
                if _valid_latlon(la, lo):
                    return (la, lo, m.group(1), m.group(2), False) if in_bbox(la, lo, bbox) else (None, None, m.group(1), m.group(2), True)
            except:
                pass

    return None, None, lat_raw, lon_raw, None

LAT_SCORE_LATLON = re.compile(r"\bLatitude\b.*\bLongitude\b|\bLongitude\b.*\bLatitude\b", re.I|re.S)
LAT_SCORE_DMS_SYM = re.compile(r"\b\d{1,2}\s*[°ºo]\s*\d{1,2}\s*['’′]\s*\d{1,2}(?:\.\d+)?\s*(?:\"|”|″)?\s*[NS]\b", re.I)
LON_SCORE_DMS_SYM = re.compile(r"\b\d{1,3}\s*[°ºo]\s*\d{1,2}\s*['’′]\s*\d{1,2}(?:\.\d+)?\s*(?:\"|”|″)?\s*[EW]\b", re.I)

def latlon_page_score(text: str):
    t = norm_coord(text or "")
    s = 0
    if LAT_SCORE_LATLON.search(t): s += 8
    if RE_LAT_DEC.search(t): s += 3
    if RE_LON_DEC.search(t): s += 3
    if LAT_SCORE_DMS_SYM.search(t): s += 3
    if LON_SCORE_DMS_SYM.search(t): s += 3
    if RE_DMS_PREFIX_N.search(t): s += 2
    if RE_DMS_PREFIX_W.search(t): s += 2
    if RE_PAIR_DMS_NOSYM.search(t): s += 2
    if RE_DMS_PREFIX_N_GLUE.search(t): s += 1
    if RE_DMS_PREFIX_W_GLUE.search(t): s += 1
    if RE_PAIR_DEC_ANY.search(t): s += 2
    if re.search(r"\bGrid\s+Northing\b|\bGrid\s+Easting\b|\bNorthing\b|\bEasting\b", t, re.I): s += 1
    return s

def extract_latlon_from_pages(pages, api10, ndic_file_no, max_scan=300):
    if not pages: return (None, None, None, None, None, True)

    scored = [(latlon_page_score(p.get("text") or ""), p) for p in pages]
    scored = [(sc, p) for sc, p in scored if sc > 0]
    scan = [p for _, p in sorted(scored, key=lambda x: x[0], reverse=True)[:max_scan]] if scored else pages[:min(40, len(pages))]

    n = len(pages)
    if n > 60:
        mid = n // 2
        scan += pages[max(0, mid-20): min(n, mid+20)]
        scan += pages[max(0, n-80): n]

    seen, uniq = set(), []
    for p in scan:
        k = p.get("page")
        if k in seen: continue
        seen.add(k); uniq.append(p)

    for p in uniq[:max_scan]:
        lat, lon, lat_raw, lon_raw, suspect = parse_lat_lon(p.get("text") or "", api10, ndic_file_no)
        if lat is not None and lon is not None and not suspect:
            return lat, lon, lat_raw, lon_raw, p.get("page"), False
    return (None, None, None, None, None, True)

# ===================== Stim (unchanged from your v2, with OCR fix + has_fields logic) =====================
RE_DATE_STIM = re.compile(r"\bDate\s*Stimulated\s*[:#]?\s*(\d{1,2}/\d{1,2}/\d{4})\b", re.I)
RE_FORM      = re.compile(r"\bStimulation\s*Formation\s*[:#]?\s*([^\n\r]{1,80})", re.I)
RE_TOP       = re.compile(r"\bTop\s*\(?(?:Ft|Feet)\)?\s*[:#]?\s*(\d+)\b", re.I)
RE_BOTTOM    = re.compile(r"\bBottom\s*\(?(?:Ft|Feet)\)?\s*[:#]?\s*(\d+)\b", re.I)
RE_STAGES    = re.compile(r"\bStimulation\s*Stages\s*[:#]?\s*(\d+)\b", re.I)
RE_VOL_UNIT  = re.compile(r"\b([0-9]{1,3}(?:,[0-9]{3})*(?:\.\d+)?)\s*(Barrels?|BBLS?|BBL|bbls?|bbl|Gallons?|GAL|gal)\b", re.I)

RE_WSS_ROW = re.compile(
    r"\b(\d{1,2}/\d{1,2}/\d{4})\s+"
    r"([A-Za-z0-9][A-Za-z0-9 &/\-]{0,60})\s+"
    r"(\d{3,5})\s+(\d{3,5})"
    r"(?:\s*[\|\u00a6'‘’\-]?\s*[A-Za-z][A-Za-z /_-]{0,25}){0,6}\s+"
    r"(?:(\d{1,3})\s+)?"
    r"(\d{3,8}(?:,\d{3})*)\s+"
    r"(Barrels?|BBLS?|BBL|bbls?|bbl|Gallons?|GAL|gal)\b",
    re.I
)

RE_TREAT_BLK = re.compile(r"\bACID,\s*SHOT,\s*FRAC\b.*?(?=\bPRODUCTION\b|\bDISPOSITION\b|\bLIST\s+OF\s+ATTACHMENTS\b|$)", re.I|re.S)
RE_VOL_GAL   = re.compile(r"\b([0-9]{1,3}(?:,[0-9]{3})*(?:\.\d+)?)\s*(?:gal|gals|gallon|gallons)\b", re.I)
RE_VOL_BBL   = re.compile(r"\b([0-9]{1,3}(?:,[0-9]{3})*(?:\.\d+)?)\s*(?:bbl|bbls|barrel|barrels)\b", re.I)
RE_STAGES_TXT= re.compile(r"\b(\d+)\s*(?:stages|stage)\b", re.I)

RE_EXTRAS_HEADER = re.compile(
    r"\bAcid\s*%.*?\bLbs?\s*Proppant.*?\bMaximum\s*Treatment\s*Pressure.*?\bMaximum\s*Treatment\s*Rate\b",
    re.I | re.S
)
RE_DETAILS_BLK = re.compile(r"\bDetails\b\s*[:#]?\s*(.*)$", re.I|re.S)

def _parse_wss_row_heuristic(joined: str):
    if not joined: return (None, None, None, None, None, None, None)
    date_re = re.compile(r"\b(\d{1,2}/\d{1,2}/\d{4})\b")
    vu_re   = re.compile(r"\b(\d{3,8}(?:,\d{3})*)\s*(Barrels?|BBLS?|BBL|bbls?|bbl|Gallons?|GAL|gal)\b", re.I)
    depth_re= re.compile(r"\b(\d{3,5})\b")

    parts = joined.splitlines() if "\n" in joined else re.split(r"\s{2,}", joined)
    for ln in [norm_coord(x) for x in parts if x]:
        mdate, mvu = date_re.search(ln), vu_re.search(ln)
        if not (mdate and mvu): continue
        nums = [int(x) for x in depth_re.findall(ln)]
        if len(nums) < 2: continue

        date_raw = mdate.group(1)
        idx = mdate.end()
        md1 = depth_re.search(ln[idx:])
        formation = clean_line(ln[idx: idx + md1.start()]) if md1 else None
        if formation: formation = re.sub(r"[|¦]+", " ", formation).strip() or None

        top, bottom = nums[0], nums[1]
        vol = _to_flt(mvu.group(1))
        u = (mvu.group(2) or "").lower()
        units = "bbl" if ("barrel" in u or u.startswith("bbl")) else ("gal" if "gal" in u else None)

        stages = None
        ms = re.search(r"\b(\d{1,3})\b\s*$", ln[:mvu.start()])
        if ms:
            v = int(ms.group(1))
            if 1 <= v <= 200: stages = v

        try: date_iso = datetime.strptime(date_raw, "%m/%d/%Y").date().isoformat()
        except: date_iso = None
        return (date_iso, formation, top, bottom, stages, vol, units)

    return (None, None, None, None, None, None, None)

def _extract_extras_from_table(text: str):
    if not text: return (None, None, None, None)
    mh = RE_EXTRAS_HEADER.search(text)
    if not mh: return (None, None, None, None)
    tail = text[mh.end(): mh.end() + 1200]
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in tail.splitlines() if ln.strip()]
    for ln in lines[:30]:
        nums = [x for x in re.findall(r"-?\d[\d,]*\.?\d*", ln) if re.search(r"\d", x)]
        vals = []
        for x in nums:
            try: vals.append(float(x.replace(",", "")))
            except: pass
        if len(vals) < 3: continue
        a = l = p = r = None
        if len(vals) >= 4 and 0 <= vals[0] <= 100:
            a, l, p, r = vals[0], int(vals[1]), int(vals[2]), vals[3]
        else:
            l, p, r = int(vals[0]), int(vals[1]), vals[2]
        return a, l, p, r
    return (None, None, None, None)

def _extract_treatment_type(joined: str, blk: str):
    text, blk = joined or "", blk or ""

    HEADER_BAD = re.compile(
        r"(acid\s*%|^acid$|^iacid$|lbs?\s*prop|max(?:imum)?\s*treat|press|rate|\bps[il]\b|bbl)",
        re.I
    )
    DETAILS_BAD = re.compile(r"^\s*Det(?:ails)?\s*$", re.I)

    def cleanup(v):
        if not v: return None
        v = v.strip()
        v = re.sub(r"\(cid:\d+\)?", " ", v, flags=re.I)
        v = re.sub(r"[|¦]+", " ", v)
        v = re.sub(r"\s{2,}", " ", v).strip()
        if "cid:" in v.lower(): return None
        if not v or len(v) < 2: return None
        if DETAILS_BAD.match(v): return None
        if HEADER_BAD.search(v): return None
        v = re.split(r"\s+\d", v, maxsplit=1)[0].strip()
        if len(v) < 2: return None
        if re.fullmatch(r"[%\-\|]+", v): return None
        return clean_line(v)

    for src in (text, blk):
        lines = [ln.strip() for ln in (src or "").splitlines()]
        for i, ln in enumerate(lines):
            if re.search(r"^(?:Type\s*(?:of\s*)?Treatment|Treatment\s*Type|Type\s*Treatment)\b", ln, re.I):
                tail = re.sub(
                    r"^(?:Type\s*(?:of\s*)?Treatment|Treatment\s*Type|Type\s*Treatment)\b",
                    "", ln, flags=re.I
                ).strip()
                tail = tail.lstrip(":#|").strip()
                v = cleanup(tail) if tail else None
                if v: return v
                for j in range(1, 4):
                    if i + j < len(lines) and lines[i + j].strip():
                        v = cleanup(lines[i + j].strip())
                        if v: return v
                        break

    m = re.search(
        r"\b(?:Type\s*(?:of\s*)?Treatment|Treatment\s*Type|Type\s*Treatment)\b"
        r"\s*[:#]?\s*([A-Za-z][A-Za-z /,&\-]{0,60})",
        text,
        re.I
    )
    if m:
        v = cleanup(m.group(1))
        if v: return v

    if re.search(r"\bACID,\s*SHOT,\s*FRAC\b", text, re.I):
        return "ACID, SHOT, FRAC"
    return None

def parse_stim(fig2_pages):
    raw_joined = "\n".join((p.get("text") or "") for p in fig2_pages)
    joined = fix_stim_ocr(raw_joined)
    strong = any(r.search(joined or "") for r in FIG2_STRONG)

    date_iso = formation = units = None
    top = bottom = stages = None
    vol = None

    treatment_type = acid_pct = lbs_proppant = None
    max_treatment_pressure_psi = max_treatment_rate_bbl_min = None
    details = None

    m = RE_WSS_ROW.search(joined)
    if m:
        try: date_iso = datetime.strptime(m.group(1), "%m/%d/%Y").date().isoformat()
        except: date_iso = None
        formation = clean_line(m.group(2).strip()) if m.group(2) else None
        top, bottom = _to_int(m.group(3)), _to_int(m.group(4))
        stages = _to_int(m.group(5)) if m.group(5) else None
        vol = _to_flt(m.group(6))
        u = (m.group(7) or "").lower()
        units = "bbl" if ("barrel" in u or u.startswith("bbl")) else ("gal" if "gal" in u else None)

    if not any([date_iso, formation, top, bottom, stages, vol, units]):
        date_iso, formation, top, bottom, stages, vol, units = _parse_wss_row_heuristic(joined)

    if not any([date_iso, formation, top, bottom, stages, vol, units]):
        ds = first(RE_DATE_STIM, joined)
        formation = first(RE_FORM, joined)
        top, bottom = _to_int(first(RE_TOP, joined)), _to_int(first(RE_BOTTOM, joined))
        stages = _to_int(first(RE_STAGES, joined))
        m2 = RE_VOL_UNIT.search(joined)
        if m2:
            vol = _to_flt(m2.group(1))
            u = (m2.group(2) or "").lower()
            units = "bbl" if ("barrel" in u or u.startswith("bbl")) else ("gal" if "gal" in u else None)
        if ds:
            try: date_iso = datetime.strptime(ds, "%m/%d/%Y").date().isoformat()
            except: date_iso = None

    blk = (RE_TREAT_BLK.search(joined or "") or [None]).group(0) if RE_TREAT_BLK.search(joined or "") else ""
    treatment_type = _extract_treatment_type(joined, blk)
    acid_pct, lbs_proppant, max_treatment_pressure_psi, max_treatment_rate_bbl_min = _extract_extras_from_table(joined)

    if acid_pct is not None and not (0 <= acid_pct <= 100): acid_pct = None
    if max_treatment_pressure_psi is not None and max_treatment_pressure_psi > 20000: max_treatment_pressure_psi = None
    if max_treatment_rate_bbl_min is not None and not (0 <= max_treatment_rate_bbl_min <= 200): max_treatment_rate_bbl_min = None

    md = RE_DETAILS_BLK.search(blk or "") or RE_DETAILS_BLK.search(joined or "")
    if md:
        details = md.group(1).strip()
        details = re.split(
            r"\b(?:PRODUCTION|DISPOSITION|LIST\s+OF\s+ATTACHMENTS|ACID,\s*SHOT,\s*FRAC)\b",
            details, maxsplit=1, flags=re.I
        )[0].strip() or None

    if blk:
        if vol is None:
            mg = RE_VOL_GAL.search(blk)
            if mg: vol, units = _to_flt(mg.group(1)), "gal"
            else:
                mb = RE_VOL_BBL.search(blk)
                if mb: vol, units = _to_flt(mb.group(1)), "bbl"
        if stages is None:
            ms = RE_STAGES_TXT.search(blk)
            if ms:
                try: stages = int(ms.group(1))
                except: pass

    has_core = any([date_iso, formation, top, bottom, stages, vol, units])
    has_extras = any([treatment_type, acid_pct, lbs_proppant, max_treatment_pressure_psi, max_treatment_rate_bbl_min, details])
    has_fields = bool(has_core or has_extras)
    stim_present = bool(strong or has_fields)

    return dict(
        stim_present=stim_present,
        stim_has_fields=has_fields,
        date_stimulated=date_iso,
        stimulation_formation=formation,
        top_ft=top,
        bottom_ft=bottom,
        stimulation_stages=stages,
        volume=vol,
        volume_units=units,
        treatment_type=treatment_type,
        acid_pct=acid_pct,
        lbs_proppant=lbs_proppant,
        max_treatment_pressure_psi=max_treatment_pressure_psi,
        max_treatment_rate_bbl_min=max_treatment_rate_bbl_min,
        details=details,
        raw_text=raw_joined,
        raw_text_clean=joined,
        fig2_pages=[p.get("page") for p in fig2_pages],
    )

# ===================== scoring/picking =====================
def group_score(groups, text):
    hits, score = [], 0
    for g in groups:
        if anyhit(g, text):
            score += 1
            hits.append(" OR ".join([r.pattern for r in g]))
    return score, hits

def labeliness_fig1(t: str) -> int:
    kws = [
        "Well Name and Number","Well Name","Operator","NAME OF OPERATOR","Address","County, State",
        "Well File No","NDIC File Number","Latitude","Longitude","Datum","Well Surface Hole Location",
        "Enesco Job","Job Type"
    ]
    return sum(1 for kw in kws if re.search(kw, t or "", re.I))

def pick(cands, priors, keep_n):
    ranked = []
    for p in cands:
        t = p.get("text") or ""
        pr = sum(1 for r in priors if r.search(t))
        ranked.append((pr, p.get("score",0), labeliness_fig1(t), p.get("page",0), p))
    ranked.sort(reverse=True)
    return [x[-1] for x in ranked[:keep_n]]

def candidates(pages, fig1_th, fig2_th, fig1_neg_penalty, disable_neg):
    FIG2_GATE = re.compile(
        r"\b(Date\s*Stimulated|Da\W*e\s*Stimulated|Specific\s+Stimulations|S\s*ecific\s+Stimulations|ACID,\s*SHOT,\s*FRAC)\b",
        re.I
    )
    c1, c2 = [], []
    for p in pages:
        t_raw = p.get("text") or ""
        t = norm_space(t_raw)
        if not t: continue

        s1, g1 = group_score(FIG1_GROUPS, t)
        if (not disable_neg) and anyhit(FIG1_NEG, t):
            s1 = max(0, s1 - fig1_neg_penalty)
        if s1 >= fig1_th:
            c1.append({"page": p.get("page"), "score": s1, "hit_groups": g1, "text": t_raw})

        s2, g2 = group_score(FIG2_GROUPS, t)
        if s2 >= fig2_th and FIG2_GATE.search(ocr_cleanup(t_raw or "")):
            c2.append({"page": p.get("page"), "score": s2, "hit_groups": g2, "text": t_raw})
    return c1, c2

# ===================== parse well =====================
def parse_well(fig1_pages, all_pages, rel_path: str, latlon_scan_pages: int):
    joined = "\n".join((p.get("text") or "") for p in fig1_pages) if fig1_pages else ""
    joined_clean = ocr_cleanup(joined)

    api10 = extract_api_from_text(joined)
    if not api10 and not API_BAD_CTX.search(joined or ""):
        api10 = extract_api_from_pages(all_pages)

    ndic = extract_ndic_from_text(joined) or extract_ndic_from_pages(all_pages)
    if (ndic is None) or (ndic == "600") or (len(str(ndic)) < 4):
        ndic = ndic_from_filename(rel_path) or ndic

    # 增强：Operator label 覆盖 ND 表单常见写法
    well_name = pick_label_value(joined_clean, ["Well Name and Number", "Well Name"])
    op = pick_label_value(joined_clean, ["Operator", "NAME OF OPERATOR", "OPERATOR"])
    addr = pick_label_value(joined_clean, ["Address"])

    if op:
        op2 = re.sub(r"\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}.*$", "", op).strip()
        op = op2 or op

    county_state = first(RE_COUNTY_STATE, joined_clean) or find_value_after_label(joined_clean, "County, State")
    if county_state and BAD_VALUE_RX.search(county_state):
        county_state = first(RE_COUNTY_STATE, joined_clean)
    county, state = split_county_state(county_state)

    enesco_job = extract_enesco_job(joined_clean) or scan_pages_for(
        RE_ENESCO_JOB, all_pages, window_kw=r"\bEnesco\b|\bJob\s*Type\b|\bAPI\b"
    )
    job_type = extract_job_type(joined_clean) or scan_pages_for(
        RE_JOB_TYPE, all_pages, window_kw=r"\bJob\s*Type\b|\bEnesco\b|\bAPI\b"
    )
    datum = extract_datum_any(joined_clean) or scan_pages_for(
        RE_DATUM_ANY, all_pages, window_kw=r"\bDat(?:u|v|r)n\b|\bDatum\b|\bLatitude\b|\bLongitude\b"
    )
    shl = extract_shl_any(joined_clean) or scan_pages_for(
        RE_SHL_ANY, all_pages, window_kw=r"\bSurface\b|\bLocation\b|\bSHL\b"
    )

    lat, lon, lat_raw, lon_raw, suspect = parse_lat_lon(joined, api10, ndic)
    latlon_page = None
    if (lat is None or lon is None) and all_pages:
        lat, lon, lat_raw, lon_raw, pno, suspect2 = extract_latlon_from_pages(
            all_pages, api10, ndic, max_scan=latlon_scan_pages
        )
        suspect, latlon_page = suspect2, pno

    latlon_suspect = bool(suspect) if (lat is not None and lon is not None) else False

    return dict(
        api=api10,
        ndic_file_no=ndic,
        well_name=well_name,
        operator=op,
        address=addr,
        county_state=county_state,
        county=county,
        state=state,
        enesco_job=enesco_job,
        job_type=job_type,
        shl_location=shl,
        datum=datum,
        latitude=lat,
        longitude=lon,
        lat_raw=lat_raw,
        lon_raw=lon_raw,
        latlon_page=latlon_page,
        latlon_suspect=latlon_suspect,
        fig1_pages=[p.get("page") for p in fig1_pages],
        raw_text=joined,
        raw_text_clean=joined_clean,
    )

# ===================== main =====================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--texts_dir", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--max_files", type=int, default=0)
    ap.add_argument("--keep_debug_text_chars", type=int, default=4000)
    ap.add_argument("--fig1_keep_n", type=int, default=2)
    ap.add_argument("--fig2_keep_n", type=int, default=2)
    ap.add_argument("--fig1_threshold", type=int, default=2)
    ap.add_argument("--fig2_threshold", type=int, default=2)
    ap.add_argument("--disable_fig1_negative", action="store_true")
    ap.add_argument("--fig1_neg_penalty", type=int, default=1)
    ap.add_argument("--latlon_scan_pages", type=int, default=350)
    args = ap.parse_args()

    texts_dir = Path(args.texts_dir).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    well_out = out_dir/"well_info.jsonl"
    stim_out = out_dir/"stimulation_data.jsonl"
    rep_out  = out_dir/"parse_report.json"
    for p in (well_out, stim_out):
        if p.exists(): p.unlink()

    text_files = iters(texts_dir, ".json")
    if args.max_files and args.max_files > 0:
        text_files = text_files[:args.max_files]

    report = dict(
        run_at=datetime.now(timezone.utc).isoformat(),
        num_files=len(text_files),
        stats=dict(
            wells_total=0,
            latlon_present=0,
            latlon_suspect=0,
            stim_present=0,
            stim_has_fields=0,
            datum_present=0,
            shl_present=0,
            enesco_present=0,
            job_type_present=0,
            county_state_present=0,
            stim_extras_present=0
        ),
        errors=[]
    )

    wells_buf, stim_buf = [], []
    for jf in text_files:
        try:
            payload = rjson(jf)
            all_pages = payload.get("pages") or []
            if not all_pages:
                continue

            fig1_c, fig2_c = candidates(
                all_pages,
                args.fig1_threshold, args.fig2_threshold,
                fig1_neg_penalty=args.fig1_neg_penalty,
                disable_neg=args.disable_fig1_negative,
            )
            fig1_pages = pick(fig1_c, FIG1_PRIOR, args.fig1_keep_n) if fig1_c else []
            fig2_pages = pick(fig2_c, FIG2_PRIOR, args.fig2_keep_n) if fig2_c else []

            rel_path = payload.get("relative_path") or jf.name
            src_pdf  = payload.get("source_pdf")

            well = parse_well(fig1_pages, all_pages, rel_path, args.latlon_scan_pages)
            stim = parse_stim(fig2_pages) if fig2_pages else dict(stim_present=False, stim_has_fields=False, raw_text="", raw_text_clean="", fig2_pages=[])

            primary_id = well.get("api") or (f"NDIC-{well.get('ndic_file_no')}" if well.get("ndic_file_no") else rel_path)

            well_row = dict(
                primary_id=primary_id,
                source_pdf=src_pdf,
                relative_path=rel_path,

                operator=well.get("operator"),
                well_name=well.get("well_name"),
                api=well.get("api"),
                enesco_job=well.get("enesco_job"),
                job_type=well.get("job_type"),
                county_state=well.get("county_state"),
                shl_location=well.get("shl_location"),
                latitude=well.get("latitude"),
                longitude=well.get("longitude"),
                datum=well.get("datum"),

                ndic_file_no=well.get("ndic_file_no"),
                county=well.get("county"),
                state=well.get("state"),
                address=well.get("address"),

                lat_raw=well.get("lat_raw"),
                lon_raw=well.get("lon_raw"),
                latlon_page=well.get("latlon_page"),
                latlon_suspect=well.get("latlon_suspect"),
                fig1_pages=well.get("fig1_pages") or [],
                raw_text=trunc(well.get("raw_text") or "", args.keep_debug_text_chars),
            )

            stim_row = dict(
                primary_id=primary_id,
                source_pdf=src_pdf,
                relative_path=rel_path,

                operator=well.get("operator"),
                well_name=well.get("well_name"),
                api=well.get("api"),
                enesco_job=well.get("enesco_job"),
                job_type=well.get("job_type"),
                county_state=well.get("county_state"),
                shl_location=well.get("shl_location"),
                latitude=well.get("latitude"),
                longitude=well.get("longitude"),
                datum=well.get("datum"),

                ndic_file_no=well.get("ndic_file_no"),

                stim_present=bool(stim.get("stim_present")),
                stim_has_fields=bool(stim.get("stim_has_fields")),
                date_stimulated=stim.get("date_stimulated"),
                stimulation_formation=stim.get("stimulation_formation"),
                top_ft=stim.get("top_ft"),
                bottom_ft=stim.get("bottom_ft"),
                stimulation_stages=stim.get("stimulation_stages"),
                volume=stim.get("volume"),
                volume_units=stim.get("volume_units"),
                treatment_type=stim.get("treatment_type"),
                acid_pct=stim.get("acid_pct"),
                lbs_proppant=stim.get("lbs_proppant"),
                max_treatment_pressure_psi=stim.get("max_treatment_pressure_psi"),
                max_treatment_rate_bbl_min=stim.get("max_treatment_rate_bbl_min"),
                details=trunc(stim.get("details") or "", 2000) if stim.get("details") else None,

                fig2_pages=stim.get("fig2_pages") or [],
                raw_text=trunc(stim.get("raw_text") or "", args.keep_debug_text_chars),
                raw_text_clean=trunc(stim.get("raw_text_clean") or "", args.keep_debug_text_chars),
            )

            wells_buf.append(well_row)
            stim_buf.append(stim_row)

            st = report["stats"]
            st["wells_total"] += 1
            if well_row["latitude"] is not None and well_row["longitude"] is not None: st["latlon_present"] += 1
            if well_row["latlon_suspect"]: st["latlon_suspect"] += 1
            if well_row.get("datum"): st["datum_present"] += 1
            if well_row.get("shl_location"): st["shl_present"] += 1
            if well_row.get("enesco_job"): st["enesco_present"] += 1
            if well_row.get("job_type"): st["job_type_present"] += 1
            if well_row.get("county_state"): st["county_state_present"] += 1
            if stim_row["stim_present"]: st["stim_present"] += 1
            if stim_row["stim_has_fields"]: st["stim_has_fields"] += 1
            if any([stim_row.get("treatment_type"), stim_row.get("acid_pct"), stim_row.get("lbs_proppant"),
                    stim_row.get("max_treatment_pressure_psi"), stim_row.get("max_treatment_rate_bbl_min"),
                    stim_row.get("details")]):
                st["stim_extras_present"] += 1

            if len(wells_buf) >= 200:
                append_jsonl(wells_buf, well_out); wells_buf.clear()
            if len(stim_buf) >= 200:
                append_jsonl(stim_buf, stim_out); stim_buf.clear()

        except Exception as e:
            report["errors"].append(dict(file=str(jf), error=f"{type(e).__name__}: {e}"))

    if wells_buf: append_jsonl(wells_buf, well_out)
    if stim_buf:  append_jsonl(stim_buf,  stim_out)
    wjson(report, rep_out)

    print("Done. Stats:", report["stats"])
    print("well_info.jsonl ->", well_out)
    print("stimulation_data.jsonl ->", stim_out)
    print("parse_report.json ->", rep_out)

if __name__ == "__main__":
    main()