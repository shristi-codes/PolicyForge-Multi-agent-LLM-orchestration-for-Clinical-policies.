# Cotiviti Intern Assessment — Project Roadmap
## Project: **PolicyForge** — An Agentic Policy-to-Edit Engine for Medicare Payment Integrity

> **Candidate:** Shristi Kumar — MS Applied Data Intelligence, San José State University
> **Chosen Topic:** #3 *Content Management in Health Care* (Conversion of Written Policy into Programming Languages, Rules, Features, or Models) — with a working bridge into Topic #2 (Classification / Anomaly Detection for Payment & Operations).
> **Submission target:** GitHub repo shared with `jesus.hurtado@cotiviti.com`; email subject `INTERN - Shristi Kumar - San Jose State University`.

---

## 0. TL;DR (read this first)

PolicyForge ingests a **real Medicare coverage policy** (NCD/LCD), uses a **multi-agent LLM orchestration** (LangGraph) with **hybrid RAG + citation grounding** to convert dense policy prose into a **machine-executable claim edit**, then applies that edit to **real CMS Part B utilization data** to flag provider-level payment-integrity outliers — every flag cited back to the exact policy clause.

To prove *depth* (not a "single LLM pass"), the build has three engineered layers:
1. **Agentic orchestration** — a 6-node LangGraph state machine with a dedicated Critic/grounding node.
2. **Hybrid retrieval** — BM25 + dense embeddings + reranking + span-level citation.
3. **LoRA fine-tuning track** — a scoped fine-tune of a small open model for policy-clause classification, benchmarked against a GPT-class baseline in a formal **eval harness**.

