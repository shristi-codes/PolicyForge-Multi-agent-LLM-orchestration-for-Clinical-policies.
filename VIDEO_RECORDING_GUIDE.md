# PolicyForge Video Recording Guide - COMPREHENSIVE DETAILED SCRIPT

## 📋 Assessment Requirements Alignment

**Topic 3: Content Management in Health Care** - Conversion of Written Policy into Programming Languages, Rules, Features, or Models

**Evaluation Criteria:**
- ✅ Technological competency demonstration
- ✅ Clear vocal presentation
- ✅ Professional visual presence  
- ✅ Speed to value ("satisfice")

**Target Time: 5-7 minutes** (detailed but concise)

---

## 🎬 DETAILED VIDEO SCRIPT

### SECTION 1: Introduction & Problem Statement (60 seconds)

**[Camera: On, centered]**  
**[Screen: Demo opening / Title slide]**

> "Hello, I'm Shristi Kumar, Master's student in Applied Data Intelligence at San José State University. Today I'm presenting PolicyForge - a multi-agent LLM system that addresses Topic 3 of the Cotiviti intern assessment: converting written Medicare coverage policies into executable payment integrity rules.

**[Pause]**

> The problem is significant: Medicare FFS improper payments exceed $30 billion annually. Payers must continuously monitor thousands of National Coverage Determinations and Local Coverage Determinations from CMS. These are dense regulatory documents written in clinical and legal prose.

**[Screen: Show demo sidebar with metrics]**

> Converting these policies into executable claim edits requires extracting specific billing codes - HCPCS codes - along with frequency limits, age restrictions, and clinical conditions. This extraction is time-intensive and error-prone.

**[Pause for emphasis]**

> My solution automates this extraction using a 6-node multi-agent LLM pipeline, achieving 98.2% F1 accuracy across 15 real CMS policies, with a clear path to production deployment."

---

### SECTION 2: Architecture & Technical Implementation (90 seconds)

**[Screen: Tab 1 - Policy Extraction OR show architecture diagram if available]**

> "Let me explain the technical architecture. PolicyForge implements a LangGraph-based orchestration of six specialized agents working in sequence.

**[Point to sidebar showing "6-Node LangGraph Pipeline"]**

> **First, the Retriever agent** uses hybrid RAG - combining BM25 lexical search with FAISS semantic embeddings. This is important because policy documents reference medical terminology that requires both exact term matching AND semantic understanding. For example, 'diabetes mellitus' and 'T2DM' need to be recognized as related concepts.

> **Second, the Extractor agent** uses Mistral-large LLM with Pydantic-enforced structured outputs. Rather than getting free-form text back from the LLM, I enforce a strict JSON schema. This ensures I always get parseable HCPCS codes, frequency limits in months, and age ranges - never ambiguous natural language.

> **Third, the Critic agent** validates extraction completeness. If critical fields are missing, it sends the extraction back through the loop. This is crucial because an incomplete extraction could lead to incorrect claim denials.

**[Show demo - select a policy]**

> Let me demonstrate with CFR 410.18 - Diabetes Screening. 

**[Click: Diabetes Screening policy]**

> The system has extracted four HCPCS codes that Medicare covers for diabetes screening. You can see the frequency limit: 12 months for high-risk patients. And here - 

**[Expand: Coverage Criteria Details]**

> The full coverage criteria including risk factors like prior diagnosis of pre-diabetes or metabolic syndrome.

**[Expand: Source Citation]**

> Most importantly - every extracted element has character-level citations back to the source policy text. This is essential for regulatory audit. If a claim is denied based on this extraction, the provider can see exactly which policy language justifies that decision.

**[Pause]**

> **Fourth, the Compiler agent** translates these criteria into executable DuckDB SQL queries. **Fifth, the Adjudicator** applies these queries to real CMS Part B provider utilization data. And **sixth, the Explainer** generates human-readable audit reports.

**[Quick clicks through different policies]**

> The system works across different policy types - cardiovascular screening, behavioral health, cancer screening - each with different rule structures."

---

### SECTION 3: The Engineering Breakthrough - Data Granularity Problem (90 seconds)

**[Screen: Tab 2 - Provider Flagging]**

