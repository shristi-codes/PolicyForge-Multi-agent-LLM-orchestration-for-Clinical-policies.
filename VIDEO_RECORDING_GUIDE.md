# Video Recording Guide for PolicyForge Demo

## Total Time: 4-5 minutes
**Recommended tool:** QuickTime Player (Mac), OBS Studio (Any OS), or Loom

---

## 🎬 Video Script & Timeline

### Introduction (30 seconds)
**[Show: Opening the demo in browser]**

> "Hi, I'm Shristi Kumar. This is PolicyForge - a multi-agent LLM system for automated Medicare policy extraction. 
> 
> The problem: Medicare processes over 1,200 policy updates annually, and manual extraction takes 45 minutes per policy at $56.25 cost with no audit trail.
> 
> PolicyForge reduces this to 8 seconds at $3.75 with 98.2% F1 accuracy and full citation traceability. Let me show you how it works."

### Part 1: Policy Extraction Demo (90 seconds)
**[Show: Tab 1 - Policy Extraction]**

> "First, the extraction pipeline. Let me select the Diabetes Screening policy."

**[Click: CFR 410.18 - Diabetes Screening]**

> "The system extracts structured criteria from unstructured CMS policy text. Here we see:
> - The covered HCPCS codes
> - Age restrictions
> - Frequency limits
> - Full coverage criteria
> 
> And critically - every extraction has source citations with character-level offsets for audit traceability."

**[Expand: Coverage Criteria Details and Source Citation]**

> "Let me show you another policy for comparison."

**[Select: Cardiovascular Screening, then Depression Screening]**

> "This demonstrates the system working across different policy types - metabolic screening, cardiovascular, and behavioral health."

### Part 2: The Engineering Breakthrough (90 seconds)
**[Switch to: Tab 2 - Provider Flagging]**

> "Now here's the key engineering challenge I solved. 
> 
> When I first applied the extracted policy rules literally to 21,521 providers in the CMS Part B dataset, it flagged 100% of providers. Completely unusable.
> 
> The issue: provider-level aggregate data doesn't support procedure-level rule enforcement.
> 
> The solution: I reframed the problem. Instead of binary rule enforcement, I use statistical outlier detection with a 2-sigma threshold."

**[Point to metrics]**

> "Mean services per beneficiary: 1.015
> Threshold at mean plus 2 standard deviations: 1.229
> 
> This identifies the 389 providers - just 1.8% - with statistically unusual billing patterns."

**[Scroll through example table]**

> "Each flagged provider gets cited to the specific policy source. This is defensible for regulatory audit and clinically realistic.
>
> That's the difference between an academic exercise and production-ready engineering."

### Part 3: Evaluation & Clinical Safety (60 seconds)
**[Switch to: Tab 3 - Evaluation Results]**

> "Let's look at the validation. The system was tested on 15 real CMS policies across three clinical tiers:
> - Cancer screening
> - Cardiovascular and metabolic
> - Behavioral health
> 
> Mean F1 of 98.2%, weighted F1 of 96.4% when accounting for clinical severity.
> 
> 14 of 15 policies achieved excellent performance with F1 above 90%."

**[Scroll through policy table]**

> "But I want to be honest about limitations."

**[Expand: Clinical Safety Analysis]**

> "98.2% F1 doesn't automatically mean safe for automation. The weighted F1 gives higher weight to cancer screening where false negatives could delay life-saving care.
> 
> For example, NCD 210.3 Colorectal Cancer at 80% F1 missed 2 codes - that's acceptable for triage, but not yet for unsupervised adjudication."

### Closing (30 seconds)
**[Show: Sidebar metrics overview]**

> "To summarize: PolicyForge demonstrates three core capabilities:
> 
> One - 98.2% extraction accuracy with full citation grounding
> Two - Statistical provider flagging at 1.8% flag rate
> Three - Honest assessment of strengths and limitations
> 
> This is production-ready for Phase 1: audit triage. With 15x cost reduction and clear path to scale.
> 
> Thank you. The full code and technical report are available on GitHub."

---

## 🎥 Recording Tips

### Before You Start
1. **Close unnecessary tabs/windows** - clean browser
2. **Hide bookmarks bar** - cleaner look
3. **Set zoom to 100%** in browser
4. **Silence notifications** - Do Not Disturb mode
5. **Test audio** - clear microphone, no background noise

### During Recording
1. **Speak clearly and confidently** - you're the expert
2. **Use your mouse to point** to specific metrics/numbers
3. **Don't rush** - pause between sections
4. **Show, don't just tell** - interact with the demo
5. **If you make a mistake** - just pause, restart that section

### Screen Recording Settings
- **Resolution:** 1920x1080 (Full HD)
- **Frame rate:** 30 fps minimum
- **Audio:** 44.1 kHz
- **Format:** MP4 (H.264 codec)

### Recommended Recording Flow
1. Launch demo: `streamlit run demo_app.py`
2. Open browser to `http://localhost:8501`
3. Start screen + audio recording
4. Follow the script above
5. Stop recording
6. Review - reshoot if needed (it's okay!)

### Quick Recording Commands

**Mac (QuickTime):**
```bash
# Built-in screen recording: Cmd + Shift + 5
```

**Any OS (OBS Studio - free):**
1. Add Display Capture source
2. Add Audio Input Capture (mic)
3. Click "Start Recording"
4. Click "Stop Recording" when done

---

## 📝 Backup: Presentation Without Live Demo

If technical issues occur, you can still present effectively:

1. **Show the code:** Walk through `demo_app.py` structure
2. **Show extraction files:** Display JSON extractions
3. **Show evaluation results:** Share the metrics
4. **Explain architecture:** Draw the 6-node pipeline

The assessors care more about your engineering thinking than perfect execution.

---

## ✅ Pre-Recording Checklist

- [ ] Demo app launches without errors
- [ ] All 4 policy options load correctly
- [ ] Browser is clean (no distracting tabs/bookmarks)
- [ ] Microphone tested and clear
- [ ] Do Not Disturb mode enabled
- [ ] Script reviewed (but don't memorize - be natural!)
- [ ] GitHub repo URL ready to share
- [ ] Backup plan ready if technical issues

---

## 🚀 You've Got This!

Remember: This is a proof of concept demonstration. The assessors want to see:
- **Your engineering thinking** (the 100% → 1.8% problem-solving)
- **Honest assessment** (knowing the limitations)
- **Clear communication** (explaining complex concepts simply)
- **Production mindset** (not just academic metrics)

You've built something real and impressive. Just show them what you did!
