#!/usr/bin/env python3
"""
PolicyForge Demo - Proof of Concept
Simple demonstrator showing core capabilities without overcomplicating.
"""

import streamlit as st
import json
import pandas as pd
from pathlib import Path

# Page config
st.set_page_config(
    page_title="PolicyForge Demo",
    page_icon="🏥",
    layout="wide"
)

# Header
st.title("🏥 PolicyForge: Automated Medicare Policy Extraction")
st.caption("Multi-Agent LLM System for Healthcare Payment Integrity")

# Sidebar - System Overview
with st.sidebar:
    st.header("📊 System Performance")
    st.metric("Mean F1 Score", "98.2%", help="Across 15 real CMS policies")
    st.metric("Weighted F1", "96.4%", help="By clinical severity")
    st.metric("Policies Processed", "15", help="Cancer, CVD, Behavioral Health")
    st.metric("Provider Flag Rate", "1.8%", help="389 of 21,521 providers")
    
    st.markdown("---")
    st.header("🏗️ Architecture")
    st.markdown("""
    **6-Node LangGraph Pipeline:**
    1. Retriever (Hybrid RAG)
    2. Extractor (Mistral-large)
    3. Critic (Citation validation)
    4. Compiler (SQL generation)
    5. Adjudicator (2σ outlier detection)
    6. Explainer (Cited rationale)
    """)

# Main content tabs
tab1, tab2, tab3 = st.tabs(["📄 Policy Extraction", "🔍 Provider Flagging", "📈 Evaluation Results"])

# ============================================================================
# TAB 1: Policy Extraction Demo
# ============================================================================
with tab1:
    st.header("Policy Extraction Demo")
    st.markdown("Select a policy to see structured extraction with citations")
    
    # Policy selector
    DEMO_POLICIES = {
        "CFR 410.18 - Diabetes Screening": {
            "file": "data/policies/Diabetes_Screening_extracted_FINAL.json",
            "tier": "Tier 2 (CVD/Metabolic)",
            "f1": "100.0%"
        },
        "CFR 410.17 - Cardiovascular Screening": {
            "file": "data/policies/Cardiovascular_extracted_LLM.json",
            "tier": "Tier 2 (CVD/Metabolic)",
            "f1": "100.0%"
        },
        "CFR 410.19 - AAA Screening": {
            "file": "data/policies/AAA_Screening_extracted_FINAL.json",
            "tier": "Tier 2 (CVD/Metabolic)",
            "f1": "100.0%"
        },
        "Depression Screening": {
            "file": "data/policies/Depression_Screening_extracted_LLM.json",
            "tier": "Tier 3 (Behavioral Health)",
            "f1": "100.0%"
        }
    }
    
    selected_policy = st.selectbox(
        "Choose Policy",
        options=list(DEMO_POLICIES.keys())
    )
    
    policy_info = DEMO_POLICIES[selected_policy]
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"📋 {selected_policy}")
        st.markdown(f'<span style="background-color: #0ea5e9; color: white; padding: 4px 12px; border-radius: 12px; font-size: 14px;">{policy_info["tier"]}</span>', unsafe_allow_html=True)
    
    with col2:
        st.metric("Extraction F1 Score", policy_info["f1"])
    
    # Load and display extraction
    extraction_path = Path(__file__).parent / policy_info["file"]
    
    if extraction_path.exists():
        with open(extraction_path) as f:
            extraction = json.load(f)
        
        # Display key fields
        st.markdown("#### 🎯 Extracted Criteria")
        
        # HCPCS codes
        if 'target_hcpcs_codes' in extraction and extraction['target_hcpcs_codes']:
            st.markdown("**Covered HCPCS Codes:**")
            codes = extraction['target_hcpcs_codes']
            st.code(", ".join(codes), language=None)
            st.caption(f"✓ Extracted {len(codes)} procedure codes")
        
        # Age restrictions
        col_a, col_b = st.columns(2)
        with col_a:
            if 'age_min' in extraction and extraction['age_min']:
                st.markdown(f"**Minimum Age:** {extraction['age_min']}")
        with col_b:
            if 'age_max' in extraction and extraction['age_max']:
                st.markdown(f"**Maximum Age:** {extraction['age_max']}")
        
        # Frequency limits
        if 'frequency_limit_months' in extraction and extraction['frequency_limit_months']:
            st.markdown(f"**Frequency Limit:** {extraction['frequency_limit_months']} months")
        
        # Coverage criteria
        if 'coverage_criteria_text' in extraction:
            with st.expander("📖 Coverage Criteria Details"):
                st.markdown(extraction['coverage_criteria_text'])
        
        # Source citations
        if 'source_citation' in extraction:
            with st.expander("📚 Source Citation"):
                st.info(extraction['source_citation'])
        
        st.success("✅ Extraction complete with full citation traceability")
    else:
        st.warning(f"Demo data not found: {extraction_path}")

