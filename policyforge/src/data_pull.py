"""Fetch and filter real CMS / OIG datasets into data/."""

from __future__ import annotations

import html
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import duckdb
import requests
from pypdf import PdfReader

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
POLICIES_DIR = DATA_DIR / "policies"
NCCI_DIR = DATA_DIR / "ncci_edits"
PARTB_PARQUET = DATA_DIR / "cms_partb_sample.parquet"
LEIE_CSV = DATA_DIR / "leie.csv"

# Anchor policy for v1 — Bone Mass Measurement
ANCHOR_POLICY_ID = "NCD_150.3"
ANCHOR_NCD_DOCUMENT_ID = "256"
ANCHOR_HCPCS = ["77080", "77081"]

CMS_COVERAGE_API = "https://api.coverage.cms.gov/v1"
CMS_DATA_CATALOG = "https://data.cms.gov/data.json"
PARTB_DATASET_ID = "92396110-2aed-4d63-a6a2-5d6207d46a29"
PARTB_DATASET_IDENTIFIER = (
    f"https://data.cms.gov/data-api/v1/dataset/{PARTB_DATASET_ID}/data-viewer"
)
BENEFIT_POLICY_MANUAL_PDF = (
    "https://www.cms.gov/Regulations-and-Guidance/Guidance/Transmittals/downloads/R70BP.pdf"
)

NCD_TEXT_FIELDS = (
    "title",
    "benefit_category",
    "item_service_description",
    "indications_limitations",
    "cross_reference",
    "revision_history",
    "other_text",
    "reasons_for_denial",
)

SECTION_80_5_START = re.compile(r"80\.5\s+-\s+Bone Mass Measurements", re.IGNORECASE)
SECTION_80_6_START = re.compile(r"80\.6\s+-", re.IGNORECASE)


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "PolicyForge/1.0 (Cotiviti intern assessment; educational use)",
            "Accept": "application/json, text/plain, */*",
        }
    )
    return session


def _strip_html(text: str) -> str:
    if not text:
        return ""
    decoded = html.unescape(text)
    decoded = decoded.replace("&sol;", "/")
    decoded = re.sub(r"<br\s*/?>", "\n", decoded, flags=re.IGNORECASE)
    decoded = re.sub(r"</p>", "\n\n", decoded, flags=re.IGNORECASE)
    decoded = re.sub(r"<[^>]+>", "", decoded)
    decoded = re.sub(r"\n{3,}", "\n\n", decoded)
    return decoded.strip()


