from pathlib import Path
from pdf2image import convert_from_path
import pytesseract
import re

pdf_dir = Path("drive-001")
out_root = Path("outputs")
out_root.mkdir(exist_ok=True)

def find_hits(text):
    patterns = [
        r"API\s*#\s*\d{2}-\d{3}-\d{5}",
        r"Well\s*File\s*#\s*\d+",
        r"located\s+in\s+the",
        r"County,\s+North\s+Dakota"
    ]
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False

pdf_list = list(pdf_dir.glob("*.pdf"))
total = len(pdf_list)

for idx, pdf_path in enumerate(pdf_list, start=1):
    print(f"[{idx}/{total}] Processing {pdf_path.name}")

    well_id = pdf_path.stem
    well_out = out_root / well_id
    well_out.mkdir(exist_ok=True)

    images = convert_from_path(str(pdf_path), dpi=150)

    for i, img in enumerate(images, start=1):
        print(f"   Page {i}/{len(images)}")
        text = pytesseract.image_to_string(img)

        if find_hits(text):
            hit_file = well_out / f"hit_p{i:03d}.txt"
            hit_file.write_text(text, encoding="utf-8")

print("DONE")
