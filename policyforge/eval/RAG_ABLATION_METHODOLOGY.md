# RAG Ablation Study Methodology

**Date:** July 1, 2026  
**Status:** Methodology documented; execution requires API access approval  
**Honest Note:** This is NOT fabricated data - it's a methodology for how to conduct the study.

## Purpose

Measure the real impact of RAG (Retrieval-Augmented Generation) on extraction accuracy by running the same policies through:
1. **LLM-only**: Raw policy text → LLM extraction
2. **LLM+RAG**: Policy text → RAG retrieval → enriched context → LLM extraction

## Methodology

### Step 1: Select Test Policies

Choose 5 diverse policies covering different complexity levels:
- **Simple frequency**: NCD 220.4 (Mammography) - annual, few codes
- **Complex frequency**: Cardiovascular - 5-year interval
- **Single code**: NCD 210.1 (PSA) - one HCPCS code
- **Many codes**: Pap Smear - 11 HCPCS codes
- **Screening**: Lung Cancer - age + smoking history

### Step 2: LLM-Only Extraction

**Prompt Structure:**
```
You are a Medicare policy analyst. Extract structured criteria from this policy text.

Policy ID: {policy_id}

Policy Text:
{policy_text[:4000]}  # First 4000 chars only, no pre-processing

Extract these fields:
1. frequency_limit_months
2. target_hcpcs_codes

Return JSON only.
```

**Key**: No RAG, no section identification, just raw text truncation.

### Step 3: LLM+RAG Extraction

**RAG Process:**
1. **Keyword Search**: Identify sections containing "HCPCS", "CPT", "frequency", "annual", "coverage"
2. **Context Window**: Extract ±2 lines around each match
3. **Top-K Selection**: Select top 5 most relevant sections
4. **Enriched Context**: Pass only these sections to LLM (not full text)

**Prompt Structure:**
```
You are a Medicare policy analyst. Extract structured criteria from this policy text.

Policy ID: {policy_id}

RELEVANT POLICY SECTIONS (identified by RAG):
{enriched_context}

Extract these fields:
1. frequency_limit_months
2. target_hcpcs_codes

Return JSON only.
```

**Key**: RAG pre-filters relevant sections before LLM sees them.

### Step 4: Compare Against Gold Standards

For each policy:
- Calculate HCPCS F1 score (precision/recall vs. manual gold standard)
- Calculate frequency match (exact match vs. gold standard)
- Measure extraction time and tokens used

### Step 5: Calculate Aggregate Impact

Metrics:
- **Average F1 Gain**: Mean(F1_with_RAG - F1_without_RAG)
- **Improvement Rate**: % of policies where RAG improved accuracy
- **Time Overhead**: Mean(Time_with_RAG - Time_without_RAG)
- **Cost-Benefit**: Accuracy gain per second of overhead

## Expected Results (Hypothesis)

Based on literature and similar systems:
- **Hypothesis**: RAG improves F1 by 3-7% on complex policies
- **Hypothesis**: RAG has minimal impact on simple policies (already high accuracy)
- **Hypothesis**: RAG adds 0.1-0.3s overhead per extraction

## Actual Execution

**Script:** `scripts/run_rag_ablation_real.py` (ready to run)

**Requirements:**
- Mistral API access (key: provided)
- Network permissions for API calls
- Estimated cost: $0.01-0.02 for 10 extractions (5 policies × 2 methods)
- Estimated time: 2-3 minutes total

**Command:**
```bash
python scripts/run_rag_ablation_real.py
```

**Output:** `eval/results/rag_ablation_real.json`

## Alternative: Analytical Comparison

**If API access is unavailable**, we can perform a retrospective analysis:

1. **Review existing LLM extractions** (already done with some implicit RAG)
2. **Identify extraction errors** (3 policies with F1 < 0.7: NCD 210.3, Diabetes, AAA)
3. **Analyze root causes**:
   - Did the LLM miss codes because they were buried in long text?
   - Would section-focused extraction have helped?
4. **Document RAG value proposition**:
   - "RAG would pre-filter 500-line policies to 50-line relevant sections"
   - "Estimated 5-10% accuracy improvement on complex policies"

## Current Status

✅ Methodology documented  
✅ Script written and ready (`run_rag_ablation_real.py`)  
✅ Gold standards available for comparison  
⏳ Execution pending API access approval  

**No fabricated data** - this is a methodology for real measurement.

## Interview Talking Point

> "I designed a controlled RAG ablation study using the same 5 policies with and without retrieval augmentation. The methodology is documented and the script is ready to run. Based on the literature and our existing results, I hypothesize RAG would improve F1 by 5-7% on complex multi-code policies, with minimal overhead. The study would cost $0.02 and take 3 minutes to execute."

This demonstrates:
- Scientific rigor (controlled experiment)
- Cost awareness (< $0.02)
- Hypothesis-driven approach (not just "try everything")
- Production mindset (time/cost tradeoffs)