> "Now let me discuss the most important engineering challenge I encountered - one that almost derailed the entire project.

**[Point to the "Problem" section]**

> When I first applied the extracted policy rules to the CMS Part B dataset, the system flagged 100% of providers. Every single one. The system appeared completely broken.

**[Pause for emphasis]**

> Here's what I discovered: the CMS Part B data I had access to contained provider-level aggregates, not individual claim-level transactions. 

> For example, NCD 150.3 - Bone Mass Measurements - states: 'No more than one screening per 23 months for the same beneficiary.' But my data only showed: Provider billed an average of 1.0 bone mass measurements per beneficiary.

> I couldn't determine if INDIVIDUAL beneficiaries were being screened too frequently. I only knew the AVERAGE across all of that provider's patients.

**[Point to Solution section]**

> Rather than abandoning the project, I reframed the problem entirely. Instead of trying to enforce procedure-level compliance - which requires claim-level data I don't have - I pivoted to **statistical outlier detection**.

**[Point to metrics]**

> The question became: which providers have billing patterns that are statistically unusual compared to their peers?

> I calculated the mean services per beneficiary across all 21,521 providers: 1.015. The standard deviation was 0.107. I set the threshold at mean plus 2 standard deviations - that's 1.229 services per beneficiary.

**[Scroll through example provider table]**

> This identified 389 providers - just 1.8% of the total - whose billing exceeds this threshold. These providers aren't necessarily committing fraud or abuse, but they warrant investigation.

**[Pause]**

> This 1.8% flag rate is operationally realistic. Payment integrity teams can't investigate 100% of providers - they need targeted audit lists. And the 2-sigma threshold is a standard statistical methodology that's defensible for regulatory audit.

**[Emphasize]**

> This pivot demonstrates real engineering thinking: when the ideal solution isn't feasible given data constraints, reframe the problem to deliver value with the data you have. That's the difference between an academic exercise and production-ready system design."

---

### SECTION 4: Evaluation & Clinical Safety Analysis (90 seconds)

**[Screen: Tab 3 - Evaluation Results]**

> "Let me show you the validation results. This is real evaluation, not a demo with cherry-picked examples.

**[Point to top metrics]**

> The system was tested on 15 real CMS policies: 4 cancer screening policies, 7 cardiovascular and metabolic policies, and 4 behavioral health policies. Mean F1 score of 98.2%. 14 out of 15 policies achieved F1 above 90%, which is considered excellent for extraction tasks.

**[Scroll through policy table]**

> You can see the breakdown: cancer screening policies like colorectal and mammography averaged 93.3% F1. Cardiovascular policies like diabetes screening and cardiac rehab achieved 100%. Behavioral health policies also 100%.

**[Pause]**

> But here's the critical insight: 98.2% mean F1 does NOT automatically mean this system is safe for unsupervised automation.

**[Expand: Clinical Safety Analysis]**

> This clinical safety analysis is what separates a thoughtful submission from a naive one. Not all errors have equal consequences.

> NCD 210.3 - Colorectal Cancer Screening - achieved only 80% F1. It missed 2 out of 11 HCPCS codes, specifically G0120 for colonoscopy and G0464 for Cologuard DNA testing.

> If this system incorrectly denies coverage for a colonoscopy, that's not just a billing error - it's a patient safety issue. Delayed colorectal cancer screening can result in late-stage cancer detection.

**[Point to weighted F1]**

> That's why I calculated weighted F1, assigning 5x weight to cancer screening policies, 3x to cardiovascular, and 1x to routine screening. The weighted F1 is 96.4%.

**[Pause for emphasis]**

> The bottom line: 96.4% weighted F1 is excellent for **audit triage** - helping payment integrity teams prioritize which claims to investigate. But it's not yet sufficient for **unsupervised adjudication** - automatically denying claims without human review.

> This is why my deployment recommendation is Phase 1: audit triage tool with mandatory human oversight. Phase 2, 6 months out, would enable hybrid automation for lower-risk policy types. Phase 3, 18 plus months, would require 99%+ accuracy and FDA regulatory clearance for fully automated adjudication.

**[Show honest assessment section]**

> I'm also clear about what doesn't work yet: no external validation against NCCI edits or second coder agreement, no confidence scoring in the extraction code, no audit trail logging for HIPAA compliance. These are requirements for production deployment that would be addressed in phased rollout."

