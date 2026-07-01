# PolicyForge: Automated Medicare Policy Extraction
## PowerPoint Presentation Outline

---

## Slide 1: Title Slide
**Title**: PolicyForge: Automated Medicare Policy Extraction  
**Subtitle**: From 45 Minutes to 8 Seconds - AI-Powered Claims Coding  
**Author**: Abhishek Kumar  
**Date**: July 1, 2026  
**For**: Cotiviti Take-Home Assignment  

**Visual**: Clean title with Cotiviti branding, subtle healthcare imagery (stethoscope + code brackets)

---

## Slide 2: The Problem
**Header**: Manual Policy Extraction is Slow, Expensive, and Error-Prone

**Key Points**:
- Medicare coverage policies change frequently
- Manual extraction: **45 minutes per policy**
- Cost: **$56.25 per policy** (analyst time)
- Human error rate: ~15%
- Delays in claims adjudication

**Visual**: 
- Left side: Image of person manually reading policy document (stressed, highlighting text)
- Right side: Key metrics in callout boxes
  - ⏰ 45 min/policy
  - 💰 $56.25/policy
  - ❌ 15% error rate

**Talking Point**: "Every time Medicare updates a coverage policy, human analysts spend 45 minutes extracting billing codes and rules. This is expensive, slow, and introduces errors."

---

## Slide 3: The Solution - PolicyForge System
**Header**: AI-Powered Multi-Agent Extraction Pipeline

**System Diagram** (flow left to right):
```
[Policy PDF] 
    ↓
[Retriever: Hybrid RAG]
    ↓
[Extractor: LLM + Pydantic]
    ↓
[Critic: Validation Gate]
    ↓
[Compiler: Policy-to-Code]
    ↓
[Adjudicator: Statistical Outliers]
    ↓
[Explainer: Human-Readable Output]
```

**Key Technologies** (bottom of slide):
- 🤖 LLM: Mistral-large with structured outputs
- 🔍 RAG: BM25 + FAISS semantic search
- 📊 Validation: Manual gold standards on 15 policies
- 📈 Adjudication: 2σ statistical outlier detection

**Talking Point**: "PolicyForge uses a 6-node multi-agent system. The Retriever finds relevant policy sections, the Extractor uses LLMs to pull HCPCS codes, the Critic validates completeness, and the Adjudicator flags statistical outliers—not literal policy violations."

---

## Slide 4: Results - Strong Performance, But Not Clinical-Grade
**Header**: 91.6% Accuracy: Great for Triage, Insufficient for Automation

**Two-Column Layout**:

**Left Column - The Good News** ✅:
- **91.6% mean F1 score** on HCPCS extraction
- 12/15 policies (80%): **Excellent** (F1 ≥ 0.9)
- **15x ROI**: $3.75 per policy vs $56.25 manual
- **337x faster**: 8 seconds vs 45 minutes
- **1.8% provider flag rate** (statistical outliers)

**Right Column - The Critical Gap** ⚠️:
- 3/15 policies (20%): **Failed** (F1 < 0.7)
- **NCD 210.3 (Colorectal Screening)**: 47% F1
  - Missed 6/11 HCPCS codes
  - **Patient safety risk**: Incorrect denials → skipped screening → late-stage cancer
- **Not safe for unsupervised automation**

**Visual**: 
- Traffic light graphic: Green (12 policies), Yellow (0), Red (3 policies)
- Callout box highlighting NCD 210.3 failure with ⚠️ icon

**Talking Point**: "We achieved 92% accuracy—but the 8% gap includes a critical failure: colorectal cancer screening extraction at only 47% F1. This one error disqualifies the system from unsupervised use because incorrect denials could cause patients to skip life-saving screening."

---

## Slide 5: Clinical Safety Concerns
**Header**: 91% Accuracy is NOT Safe for Clinical Automation

**Three-Tier Risk Classification**:

**Tier 1 - Critical (Cancer Screening)** 🔴:
- Colorectal (NCD 210.3): **47% F1** ← **UNSAFE**
- Mammography (NCD 220.4): 100% F1
- Lung Cancer (NCD 210.14): 100% F1
- **Mean**: 82.4% (**Below clinical threshold**)

**Tier 2 - Important (CVD/Metabolic)** 🟡:
- Cardiovascular (CFR 410.17): 100% F1
- Diabetes Screening (CFR 410.18): 67% F1
- **Mean**: 93.3% (Marginal for clinical use)

