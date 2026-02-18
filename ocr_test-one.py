from pathlib import Path
from pdf2image import convert_from_path
import pytesseract
import re

pdf_path = Path("drive-001") / "W11920.pdf"
out_base = Path("outputs") / pdf_path.stem
out_base.mkdir(parents=True, exist_ok=True)

max_pages = 200

hit_pages = []

for p in range(1, max_pages + 1):
    try:
        images = convert_from_path(str(pdf_path), dpi=120, first_page=p, last_page=p)
    except Exception:
        break

    t = pytesseract.image_to_string(images[0], config="--oem 1 --psm 6")
    low = t.lower()

    has_api = bool(re.search(r"\b\d{2}-\d{3}-\d{5}\b", t)) or ("api" in low)
    has_geo_words = any(k in low for k in ["latitude", "longitude", "datum", "nad", "surface hole", "shl", "bottom hole", "bhl"])
    has_dms = ("°" in t) or bool(re.search(r"\d{2,3}\s*°\s*\d{1,2}\s*'\s*\d{1,2}(\.\d+)?\s*\"?\s*[NS]", t))
    has_nw = bool(re.search(r"\b\d{2,3}\s+\d{1,2}\s+\d{1,2}(\.\d+)?\s*[NW]\b", t))

    if has_api or has_geo_words or has_dms or has_nw:
        hit_pages.append((p, t))
        (out_base / f"hit_p{p:03d}.txt").write_text(t, encoding="utf-8")

    if p % 5 == 0:
        print("page", p)

(out_base / "hit_summary.txt").write_text(
    "\n".join([f"p{p:03d}" for p, _ in hit_pages]),
    encoding="utf-8"
)

print("hits:", [p for p, _ in hit_pages])
print("saved to:", out_base)