---

### SECTION 5: Business Value & Cotiviti Relevance (60 seconds)

**[Screen: Tab 3 or return to slides if available]**

> "Why does this matter to Cotiviti specifically?

**[Point to business value metrics if visible]**

> **First: Cost efficiency.** The LLM API cost per policy extraction is about $0.003. Even with human review time, total cost is dramatically lower than manual extraction. At scale - say 1,000 policies per year - this represents significant operational savings.

> **Second: Speed to market.** When CMS issues a policy update, payers need to update their claim edits immediately. Automated extraction can process policies in seconds rather than days or weeks. In a competitive payer market, faster policy implementation means faster improper payment detection for clients.

> **Third: Audit defensibility.** Every flag this system generates is cited back to specific policy text with character offsets. When a provider disputes a claim denial, Cotiviti can point to the exact policy language. This citation grounding is a competitive advantage versus black-box commercial systems.

> **Fourth: Scalability.** This architecture can handle CMS's policy update volume. The multi-agent design processes policies in parallel. There's no bottleneck requiring linear analyst time per policy.

**[Pause]**

> From a strategic perspective, this positions Cotiviti to offer 'AI-powered payment integrity' to clients - faster policy updates, better audit targeting through the 1.8% flag rate, and full regulatory traceability.

> It also provides intellectual property ownership versus paying licensing fees for commercial policy extraction systems."

---

### SECTION 6: Demonstration of Technologies (Assessment Requirement) (45 seconds)

**[Screen: Show demo in action / code if time permits]**

> "Let me quickly demonstrate the core technologies per the assessment requirements:

**[Tab through demo or show architecture]**

> **Multi-agent orchestration:** LangGraph state machine with 6 specialized agents - this is agentic generative AI, not just a single LLM call.

> **Hybrid RAG:** BM25 for lexical matching plus FAISS for semantic similarity with reciprocal rank fusion for reranking - this is the retrieval-augmented generation pattern.

> **Structured extraction:** Mistral-large LLM with Pydantic schema enforcement - ensuring machine-parseable output, not free-form text.

> **Statistical anomaly detection:** 2-sigma outlier detection on utilization data - time-series anomaly detection for payment integrity operations.

> **Citation grounding:** Span-level character offsets linking every extraction back to source policy text - this is the NLP and content summarization capability.

**[Show one more policy extraction quickly]**

> The system works end-to-end: policy document in, structured criteria extracted with citations, executable SQL queries generated, provider outliers flagged for investigation."

---

### SECTION 7: Honest Self-Assessment & Next Steps (45 seconds)

**[Screen: Return to demo or slides with limitations]**

> "I want to close with intellectual honesty about this project's maturity level.

> This is a **validated proof of concept**, not production software. It's been tested on 15 policies - that's enough to prove technical feasibility, but production would require validation on 50 to 100 policies minimum.

> The extraction accuracy is measured and documented - 98.2% F1 - but there's no second-coder validation or inter-rater agreement study. That would be essential for regulatory confidence.

> The system doesn't have NCCI cross-validation. The National Correct Coding Initiative publishes editing rules that should align with coverage policies. I haven't validated consistency between PolicyForge extractions and NCCI edits.

> And critically: this was evaluated on provider-aggregate data, not claim-level data. True claim adjudication requires individual claim detail, which I didn't have access to. That's why the 1.8% outlier flagging is the right problem formulation for the data available.

**[Pause]**

> If Cotiviti were to pursue this, my recommendation would be a 3-month Phase 1 pilot: validate automated extraction on 50 high-impact policies, measure time savings versus current analyst workflow, build an integration with your payment integrity platform, and present a go-no-go decision with measured ROI.

> The technical foundation is proven. The business case would be validated through pilot measurement."

---

### SECTION 8: Closing (15 seconds)

**[Camera: On, professional close]**

> "Thank you for your time. This project demonstrates my ability to:  
> - Apply advanced LLM technologies to real healthcare payment integrity problems  
> - Discover and solve data constraints through creative problem reframing  
> - Validate work rigorously with honest assessment of limitations  
> - And think strategically about production deployment and business value.

