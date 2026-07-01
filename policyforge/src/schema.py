"""Pydantic schemas for policy criteria, citations, and compiled edits."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """Verbatim policy span with character offsets for auditability."""

    text: str = Field(
        ..., 
        description="Exact verbatim text from policy document"
    )
    start_char: int = Field(
        ..., 
        description="Starting character position in policy text"
    )
    end_char: int = Field(
        ..., 
        description="Ending character position in policy text"
    )
    section: str | None = Field(
        None, 
        description="Policy section identifier (e.g., '80.5.5 - Frequency Standards')"
    )
    confidence: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for this citation (0-1)"
    )


class PolicyCriteria(BaseModel):
    """Structured criteria extracted from a coverage policy with citations."""

    policy_id: str
    
    # Frequency criteria
    frequency_limit_months: int | None = Field(
        None,
        description="Minimum months between covered procedures (e.g., 23 for BMM)",
    )
    frequency_citation: Citation | None = Field(
        None,
        description="Source citation for frequency limit",
    )
    
    # Procedure codes
    target_hcpcs_codes: list[str] = Field(
        default_factory=list,
        description="HCPCS procedure codes covered by this policy",
    )
    hcpcs_citation: Citation | None = Field(
        None,
        description="Source citation for HCPCS codes",
    )
    
    # Age constraints
    age_min: int | None = Field(None, description="Minimum beneficiary age")
    age_max: int | None = Field(None, description="Maximum beneficiary age")
    age_citation: Citation | None = Field(
        None,
        description="Source citation for age constraints",
    )
    
    # Eligible conditions
    eligible_conditions: list[str] = Field(
        default_factory=list,
        description="Clinical conditions that make beneficiaries eligible",
    )
    conditions_citation: Citation | None = Field(
        None,
        description="Source citation for eligible conditions",
    )
    
    # ICD-10 diagnoses
    eligible_icd10_diagnoses: list[str] = Field(
        default_factory=list,
        description="ICD-10 diagnosis codes (if explicitly stated)",
    )
    icd10_citation: Citation | None = Field(
        None,
        description="Source citation for ICD-10 codes",
    )
    
    # Exclusions
    exclusions: list[str] = Field(
        default_factory=list,
        description="Explicitly non-covered items or circumstances",
    )
    exclusions_citation: Citation | None = Field(
        None,
        description="Source citation for exclusions",
    )
    
    # Legacy field for backward compatibility
    citations: list[Citation] = Field(
        default_factory=list,
        description="Additional source text spans (legacy field)",
    )
    
    def get_citation_grounding_rate(self) -> float:
        """Calculate fraction of non-null criteria that have citations."""
        total_criteria = 0
        cited_criteria = 0
        
        # Check each field that has a value
        if self.frequency_limit_months is not None:
            total_criteria += 1
            if self.frequency_citation is not None:
                cited_criteria += 1
        
        if self.target_hcpcs_codes:
            total_criteria += 1
            if self.hcpcs_citation is not None:
                cited_criteria += 1
        
        if self.age_min is not None or self.age_max is not None:
            total_criteria += 1
            if self.age_citation is not None:
                cited_criteria += 1
        
        if self.eligible_conditions:
            total_criteria += 1
            if self.conditions_citation is not None:
                cited_criteria += 1
        
        if self.eligible_icd10_diagnoses:
            total_criteria += 1
            if self.icd10_citation is not None:
                cited_criteria += 1
        
        if self.exclusions:
            total_criteria += 1
            if self.exclusions_citation is not None:
                cited_criteria += 1
        
        return cited_criteria / total_criteria if total_criteria > 0 else 0.0


class CompiledEdit(BaseModel):
    """Executable edit logic compiled from policy criteria."""

    policy_id: str
    criteria: PolicyCriteria
    filter_logic: str = Field(
        ..., description="Python/SQL expression for filtering claims"
    )
    threshold_expression: str = Field(
        ..., description="Analytical threshold for flagging outliers"
    )
    description: str = Field(..., description="Human-readable edit description")


class ProviderUtilization(BaseModel):
    """Provider-level utilization metrics from CMS Part B data."""

    npi: str
    provider_name: str
    provider_type: str
    hcpcs_cd: str
    hcpcs_desc: str
    tot_benes: int
    tot_srvcs: int
    avg_srvcs_per_bene: float
    avg_sbmtd_chrg: float
    avg_mdcr_alowd_amt: float
    avg_mdcr_pymt_amt: float


class FlaggedProvider(BaseModel):
    """Provider flagged by the adjudicator with policy-cited rationale."""

    npi: str
    provider_name: str
    provider_type: str
    hcpcs_cd: str
    tot_benes: int
    tot_srvcs: int
    avg_srvcs_per_bene: float
    flag_reason: str
    anomaly_score: float = Field(
        ..., description="Quantitative deviation metric (e.g., services/bene ratio)"
    )
    severity: Literal["low", "medium", "high", "critical"] = Field(
        ..., description="Risk severity based on anomaly magnitude"
    )
    citations: list[Citation] = Field(default_factory=list)


ClauseLabel = Literal[
    "frequency", "age", "diagnosis", "procedure", "exclusion", "other"
]
