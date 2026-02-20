import argparse
import json
import subprocess
import shutil
from pathlib import Path
from datetime import datetime, timezone

import pdfplumber


# Utils
def safe_write_json(data: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(out_path)


def iter_pdfs(pdf_dir: Path) -> list[Path]:
    return sorted([p for p in pdf_dir.rglob("*.pdf") if p.is_file()])


def text_quality(pages: list[dict], short_threshold: int = 50) -> tuple[int, int]:
    total = 0
    short = 0
    for p in pages:
        t = (p.get("text") or "").strip()
        total += len(t)
        if len(t) < short_threshold:
            short += 1
    return total, short


def maybe_truncate_text(t: str, max_chars: int) -> str:
    if max_chars <= 0:
        return t
    if len(t) <= max_chars:
        return t
    return t[:max_chars] + "\n...[TRUNCATED]..."


# OCR
def get_ocrmypdf_path() -> str:
    ocr_bin = shutil.which("ocrmypdf")
    if not ocr_bin:
        raise FileNotFoundError(
            "Cannot find 'ocrmypdf' in PATH.\n"
            "Try:\n"
            "  which ocrmypdf\n"
            "  ocrmypdf --version\n"
            "Install (Ubuntu/WSL):\n"
            "  sudo apt-get install -y ocrmypdf tesseract-ocr\n"
        )
    return ocr_bin


def get_qpdf_path() -> str | None:
    return shutil.which("qpdf")


def fix_pdf_with_qpdf(src_pdf: Path, fixed_pdf: Path) -> bool:
    """
    Try to rewrite/linearize PDF with qpdf to reduce Ghostscript failures.
    Returns True if fixed_pdf created.
    """
    qpdf = get_qpdf_path()
    if not qpdf:
        return False
    fixed_pdf.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run([qpdf, "--linearize", str(src_pdf), str(fixed_pdf)], check=True)
        return fixed_pdf.exists()
    except subprocess.CalledProcessError:
        return False


def run_ocrmypdf(
    src_pdf: Path,
    ocr_pdf: Path,
    ocr_bin: str,
    *,
    force_ocr: bool = False,
    clean: bool = False,
    capture_on_error: bool = True,
) -> tuple[bool, str]:
    """
    Run ocrmypdf.
    Returns: (success, error_msg)
    - Success path: do NOT capture stdout/stderr (fast).
    - Error path: capture stderr (useful debugging) if capture_on_error True.
    """
    ocr_pdf.parent.mkdir(parents=True, exist_ok=True)

    cmd = [ocr_bin, "--deskew", "--rotate-pages"]
    if clean:
        cmd += ["--clean"]
    cmd += ["--force-ocr"] if force_ocr else ["--skip-text"]
    cmd += [str(src_pdf), str(ocr_pdf)]

    try:
        subprocess.run(cmd, check=True)
        return True, ""
    except subprocess.CalledProcessError as e:
        if not capture_on_error:
            return False, str(e)

        # re-run with capture_output to get stderr detail
        try:
            r = subprocess.run(cmd, check=False, capture_output=True)
            stderr = (r.stderr or b"").decode("utf-8", errors="ignore")
            return False, stderr[:3000]
        except Exception:
            return False, str(e)


# PDF text
def extract_text_by_page(pdf_path: Path, *, truncate_chars: int = 0, compact: bool = False) -> list[dict]:
    """
    Extract text per page.
    - compact=True: drop pages with empty text after stripping
    - truncate_chars: truncate each page text to limit JSON size
    """
    pages_out: list[dict] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
            text = maybe_truncate_text(text, truncate_chars)
            if compact and (not text.strip()):
                continue
            pages_out.append({"page": i, "text": text})
    return pages_out


# Main
def main():
    parser = argparse.ArgumentParser(
        description="Batch OCR PDFs and dump per-page text to JSON (final robust version)."
    )
    parser.add_argument("--pdf_dir", required=True, help="Input PDF directory (recursive traversal)")
    parser.add_argument("--out_dir", required=True, help="Output directory (contains ocr_pdfs/ and texts/)")

    parser.add_argument("--do_ocr", action="store_true", help="Enable ocrmypdf (recommended)")
    parser.add_argument("--no_ocr", action="store_true", help="Skip OCR")
    parser.add_argument("--force_ocr", action="store_true", help="Use --force-ocr (slower but more robust)")
    parser.add_argument("--clean", action="store_true", help="Enable --clean (slower; optional)")

    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output JSON files")
    parser.add_argument("--max_files", type=int, default=0, help="Process only first N PDFs (0 = all)")

    parser.add_argument(
        "--min_text_chars",
        type=int,
        default=0,
        help="If total extracted text chars < this value, retry OCR with --force-ocr (0 disables retry).",
    )

    parser.add_argument(
        "--compact",
        action="store_true",
        help="Only keep pages with non-empty text (reduces JSON size).",
    )
    parser.add_argument(
        "--truncate_chars",
        type=int,
        default=0,
        help="Truncate each page text to N chars (0 = no truncation). Helps keep JSON small.",
    )

    parser.add_argument(
        "--try_fix_pdf",
        action="store_true",
        help="If OCR fails, try qpdf fix and retry OCR once (recommended). Requires qpdf installed.",
    )

    args = parser.parse_args()

    pdf_dir = Path(args.pdf_dir).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    ocr_dir = out_dir / "ocr_pdfs"
    force_ocr_dir = out_dir / "ocr_pdfs_force"
    fixed_dir = out_dir / "pdf_fixed"
    txt_dir = out_dir / "texts"

    if not pdf_dir.exists():
        raise FileNotFoundError(f"pdf_dir not found: {pdf_dir}")

    if args.no_ocr and args.do_ocr:
        raise ValueError("Choose either --do_ocr or --no_ocr.")

    do_ocr = args.do_ocr and (not args.no_ocr)

    ocr_bin = None
    if do_ocr:
        ocr_bin = get_ocrmypdf_path()
        print(f"Using ocrmypdf: {ocr_bin}")

    if args.try_fix_pdf and (get_qpdf_path() is None):
        print("NOTE: --try_fix_pdf enabled but qpdf not found. Install via:")
        print("  sudo apt-get install -y qpdf")
        print("Continuing without qpdf fix.")

    pdfs = iter_pdfs(pdf_dir)
    if args.max_files and args.max_files > 0:
        pdfs = pdfs[: args.max_files]

    if not pdfs:
        print(f"No PDFs found under: {pdf_dir}")
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Found {len(pdfs)} PDF(s). do_ocr={do_ocr}. Output -> {out_dir}")

    ok = 0
    fail = 0
    ocr_failed: list[str] = []

    for idx, src_pdf in enumerate(pdfs, start=1):
        rel = src_pdf.relative_to(pdf_dir)
        out_json = (txt_dir / rel).with_suffix(".json")
        out_ocr_pdf = (ocr_dir / rel)

        if out_json.exists() and (not args.overwrite):
            print(f"[{idx}/{len(pdfs)}] SKIP (exists) {rel}")
            ok += 1
            continue

        try:
            print(f"[{idx}/{len(pdfs)}] PROCESS {rel}")

            pdf_to_read = src_pdf
            ocr_used = False
            ocr_error = False
            ocr_error_msg = ""
            ocr_attempted = False
            fixed_attempted = False

            # 1) OCR pass (optional)
            if do_ocr and ocr_bin:
                ocr_attempted = True
                if not out_ocr_pdf.exists() or args.overwrite:
                    success, err = run_ocrmypdf(
                        src_pdf,
                        out_ocr_pdf,
                        ocr_bin,
                        force_ocr=args.force_ocr,
                        clean=args.clean,
                    )
                    if success:
                        ocr_used = True
                    else:
                        ocr_error = True
                        ocr_error_msg = err
                        ocr_failed.append(str(rel))
                        print("  OCR FAILED. Will fallback to original PDF.")
                        if err:
                            print("  OCR stderr (head):", err[:2000].replace("\n", " ")[:500])

                        # Optional: try fix with qpdf then retry OCR once
                        if args.try_fix_pdf and (get_qpdf_path() is not None):
                            fixed_attempted = True
                            fixed_pdf = fixed_dir / rel
                            if fix_pdf_with_qpdf(src_pdf, fixed_pdf):
                                print("  Trying OCR again after qpdf fix...")
                                success2, err2 = run_ocrmypdf(
                                    fixed_pdf,
                                    out_ocr_pdf,
                                    ocr_bin,
                                    force_ocr=args.force_ocr,
                                    clean=args.clean,
                                )
                                if success2:
                                    ocr_used = True
                                    ocr_error = False
                                    ocr_error_msg = ""
                                    print("  OCR succeeded after qpdf fix.")
                                else:
                                    ocr_error_msg = err2 or ocr_error_msg

                if out_ocr_pdf.exists():
                    pdf_to_read = out_ocr_pdf

            # 2) Extract per-page text
            pages = extract_text_by_page(
                pdf_to_read,
                truncate_chars=args.truncate_chars,
                compact=args.compact,
            )
            total_chars, short_pages = text_quality(pages, short_threshold=50)
            print(f"  text_chars={total_chars}, short_pages(<50)={short_pages}/{len(pages)}")

            # 3) Optional retry: if text is too small, force OCR and re-extract
            retried_force_ocr = False
            if do_ocr and ocr_bin and args.min_text_chars and total_chars < args.min_text_chars:
                retry_pdf = (force_ocr_dir / rel.parent / f"{rel.stem}.pdf")
                retry_pdf.parent.mkdir(parents=True, exist_ok=True)
                print(f"  RETRY: text_chars<{args.min_text_chars}, running force OCR -> {retry_pdf}")

                success3, err3 = run_ocrmypdf(
                    src_pdf,
                    retry_pdf,
                    ocr_bin,
                    force_ocr=True,
                    clean=args.clean,
                )
                if success3:
                    retried_force_ocr = True
                    pdf_to_read = retry_pdf
                    pages = extract_text_by_page(
                        pdf_to_read,
                        truncate_chars=args.truncate_chars,
                        compact=args.compact,
                    )
                    total_chars, short_pages = text_quality(pages, short_threshold=50)
                    print(f"  AFTER RETRY: text_chars={total_chars}, short_pages(<50)={short_pages}/{len(pages)}")
                else:
                    print("  Force OCR retry FAILED.")
                    if err3:
                        print("  Retry stderr (head):", err3[:500].replace("\n", " "))

            payload = {
                "source_pdf": str(src_pdf),
                "relative_path": str(rel),
                "processed_at": datetime.now(timezone.utc).isoformat(),

                "ocr_enabled": do_ocr,
                "ocr_attempted": ocr_attempted,
                "ocr_used": ocr_used,
                "ocr_error": ocr_error,
                "ocr_error_msg": ocr_error_msg,
                "force_ocr_flag": bool(args.force_ocr),
                "clean_flag": bool(args.clean),
                "try_fix_pdf_flag": bool(args.try_fix_pdf),
                "fixed_attempted": fixed_attempted,
                "retried_force_ocr": retried_force_ocr,

                "pdf_used_for_text": str(pdf_to_read),
                "num_pages_extracted": len(pages),
                "total_text_chars": total_chars,
                "short_pages": short_pages,

                "compact": bool(args.compact),
                "truncate_chars": int(args.truncate_chars),

                "pages": pages,
            }

            safe_write_json(payload, out_json)
            ok += 1

        except Exception as e:
            fail += 1
            print(f"  FAILED: {rel} -> {type(e).__name__}: {e}")

    if ocr_failed:
        (out_dir / "ocr_failed.txt").write_text("\n".join(ocr_failed), encoding="utf-8")
        print(f"\nOCR failed list -> {out_dir / 'ocr_failed.txt'}")

    print(f"\nDone. ok={ok}, fail={fail}")
    print(f"JSON dumps: {txt_dir}")
    if do_ocr:
        print(f"OCR PDFs:    {ocr_dir}")
        if args.min_text_chars:
            print(f"Force-OCR retries: {force_ocr_dir}")
        if args.try_fix_pdf:
            print(f"Fixed PDFs (qpdf): {fixed_dir}")


if __name__ == "__main__":
    main()