> The complete code, technical report, evaluation data, and this presentation are available in the GitHub repository. I welcome your questions and feedback. Thank you."

**[End recording]**

---

## 📊 KEY TALKING POINTS REFERENCE

### Technical Depth Points
- **Hybrid RAG:** BM25 + FAISS with RRF reranking (not just simple retrieval)
- **Structured outputs:** Pydantic-enforced JSON schemas (not free-form LLM text)
- **6-node orchestration:** LangGraph state machine (not linear pipeline)
- **2-sigma methodology:** Standard statistical outlier detection (defensible)
- **Character-level citations:** Span offsets for regulatory audit (not just "page 5")

### Engineering Maturity Points
- **Data granularity discovery:** Provider-level vs claim-level limitation
- **Problem reframing:** 100% flag rate → 1.8% outlier targeting
- **Weighted evaluation:** Clinical severity tiers (not just mean accuracy)
- **Honest limitations:** What works / what doesn't / what's next
- **Phased deployment:** Triage (now) → Hybrid (6mo) → Full automation (18mo+)

### Business Value Points
- **Cost**: $0.003 API cost (measurable), not inflated ROI claims
- **Speed**: 8 seconds processing (measured), orders of magnitude faster
- **Scale**: Parallel multi-agent processing, no linear bottleneck
- **Audit**: Character-level citation traceability (competitive advantage)
- **IP**: Internal capability vs. commercial licensing fees

### Assessment Requirements Alignment
- ✅ **Technology demonstration:** Multi-agent LLM, RAG, structured extraction
- ✅ **Hands-on engineering:** Working code, real data, measured results
- ✅ **Basic competency:** 98.2% F1, 15 policies, statistical outlier detection
- ✅ **Speed to value:** POC complete, clear next steps, phased deployment

---

## 🎥 RECORDING SETUP & TIPS

### Before Recording

**Technical Setup:**
1. Launch demo: `cd policyforge && source .venv/bin/activate && streamlit run demo_app.py`
2. Browser: http://localhost:8501, zoom 100%, hide bookmarks
3. Close unnecessary windows/tabs
4. Enable Do Not Disturb mode
5. Test microphone (clear, no echo)
6. Position camera at eye level

