"""Apply compiled edit logic to CMS Part B data and flag provider outliers."""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import pandas as pd

from src.schema import CompiledEdit, FlaggedProvider, ProviderUtilization

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
PARTB_PARQUET = DATA_DIR / "cms_partb_sample.parquet"


def load_provider_utilization(
    parquet_path: Path | str = PARTB_PARQUET,
) -> list[ProviderUtilization]:
    """
    Load CMS Part B provider utilization data from parquet into typed records.

    Args:
        parquet_path: Path to the filtered Part B parquet file

    Returns:
        List of ProviderUtilization records

    Raises:
        FileNotFoundError: If parquet file doesn't exist
    """
    parquet_path = Path(parquet_path)
    if not parquet_path.exists():
        raise FileNotFoundError(
            f"Part B parquet not found: {parquet_path}. "
            "Run `python -m src.data_pull partb` first."
        )

    con = duckdb.connect()
    df = con.execute(
        f"""
        SELECT 
            CAST(Rndrng_NPI AS VARCHAR) as npi,
            COALESCE(
                Rndrng_Prvdr_Last_Org_Name || ', ' || Rndrng_Prvdr_First_Name,
                Rndrng_Prvdr_Last_Org_Name,
                'Unknown Provider'
            ) as provider_name,
            COALESCE(Rndrng_Prvdr_Type, 'Unknown') as provider_type,
            HCPCS_Cd as hcpcs_cd,
            COALESCE(HCPCS_Desc, '') as hcpcs_desc,
            CAST(Tot_Benes AS INTEGER) as tot_benes,
            CAST(Tot_Srvcs AS INTEGER) as tot_srvcs,
            CAST(Tot_Srvcs AS DOUBLE) / CAST(Tot_Benes AS DOUBLE) as avg_srvcs_per_bene,
            CAST(Avg_Sbmtd_Chrg AS DOUBLE) as avg_sbmtd_chrg,
            CAST(Avg_Mdcr_Alowd_Amt AS DOUBLE) as avg_mdcr_alowd_amt,
            CAST(Avg_Mdcr_Pymt_Amt AS DOUBLE) as avg_mdcr_pymt_amt
        FROM read_parquet('{parquet_path.as_posix()}')
        WHERE Tot_Benes IS NOT NULL 
          AND Tot_Srvcs IS NOT NULL
          AND CAST(Tot_Benes AS INTEGER) > 0
        """
    ).fetchdf()
    con.close()

    logger.info("Loaded %d provider-HCPCS records from %s", len(df), parquet_path)

    records = [ProviderUtilization(**row) for row in df.to_dict(orient="records")]
    return records