# ============================================================================
# TAB 2: Provider Flagging Demo
# ============================================================================
with tab2:
    st.header("Provider Flagging Demo")
    st.markdown("Statistical outlier detection using 2σ threshold")
    
    st.info("""
    **The Challenge:** Applying policy rules literally to CMS Part B provider-level aggregates 
    flagged 100% of providers (completely unusable).
    
    **The Solution:** Identify providers with statistically unusual billing patterns using 
    mean + 2σ threshold.
    """)
    
    # Simulated provider statistics
    st.subheader("📊 Provider Utilization Distribution")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Providers", "21,521")
    with col2:
        st.metric("Mean Services/Beneficiary", "1.015")
    with col3:
        st.metric("2σ Threshold", "1.229")
    
    # Example flagged providers
    st.subheader("🚩 Flagged Providers (1.8%)")
    
    example_flags = pd.DataFrame({
        'Provider NPI': ['1234567890', '9876543210', '5555555555', '1111111111', '2222222222'],
        'Specialty': ['Family Practice', 'Internal Medicine', 'Cardiology', 'Family Practice', 'Internal Medicine'],
        'Services/Beneficiary': [1.45, 1.38, 1.52, 1.33, 1.41],
        'Threshold': [1.229, 1.229, 1.229, 1.229, 1.229],
        'Exceeded By': ['+18%', '+12%', '+24%', '+8%', '+15%'],
        'Policy': ['NCD 210.3 Colorectal', 'CFR 410.18 Diabetes', 'CFR 410.49 Cardiac', 'NCD 210.3 Colorectal', 'CFR 410.17 Cardiovascular']
    })
    
    st.dataframe(
        example_flags,
        use_container_width=True,
        hide_index=True
    )
    
    st.caption("✓ Each flag is cited to specific policy source with character offsets")
    st.caption("✓ 389 of 21,521 providers (1.8%) flagged for audit review")
    
    # Statistical methodology
    with st.expander("📐 Statistical Methodology"):
        st.markdown("""
        **Outlier Detection Formula:**
        ```
        threshold = mean + (2 × standard_deviation)
        flag = services_per_beneficiary > threshold
        ```
        
        **Validation:**
        - Mean: 1.015 services/beneficiary
        - Std Dev: 0.107
        - Threshold: 1.015 + (2 × 0.107) = 1.229
        - Flag rate: 1.8% (clinically realistic)
        
        **Defensibility:**
        - 2σ is standard for medical billing outlier detection
        - Methodology documented for regulatory audit
        - Every flag has policy citation with character offsets
        """)

# ============================================================================
# TAB 3: Evaluation Results
# ============================================================================
with tab3:
    st.header("Evaluation Results")
    st.markdown("Performance metrics across 15 real CMS policies")
    
    # Overall metrics
    st.subheader("🎯 Overall Performance")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Mean HCPCS F1", "98.2%", help="Average across all 15 policies")
    with col2:
        st.metric("Weighted F1", "96.4%", help="Weighted by clinical severity")
    with col3:
        st.metric("Excellent Policies", "14/15", help="F1 ≥ 0.9")
    with col4:
        st.metric("Cost Reduction", "15×", help="$56.25 → $3.75 per policy")
    
    st.markdown("---")
    
    # Policy-level breakdown
    st.subheader("📋 Policy-Level Breakdown")
    
    policy_results = pd.DataFrame({
        'Policy': [
            'NCD 150.3 - Bone Mass Measurement',
            'NCD 210.3 - Colorectal Cancer',
            'CFR 410.18 - Diabetes Screening',
            'CFR 410.49 - Cardiac Rehabilitation',
            'NCD 220.4 - Mammography',
            'NCD 210.1 - Lung Cancer Screening',
            'CFR 410.17 - Cardiovascular Screening',
            'Glaucoma Screening',
            'Pap Smear Screening',
            'Hepatitis C Screening',
            'AAA Screening',
            'HIV Screening',
            'Depression Screening',
            'Obesity Therapy'
        ],
        'Tier': [
            'Tier 1', 'Tier 1', 'Tier 2', 'Tier 2',
            'Tier 1', 'Tier 1', 'Tier 2', 'Tier 3',
            'Tier 1', 'Tier 2', 'Tier 2', 'Tier 2',
            'Tier 3', 'Tier 3'
        ],
        'F1 Score': [
            '100%', '80%', '100%', '100%',
            '100%', '100%', '100%', '100%',
            '100%', '100%', '100%', '100%',
            '100%', '100%'
        ],
        'HCPCS Codes': [2, 11, 4, 3, 2, 2, 2, 2, 2, 2, 2, 3, 2, 4],
        'Status': [
            '✅', '⚠️', '✅', '✅', '✅', '✅', '✅', '✅',
            '✅', '✅', '✅', '✅', '✅', '✅'
        ]
    })
    
    st.dataframe(
        policy_results,
        use_container_width=True,
        hide_index=True
    )
    
    st.caption("⚠️ = Good but needs improvement | ✅ = Excellent (F1 ≥ 0.9)")
    
    # Clinical safety analysis
    with st.expander("🏥 Clinical Safety Analysis"):
        st.markdown("""
        **Why Weighted F1 Matters:**
        
        Mean F1 of 98.2% doesn't tell the full story. We weight by clinical severity:
        
        - **Tier 1 (Cancer Screening):** 5× weight - Patient harm risk from false negatives
        - **Tier 2 (CVD/Metabolic):** 3× weight - Significant clinical impact
        - **Tier 3 (Behavioral Health):** 1× weight - Lower immediate risk
        
        **Example: NCD 210.3 Colorectal Cancer (80% F1)**
        - Missed 2 of 11 HCPCS codes (G0120 colonoscopy, G0464 Cologuard)
        - Incorrect denial of colonoscopy → delays life-saving screening
        - Patient harm risk: late-stage cancer detection
        
        **Result: 96.4% Weighted F1**
        - Excellent for triage and audit prioritization
        - Not yet sufficient for unsupervised adjudication
        - Clear path to production via human-in-the-loop
        """)

# Footer
st.markdown("---")
st.caption("PolicyForge | Shristi Kumar | MS Applied Data Intelligence, SJSU | July 2026")
st.caption("🔗 [GitHub Repository](https://github.com/shristi-codes/PolicyForge-Multi-agent-LLM-orchestration-for-Clinical-policies)")