**Content Preparation:**
- Print this script for reference (don't memorize robotically)
- Have GitHub repo URL ready: `github.com/shristi-codes/PolicyForge...`
- Practice technical terms: "Pydantic", "FAISS", "HCPCS", "reciprocal rank fusion"
- Time yourself: aim for 6-7 minutes (detailed but not rushed)

### During Recording

**Delivery Style:**
- **Confident but humble:** "I built this... and here are the limitations"
- **Technical but accessible:** Explain acronyms first time
- **Enthusiastic but professional:** This is an interview, not a sales pitch
- **Pause for emphasis:** After key points (100% flag rate, weighted F1, 1.8% solution)

**Visual Presence:**
- Look at camera when speaking to "audience"
- Look at screen when demonstrating
- Use mouse pointer to highlight specific numbers
- Sit up straight, professional attire
- Good lighting on your face

**Pacing:**
- Don't rush through metrics - let them land
- Pause 1-2 seconds between major sections
- Speak slightly slower than normal conversation
- If you make a small mistake, keep going (editing is okay)
- If you make a major mistake, pause 5 seconds, restart that paragraph

### Recording Tools

**Recommended: OBS Studio (Free)**
1. Add Display Capture (your screen)
2. Add Video Capture (your webcam) - position in corner
3. Add Audio Input (your microphone)
4. Settings: 1920x1080, 30fps, MP4 format
5. Record → Stop → Check → Re-record if needed

**Mac Alternative: QuickTime**
- Cmd+Shift+5 → Record selected portion
- Position yourself in corner via FaceTime, screenshot, overlay
- Simpler but less flexible

**Recording Checklist:**
- [ ] Screen sharing demo visible
- [ ] Webcam positioned (corner or side)
- [ ] Audio clear (no echo, background noise)
- [ ] Resolution 1920x1080 or 1280x720 minimum
- [ ] Test recording 30 seconds, verify quality

---

## 📝 SCRIPT CUSTOMIZATION NOTES

### If Demo Doesn't Work
**Backup Plan:**
- Show the GitHub repository instead
- Walk through `demo_app.py` code
- Display `eval/results/*.json` files
- Show architecture diagram if you have one
- Point to `policyforge/README.md` metrics

**Script adjustment:**
> "I had planned to do a live demo, but let me walk through the code and results instead. Here in the evaluation results file, you can see the measured 98.2% F1 across 15 policies..."

### If You Need to Cut for Time
**Prioritize sections in this order:**
1. **Section 3 (Engineering Breakthrough)** - This is your strongest material
2. **Section 4 (Evaluation & Clinical Safety)** - Shows depth of thinking
3. **Section 2 (Architecture)** - Technical competency
4. **Section 5 (Business Value)** - Cotiviti relevance
5. **Section 7 (Honest Assessment)** - Professional maturity
6. **Section 6 (Tech Demo)** - Can be abbreviated
7. **Section 1 (Introduction)** - Keep brief

**Minimum viable script:** Sections 1, 3, 4, 7 = 4 minutes

### If You Want to Expand (7+ minutes)
**Add these details:**
- Show 2-3 more policy extractions in detail
- Explain Pydantic schema structure
- Show actual Python code snippets
- Walk through one provider flag in detail
- Discuss NCCI validation plan
- Explain FAISS indexing process

---

## 🎯 FINAL CHECKLIST

### Content
- [ ] Addressed Topic 3 explicitly (content management, policy conversion)
- [ ] Demonstrated multi-agent orchestration (LangGraph)
- [ ] Explained hybrid RAG (BM25 + FAISS)
- [ ] Showed structured extraction (Pydantic)
- [ ] Presented 100% → 1.8% engineering breakthrough
- [ ] Explained weighted F1 clinical safety analysis
- [ ] Honest about limitations (external validation, scale, claim data)
- [ ] Provided next steps (Phase 1 pilot)
- [ ] Mentioned GitHub repo availability

### Delivery
- [ ] Clear vocal presentation (not rushed, not monotone)
- [ ] Professional visual presence (camera on, well-lit, appropriate attire)
- [ ] Demonstrated technological competency (not just slides, actual working system)
- [ ] Time: 5-7 minutes (detailed but concise)

### Technical Quality
- [ ] Screen recording clear (1920x1080 or 1280x720)
- [ ] Audio clear (no echo, background noise, clipping)
- [ ] Webcam visible (positioned appropriately)
- [ ] Demo functional or backup plan executed
- [ ] Saved as MP4 file for upload

### Submission
- [ ] Video file named appropriately: `PolicyForge_Video_ShuristiKumar.mp4`
- [ ] GitHub repo updated with all files
- [ ] Video uploaded to GitHub or linked in README
- [ ] Repository shared with jesus.hurtado@cotiviti.com
- [ ] Email sent with subject: "INTERN - Shristi Kumar - San José State University"

---

## 🚀 YOU'RE READY!

This is comprehensive preparation. You have:
- ✅ Detailed script with technical depth
- ✅ Honest assessment integrated throughout
- ✅ Clear alignment to assessment requirements
- ✅ Professional delivery guidance
- ✅ Backup plans if issues arise

**Remember:** The assessors are evaluating:
1. **Can you build real things?** (Yes - 98.2% F1 on 15 policies)
2. **Can you solve real problems?** (Yes - 100% → 1.8% breakthrough)
3. **Do you know your limitations?** (Yes - honest about scale, validation, data)
4. **Can you communicate clearly?** (Demonstrate this in your video)

You've done the hard technical work. Now just show them what you built!

**One final tip:** If you're nervous, remember: you know this project better than anyone. You built it. You understand it. You discovered and solved real problems. Just explain what you did to someone who's smart but doesn't know the details yet. You've got this!

---

## ⚡ QUICK START

1. **Read this entire script once**
2. **Practice sections 3 & 4** (your strongest material)
3. **Launch demo:** `cd policyforge && source .venv/bin/activate && streamlit run demo_app.py`
4. **Set up recording** (OBS or QuickTime)
5. **Do a 1-minute test recording** (verify quality)
6. **Take 3 deep breaths**
7. **Press record and deliver**
8. **Review - if major issues, re-record**
9. **Upload and submit!**

Good luck! 🎬
