#!/usr/bin/env python3
"""
Generate PolicyForge PowerPoint Presentation (.pptx)

Requirements (from assessment):
- Overview of written report AND POC
- Quality slide organization, design, and visual aids
- Professional visual presence

Design philosophy:
- Dark navy header bar on every slide (brand consistency)
- One key insight per slide, never more than 6 bullets
- Real numbers front-and-center
- Honest about limitations (clinical safety)
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
import pptx

# ── Brand palette ─────────────────────────────────────────────────────────────
NAVY   = RGBColor(0x1F, 0x49, 0x7D)   # Cotiviti-style deep navy
TEAL   = RGBColor(0x00, 0x7B, 0x83)   # Accent teal
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT  = RGBColor(0xF2, 0xF7, 0xFB)   # Very light blue background
DARK   = RGBColor(0x1A, 0x1A, 0x2E)   # Near-black text
GREEN  = RGBColor(0x2E, 0x75, 0x2F)
AMBER  = RGBColor(0xBF, 0x87, 0x00)
RED    = RGBColor(0xC0, 0x2B, 0x2B)
GRAY   = RGBColor(0x55, 0x65, 0x72)

SLIDE_W = Inches(13.33)   # widescreen 16:9
SLIDE_H = Inches(7.5)


# ─────────────────────────────────────────────────────────────────────────────
# Low-level helpers
# ─────────────────────────────────────────────────────────────────────────────

def add_rect(slide, left, top, width, height, fill_color, line_color=None):
    shape = slide.shapes.add_shape(
        pptx.enum.shapes.MSO_SHAPE_TYPE.RECTANGLE
        if False else 1,           # 1 == MSO_SHAPE.RECTANGLE
        left, top, width, height
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    if line_color:
        shape.line.color.rgb = line_color
    else:
        shape.line.fill.background()
    return shape

def tf_para(tf, text, size, bold=False, color=WHITE, align=PP_ALIGN.LEFT, space_before=0):
    para = tf.add_paragraph()
    para.text = text
    para.alignment = align
    run = para.runs[0]
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    para.space_before = Pt(space_before)
    return para

def add_textbox(slide, text, left, top, width, height,
                size=18, bold=False, color=DARK, align=PP_ALIGN.LEFT,
                wrap=True, italic=False):
    txb = slide.shapes.add_textbox(left, top, width, height)
    txb.word_wrap = wrap
    tf = txb.text_frame
    tf.word_wrap = wrap
    tf_para(tf, text, size, bold=bold, color=color, align=align)
    para = tf.paragraphs[0]
    if italic and para.runs:
        para.runs[0].font.italic = True
    elif italic:
        # set italic via paragraph's default run font
        from pptx.oxml.ns import qn as _qn
        from lxml import etree as _etree
        rPr = para._p.get_or_add_pPr()
        # fallback: just mark via run added manually
        run = para.add_run()
        run.text = ""
        run.font.italic = True
    return txb

def header_bar(slide, title_text, subtitle_text=""):
    """Dark navy bar across the top with title inside."""
    bar = add_rect(slide, Inches(0), Inches(0), SLIDE_W, Inches(1.35), NAVY)
    txb = slide.shapes.add_textbox(Inches(0.4), Inches(0.12), Inches(12.0), Inches(0.65))
    txb.word_wrap = False
    tf = txb.text_frame
    tf_para(tf, title_text, 24, bold=True, color=WHITE)
    if subtitle_text:
        txb2 = slide.shapes.add_textbox(Inches(0.4), Inches(0.72), Inches(12.0), Inches(0.45))
        tf2 = txb2.text_frame
        tf_para(tf2, subtitle_text, 13, color=RGBColor(0xC5, 0xD8, 0xF0))
    return bar

def footer_bar(slide, text="PolicyForge  |  Cotiviti Intern Assessment  |  July 2026"):
    bar = add_rect(slide, Inches(0), Inches(7.2), SLIDE_W, Inches(0.3), NAVY)
    txb = slide.shapes.add_textbox(Inches(0.3), Inches(7.21), Inches(12), Inches(0.28))
    tf = txb.text_frame
    tf_para(tf, text, 9, color=RGBColor(0xC5, 0xD8, 0xF0))

def bullet_box(slide, bullets, left, top, width, height,
               size=15, bullet_color=TEAL, text_color=DARK, line_spacing=1.3):
    txb = slide.shapes.add_textbox(left, top, width, height)
    txb.word_wrap = True
    tf = txb.text_frame
    tf.word_wrap = True
    first = True
    for item in bullets:
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        p.text = f"▸  {item}"
        p.space_before = Pt(4)
        r = p.runs[0]
        r.font.size = Pt(size)
        r.font.color.rgb = text_color

def metric_card(slide, left, top, value, label, value_color=TEAL, bg=LIGHT):
    w, h = Inches(2.2), Inches(1.2)
    box = add_rect(slide, left, top, w, h, bg)
    # value
    txb = slide.shapes.add_textbox(left+Inches(0.1), top+Inches(0.05), w-Inches(0.2), Inches(0.65))
    tf = txb.text_frame
    tf_para(tf, value, 30, bold=True, color=value_color, align=PP_ALIGN.CENTER)
    # label
    txb2 = slide.shapes.add_textbox(left+Inches(0.05), top+Inches(0.68), w-Inches(0.1), Inches(0.45))
    tf2 = txb2.text_frame
    tf_para(tf2, label, 10, color=GRAY, align=PP_ALIGN.CENTER)


# ─────────────────────────────────────────────────────────────────────────────
# Individual slides
# ─────────────────────────────────────────────────────────────────────────────

def slide_title(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = NAVY

    # Big white title
    add_textbox(slide,
        "PolicyForge",
        Inches(0.7), Inches(1.4), Inches(12), Inches(1.3),
        size=52, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

    add_textbox(slide,
        "Automated Medicare Policy Extraction Using\nMulti-Agent LLMs & Retrieval-Augmented Generation",
        Inches(0.7), Inches(2.85), Inches(12), Inches(1.0),
        size=20, color=RGBColor(0xC5, 0xD8, 0xF0), align=PP_ALIGN.CENTER)

    # Teal divider line
    divider = add_rect(slide, Inches(4.2), Inches(4.1), Inches(4.93), Inches(0.04), TEAL)

    add_textbox(slide,
        "Cotiviti Intern Assessment  ·  Topic 3: Content Management in Health Care",
        Inches(0.7), Inches(4.25), Inches(12), Inches(0.4),
        size=13, color=RGBColor(0x90, 0xB8, 0xD8), align=PP_ALIGN.CENTER)

    add_textbox(slide,
        "Abhishek Kumar  ·  July 2026",
        Inches(0.7), Inches(4.75), Inches(12), Inches(0.4),
        size=13, color=WHITE, align=PP_ALIGN.CENTER)

    # Bottom stat strip
    add_rect(slide, Inches(0), Inches(6.1), SLIDE_W, Inches(1.1), RGBColor(0x17, 0x37, 0x60))
    stats = [
        ("15", "Real CMS Policies"), ("98.2%", "Mean F1 Score"),
        ("96.4%", "Weighted F1"), ("15×", "Cost Reduction"),
        ("1.8%", "Provider Flag Rate")
    ]
    for i, (val, lbl) in enumerate(stats):
        x = Inches(0.3 + i * 2.6)
        add_textbox(slide, val, x, Inches(6.15), Inches(2.4), Inches(0.5),
                    size=22, bold=True, color=TEAL, align=PP_ALIGN.CENTER)
        add_textbox(slide, lbl, x, Inches(6.65), Inches(2.4), Inches(0.4),
                    size=10, color=WHITE, align=PP_ALIGN.CENTER)


def slide_problem(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = WHITE
    header_bar(slide, "The Problem", "Manual policy extraction cannot keep pace with Medicare policy velocity")
    footer_bar(slide)

    # Left: pain points
    add_textbox(slide, "Current State", Inches(0.4), Inches(1.5), Inches(5.5), Inches(0.45),
                size=14, bold=True, color=NAVY)
    pains = [
        "45 min per policy — a single analyst processes ~11/day",
        "$56.25 per extraction (analyst @ $75/hr)",
        "CMS issued 1,200+ policy updates in 2023",
        "Human error rate ~15% on complex multi-code policies",
        "Delays cascade into claims backlogs and audit gaps",
    ]
    bullet_box(slide, pains, Inches(0.4), Inches(1.95), Inches(5.6), Inches(3.5), size=14)

    # Right: scale graphic (3 big numbers)
    add_rect(slide, Inches(6.6), Inches(1.5), Inches(6.2), Inches(4.9), LIGHT)
    add_textbox(slide, "The Scale of the Problem", Inches(6.8), Inches(1.6),
                Inches(5.8), Inches(0.4), size=13, bold=True, color=NAVY)

    cards = [
        ("1,200+", "CMS policy updates per year"),
        ("$67M+",  "Estimated annual payer burden\n(industry-wide)"),
        ("45 min", "Manual extraction per policy"),
    ]
    for idx, (v, l) in enumerate(cards):
        y = Inches(2.1 + idx * 1.4)
        add_rect(slide, Inches(6.8), y, Inches(5.7), Inches(1.2), WHITE)
        add_textbox(slide, v, Inches(6.9), y + Inches(0.05), Inches(2.0), Inches(0.7),
                    size=28, bold=True, color=TEAL)
        add_textbox(slide, l, Inches(9.1), y + Inches(0.18), Inches(3.3), Inches(0.7),
                    size=13, color=DARK)


def slide_solution(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = WHITE
    header_bar(slide, "The Solution: PolicyForge Architecture",
               "6-node LangGraph multi-agent pipeline from policy PDF to actionable rules")
    footer_bar(slide)

    # Pipeline flow diagram
    nodes = [
        ("Retriever",   "Hybrid RAG\nBM25 + FAISS",           TEAL),
        ("Extractor",   "LLM + Pydantic\nStructured Output",   NAVY),
        ("Critic",      "Validation\nGate",                    RGBColor(0x5B, 0x48, 0x99)),
        ("Compiler",    "Policy →\nExecutable Rules",          RGBColor(0x00, 0x6D, 0x77)),
        ("Adjudicator", "Statistical\nOutlier 2σ",             AMBER),
        ("Explainer",   "Plain-English\nAudit Summary",        GREEN),
    ]

    box_w, box_h = Inches(1.75), Inches(1.05)
    gap = Inches(0.18)
    start_x = Inches(0.25)
    y_box = Inches(1.6)

    for i, (name, desc, col) in enumerate(nodes):
        x = start_x + i * (box_w + gap)
        # colored box
        add_rect(slide, x, y_box, box_w, box_h, col)
        # name
        add_textbox(slide, name, x, y_box + Inches(0.06), box_w, Inches(0.38),
                    size=13, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        # desc
        add_textbox(slide, desc, x, y_box + Inches(0.44), box_w, Inches(0.55),
                    size=10, color=WHITE, align=PP_ALIGN.CENTER)
        # arrow
        if i < len(nodes) - 1:
            ax = x + box_w + Inches(0.01)
            add_textbox(slide, "→", ax, y_box + Inches(0.3), gap + Inches(0.1), Inches(0.4),
                        size=16, bold=True, color=NAVY, align=PP_ALIGN.CENTER)

    # Technologies row
    add_textbox(slide, "Key Technologies", Inches(0.4), Inches(2.85), Inches(12), Inches(0.35),
                size=12, bold=True, color=NAVY)
    techs = [
        "🤖  Mistral-large-latest  (structured JSON output, temperature=0)",
        "🔍  sentence-transformers + FAISS  (semantic retrieval)",
        "📐  LangGraph  (stateful 6-node DAG with conditional critic loop)",
        "🗃️  DuckDB  (21,521 provider records, Part B utilization)",
    ]
    bullet_box(slide, techs, Inches(0.4), Inches(3.25), Inches(12.5), Inches(2.5), size=13)

    # Results preview strip
    add_rect(slide, Inches(0), Inches(5.9), SLIDE_W, Inches(1.05), LIGHT)
    add_textbox(slide, "Validated on 15 real CMS policies  ·  98.2% mean F1  ·  96.4% weighted F1  ·  15× cost reduction",
                Inches(0.3), Inches(6.1), Inches(12.7), Inches(0.55),
                size=14, bold=True, color=NAVY, align=PP_ALIGN.CENTER)


def slide_results(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = WHITE
    header_bar(slide, "Results: Evaluation on 15 Real Medicare Policies",
               "Manual gold standards created by reading each policy text — no fabricated data")
    footer_bar(slide)

    # 5 metric cards
    metrics = [
        ("98.2%",  "Mean F1\n(all 15 policies)",     TEAL),
        ("96.4%",  "Weighted F1\n(by clinical severity)", NAVY),
        ("14/15",  "Policies F1 ≥ 0.9\n(excellent)", GREEN),
        ("15×",    "Cost Reduction\n$56 → $3.75",    RGBColor(0x00, 0x6D, 0x77)),
        ("1.8%",   "Provider Flag Rate\n(2σ outliers)",AMBER),
    ]
    for i, (val, lbl, col) in enumerate(metrics):
        x = Inches(0.3 + i * 2.6)
        add_rect(slide, x, Inches(1.55), Inches(2.45), Inches(1.3), LIGHT)
        add_textbox(slide, val, x, Inches(1.6), Inches(2.45), Inches(0.7),
                    size=30, bold=True, color=col, align=PP_ALIGN.CENTER)
        add_textbox(slide, lbl, x, Inches(2.3), Inches(2.45), Inches(0.5),
                    size=10, color=GRAY, align=PP_ALIGN.CENTER)

    # Per-tier table
    add_textbox(slide, "Performance by Clinical Severity Tier", Inches(0.4), Inches(3.1),
                Inches(12), Inches(0.4), size=13, bold=True, color=NAVY)

    tiers = [
        ("TIER 1  —  Critical  (Cancer Screening)",    "93.3%", "🔴 Human review required",    RED,   Inches(0.4)),
        ("TIER 2  —  Important  (CVD / Metabolic)",   "100%",  "🟡 Safe for hybrid automation",AMBER, Inches(4.45)),
        ("TIER 3  —  Routine  (Behavioral Health)",   "100%",  "🟢 Safe for automation",       GREEN, Inches(8.5)),
    ]
    for label, f1, status, col, x in tiers:
        add_rect(slide, x, Inches(3.6), Inches(3.8), Inches(2.8), LIGHT)
        add_textbox(slide, label, x+Inches(0.1), Inches(3.7), Inches(3.6), Inches(0.5),
                    size=10, bold=True, color=col)
        add_textbox(slide, f1,   x+Inches(0.1), Inches(4.25), Inches(3.6), Inches(0.7),
                    size=34, bold=True, color=col, align=PP_ALIGN.CENTER)
        add_textbox(slide, "Mean F1", x+Inches(0.1), Inches(4.95), Inches(3.6), Inches(0.3),
                    size=10, color=GRAY, align=PP_ALIGN.CENTER)
        add_textbox(slide, status, x+Inches(0.1), Inches(5.35), Inches(3.6), Inches(0.35),
                    size=11, color=DARK, align=PP_ALIGN.CENTER)


def slide_safety(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = WHITE
    header_bar(slide, "Clinical Safety: 98% ≠ Safe for Automation",
               "Mean F1 hides critical failures — weighted analysis reveals patient-harm risk")
    footer_bar(slide)

    # Left panel: the warning
    add_rect(slide, Inches(0.3), Inches(1.55), Inches(5.7), Inches(4.85),
             RGBColor(0xFF, 0xF3, 0xF3))

    add_textbox(slide, "⚠  Critical Failure: NCD 210.3", Inches(0.5), Inches(1.65),
                Inches(5.3), Inches(0.45), size=13, bold=True, color=RED)

    add_textbox(slide,
        "Colorectal Cancer Screening at 80% F1\n"
        "→ 2 of 11 HCPCS codes missed\n"
        "→ Colonoscopy (G0120) & Cologuard (G0464)\n   not extracted",
        Inches(0.5), Inches(2.15), Inches(5.3), Inches(1.3), size=13, color=DARK)

    add_textbox(slide, "Patient Harm Pathway:", Inches(0.5), Inches(3.5),
                Inches(5.3), Inches(0.35), size=12, bold=True, color=RED)

    chain = [
        "Incorrect extraction",
        "→ wrong coverage rule",
        "→ claim denied",
        "→ patient skips colonoscopy",
        "→ late-stage cancer",
        "→ preventable death",
    ]
    for j, step in enumerate(chain):
        add_textbox(slide, step, Inches(0.6), Inches(3.9 + j * 0.3), Inches(5.0), Inches(0.3),
                    size=12, color=RED if j > 2 else DARK, bold=(j > 2))

    # Right panel: error taxonomy
    add_rect(slide, Inches(6.3), Inches(1.55), Inches(6.6), Inches(4.85), LIGHT)
    add_textbox(slide, "Error Taxonomy", Inches(6.5), Inches(1.65),
                Inches(6.2), Inches(0.4), size=13, bold=True, color=NAVY)

    taxonomy = [
        ("A",  RED,   "CRITICAL — Missed cancer-screening codes",
                      "NCD 210.3: G0120, G0464 not found",
                      "Impact: incorrect claim denial, patient harm"),
        ("B",  AMBER, "MODERATE — Obsolete code extracted",
                      "AAA: G0389 (retired 2017) returned",
                      "Impact: billing delay, manual correction needed"),
        ("C",  GREEN, "MINOR — Frequency off by 1 month",
                      "Mammography: 11 vs 12 months",
                      "Impact: timing adjustment, no patient harm"),
    ]
    for idx, (letter, col, head, ex, imp) in enumerate(taxonomy):
        y = Inches(2.1 + idx * 1.4)
        add_rect(slide, Inches(6.4), y, Inches(0.4), Inches(1.1), col)
        add_textbox(slide, letter, Inches(6.4), y+Inches(0.3), Inches(0.4), Inches(0.5),
                    size=16, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        add_textbox(slide, head, Inches(6.9), y+Inches(0.05), Inches(5.8), Inches(0.35),
                    size=12, bold=True, color=col)
        add_textbox(slide, ex,   Inches(6.9), y+Inches(0.4),  Inches(5.8), Inches(0.3),
                    size=11, color=DARK, italic=True)
        add_textbox(slide, imp,  Inches(6.9), y+Inches(0.72), Inches(5.8), Inches(0.3),
                    size=11, color=GRAY)


def slide_recommendation(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = WHITE
    header_bar(slide, "Strategic Recommendation for Cotiviti",
               "Three-phase deployment roadmap balancing speed-to-value with patient safety")
    footer_bar(slide)

    phases = [
        (GREEN,  "A — DEPLOY NOW",
                 "Audit Triage Tool",
                 "Risk: LOW  |  Timeline: Immediate",
                 [
                     "Flag top 1.8% of providers (2σ outlier)",
                     "Human auditors review ALL flagged cases",
                     "No automated denials — human in the loop",
                     "14× ROI · $52K savings per 1,000 policies",
                     "Regulatory exposure: minimal",
                 ]),
        (AMBER,  "B — 6-MONTH ROADMAP",
                 "Hybrid Automation",
                 "Risk: MEDIUM  |  Prerequisite: NCCI validation",
                 [
                     "Tier 2/3 policies auto-approved (100% F1)",
                     "Tier 1 cancer policies: mandatory review",
                     "Confidence routing: auto / review / escalate",
                     "Expected ROI: 20× after validation",
                     "Requires audit trail + medical coder cert.",
                 ]),
        (RED,    "C — 18+ MONTHS",
                 "Full Automation",
                 "Risk: HIGH  |  Not recommended yet",
                 [
                     "Requires ≥99% weighted F1 (currently 96.4%)",
                     "FDA 510(k) review for clinical decision support",
                     "HIPAA-compliant audit logging required",
                     "Continuous model monitoring + rollback",
                     "Do NOT deploy until Option B validated",
                 ]),
    ]

    for i, (col, phase, title, risk, bullets) in enumerate(phases):
        x = Inches(0.25 + i * 4.35)
        # header bar for this card
        add_rect(slide, x, Inches(1.55), Inches(4.15), Inches(0.55), col)
        add_textbox(slide, phase, x+Inches(0.1), Inches(1.58), Inches(3.95), Inches(0.45),
                    size=12, bold=True, color=WHITE)
        # card body
        add_rect(slide, x, Inches(2.1), Inches(4.15), Inches(4.3), LIGHT)
        add_textbox(slide, title, x+Inches(0.12), Inches(2.15), Inches(3.95), Inches(0.45),
                    size=14, bold=True, color=col)
        add_textbox(slide, risk,  x+Inches(0.12), Inches(2.6),  Inches(3.95), Inches(0.35),
                    size=11, color=GRAY, italic=True)

        for j, b in enumerate(bullets):
            add_textbox(slide, f"▸  {b}",
                        x+Inches(0.12), Inches(3.05 + j*0.5),
                        Inches(3.95), Inches(0.44),
                        size=11.5, color=DARK)

    # Bottom bar: key message
    add_rect(slide, Inches(0), Inches(6.45), SLIDE_W, Inches(0.72), NAVY)
    add_textbox(slide,
        '96.4% Weighted F1 = Excellent for TRIAGE  ·  Not yet sufficient for AUTOMATION  ·  '
        'Option A today → Option B in 6 months → Reassess Option C at 99%+',
        Inches(0.3), Inches(6.5), Inches(12.7), Inches(0.55),
        size=13, bold=True, color=WHITE, align=PP_ALIGN.CENTER)


def slide_poc(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = WHITE
    header_bar(slide, "POC Demo: Live System Capabilities",
               "End-to-end pipeline running on real CMS policy texts — reproducible from GitHub")
    footer_bar(slide)

    # Left: what the POC does
    add_textbox(slide, "What PolicyForge Does", Inches(0.4), Inches(1.55),
                Inches(6.0), Inches(0.4), size=13, bold=True, color=NAVY)

    steps = [
        ("1", "Ingest",      "Reads raw NCD/CFR policy text from CMS.gov"),
        ("2", "Retrieve",    "BM25 + FAISS finds coverage-relevant sections"),
        ("3", "Extract",     "Mistral LLM returns structured HCPCS + freq JSON"),
        ("4", "Validate",    "Critic agent checks completeness, retries if empty"),
        ("5", "Adjudicate",  "Flags providers >2σ utilization (1.8% flag rate)"),
        ("6", "Explain",     "Plain-English audit memo for human reviewer"),
    ]
    for idx, (num, step, desc) in enumerate(steps):
        y = Inches(2.0 + idx * 0.75)
        add_rect(slide, Inches(0.4), y, Inches(0.45), Inches(0.55), TEAL)
        add_textbox(slide, num, Inches(0.4), y+Inches(0.05), Inches(0.45), Inches(0.45),
                    size=14, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        add_textbox(slide, f"{step}: {desc}",
                    Inches(0.95), y+Inches(0.08), Inches(5.6), Inches(0.45),
                    size=12, color=DARK)

    # Right: sample output box
    add_rect(slide, Inches(6.8), Inches(1.55), Inches(6.1), Inches(5.4), RGBColor(0x0D, 0x1B, 0x2A))
    add_textbox(slide, "Sample Extraction Output  (NCD 150.3 — Bone Mass)",
                Inches(6.9), Inches(1.62), Inches(5.8), Inches(0.38),
                size=10, bold=True, color=TEAL)

    code = (
        '{\n'
        '  "policy_id": "NCD_150.3",\n'
        '  "target_hcpcs_codes": [\n'
        '    "77080","77081","77085",\n'
        '    "77086","76977","77078","77079"\n'
        '  ],\n'
        '  "frequency_limit_months": 24,\n'
        '  "age_min": null,\n'
        '  "extraction_f1": 0.933,\n'
        '  "review_required": false\n'
        '}'
    )
    add_textbox(slide, code, Inches(6.9), Inches(2.07), Inches(5.8), Inches(4.5),
                size=11, color=RGBColor(0x00, 0xFF, 0x88))


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def build_presentation():
    prs = Presentation()
    prs.slide_width  = SLIDE_W
    prs.slide_height = SLIDE_H

    slide_title(prs)
    slide_problem(prs)
    slide_solution(prs)
    slide_results(prs)
    slide_safety(prs)
    slide_recommendation(prs)
    slide_poc(prs)

    path = "../PolicyForge_Presentation.pptx"
    prs.save(path)
    print(f"✅ PowerPoint saved: {path}  ({len(prs.slides)} slides)")
    return path


if __name__ == "__main__":
    build_presentation()