**Design principle (reconciling the PDF's "don't overcomplicate"):** the *demo* shows a clean end-to-end run in ~90 seconds; the *depth* lives in a design that actually works and is measured. Working depth > shallow simplicity.

---

## 1. The Real Problem (this is not a toy)

Medicare Fee-for-Service **improper payments run ~$30B+ per year** (CMS estimates). A large share stems from services billed outside coverage rules — wrong frequency, ineligible diagnosis, non-covered indication, or coding errors.

The rules that catch these live in **thousands of written coverage policies** (National Coverage Determinations + Local Coverage Determinations) authored in dense clinical/legal prose. Turning that prose into **auditable, machine-executable claim edits** is today largely **manual, slow, inconsistent, and hard to trace back to source** — which is precisely the content-management challenge in the assessment prompt, and precisely what a payment-integrity company like Cotiviti productizes.

**The real question PolicyForge answers:**
> *Can we reliably and auditably convert written coverage policy into executable edits, then apply them to real utilization data to surface improper-payment risk — with every decision traceable to the policy text?*

---

## 2. The Solution: PolicyForge

A pipeline of specialized agents that mirrors how a payment-integrity analyst actually reasons:

| Stage | Human analyst does… | PolicyForge agent does… |
|-------|---------------------|--------------------------|
| Read policy | Reads NCD/LCD prose | **Retriever** pulls relevant clauses (RAG) |
| Extract criteria | Notes frequency/age/dx/HCPCS limits | **Extractor** emits structured JSON |
| Sanity-check | Verifies against source | **Critic** grounds each criterion to a cited span; rejects hallucinations |
| Codify | Writes the edit logic | **Compiler** renders JSON → executable rule |
| Screen claims | Runs edit on utilization | **Adjudicator** applies edit to real CMS data |
| Explain | Writes rationale | **Explainer** produces cited natural-language justification |

Output: a ranked list of **real flagged providers** with a plain-English, policy-cited rationale — a defensible payment-integrity screening signal.

---

## 3. Topic Mapping (why this maximizes the score)

- **Primary — Topic 3:** "Conversion of Written Policy into Programming Languages, Rules, Features, or Models" → PolicyForge *literally does this* (policy → JSON → executable edit).
- **Bridge — Topic 2:** "Classification, Prediction, Anomaly Detection for Treatment, Payment & Operations (TPO)" → the Adjudicator flags utilization outliers on real Part B data.
- **Cotiviti alignment:** their core business is medical-policy-driven claim editing and payment integrity. This is a direct, credible demonstration of their value chain.

---

## 4. Datasets — all real, all public, zero PHI (with links)

| # | Dataset | Role in PolicyForge | Link | PHI? |
|---|---------|---------------------|------|------|
| 1 | **CMS Medicare Coverage Database (NCDs/LCDs)** | Input policy documents (the prose we codify) | https://www.cms.gov/medicare-coverage-database/ | None (public policy text) |
| 2 | **Medicare Physician & Other Practitioners — by Provider and Service** | Real Part B utilization to apply edits to (NPI × HCPCS × place of service; `Tot_Benes`, `Tot_Srvcs`, `Avg_Sbmtd_Chrg`, `Avg_Mdcr_Alowd_Amt`) | https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners/medicare-physician-other-practitioners-by-provider-and-service | None (aggregated, redacted) |
| 3 | **NCCI Edits (National Correct Coding Initiative)** | **Ground-truth edits** to benchmark our generated edits against | https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-ncci-edits | None |
| 4 | **OIG LEIE (List of Excluded Individuals/Entities)** | Enrichment: cross-check flagged NPIs against real exclusions | https://oig.hhs.gov/exclusions/exclusions_list.asp | None |
| 5 | **HCPCS Level II code set** | Map policy procedures → billing codes | https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-system | None |
| 6 | **ICD-10-CM code set** | Map diagnosis criteria → codes | https://www.cms.gov/medicare/coding-billing/icd-10-codes | None |
| 7 | *(Optional)* **MTSamples** clinical notes | Only if extending to note-level NLP | https://mtsamples.com | De-identified samples |
| 8 | *(Models)* **Hugging Face** open LLMs (Phi-3-mini, Mistral-7B, BioMistral) | LoRA fine-tuning base | https://huggingface.co/models | N/A |

**Authenticity note:** Dataset #2 "aggregates 100% of final-action non-institutional Part B claims" — it is *real* Medicare data, aggregated to provider+procedure so it contains **no patient identifiers**. This directly satisfies the requirement to use authentic clinical/payment data.

**Anchor policy for v1:** *Bone Mass Measurement (NCD 150.3)* — covered **once every 24 months** (with exceptions). Clean, codifiable frequency + eligibility criteria; HCPCS such as 77080/77081. Second policy (colorectal or diabetes screening) added for generalization evidence.

---

## 5. System Architecture (multi-agent orchestration)

```
                         ┌─────────────────────────────────────────────┐
                         │              PolicyForge (LangGraph)          │
                         │                                               │
  Real NCD/LCD policy ──►│  1. RETRIEVER  ──►  2. EXTRACTOR             │
   (CMS MCD, dataset #1) │   (hybrid RAG)       (JSON criteria)         │
                         │        │                    │                │
                         │        ▼                    ▼                │
                         │   3. CRITIC / GROUNDING VALIDATOR            │
                         │   (span citations, hallucination gate)      │
                         │        │  ok?  ──no──► loop back / flag      │
                         │        ▼ yes                                 │
                         │   4. COMPILER  ──►  executable edit (DSL/py) │
                         │        │                                     │
  Real CMS Part B  ──────┼───►  5. ADJUDICATOR  (apply edit to data)   │
   utilization (#2)      │        │                                     │
                         │        ▼                                     │
                         │   6. EXPLAINER (cited rationale)  ──► OUTPUT │
                         └─────────────────────────────────────────────┘
                                          │
                            Streamlit UI: policy in → rules → edit code
                            → flagged REAL providers + citations + LEIE check
```

**State object** (passed between nodes): `policy_id`, `retrieved_spans[]`, `criteria_json`, `citations[]`, `validation_status`, `compiled_edit`, `flagged_providers[]`, `explanations[]`, `costs/latency`.

**Why LangGraph (not a linear chain):** enables the **Critic feedback loop** (re-extract if grounding fails), conditional branching, and per-node observability — the difference between "an LLM call" and "an engineered agentic system."

---

## 6. LLM Orchestration Depth — the differentiators

This is where PolicyForge separates from a "plain LLM pass." Three engineered layers, each measured.

### Depth Layer 1 — Agentic orchestration with a grounding gate
- **6-node LangGraph state machine** (above).
- **Critic/Validator node** enforces that *every* extracted criterion carries a **verbatim source span + char offsets**. If a criterion can't be grounded, it's rejected or routed back — a concrete **hallucination-reduction mechanism**, not a hope.
- **Structured outputs** via JSON-schema / function-calling so downstream compilation is deterministic.
- **Per-node tracing** (LangSmith or lightweight logging) for cost, latency, token budget.

### Depth Layer 2 — Hybrid RAG with citation grounding
- **Chunking** of the policy corpus (NCD/LCD + coding guidelines) with section-aware splitting.
- **Hybrid retrieval:** BM25 (lexical) ⊕ dense embeddings (semantic) → **reciprocal-rank fusion** → **cross-encoder reranker**.
- **Citation grounding:** retrieved spans are the *only* evidence the Extractor may use; the Critic verifies criterion ⇄ span alignment.
- **Optional GraphRAG:** NCDs cross-reference other policies/codes — model these as a small graph so retrieval follows references (shows retrieval sophistication).
- **Vector store:** FAISS (local, reproducible) or Chroma.

### Depth Layer 3 — LoRA fine-tuning + formal evaluation
- **Task:** *policy-clause classification* — label each policy sentence as `frequency | age | diagnosis | procedure | exclusion | other`. (A crisp, bounded task that measurably improves extraction.)
- **Gold set:** hand-annotate ~80–120 clauses across 3–4 real policies (small, honest, documented).
- **Base model:** Phi-3-mini or Mistral-7B via **PEFT/LoRA** (`<1%` trainable params) — trainable on a single GPU / Colab.
- **Benchmark:** LoRA-tuned small model **vs.** GPT-class few-shot baseline **vs.** zero-shot base — report macro-F1, cost, latency.
- **Narrative:** demonstrates that a **cheap specialized model** can match/approach a large general model on a narrow, high-volume classification step — a real cost/scale argument for Cotiviti.

> This mirrors prior work (LoRA/PEFT on Whisper: 55.8% relative WER improvement with <1% trainable params) so it's credible and executable.

### The Eval Harness (this is what "surpasses expectations")
A dedicated, reproducible evaluation — most candidates will ship a demo with **no measurement**.

| Metric | What it measures | Target |
|--------|------------------|--------|
| **Extraction F1** (per field) | frequency/age/dx/HCPCS/exclusion correctness vs gold | ≥ 0.85 |
| **Citation grounding rate** | % criteria with a valid verbatim source span (hallucination proxy) | ≥ 0.95 |
| **Edit correctness vs NCCI** | generated edits agree with real NCCI ground-truth where overlapping | report + error analysis |
| **Provider-flag precision** | spot-check flagged NPIs (LEIE / manual) | report top-k precision |
| **Clause-classification macro-F1** | LoRA vs GPT vs base | LoRA competitive at lower cost |
| **Cost & latency per policy** | \$/policy, seconds/policy | report + ablation |

**Ablation table** (base LLM zero-shot → +few-shot → +RAG → +Critic → +LoRA-clause-classifier) turns the POC into an *experiment*, showing exactly what each engineered layer buys.

---

## 7. Tech Stack

| Layer | Tools |
|-------|-------|
| Orchestration | **LangGraph**, LangChain |
| LLMs | OpenAI (GPT-4-class) and/or Gemini for agents; **Phi-3-mini / Mistral-7B** for LoRA |
| Retrieval | FAISS/Chroma, BM25 (rank_bm25), sentence-transformers, cross-encoder reranker |
| Fine-tuning | Hugging Face `transformers`, `peft` (LoRA), `bitsandbytes` (4-bit), `trl` |
| Data | pandas, DuckDB (for the real CMS CSV, which is large) |
| App / demo | **Streamlit** |
| Eval | custom harness + `scikit-learn` metrics; optional LangSmith tracing |
| Packaging | Python 3.11, `requirements.txt`, `.env` for keys, reproducible seeds |

---

## 8. Deliverables — mapped 1:1 to the assessment PDF

| PDF requirement | PolicyForge deliverable | "Surpass" upgrade |
|-----------------|-------------------------|-------------------|
| **2-page Word report** (define concept, trends, opportunities/threats, strategic options; APA/MLA bib on p.3) | `report/PolicyForge_Report.docx` | Real $ problem sizing; ablation-backed claims; explicit Cotiviti investment recommendation |
| **Hackathon POC** (simple, prove the concept) | Working repo + Streamlit demo, end-to-end on real data | Agentic + RAG + LoRA + eval harness — but demo stays clean/fast |
| **PowerPoint** (overview of report + POC) | `slides/PolicyForge.pptx` (~10–12 slides) | Architecture diagram, live-demo screenshots, eval charts |
| **MP4 video** (you on camera + slides + screenshare of working POC) | `demo.mp4` (~6–8 min) | Crisp live run; state the honest caveats; recommendation close |
| **Submission** (GitHub, share + email) | Repo shared with reviewer; email w/ correct subject | Professional README, reproducible setup, `EVAL.md` |

---

## 9. "Surpass Expectations" — explicit list

1. **Measured, not just demoed** — full eval harness + ablation table.
2. **Real ground truth** — validate generated edits against **NCCI** and enrich flags with **LEIE**.
3. **Grounding gate** — engineered hallucination control with span-level citations (auditable = payment-integrity-grade).
4. **LoRA cost argument** — small fine-tuned model vs. GPT baseline: a scalability story Cotiviti cares about.
5. **Honest scoping** — explicitly state provider-level screening ≠ per-claim adjudication (shows domain maturity).
6. **Reproducibility** — seeds, pinned deps, one-command run, documented data pulls.
7. **Strategic report** — quantified problem, concrete investment recommendation, risk register.

---

## 10. Phased Timeline (satisfice-aware: working core first, depth layered)

| Day | Phase | Output | Gate |
|-----|-------|--------|------|
| **1** | Setup + data | Repo skeleton; pull anchor policy (#1); pull filtered CMS Part B extract (#2) via DuckDB; grab NCCI (#3) + LEIE (#4) | Data loads locally |
| **2** | Core pipeline v1 | Extractor → Compiler → Adjudicator working (single-agent) on real data; basic Streamlit | **End-to-end run works** (satisfice bar met) |
| **3** | Depth L1+L2 | Convert to LangGraph 6-node graph; add hybrid RAG + Critic grounding + citations | Flags carry citations |
| **4** | Depth L3 | Annotate gold set; LoRA fine-tune clause classifier; run eval harness + ablations | Eval numbers produced |
| **5** | Report + slides | 2-page report (+bib); PPTX with arch + eval charts | Docs done |
| **6** | Video + polish | Record MP4 (camera + demo); README + EVAL.md; reproducibility pass | Repo clean |
| **7** | Submit | Share repo + email reviewer | **Submitted** |

> If time is tight, **Days 1–2 alone already satisfy the PDF** (working POC). Days 3–4 are what make it *surpass*. Ship the core early, then layer — never risk having nothing that runs.

---

## 11. Repo Structure

```
policyforge/
├── README.md                  # problem, architecture, quickstart, screenshots
├── EVAL.md                    # metrics, ablation table, methodology
├── requirements.txt
├── .env.example               # OPENAI_API_KEY / GEMINI_API_KEY
├── data/
│   ├── policies/              # real NCD/LCD text (dataset #1)
│   ├── cms_partb_sample.parquet   # filtered real utilization (dataset #2)
│   ├── ncci_edits/            # ground-truth edits (dataset #3)
│   └── leie.csv               # exclusions (dataset #4)
├── src/
│   ├── graph.py               # LangGraph state machine (6 nodes)
│   ├── agents/
│   │   ├── retriever.py       # hybrid RAG + rerank
│   │   ├── extractor.py       # policy → criteria JSON
│   │   ├── critic.py          # grounding / citation gate
│   │   ├── compiler.py        # criteria JSON → executable edit
│   │   ├── adjudicator.py     # apply edit to real CMS data
│   │   └── explainer.py       # cited rationale
│   ├── rag/                   # chunking, embeddings, BM25, reranker, FAISS
│   ├── schema.py              # Pydantic rule schema
│   └── data_pull.py           # scripts to fetch/filter real datasets
├── finetune/
│   ├── annotate/gold.jsonl    # ~100 labeled clauses
│   ├── train_lora.py          # PEFT/LoRA training
│   └── compare.py             # LoRA vs GPT vs base
├── eval/
│   ├── harness.py             # runs all metrics
│   └── ablation.py            # layer-by-layer study
├── app.py                     # Streamlit demo
├── report/PolicyForge_Report.docx
├── slides/PolicyForge.pptx
└── demo.mp4
```

---

## 12. Eval Plan & Metrics (methodology)

1. **Gold annotations:** for 3–4 policies, hand-label the criteria (frequency, age, eligible HCPCS/ICD, exclusions) and clause types. Documented in `finetune/annotate/`.
2. **Extraction F1:** compare Extractor+Critic output to gold, per field. Error analysis on misses.
3. **Grounding rate:** fraction of criteria with a verbatim, offset-verified source span.
4. **Edit correctness:** where PolicyForge edits overlap NCCI, measure agreement; discuss divergences honestly.
5. **Flag precision:** take top-k flagged NPIs, check LEIE + manual plausibility; report precision@k.
6. **LoRA benchmark:** macro-F1 / cost / latency across LoRA-small vs GPT few-shot vs base zero-shot.
7. **Ablation:** toggle RAG, Critic, LoRA to quantify each layer's contribution.

---

## 13. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| CMS Part B file is huge | Filter to anchor-policy HCPCS via **DuckDB**; ship a small parquet sample |
| LoRA GPU/time constraints | Use 4-bit + Phi-3-mini; keep gold set small; Colab fallback |
| LLM hallucination on clinical criteria | Critic grounding gate + citation requirement + human-in-the-loop note |
| Over-engineering vs PDF's "satisfice" | Days 1–2 ship a working core first; depth is additive, never blocking |
| Frequency rule needs per-beneficiary data | Use `Tot_Srvcs/Tot_Benes` as provider-level proxy; **state the limitation explicitly** |
| API cost | Cache LLM calls; cap tokens; log spend |

---

## 14. Stretch Goals (if ahead of schedule)

- **GraphRAG** over policy cross-references.
- **Second + third policies** to show generalization (frequency, age, diagnosis rule types).
- **Confidence scoring** per generated edit.
- **Feedback UI** where a reviewer accepts/rejects an edit (human-in-the-loop, RLHF-flavored).

---

## 15. Submission Checklist

- [ ] Repo public/shared with `jesus.hurtado@cotiviti.com`
- [ ] `README.md` with quickstart + screenshots
- [ ] `EVAL.md` with metrics + ablation table
- [ ] Working `app.py` (one-command run) on **real** data
- [ ] `report/PolicyForge_Report.docx` (2 pages + APA/MLA bibliography on p.3)
- [ ] `slides/PolicyForge.pptx`
- [ ] `demo.mp4` (camera + slides + live POC screenshare)
- [ ] Email sent — subject: `INTERN - Shristi Kumar - San Jose State University`
- [ ] All datasets cited with links; PHI-free confirmed

---

### One-sentence pitch for the video open
> *"Medicare loses tens of billions a year to improper payments hidden inside thousands of written coverage policies — PolicyForge is an agentic system that reads those real policies, converts them into auditable, executable claim edits with citations, and applies them to real Medicare utilization data to surface payment-integrity risk."*