def _download_file(
    url: str,
    dest: Path,
    *,
    force: bool = False,
    chunk_size: int = 8 * 1024 * 1024,
    timeout: tuple[int, int] = (30, 600),
) -> Path:
    """Stream-download *url* to *dest*, skipping if cached unless *force*."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0 and not force:
        logger.info("Using cached file: %s (%d bytes)", dest, dest.stat().st_size)
        return dest

    logger.info("Downloading %s -> %s", url, dest)
    session = _session()
    with session.get(url, stream=True, timeout=timeout) as response:
        response.raise_for_status()
        total = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        with dest.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                handle.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    if downloaded == len(chunk) or pct % 10 == 0:
                        logger.info(
                            "  %d / %d bytes (%.0f%%)", downloaded, total, pct
                        )

    logger.info("Download complete: %s (%d bytes)", dest, dest.stat().st_size)
    return dest


def _fetch_ncd_record(ncd_document_id: str = ANCHOR_NCD_DOCUMENT_ID) -> dict[str, Any]:
    """Fetch NCD metadata and text fields from the CMS Coverage API."""
    url = f"{CMS_COVERAGE_API}/data/ncd/?ncdid={ncd_document_id}"
    response = _session().get(url, timeout=60)
    response.raise_for_status()
    payload = response.json()
    records = payload.get("data") or []
    if not records:
        raise RuntimeError(f"No NCD record returned for ncdid={ncd_document_id}")
    return records[0]


def _extract_section_80_5_from_pdf(pdf_path: Path) -> str:
    """Extract Medicare Benefit Policy Manual §80.5 from the R70BP transmittal."""
    reader = PdfReader(str(pdf_path))
    full_text = "\n".join(page.extract_text() or "" for page in reader.pages)

    matches = list(SECTION_80_5_START.finditer(full_text))
    if not matches:
        raise RuntimeError("Section 80.5 not found in benefit policy manual PDF")

    # Use the last table-of-contents hit so we land in the body text.
    start = matches[-1].start()
    end_match = SECTION_80_6_START.search(full_text, start + 1)
    end = end_match.start() if end_match else len(full_text)
    section = full_text[start:end].strip()
    section = re.sub(r"\n{3,}", "\n\n", section)
    return section


def _format_ncd_text(ncd: dict[str, Any], benefit_policy_section: str) -> str:
    """Render a single plain-text policy document for RAG / extraction."""
    lines = [
        f"National Coverage Determination {ncd.get('document_display_id', '')}",
        f"Title: {ncd.get('title', '')}",
        f"Publication: {ncd.get('publication_number', '')}",
        f"Effective date: {ncd.get('effective_date', '')}",
        f"Benefit category: {_strip_html(ncd.get('benefit_category', ''))}",
        "",
        "=" * 72,
        "NCD SUMMARY (CMS Medicare Coverage Database)",
        "=" * 72,
        "",
    ]

    for field in NCD_TEXT_FIELDS:
        if field in {"title", "benefit_category"}:
            continue
        raw = ncd.get(field, "")
        cleaned = _strip_html(raw)
        if not cleaned:
            continue
        heading = field.replace("_", " ").title()
        lines.extend([heading, "-" * len(heading), cleaned, ""])

    lines.extend(
        [
            "=" * 72,
            "MEDICARE BENEFIT POLICY MANUAL — Chapter 15, Section 80.5",
            "(Pub. 100-02; extracted from CMS Transmittal R70BP)",
            "=" * 72,
            "",
            benefit_policy_section,
            "",
            "=" * 72,
            "SOURCE REFERENCES",
            "=" * 72,
            f"- NCD viewer: https://www.cms.gov/medicare-coverage-database/view/ncd.aspx?ncdid={ncd.get('document_id', ANCHOR_NCD_DOCUMENT_ID)}",
            f"- Coverage API: {CMS_COVERAGE_API}/data/ncd/?ncdid={ncd.get('document_id', ANCHOR_NCD_DOCUMENT_ID)}",
            f"- Benefit Policy Manual PDF: {BENEFIT_POLICY_MANUAL_PDF}",
        ]
    )
    return "\n".join(lines)


def pull_anchor_policy(*, force: bool = False) -> Path:
    """
    Download NCD 150.3 (Bone Mass Measurement) and the referenced §80.5 manual text.

    The NCD itself points to Pub. 100-02 §80.5 for coverage conditions; this function
    combines both sources into ``data/policies/NCD_150.3.txt`` plus a JSON sidecar.
    """
    POLICIES_DIR.mkdir(parents=True, exist_ok=True)
    text_path = POLICIES_DIR / "NCD_150.3.txt"
    json_path = POLICIES_DIR / "NCD_150.3.json"
    pdf_path = RAW_DIR / "R70BP_benefit_policy_manual.pdf"

    if text_path.exists() and json_path.exists() and not force:
        logger.info("Using cached policy: %s", text_path)
        return text_path

    logger.info("Fetching NCD 150.3 from CMS Coverage API...")
    ncd = _fetch_ncd_record()

    logger.info("Downloading Medicare Benefit Policy Manual transmittal (R70BP)...")
    _download_file(BENEFIT_POLICY_MANUAL_PDF, pdf_path, force=force)
    section_80_5 = _extract_section_80_5_from_pdf(pdf_path)

    policy_text = _format_ncd_text(ncd, section_80_5)
    text_path.write_text(policy_text, encoding="utf-8")

    sidecar = {
        "policy_id": ANCHOR_POLICY_ID,
        "document_id": ncd.get("document_id"),
        "document_display_id": ncd.get("document_display_id"),
        "title": ncd.get("title"),
        "effective_date": ncd.get("effective_date"),
        "sources": {
            "coverage_api": f"{CMS_COVERAGE_API}/data/ncd/?ncdid={ANCHOR_NCD_DOCUMENT_ID}",
            "benefit_policy_manual_pdf": BENEFIT_POLICY_MANUAL_PDF,
        },
        "hcpcs_codes": ANCHOR_HCPCS,
    }
    json_path.write_text(json.dumps(sidecar, indent=2), encoding="utf-8")

    logger.info("Saved policy text (%d chars) -> %s", len(policy_text), text_path)
    return text_path


def _resolve_partb_csv_url() -> str:
    """Resolve the latest Part B provider-and-service CSV URL from data.cms.gov."""
    response = _session().get(CMS_DATA_CATALOG, timeout=60)
    response.raise_for_status()
    catalog = response.json()

    target_title = "Medicare Physician & Other Practitioners - by Provider and Service"

    for dataset in catalog.get("dataset", []):
        title = dataset.get("title", "")
        identifier = dataset.get("identifier", "")
        if title != target_title and PARTB_DATASET_ID not in identifier:
            continue

        csv_urls: list[tuple[str, str]] = []
        for dist in dataset.get("distribution", []):
            url = dist.get("downloadURL", "")
            dist_title = dist.get("title", "")
            if url.endswith(".csv"):
                csv_urls.append((dist_title, url))
        if not csv_urls:
            raise RuntimeError(f"No CSV distributions found for dataset: {title}")

        csv_urls.sort(key=lambda item: item[0], reverse=True)
        latest_title, latest_url = csv_urls[0]
        logger.info("Resolved Part B CSV: %s", latest_title)
        return latest_url

    raise RuntimeError(
        "Could not resolve Medicare Part B CSV URL from data.cms.gov catalog"
    )


def _fetch_partb_via_api(hcpcs_codes: list[str]) -> Path:
    """
    Fallback: paginate the CMS Data API for each HCPCS code and write parquet via DuckDB.

    Used when the full CSV download is unavailable; still produces the same parquet schema.
    """
    base_url = f"https://data.cms.gov/data-api/v1/dataset/{PARTB_DATASET_ID}/data"
    session = _session()
    rows: list[dict[str, Any]] = []
    page_size = 5000

    for code in hcpcs_codes:
        offset = 0
        while True:
            params = urlencode(
                {
                    "filter[HCPCS_Cd]": code,
                    "size": page_size,
                    "offset": offset,
                }
            )
            url = f"{base_url}?{params}"
            logger.info("API fetch HCPCS %s offset=%d", code, offset)
            response = session.get(url, timeout=120)
            response.raise_for_status()
            batch = response.json()
            if not batch:
                break
            rows.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size

    if not rows:
        raise RuntimeError(f"No Part B rows returned for HCPCS codes: {hcpcs_codes}")

    con = duckdb.connect()
    con.register("partb_rows", rows)
    PARTB_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    con.execute(
        f"""
        COPY (SELECT * FROM partb_rows)
        TO '{PARTB_PARQUET.as_posix()}' (FORMAT PARQUET)
        """
    )
    count = con.execute("SELECT COUNT(*) FROM partb_rows").fetchone()[0]
    con.close()
    logger.info("Wrote %d rows via API fallback -> %s", count, PARTB_PARQUET)
    return PARTB_PARQUET


def filter_partb_utilization(
    hcpcs_codes: list[str] | None = None,
    *,
    force_download: bool = False,
    prefer_api: bool = False,
) -> Path:
    """
    Filter CMS Part B utilization to anchor HCPCS codes and write parquet.

    Primary path: download the public CSV (cached under ``data/raw/``) and filter with
    DuckDB. Fallback: paginate the CMS Data API when ``prefer_api=True`` or the CSV
    download fails.
    """
    codes = hcpcs_codes or ANCHOR_HCPCS
    codes = [code.strip() for code in codes if code.strip()]
    if not codes:
        raise ValueError("At least one HCPCS code is required")

    PARTB_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    if PARTB_PARQUET.exists() and not force_download:
        logger.info("Using cached parquet: %s", PARTB_PARQUET)
        return PARTB_PARQUET

    if prefer_api:
        return _fetch_partb_via_api(codes)

    csv_path = RAW_DIR / "cms_partb_by_provider_and_service.csv"
    try:
        csv_url = _resolve_partb_csv_url()
        _download_file(csv_url, csv_path, force=force_download)
    except Exception as exc:
        logger.warning("CSV download failed (%s); falling back to CMS Data API", exc)
        return _fetch_partb_via_api(codes)

    codes_sql = ", ".join(f"'{code}'" for code in codes)
    csv_posix = csv_path.as_posix()
    parquet_posix = PARTB_PARQUET.as_posix()
    logger.info("Filtering CSV with DuckDB for HCPCS in (%s)...", ", ".join(codes))

    con = duckdb.connect()
    try:
        count = con.execute(
            f"""
            SELECT COUNT(*) FROM read_csv_auto('{csv_posix}', header=true)
            WHERE HCPCS_Cd IN ({codes_sql})
            """
        ).fetchone()[0]
        logger.info("Matched %d rows", count)
        if count == 0:
            raise RuntimeError(
                f"DuckDB filter returned 0 rows for HCPCS codes: {codes}"
            )

        con.execute(
            f"""
            COPY (
                SELECT *
                FROM read_csv_auto('{csv_posix}', header=true)
                WHERE HCPCS_Cd IN ({codes_sql})
            )
            TO '{parquet_posix}' (FORMAT PARQUET)
            """
        )
    finally:
        con.close()

    logger.info("Wrote filtered Part B sample -> %s", PARTB_PARQUET)
    return PARTB_PARQUET


def pull_ncci_edits(*, force: bool = False) -> Path:
    """Download NCCI ground-truth edits. TODO: implement in a later phase."""
    NCCI_DIR.mkdir(parents=True, exist_ok=True)
    raise NotImplementedError("NCCI download not yet implemented")


def pull_leie(*, force: bool = False) -> Path:
    """Download OIG LEIE exclusions list. TODO: implement in a later phase."""
    raise NotImplementedError("LEIE download not yet implemented")


def pull_all(*, force: bool = False, prefer_api: bool = False) -> dict[str, Path]:
    """Run anchor-policy and Part B data pulls."""
    return {
        "policy": pull_anchor_policy(force=force),
        "partb": filter_partb_utilization(force_download=force, prefer_api=prefer_api),
    }


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


if __name__ == "__main__":
    _configure_logging()
    force = "--force" in sys.argv
    prefer_api = "--api" in sys.argv

    if len(sys.argv) > 1 and sys.argv[1] not in {"--force", "--api"}:
        command = sys.argv[1]
        if command == "policy":
            path = pull_anchor_policy(force=force)
            print(f"Policy saved: {path}")
        elif command == "partb":
            path = filter_partb_utilization(force_download=force, prefer_api=prefer_api)
            print(f"Part B parquet: {path}")
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
    else:
        results = pull_all(force=force, prefer_api=prefer_api)
        for name, path in results.items():
            print(f"{name}: {path}")
