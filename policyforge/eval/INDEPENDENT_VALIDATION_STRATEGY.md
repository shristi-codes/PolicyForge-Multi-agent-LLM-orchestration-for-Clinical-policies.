# Independent Validation Strategy

**Date:** July 1, 2026  
**Purpose:** Validate PolicyForge extractions against external ground truth  
**Status:** Methodology documented; ready for implementation

## Overview

To reach 90th percentile, the project needs **independent validation** - comparing our extractions against authoritative external sources or independent human annotators.

## Validation Option 1: NCCI Edits Comparison (Recommended)

### What is NCCI?

The **National Correct Coding Initiative (NCCI)** is CMS's official coding policy system. It contains:
- Procedure code pairs that cannot be billed together
- Medically Unlikely Edits (MUEs) - frequency/quantity limits
- Official coverage rules tied to HCPCS codes

### Why NCCI is the Gold Standard

- **Authoritative**: Published by CMS, used by all Medicare contractors
- **Comprehensive**: Covers thousands of HCPCS codes
- **Machine-Readable**: Available as structured files (Excel/CSV)
- **Updated Quarterly**: Reflects current policy

### How to Access NCCI

**Source**: [CMS NCCI Downloads](https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-ncci/ncci-medicare-downloads)

**Files Needed:**
- Practitioner PTP Edits (Procedure-to-Procedure)
- MUE Tables (Medically Unlikely Edits)

**Cost**: Free

### Validation Methodology

For each PolicyForge extraction:

1. **Extract NCCI rules** for the same HCPCS codes
2. **Compare frequency limits**: Does PolicyForge's `frequency_limit_months` match NCCI's MUE?
3. **Calculate agreement rate**: 
   ```python
   agreement = matching_policies / total_policies
   ```
4. **Report discrepancies**: Document where PolicyForge differs from NCCI and why

**Example:**

```python
# PolicyForge extraction for NCD 220.4 (Mammography)
policyforge = {
    "target_hcpcs_codes": ["77065", "77066", "77067"],
    "frequency_limit_months": 12
}

# NCCI MUE for 77067
ncci = {
    "hcpcs_code": "77067",
    "mue_value": 1,  # 1 per day
    "frequency": "annual"  # 11 months minimum
}

# Comparison
agreement = (policyforge["frequency_limit_months"] == 12) and (ncci["frequency"] == "annual")
# Result: ✅ MATCH
```

### Expected Results

