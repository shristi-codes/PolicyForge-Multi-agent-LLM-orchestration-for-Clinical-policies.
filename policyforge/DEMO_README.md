# PolicyForge Demo - Quick Start Guide

## Overview
Simple proof-of-concept demonstrator showing PolicyForge's core capabilities:
- Policy extraction with 98.2% F1 accuracy
- Provider flagging with 1.8% flag rate
- Full citation traceability

## Running the Demo

### 1. Install Dependencies
```bash
cd policyforge
pip install streamlit pandas
```

### 2. Launch the Demo
```bash
streamlit run demo_app.py
```

The demo will open in your browser at `http://localhost:8501`

## Demo Features

### Tab 1: Policy Extraction
- Select from 4 example policies
- View structured extraction results
- See HCPCS codes, age restrictions, frequency limits
- Full citation traceability

### Tab 2: Provider Flagging
- Statistical outlier detection (2σ method)
- Example flagged providers
- Shows 1.8% flag rate (389 of 21,521 providers)
- Defensible methodology for audit

### Tab 3: Evaluation Results
- 98.2% mean F1 across 15 policies
- 96.4% weighted F1 by clinical severity
- Policy-level breakdown
- Clinical safety analysis

## Architecture

**6-Node LangGraph Pipeline:**
1. **Retriever** - Hybrid RAG (BM25 + FAISS)
2. **Extractor** - Mistral-large with structured outputs
3. **Critic** - Citation validation with span-level grounding
4. **Compiler** - SQL generation from criteria
5. **Adjudicator** - 2σ outlier detection
6. **Explainer** - Cited rationale for flags

## Key Metrics

- **Speed:** 8 seconds vs 45 minutes per policy
- **Cost:** $3.75 vs $56.25 per policy (15× reduction)
- **Accuracy:** 98.2% F1 (mean), 96.4% F1 (weighted)
- **Scale:** 15 policies, 21,521 providers
- **Flag Rate:** 1.8% (clinically realistic)

## Video Demo Tips

For screen recording:
1. Start with Tab 1 - show policy extraction
2. Select different policies to show variety
3. Switch to Tab 2 - explain the 100% → 1.8% breakthrough
4. Show Tab 3 - highlight clinical safety analysis
5. Total demo time: 3-4 minutes

## Notes

- This is a proof-of-concept demonstrator (not production-ready)
- Loads pre-computed results for speed
- Demonstrates core capabilities without overcomplicating
- Focus on engineering principles and methodology
