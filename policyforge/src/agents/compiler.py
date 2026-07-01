"""Criteria JSON → executable edit logic (Python/SQL filter expressions)."""

from __future__ import annotations

import logging
from typing import Literal

from src.schema import CompiledEdit, PolicyCriteria

logger = logging.getLogger(__name__)


def compile_frequency_edit(
    criteria: PolicyCriteria,
    *,
    threshold_multiplier: float = 1.5,
) -> CompiledEdit:
    """
    Compile frequency-based policy criteria into executable provider-level filter logic.

    For NCD 150.3 BMM: Medicare covers once every 23 months. At the provider-level
    utilization summary (aggregated over a calendar year), we flag providers whose
    average services per beneficiary significantly exceeds the policy-expected frequency.

    Args:
        criteria: Extracted policy criteria
        threshold_multiplier: Flag providers with avg_srvcs_per_bene > (12/freq_months * multiplier)

    Returns:
        CompiledEdit: Executable filter logic and threshold expression

    Raises:
        ValueError: If frequency_limit_months is not set
    """
    if not criteria.frequency_limit_months:
        raise ValueError(
            f"Policy {criteria.policy_id} has no frequency_limit_months; "
            "cannot compile frequency edit"
        )

    freq_months = criteria.frequency_limit_months
    hcpcs_codes = criteria.target_hcpcs_codes or []

    # Expected annual frequency: 12 months / 23 months ≈ 0.52 services per bene per year
    expected_annual_freq = 12.0 / freq_months

    # Flag threshold: expected * multiplier
    threshold = expected_annual_freq * threshold_multiplier

    # DuckDB/Pandas filter expression
    hcpcs_filter = (
        f"HCPCS_Cd IN ({', '.join(repr(c) for c in hcpcs_codes)})"
        if hcpcs_codes
        else "TRUE"
    )

    filter_logic = f"""
-- Filter to relevant HCPCS codes
WHERE {hcpcs_filter}
  AND Tot_Benes >= 11  -- CMS redaction threshold
  AND (CAST(Tot_Srvcs AS DOUBLE) / CAST(Tot_Benes AS DOUBLE)) > {threshold}
""".strip()

    threshold_expression = (
        f"avg_srvcs_per_bene > {threshold:.4f}  "
        f"(expected: {expected_annual_freq:.4f}, policy: once per {freq_months} months)"
    )

    description = (
        f"Frequency edit for {criteria.policy_id}: "
        f"Flag providers billing HCPCS {hcpcs_codes} at rates exceeding "
        f"{threshold:.2f} services/beneficiary/year "
        f"(policy allows once every {freq_months} months = ~{expected_annual_freq:.2f}/year). "
        f"Threshold = {threshold_multiplier}x expected frequency."
    )

    logger.info(
        "Compiled frequency edit: threshold=%.4f srvcs/bene (policy: once per %d months)",
        threshold,
        freq_months,
    )

    return CompiledEdit(
        policy_id=criteria.policy_id,
        criteria=criteria,
        filter_logic=filter_logic,
        threshold_expression=threshold_expression,
        description=description,
    )


def compile_criteria_to_edit(
    criteria: PolicyCriteria,
    *,
    edit_type: Literal["frequency", "age", "diagnosis"] = "frequency",
    **kwargs,
) -> CompiledEdit:
    """
    Compile policy criteria into an executable edit based on rule type.

    Args:
        criteria: Extracted policy criteria
        edit_type: Type of edit to compile
        **kwargs: Additional parameters passed to specific compilers

    Returns:
        CompiledEdit: Executable edit logic

    Raises:
        ValueError: If edit_type is not supported or criteria is incomplete
    """
    if edit_type == "frequency":
        return compile_frequency_edit(criteria, **kwargs)
    elif edit_type == "age":
        raise NotImplementedError("Age-based edits not yet implemented")
    elif edit_type == "diagnosis":
        raise NotImplementedError("Diagnosis-based edits not yet implemented")
    else:
        raise ValueError(f"Unknown edit_type: {edit_type}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Example: compile the anchor policy criteria
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

    from src.agents.extractor import extract_anchor_policy

    criteria = extract_anchor_policy()
    edit = compile_criteria_to_edit(criteria, edit_type="frequency")

    print("\n" + "=" * 72)
    print("COMPILED EDIT")
    print("=" * 72)
    print(f"Policy: {edit.policy_id}")
    print(f"Description: {edit.description}")
    print(f"\nThreshold: {edit.threshold_expression}")
    print(f"\nFilter Logic:\n{edit.filter_logic}")
