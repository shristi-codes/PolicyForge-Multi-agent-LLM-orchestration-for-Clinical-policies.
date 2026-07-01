"""End-to-end test of the Day 2 core pipeline: extract → compile → adjudicate."""

import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.agents.adjudicator import adjudicate_edit
from src.agents.compiler import compile_criteria_to_edit
from src.agents.extractor import extract_anchor_policy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)


def main():
    """Run the full pipeline on NCD 150.3."""
    print("\n" + "=" * 80)
    print("POLICYFORGE DAY 2 PIPELINE TEST")
    print("=" * 80)

    # Step 1: Extract criteria from policy text
    print("\n[1/3] EXTRACTING policy criteria from NCD 150.3...")
    try:
        criteria = extract_anchor_policy()
        print(f"✓ Extracted criteria successfully")
        print(f"  - Frequency limit: {criteria.frequency_limit_months} months")
        print(f"  - Target HCPCS: {criteria.target_hcpcs_codes}")
        print(f"  - Eligible conditions: {len(criteria.eligible_conditions)}")
    except Exception as exc:
        print(f"✗ Extraction failed: {exc}")
        return 1

    # Step 2: Compile criteria into executable edit
    print("\n[2/3] COMPILING edit logic...")
    try:
        edit = compile_criteria_to_edit(criteria, edit_type="frequency")
        print(f"✓ Compiled edit successfully")
        print(f"  - Policy: {edit.policy_id}")
        print(f"  - Threshold: {edit.threshold_expression}")
    except Exception as exc:
        print(f"✗ Compilation failed: {exc}")
        return 1

    # Step 3: Adjudicate against real Part B data
    print("\n[3/3] ADJUDICATING against CMS Part B data...")
    try:
        flagged = adjudicate_edit(edit)
        print(f"✓ Adjudication complete")
        print(f"  - Total flagged: {len(flagged)} providers")

        if flagged:
            severity_counts = {}
            for p in flagged:
                severity_counts[p.severity] = severity_counts.get(p.severity, 0) + 1

            print(f"\n  Severity breakdown:")
            for sev in ["critical", "high", "medium", "low"]:
                count = severity_counts.get(sev, 0)
                if count > 0:
                    print(f"    {sev.upper():>8}: {count:>4} providers")

            # Show top 5
            print(f"\n  Top 5 flagged providers:")
            for i, p in enumerate(flagged[:5], 1):
                print(
                    f"    {i}. NPI {p.npi}: {p.avg_srvcs_per_bene:.2f} srvcs/bene "
                    f"({p.anomaly_score:.1f}x) [{p.severity}]"
                )
        else:
            print("  No providers flagged (all within policy compliance)")

    except Exception as exc:
        print(f"✗ Adjudication failed: {exc}")
        import traceback

        traceback.print_exc()
        return 1

    print("\n" + "=" * 80)
    print("✓ PIPELINE TEST PASSED")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