- **High agreement** (85-95%) on simple frequency-based rules
- **Lower agreement** (70-80%) on complex condition-based rules (NCCI doesn't capture all clinical logic)
- **Discrepancies** where PolicyForge correctly interprets NCD text but NCCI uses different encoding

### Implementation Script

**Filename**: `scripts/validate_against_ncci.py`

**Pseudocode:**
```python
def validate_against_ncci():
    # 1. Download NCCI MUE file
    ncci_data = load_ncci_mue_file()
    
    # 2. Load PolicyForge extractions
    policyforge_data = load_extractions()
    
    # 3. For each policy
    for policy in policyforge_data:
        for hcpcs in policy['target_hcpcs_codes']:
            # Find NCCI rule
            ncci_rule = ncci_data.get(hcpcs)
            
            # Compare
            if ncci_rule:
                agreement = compare_frequency(
                    policy['frequency_limit_months'],
                    ncci_rule['frequency']
                )
                results.append({
                    'policy': policy['id'],
                    'hcpcs': hcpcs,
                    'agreement': agreement
                })
    
    # 4. Calculate aggregate agreement rate
    total_agreement = sum(r['agreement'] for r in results) / len(results)
    
    return total_agreement
```

**Time to Implement**: 2-3 hours  
**Cost**: $0 (NCCI files are free)

---

## Validation Option 2: Inter-Annotator Agreement

### Concept

Have a **second independent person** manually extract criteria from the same policies, then measure agreement between:
- PolicyForge LLM extraction
- Your manual extraction (gold standard)
- Second annotator's extraction

### Methodology

1. **Select 5 representative policies**
2. **Provide second annotator with**:
   - Policy text files
   - Extraction instructions (same as you used)
   - JSON schema to fill out
3. **Do NOT show them**:
   - PolicyForge's LLM extractions
   - Your gold standards
4. **Measure agreement** using Cohen's Kappa:
   ```python
   kappa = (observed_agreement - chance_agreement) / (1 - chance_agreement)
   ```

### Expected Results

- **Kappa > 0.8**: Excellent agreement (extraction task is well-defined)
- **Kappa 0.6-0.8**: Good agreement (some subjective interpretation)
- **PolicyForge vs. Annotator**: Should match at 80-85% if both are accurate

### Who to Ask

- Classmate/peer reviewer
- Healthcare informatics student
- Online annotation service (e.g., Amazon MTurk - costs $5-10)

### Example Output

```json
{
  "validation_method": "inter_annotator_agreement",
  "policies_validated": 5,
  "annotators": ["You (gold standard)", "Peer Annotator A"],
  "agreement_metrics": {
    "cohens_kappa": 0.83,
    "raw_agreement": 0.89,
    "interpretation": "Excellent agreement"
  },
  "policyforge_vs_annotator": {
    "hcpcs_agreement": 0.87,
    "frequency_agreement": 0.80
  },
  "conclusion": "PolicyForge extractions match independent human annotator 87% of the time"
}
```

**Time to Implement**: 3-4 hours (including annotator time)  
**Cost**: $0 (peer) or $5-10 (paid service)

---

## Validation Option 3: Production Claims Data (Advanced)

### Concept

If you have access to **real Medicare claims data**, validate extractions by:
1. Apply PolicyForge rules to actual claims
2. Compare against **known adjudication results** from CMS
3. Measure precision/recall of flagged claims

### Why This is Gold Standard

- Uses real-world data (not synthetic)
- Tests end-to-end pipeline (extraction → compilation → adjudication)
- Directly measures business impact

### Requirements

- Access to CMS claims data (e.g., via university research agreement)
- Known adjudication outcomes (approved/denied claims)

**Estimated Time**: 10-20 hours  
**Cost**: Varies (data access agreements)

**Feasibility**: Low for a take-home project, but excellent interview talking point

---

## Recommended Approach for This Project

**Best ROI**: **NCCI Validation** (Option 1)

Why:
- ✅ Authoritative external source (not self-validation)
- ✅ Free and publicly available
- ✅ Achievable in 2-3 hours
- ✅ Demonstrates industry awareness (knowing NCCI exists)
- ✅ Honest comparison (will show ~85-90% agreement, not 100%)

**Second Best**: **Inter-Annotator Agreement** (Option 2)

Why:
- ✅ Independent validation
- ✅ Low cost
- ✅ Measures task difficulty (if kappa is low, extraction is inherently hard)

---

## Current Status

✅ Validation strategies documented  
✅ NCCI methodology designed  
⏳ Implementation pending (2-3 hours work)  
⏳ NCCI file download required  

**No fabricated data** - these are real validation approaches.

---

## Interview Talking Point

> "To validate PolicyForge's extractions independently, I would compare against CMS's official NCCI edits. NCCI publishes medically unlikely edit (MUE) tables quarterly that define frequency limits for thousands of HCPCS codes. I'd download the current MUE file, match our extracted HCPCS codes, and calculate agreement rate on frequency limits. Based on the complexity of our policies, I'd expect 85-90% agreement - with discrepancies reflecting where NCD text provides more nuanced rules than NCCI's simplified tables. This demonstrates that PolicyForge correctly interprets policy language, not just matches obvious patterns."

This shows:
- **Industry knowledge** (knows NCCI exists and its role)
- **Honest expectations** (85-90%, not 100%)
- **Critical thinking** (can explain discrepancies)
- **Production mindset** (compares to operational ground truth)
