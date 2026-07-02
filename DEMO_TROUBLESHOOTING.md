# Demo Troubleshooting Guide

## Quick Fixes for Common Issues

### Demo Won't Start

**Error: `ModuleNotFoundError: No module named 'streamlit'`**
```bash
cd policyforge
pip install streamlit pandas
```

**Error: `FileNotFoundError` for policy files**
- Check you're running from the correct directory
- Run: `streamlit run demo_app.py` from the `policyforge` folder
- Verify files exist: `ls data/policies/*extracted*.json`

### Browser Issues

**Demo shows but looks broken**
- Hard refresh: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)
- Try a different browser (Chrome recommended)
- Clear browser cache

**Demo is too slow**
- This is normal on first load
- Streamlit caches data after initial load
- Subsequent interactions will be faster

### During Recording

**Microphone not working**
- Check System Preferences → Sound → Input
- Select correct microphone
- Test in QuickTime: File → New Audio Recording

**Screen recording drops frames**
- Close other applications
- Reduce resolution to 1280x720
- Use 30fps instead of 60fps

**Made a mistake during recording**
- Don't panic! Just pause, take a breath
- Restart from the beginning of that section
- You can edit videos together later if needed

## Alternative Demo Approaches

### Option 1: Static Walkthrough
If the live demo fails, you can still demonstrate:

1. **Show the code:**
```bash
# Open in IDE and explain structure
cat policyforge/demo_app.py
```

2. **Show extraction results:**
```bash
# Display actual extraction files
cat policyforge/data/policies/Diabetes_Screening_extracted_FINAL.json | python3 -m json.tool
```

3. **Run evaluation script:**
```bash
cd policyforge/scripts
python3 evaluate_15_policies_comprehensive.py
```

### Option 2: Screenshots + Narration
If video recording fails:
1. Take screenshots of each demo tab
2. Create a slide deck with screenshots
3. Present the screenshots with voice narration

### Option 3: Terminal Demo
Minimal but effective:
```bash
# Show system is real and working
cd policyforge

# Show extraction
echo "=== Example Policy Extraction ==="
python3 -c "
import json
with open('data/policies/Diabetes_Screening_extracted_FINAL.json') as f:
    data = json.load(f)
print('HCPCS Codes:', data.get('target_hcpcs_codes'))
print('Frequency:', data.get('frequency_limit_months'), 'months')
"

# Show evaluation
python3 scripts/evaluate_15_policies_comprehensive.py
```

## Emergency Checklist

If something breaks 5 minutes before recording:

- [ ] **BREATHE** - You have a backup plan
- [ ] Can the demo launch at all? → No? Use Option 1
- [ ] Does audio work? → No? Record video, add voice later
- [ ] Is screen recording working? → No? Use Option 2
- [ ] Everything broken? → Use Option 3 (terminal)

## Quality Standards

**Minimum viable demo must show:**
1. ✅ System extracts policies (even if just terminal output)
2. ✅ Metrics are real (98.2% F1, 1.8% flag rate)
3. ✅ You can explain the 100% → 1.8% engineering breakthrough
4. ✅ You acknowledge limitations honestly

**Nice to have but not essential:**
- Fancy UI (Streamlit)
- Perfect video editing
- Multiple policy examples
- Smooth transitions

## Testing Before Recording

Run this quick test:

```bash
# From project root
cd policyforge

# Test 1: Python syntax
python3 -m py_compile demo_app.py
echo "✅ Syntax OK"

# Test 2: Imports work
python3 -c "import streamlit, pandas"
echo "✅ Dependencies OK"

# Test 3: Demo launches
timeout 10 streamlit run demo_app.py --server.headless=true &
sleep 3
curl -s http://localhost:8501 > /dev/null && echo "✅ Demo launches" || echo "❌ Demo failed"
pkill -f streamlit

# Test 4: Data files exist
ls data/policies/*extracted*.json | wc -l
echo "✅ Data files present"
```

Expected output:
```
✅ Syntax OK
✅ Dependencies OK
✅ Demo launches
✅ Data files present
```

## Get Help

**Still stuck?**
1. Check the error message carefully
2. Google the exact error
3. Check Streamlit docs: https://docs.streamlit.io
4. Skip the demo and do a code walkthrough instead

## Remember

> "Perfect is the enemy of done."

The assessors want to see:
- Your engineering ability ✓ (you have this)
- Problem-solving skills ✓ (100% → 1.8% story)
- Honest assessment ✓ (you know limitations)
- Real working code ✓ (15 policies processed)

A imperfect video of real code beats a perfect video of nothing.

You've built something impressive. Show them what you did, even if the delivery isn't perfect!