def adjudicate_frequency_edit(
    edit: CompiledEdit,
    utilization_data: list[ProviderUtilization] | None = None,
    *,
    parquet_path: Path | str = PARTB_PARQUET,
) -> list[FlaggedProvider]:
    """
    Apply frequency-based compiled edit to provider utilization data.

    Args:
        edit: Compiled edit with filter logic
        utilization_data: Pre-loaded utilization records (optional)
        parquet_path: Path to Part B parquet (used if utilization_data is None)

    Returns:
        List of flagged providers sorted by anomaly score (descending)

    Raises:
        FileNotFoundError: If parquet doesn't exist and no data provided
        ValueError: If edit criteria is missing frequency_limit_months
    """
    if not edit.criteria.frequency_limit_months:
        raise ValueError(
            f"Edit {edit.policy_id} has no frequency_limit_months; cannot adjudicate"
        )

    freq_months = edit.criteria.frequency_limit_months
    expected_annual = 12.0 / freq_months

    if utilization_data is None:
        utilization_data = load_provider_utilization(parquet_path)

    logger.info("Adjudicating %d provider records against edit", len(utilization_data))

    # Extract threshold from threshold_expression (parse "avg_srvcs_per_bene > X")
    threshold_str = edit.threshold_expression.split(">")[1].split()[0]
    threshold = float(threshold_str)

    flagged: list[FlaggedProvider] = []

    for record in utilization_data:
        if record.hcpcs_cd not in edit.criteria.target_hcpcs_codes:
            continue

        if record.tot_benes < 11:  # CMS redaction threshold
            continue

        if record.avg_srvcs_per_bene <= threshold:
            continue

        # Calculate anomaly score: ratio of actual to expected frequency
        anomaly_score = record.avg_srvcs_per_bene / expected_annual

        # Severity classification
        if anomaly_score >= 4.0:
            severity = "critical"
        elif anomaly_score >= 3.0:
            severity = "high"
        elif anomaly_score >= 2.0:
            severity = "medium"
        else:
            severity = "low"

        flag_reason = (
            f"Provider billed {record.tot_srvcs} {record.hcpcs_cd} services "
            f"for {record.tot_benes} beneficiaries "
            f"(avg {record.avg_srvcs_per_bene:.2f} services/bene). "
            f"Policy allows once per {freq_months} months "
            f"(~{expected_annual:.2f} services/bene/year expected). "
            f"Utilization is {anomaly_score:.1f}x expected."
        )

        flagged.append(
            FlaggedProvider(
                npi=record.npi,
                provider_name=record.provider_name,
                provider_type=record.provider_type,
                hcpcs_cd=record.hcpcs_cd,
                tot_benes=record.tot_benes,
                tot_srvcs=record.tot_srvcs,
                avg_srvcs_per_bene=record.avg_srvcs_per_bene,
                flag_reason=flag_reason,
                anomaly_score=anomaly_score,
                severity=severity,
            )
        )

    # Sort by anomaly score descending
    flagged.sort(key=lambda p: p.anomaly_score, reverse=True)

    logger.info(
        "Flagged %d providers (%.1f%% of %d total)",
        len(flagged),
        100.0 * len(flagged) / len(utilization_data) if utilization_data else 0,
        len(utilization_data),
    )

    return flagged


def adjudicate_edit(
    edit: CompiledEdit,
    utilization_data: list[ProviderUtilization] | None = None,
    **kwargs,
) -> list[FlaggedProvider]:
    """
    Apply compiled edit to utilization data and return flagged providers.

    Routes to appropriate adjudication logic based on edit type.

    Args:
        edit: Compiled edit with filter logic
        utilization_data: Pre-loaded utilization records (optional)
        **kwargs: Additional parameters for specific adjudicators

    Returns:
        List of flagged providers

    Raises:
        ValueError: If edit type cannot be determined
    """
    # Infer edit type from criteria
    if edit.criteria.frequency_limit_months:
        return adjudicate_frequency_edit(edit, utilization_data, **kwargs)
    else:
        raise ValueError("Cannot determine edit type from criteria")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

    from src.agents.compiler import compile_criteria_to_edit
    from src.agents.extractor import extract_anchor_policy

    # Run full pipeline: extract → compile → adjudicate
    logger.info("=== POLICY EXTRACTION ===")
    criteria = extract_anchor_policy()

    logger.info("\n=== EDIT COMPILATION ===")
    edit = compile_criteria_to_edit(criteria, edit_type="frequency")

    logger.info("\n=== ADJUDICATION ===")
    flagged = adjudicate_edit(edit)

    print("\n" + "=" * 72)
    print(f"FLAGGED PROVIDERS: {len(flagged)} total")
    print("=" * 72)

    # Show top 10 by severity
    for i, provider in enumerate(flagged[:10], 1):
        print(f"\n{i}. NPI {provider.npi} ({provider.provider_type})")
        print(f"   Name: {provider.provider_name}")
        print(f"   HCPCS: {provider.hcpcs_cd}")
        print(
            f"   Utilization: {provider.tot_srvcs} services / {provider.tot_benes} benes "
            f"= {provider.avg_srvcs_per_bene:.2f} srvcs/bene"
        )
        print(
            f"   Anomaly: {provider.anomaly_score:.2f}x expected | Severity: {provider.severity.upper()}"
        )

    # Summary by severity
    severity_counts = {}
    for p in flagged:
        severity_counts[p.severity] = severity_counts.get(p.severity, 0) + 1

    print("\n" + "=" * 72)
    print("SEVERITY DISTRIBUTION")
    print("=" * 72)
    for sev in ["critical", "high", "medium", "low"]:
        count = severity_counts.get(sev, 0)
        pct = 100.0 * count / len(flagged) if flagged else 0
        print(f"{sev.upper():>10}: {count:>5} ({pct:>5.1f}%)")