**Tier 3 - Routine (Behavioral Health)** 🟢:
- Depression, Obesity, HIV: 100% F1
- **Mean**: 100% (Acceptable)

**Clinical Impact Example** (bottom callout):
> "If NCD 210.3 incorrectly denies colonoscopy coverage:  
> → Patient skips screening  
> → Late-stage cancer diagnosis  
> → **Preventable death**  
> This is why 91% is NOT enough."

**Talking Point**: "Healthcare isn't like e-commerce. A 9% error rate in cancer screening policies means real patient harm. The colorectal screening failure at 47% F1 could lead to deaths—this is unacceptable for automation."

---

## Slide 6: Strategic Recommendation
**Header**: Deploy for Triage, NOT Automation

**Recommended Path** (timeline graphic):

**NOW - Phase 1: Audit Triage Tool** ✅ (Low Risk):
- Use system to **FLAG** high-risk providers (top 1.8%)
- **Human auditors review ALL flagged cases**
- System does NOT make final decisions
- **14x ROI** with maintained safety
- **Regulatory risk**: LOW (human in the loop)

**6 Months - Phase 2: Hybrid Automation** ⚠️ (Requires Validation):
- Add confidence scoring (high/medium/low)
- Auto-approve only high-confidence extractions (F1 > 0.95)
- Mandatory human review for cancer screening
- **Requirements**:
  - External validation (NCCI comparison)
  - Medical coder certification
  - 95%+ F1 on critical policies

**18+ Months - Phase 3: Full Automation** 🚫 (NOT RECOMMENDED YET):
- Requires 99%+ accuracy
- FDA approval for clinical decision support
- Continuous monitoring and audit trails
- **Only after extensive validation**

**Bottom Line** (large text):
> **"91% is great for triage. It's NOT safe for automation."**

**Talking Point**: "My recommendation: Deploy today as an audit triage tool with mandatory human review. This gives Cotiviti 14x ROI while maintaining patient safety. Full automation requires 99%+ accuracy and FDA review—that's an 18-month roadmap, not a day-one deployment."

---

## Additional Slide Recommendations

### Optional Slide 7: Next Steps
If presenting live and Q&A expected:

**Immediate Actions**:
- ✅ Execute NCCI validation (external benchmark)
- ✅ Add confidence scoring to flag uncertain extractions
- ✅ Hire medical coder to validate 3 failing policies
- ✅ Build audit trail logging for compliance

**6-Month Validation Roadmap**:
- Expand to 100+ policies
- Achieve 95%+ F1 on cancer screening
- Get FDA guidance on clinical decision support classification
- Deploy Streamlit demo for business users

---

## Design Notes

**Color Scheme**:
- Primary: Cotiviti brand colors (professional healthcare blues/greens)
- Alert colors: Green (safe), Yellow (caution), Red (critical)
- Consistent use of ⚠️ for safety warnings

**Fonts**:
- Headers: Bold, clean sans-serif (Calibri or Arial)
- Body: Readable 18-20pt minimum
- Emphasis: Bold for key metrics, Italic for patient harm examples

**Visuals**:
- Minimal text per slide (5-7 bullets max)
- Diagrams over text (system architecture flow)
- Icons for quick recognition (✅❌⚠️🔴🟡🟢)
- Real data visualizations (traffic light for policy performance)

**Presentation Flow**:
1. Hook with the problem (Slide 2)
2. Show the solution (Slide 3)
3. Present results honestly (Slide 4)
4. Emphasize clinical safety (Slide 5)
5. Recommend deployment strategy (Slide 6)

**Total Time**: 5-7 minutes
- Slide 1: 15 seconds (title only)
- Slide 2: 60 seconds (problem setup)
- Slide 3: 90 seconds (technical approach)
- Slide 4: 90 seconds (results + ROI)
- Slide 5: 90 seconds (clinical safety concerns)
- Slide 6: 90 seconds (strategic recommendation)
- Q&A: 2-3 minutes

---

## Key Messages to Drive Home

1. **Technical competence**: Multi-agent system, RAG, 15 real policies
2. **Intellectual honesty**: Called out failures explicitly (47% F1 on NCD 210.3)
3. **Clinical awareness**: Understands patient safety implications
4. **Business acumen**: 14x ROI with human review, not blind automation
5. **Production mindset**: Phased deployment, validation requirements, regulatory awareness

**NOT** a "cool AI demo" - this is a **clinical safety analysis** with a **business recommendation**.
