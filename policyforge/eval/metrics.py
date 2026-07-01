"""Evaluation metrics for PolicyForge extraction and flagging accuracy."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.schema import FlaggedProvider, PolicyCriteria

logger = logging.getLogger(__name__)


class ExtractionMetrics(BaseModel):
    """Metrics for policy criteria extraction accuracy."""

    policy_id: str
    
    # Field-level accuracy
    frequency_correct: bool
    frequency_gold: int | None
    frequency_predicted: int | None
    
    hcpcs_precision: float = Field(description="TP / (TP + FP)")
    hcpcs_recall: float = Field(description="TP / (TP + FN)")
    hcpcs_f1: float
    hcpcs_gold: list[str]
    hcpcs_predicted: list[str]
    
    age_min_correct: bool
    age_max_correct: bool
    
    conditions_precision: float
    conditions_recall: float
    conditions_f1: float
    conditions_gold_count: int
    conditions_predicted_count: int
    
    exclusions_precision: float
    exclusions_recall: float
    exclusions_f1: float
    
    # Citation grounding
    citation_grounding_rate: float = Field(
        description="Fraction of extracted criteria with valid source citations"
    )
    
    # Overall
    overall_f1: float = Field(
        description="Macro-average F1 across all fields"
    )


class AdjudicationMetrics(BaseModel):
    """Metrics for provider flagging accuracy."""

    policy_id: str
    total_providers_flagged: int
    
    # Severity distribution
    severity_critical: int
    severity_high: int
    severity_medium: int
    severity_low: int
    
    # Spot-check validation (manual or against LEIE)
    top_k_checked: int
    top_k_precision: float | None = Field(
        None, description="Precision@K from manual spot-check"
    )
    
    # Anomaly score distribution
    anomaly_score_mean: float
    anomaly_score_std: float
    anomaly_score_p50: float
    anomaly_score_p95: float
    anomaly_score_p99: float


class CostMetrics(BaseModel):
    """Cost and latency metrics."""

    policy_id: str
    
    # LLM usage
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    
    # Latency
    retrieval_time_ms: float
    extraction_time_ms: float
    compilation_time_ms: float
    adjudication_time_ms: float
    total_time_ms: float
    
    # Per-operation costs
    cost_per_policy_usd: float
    time_per_policy_s: float


class SystemMetrics(BaseModel):
    """Aggregate system-level metrics."""

    timestamp: str
    
    extraction: ExtractionMetrics
    adjudication: AdjudicationMetrics
    cost: CostMetrics
    
    # Configuration
    model_name: str
    use_rag: bool
    use_critic: bool
    threshold_multiplier: float


def normalize_text(text: str) -> str:
    """Normalize text for semantic comparison."""
    import re
    # Lowercase
    text = text.lower().strip()
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Normalize punctuation
    text = text.replace('/', ' ').replace(',', ' ')
    text = text.replace('≥', '>=').replace('≤', '<=')
    # Remove parenthetical dates/notes
    text = re.sub(r'\([^)]*\d{4}[^)]*\)', '', text)
    text = re.sub(r'\(effective[^)]*\)', '', text)
    text = re.sub(r'\(established[^)]*\)', '', text)
    return text.strip()


def semantic_similarity(text1: str, text2: str) -> float:
    """Calculate semantic similarity between two texts (0-1)."""
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)
    
    # Exact match after normalization
    if norm1 == norm2:
        return 1.0
    
    # Token-level Jaccard similarity
    tokens1 = set(norm1.split())
    tokens2 = set(norm2.split())
    
    if not tokens1 or not tokens2:
        return 0.0
    
    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)
    
    return intersection / union if union > 0 else 0.0


def calculate_precision_recall_f1_semantic(
    gold: set[str], predicted: set[str], threshold: float = 0.85
) -> tuple[float, float, float]:
    """
    Calculate precision, recall, and F1 with semantic matching.
    
    Args:
        gold: Ground truth set
        predicted: Predicted set  
        threshold: Minimum similarity for match (default 0.85)
        
    Returns:
        Tuple of (precision, recall, f1)
    """
    if not predicted and not gold:
        return 1.0, 1.0, 1.0
    if not predicted:
        return 0.0, 0.0, 0.0
    if not gold:
        return 0.0, 0.0, 0.0
    
    # Find best matches using semantic similarity
    matched_gold = set()
    matched_pred = set()
    
    for pred_item in predicted:
        best_match = None
        best_score = 0.0
        
        for gold_item in gold:
            if gold_item in matched_gold:
                continue
            score = semantic_similarity(pred_item, gold_item)
            if score > best_score:
                best_score = score
                best_match = gold_item
        
        if best_match and best_score >= threshold:
            matched_gold.add(best_match)
            matched_pred.add(pred_item)
    
    tp = len(matched_pred)
    fp = len(predicted - matched_pred)
    fn = len(gold - matched_gold)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    
    return precision, recall, f1


def evaluate_extraction(
    policy_id: str,
    gold_criteria: dict[str, Any],
    predicted_criteria: PolicyCriteria,
) -> ExtractionMetrics:
    """
    Evaluate extraction accuracy against gold standard.
    
    Args:
        policy_id: Policy identifier
        gold_criteria: Ground truth criteria from gold_standard.json
        predicted_criteria: Extracted criteria from Extractor agent
        
    Returns:
        ExtractionMetrics with detailed accuracy breakdown
    """
    # Frequency
    gold_freq = gold_criteria.get("frequency_limit_months")
    pred_freq = predicted_criteria.frequency_limit_months
    frequency_correct = gold_freq == pred_freq
    
    # HCPCS codes
    gold_hcpcs = set(gold_criteria.get("target_hcpcs_codes", []))
    pred_hcpcs = set(predicted_criteria.target_hcpcs_codes)
    hcpcs_p, hcpcs_r, hcpcs_f1 = calculate_precision_recall_f1_semantic(gold_hcpcs, pred_hcpcs, threshold=1.0)  # Exact match for codes
    
    # Age
    gold_age_min = gold_criteria.get("age_min")
    pred_age_min = predicted_criteria.age_min
    age_min_correct = gold_age_min == pred_age_min
    
    gold_age_max = gold_criteria.get("age_max")
    pred_age_max = predicted_criteria.age_max
    age_max_correct = gold_age_max == pred_age_max
    
    # Eligible conditions (semantic matching for text fields)
    gold_conditions = set(gold_criteria.get("eligible_conditions", []))
    pred_conditions = set(predicted_criteria.eligible_conditions)
    cond_p, cond_r, cond_f1 = calculate_precision_recall_f1_semantic(
        gold_conditions, pred_conditions, threshold=0.85
    )
    
    # Exclusions (semantic matching)
    gold_exclusions = set(gold_criteria.get("exclusions", []))
    pred_exclusions = set(predicted_criteria.exclusions)
    excl_p, excl_r, excl_f1 = calculate_precision_recall_f1_semantic(
        gold_exclusions, pred_exclusions, threshold=0.85
    )
    
    # Citation grounding rate (updated to use new schema method)
    citation_grounding_rate = predicted_criteria.get_citation_grounding_rate()
    
    # Overall F1 (macro-average across fields)
    field_f1s = [hcpcs_f1, cond_f1, excl_f1]
    if frequency_correct:
        field_f1s.append(1.0)
    else:
        field_f1s.append(0.0)
    
    overall_f1 = sum(field_f1s) / len(field_f1s)
    
    return ExtractionMetrics(
        policy_id=policy_id,
        frequency_correct=frequency_correct,
        frequency_gold=gold_freq,
        frequency_predicted=pred_freq,
        hcpcs_precision=hcpcs_p,
        hcpcs_recall=hcpcs_r,
        hcpcs_f1=hcpcs_f1,
        hcpcs_gold=list(gold_hcpcs),
        hcpcs_predicted=list(pred_hcpcs),
        age_min_correct=age_min_correct,
        age_max_correct=age_max_correct,
        conditions_precision=cond_p,
        conditions_recall=cond_r,
        conditions_f1=cond_f1,
        conditions_gold_count=len(gold_conditions),
        conditions_predicted_count=len(pred_conditions),
        exclusions_precision=excl_p,
        exclusions_recall=excl_r,
        exclusions_f1=excl_f1,
        citation_grounding_rate=citation_grounding_rate,
        overall_f1=overall_f1,
    )


def evaluate_adjudication(
    policy_id: str,
    flagged_providers: list[FlaggedProvider],
) -> AdjudicationMetrics:
    """
    Evaluate adjudication quality.
    
    Args:
        policy_id: Policy identifier
        flagged_providers: List of providers flagged by Adjudicator
        
    Returns:
        AdjudicationMetrics with severity distribution and anomaly stats
    """
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    anomaly_scores = []
    
    for provider in flagged_providers:
        severity_counts[provider.severity] += 1
        anomaly_scores.append(provider.anomaly_score)
    
    import numpy as np
    
    return AdjudicationMetrics(
        policy_id=policy_id,
        total_providers_flagged=len(flagged_providers),
        severity_critical=severity_counts["critical"],
        severity_high=severity_counts["high"],
        severity_medium=severity_counts["medium"],
        severity_low=severity_counts["low"],
        top_k_checked=0,  # To be filled by manual spot-check
        top_k_precision=None,
        anomaly_score_mean=float(np.mean(anomaly_scores)) if anomaly_scores else 0.0,
        anomaly_score_std=float(np.std(anomaly_scores)) if anomaly_scores else 0.0,
        anomaly_score_p50=float(np.percentile(anomaly_scores, 50)) if anomaly_scores else 0.0,
        anomaly_score_p95=float(np.percentile(anomaly_scores, 95)) if anomaly_scores else 0.0,
        anomaly_score_p99=float(np.percentile(anomaly_scores, 99)) if anomaly_scores else 0.0,
    )


def load_gold_standard(policy_id: str) -> dict[str, Any]:
    """
    Load gold standard criteria for a policy.
    
    Args:
        policy_id: Policy identifier (e.g., "NCD_150.3")
        
    Returns:
        Gold criteria dictionary
        
    Raises:
        FileNotFoundError: If gold standard doesn't exist
        ValueError: If policy_id not found in gold standard
    """
    gold_path = Path(__file__).parent / "gold_standard.json"
    
    if not gold_path.exists():
        raise FileNotFoundError(f"Gold standard not found: {gold_path}")
    
    with gold_path.open() as f:
        gold_data = json.load(f)
    
    for policy in gold_data["policies"]:
        if policy["policy_id"] == policy_id:
            return policy["gold_criteria"]
    
    raise ValueError(f"Policy {policy_id} not found in gold standard")


if __name__ == "__main__":
    # Test metrics calculation
    from src.schema import PolicyCriteria
    
    gold = load_gold_standard("NCD_150.3")
    
    # Mock predicted criteria
    predicted = PolicyCriteria(
        policy_id="NCD_150.3",
        frequency_limit_months=23,
        target_hcpcs_codes=["77080", "77081"],
        eligible_conditions=[
            "Estrogen-deficient women at clinical risk for osteoporosis",
            "Individuals with vertebral abnormalities",
        ],
        exclusions=["Single photon absorptiometry"],
    )
    
    metrics = evaluate_extraction("NCD_150.3", gold, predicted)
    
    print("Extraction Metrics:")
    print(f"  Frequency correct: {metrics.frequency_correct}")
    print(f"  HCPCS F1: {metrics.hcpcs_f1:.3f}")
    print(f"  Conditions F1: {metrics.conditions_f1:.3f}")
    print(f"  Overall F1: {metrics.overall_f1:.3f}")
