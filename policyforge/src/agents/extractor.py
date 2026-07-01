"""Policy text → structured criteria JSON using LLM with structured outputs."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError

from src.schema import Citation, PolicyCriteria

# Load environment variables from .env
load_dotenv()

logger = logging.getLogger(__name__)

POLICY_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "policies"


def extract_criteria_from_policy(
    policy_path: Path | str,
    *,
    policy_id: str = "NCD_150.3",
    model: str = "gpt-4o-2024-08-06",
) -> PolicyCriteria:
    """
    Extract structured policy criteria from NCD text using OpenAI structured outputs.

    Args:
        policy_path: Path to the policy text file
        policy_id: Policy identifier (e.g., "NCD_150.3")
        model: OpenAI model to use (must support structured outputs)

    Returns:
        PolicyCriteria: Validated Pydantic model with extracted rules

    Raises:
        FileNotFoundError: If policy file doesn't exist
        ValueError: If API key is missing or extraction fails
        ValidationError: If LLM output doesn't match schema
    """
    policy_path = Path(policy_path)
    if not policy_path.exists():
        raise FileNotFoundError(f"Policy file not found: {policy_path}")

    policy_text = policy_path.read_text(encoding="utf-8")
    logger.info("Loaded policy text from %s (%d chars)", policy_path, len(policy_text))

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable required for extraction. "
            "Set it in .env or export OPENAI_API_KEY=..."
        )

    client = OpenAI(api_key=api_key)

    # System prompt for clinical policy extraction
    system_prompt = """You are a medical policy analyst extracting structured coverage rules from Medicare NCDs.

Your task:
1. Identify the **frequency limit** (e.g., "once every 23 months") → extract as integer months
2. Extract all **HCPCS procedure codes** mentioned or referenced
3. Find any **age constraints** (min/max age)
4. List **eligible clinical conditions** (e.g., "estrogen-deficient women", "vertebral abnormalities")
5. Extract **ICD-10 diagnosis codes** if explicitly stated (skip if only condition descriptions)
6. Note **exclusions** (non-covered items)

Be precise. If a field is not explicitly stated, leave it null/empty. For frequency, convert phrases like "once every 2 years" or "at least 23 months" to integer months."""

    user_prompt = f"""Extract structured coverage criteria from this Medicare policy:

POLICY ID: {policy_id}

{policy_text}

Return structured JSON matching the schema."""

    logger.info("Calling OpenAI API with model=%s for structured extraction", model)

    try:
        completion = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=PolicyCriteria,
            temperature=0.0,
        )

        extracted = completion.choices[0].message.parsed
        if extracted is None:
            # Fallback to manual parsing if structured output fails
            raw_content = completion.choices[0].message.content
            if raw_content:
                logger.warning("Structured output was None, parsing raw JSON")
                extracted_dict = json.loads(raw_content)
                extracted = PolicyCriteria(**extracted_dict)
            else:
                raise ValueError("LLM returned no content")

        # Ensure policy_id is set
        if not extracted.policy_id:
            extracted.policy_id = policy_id

        logger.info(
            "Extraction complete: frequency=%s months, HCPCS=%s, conditions=%d",
            extracted.frequency_limit_months,
            extracted.target_hcpcs_codes,
            len(extracted.eligible_conditions),
        )

        return extracted

    except ValidationError as exc:
        logger.error("LLM output failed Pydantic validation: %s", exc)
        raise
    except Exception as exc:
        logger.error("Extraction failed: %s", exc)
        raise ValueError(f"Policy extraction failed: {exc}") from exc


def extract_anchor_policy(*, force: bool = False) -> PolicyCriteria:
    """
    Extract criteria from the anchor policy NCD 150.3 (Bone Mass Measurement).

    Uses cached result from data/policies/NCD_150.3_criteria.json if available,
    unless force=True.
    """
    policy_txt = POLICY_DIR / "NCD_150.3.txt"
    cache_json = POLICY_DIR / "NCD_150.3_criteria.json"

    if cache_json.exists() and not force:
        logger.info("Loading cached criteria from %s", cache_json)
        data = json.loads(cache_json.read_text(encoding="utf-8"))
        return PolicyCriteria(**data)

    criteria = extract_criteria_from_policy(policy_txt, policy_id="NCD_150.3")

    # Cache the result
    POLICY_DIR.mkdir(parents=True, exist_ok=True)
    cache_json.write_text(
        criteria.model_dump_json(indent=2),
        encoding="utf-8",
    )
    logger.info("Cached criteria to %s", cache_json)

    return criteria


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    import sys

    force = "--force" in sys.argv

    criteria = extract_anchor_policy(force=force)
    print("\n" + "=" * 72)
    print("EXTRACTED POLICY CRITERIA")
    print("=" * 72)
    print(criteria.model_dump_json(indent=2))
