"""Enhanced extractor with citation tracking for auditability."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError

from src.schema import Citation, PolicyCriteria

load_dotenv()

logger = logging.getLogger(__name__)

POLICY_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "policies"


def find_text_span(
    source_text: str, search_text: str, context_chars: int = 50
) -> Citation | None:
    """
    Find a text span in the source and return a Citation with character offsets.
    
    Args:
        source_text: Full policy text to search in
        search_text: Text to find (can be partial/fuzzy)
        context_chars: Number of context characters to include
        
    Returns:
        Citation object with character offsets, or None if not found
    """
    # Normalize search text for matching
    search_normalized = search_text.lower().strip()
    
    # Try exact match first
    idx = source_text.lower().find(search_normalized)
    
    if idx == -1:
        # Try finding key phrases
        key_phrases = [
            phrase.strip()
            for phrase in search_normalized.split()
            if len(phrase.strip()) > 3
        ]
        
        for phrase in key_phrases[:3]:  # Try first 3 significant words
            idx = source_text.lower().find(phrase)
            if idx != -1:
                break
    
    if idx == -1:
        logger.warning(f"Could not find citation for: {search_text[:50]}...")
        return None
    
    # Expand to include context
    start = max(0, idx - context_chars)
    end = min(len(source_text), idx + len(search_text) + context_chars)
    
    # Try to find section header
    section = None
    section_pattern = r"\d+\.\d+\.?\d* - [^\n]+"
    text_before = source_text[max(0, start - 200):start]
    section_matches = list(re.finditer(section_pattern, text_before))
    if section_matches:
        section = section_matches[-1].group(0)
    
    return Citation(
        text=source_text[start:end],
        start_char=start,
        end_char=end,
        section=section,
        confidence=1.0 if idx >= 0 else 0.7,
    )


def extract_criteria_with_citations(
    policy_path: Path | str,
    *,
    policy_id: str = "NCD_150.3",
) -> PolicyCriteria:
    """
    Extract policy criteria with source citations for auditability.
    
    This version manually extracts from NCD 150.3 with known citations
    to demonstrate the citation grounding system.
    
    Args:
        policy_path: Path to policy text file
        policy_id: Policy identifier
        
    Returns:
        PolicyCriteria with populated citations
    """
    policy_path = Path(policy_path)
    if not policy_path.exists():
        raise FileNotFoundError(f"Policy file not found: {policy_path}")
    
    policy_text = policy_path.read_text(encoding="utf-8")
    logger.info(f"Loaded policy text from {policy_path} ({len(policy_text)} chars)")
    
    # For NCD 150.3, we know the key facts - extract with citations
    if policy_id == "NCD_150.3":
        # Frequency: 23 months
        freq_citation = find_text_span(
            policy_text,
            "Medicare pays for a screening BMM once every 2 years (at least 23 months have passed"
        )
        
        # HCPCS codes (not in policy text, from coding guidelines)
        hcpcs_citation = Citation(
            text="HCPCS codes 77080 and 77081 are standard procedure codes for bone mass measurement",
            start_char=0,
            end_char=0,
            section="CMS Coding Guidelines (external reference)",
            confidence=0.9,
        )
        
        # Eligible conditions
        conditions_citation = find_text_span(
            policy_text,
            "To be covered, a beneficiary must meet at least one of the five conditions listed below"
        )
        
        # Exclusions
        exclusions_citation = find_text_span(
            policy_text,
            "The following BMMs are noncovered under Medicare because they are not considered reasonable and necessary"
        )
        
        return PolicyCriteria(
            policy_id=policy_id,
            frequency_limit_months=23,
            frequency_citation=freq_citation,
            target_hcpcs_codes=["77080", "77081"],
            hcpcs_citation=hcpcs_citation,
            eligible_conditions=[
                "Estrogen-deficient women at clinical risk for osteoporosis",
                "Individuals with vertebral abnormalities indicative of osteoporosis/osteopenia/fracture",
                "Individuals receiving/expecting glucocorticoid therapy ≥5mg prednisone/day for >3 months",
                "Individuals with primary hyperparathyroidism",
                "Individuals being monitored for FDA-approved osteoporosis drug therapy response",
            ],
            conditions_citation=conditions_citation,
            exclusions=[
                "Single photon absorptiometry (effective January 1, 2007)",
                "Dual photon absorptiometry (established in 1983)",
            ],
            exclusions_citation=exclusions_citation,
        )
    
    else:
        # For other policies, would need LLM extraction
        raise NotImplementedError(f"Citation extraction not yet implemented for {policy_id}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    
    # Test citation extraction
    policy_path = POLICY_DIR / "NCD_150.3.txt"
    criteria = extract_criteria_with_citations(policy_path, policy_id="NCD_150.3")
    
    print("\nExtracted Criteria with Citations:")
    print(f"Policy: {criteria.policy_id}")
    print(f"\nFrequency: {criteria.frequency_limit_months} months")
    if criteria.frequency_citation:
        print(f"  Citation: '{criteria.frequency_citation.text[:100]}...'")
        print(f"  Section: {criteria.frequency_citation.section}")
        print(f"  Chars: {criteria.frequency_citation.start_char}-{criteria.frequency_citation.end_char}")
    
    print(f"\nHCPCS Codes: {criteria.target_hcpcs_codes}")
    if criteria.hcpcs_citation:
        print(f"  Citation: '{criteria.hcpcs_citation.text[:100]}...'")
    
    print(f"\nCitation Grounding Rate: {criteria.get_citation_grounding_rate():.1%}")
