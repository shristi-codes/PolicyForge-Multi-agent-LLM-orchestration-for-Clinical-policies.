#!/usr/bin/env python3
"""
Complete LLM Extraction - Extract all remaining policies to reach 15 total
"""

import sys
sys.path.insert(0, '.')
import json
import requests
import time
from pathlib import Path

API_KEY = "f7aoZhlIpeTRvtIuee2pqSrppCFKhGQ3"
API_URL = "https://api.mistral.ai/v1/chat/completions"

def extract_with_llm(policy_text: str, policy_id: str) -> dict:
    """Use Mistral LLM to extract policy criteria."""
    
    prompt = f"""You are a Medicare policy analyst. Extract structured criteria from this policy text.

Policy ID: {policy_id}
Policy Text:
{policy_text[:5000]}

Extract these fields precisely:
1. frequency_limit_months: How often (12=annual, 24=biennial, 60=5yr, null=one-time or as-needed)
2. target_hcpcs_codes: ALL HCPCS/CPT codes mentioned (list)
3. age_min: Minimum age (null if none)
4. age_max: Maximum age (null if none)
5. eligible_conditions: Medical conditions qualifying for coverage (brief list)
6. exclusions: What's NOT covered (brief list)

Return ONLY valid JSON:
{{
  "policy_id": "{policy_id}",
  "frequency_limit_months": 12,
  "target_hcpcs_codes": ["G0103"],
  "age_min": 50,
  "age_max": null,
  "eligible_conditions": ["description"],
  "eligible_icd10_diagnoses": [],
  "exclusions": ["exclusion"],
  "citations": []
}}"""

    for attempt in range(3):
        try:
            response = requests.post(
                API_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {API_KEY}"
                },
                json={
                    "model": "mistral-large-latest",
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.1
                },
                timeout=45
            )
            
            if response.status_code == 429:
                wait_time = 60 * (attempt + 1)
                print(f"  Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            response.raise_for_status()
            result = response.json()
            content = result['choices'][0]['message']['content']
            return json.loads(content)
            
        except Exception as e:
            print(f"  Attempt {attempt+1} error: {str(e)[:100]}")
            if attempt < 2:
                time.sleep(10)
            continue
    
    return None

def main():
    print('='*80)
    print('COMPLETE LLM EXTRACTION - Building to 15 Policies')
    print('='*80)
    print()
    
    # All policies to extract (including ones already done for verification)
    all_policies = [
        ('data/policies/NCD_150.3.txt', 'NCD_150.3'),
        ('data/policies/NCD_210.3.txt', 'NCD_210.3'),
        ('data/policies/CFR_410.18_Diabetes_Screening.txt', 'Diabetes_Screening'),
        ('data/policies/CFR_410.49_Cardiac_Rehab.txt', 'Cardiac_Rehab'),
        ('data/policies/NCD_210.13_Hepatitis_C_Screening.txt', 'Hepatitis_C'),
        ('data/policies/NCD_210.14_Lung_Cancer_Screening.txt', 'Lung_Cancer'),
        ('data/policies/CFR_410.19_AAA_Screening.txt', 'AAA_Screening'),
        ('data/policies/NCD_210.7_HIV_Screening.txt', 'HIV_Screening'),
    ]
    
    results = []
    extracted_count = 0
    
    for policy_path, policy_id in all_policies:
        if not Path(policy_path).exists():
            print(f'⚠️  Skipping {policy_id} - file not found')
            continue
        
        # Check if already extracted
        output_path = f'data/policies/{policy_id}_extracted_LLM.json'
        if Path(output_path).exists():
            print(f'✓ {policy_id} - already extracted, skipping')
            results.append({'policy_id': policy_id, 'success': True, 'skipped': True})
            continue
        
        print(f'Extracting: {policy_id}')
        
        with open(policy_path) as f:
            policy_text = f.read()
        
        print(f'  🤖 Running LLM extraction...')
        extracted = extract_with_llm(policy_text, policy_id)
        
        if extracted:
            with open(output_path, 'w') as f:
                json.dump(extracted, f, indent=2)
            
            hcpcs = extracted.get('target_hcpcs_codes', [])
            freq = extracted.get('frequency_limit_months', 'null')
            print(f'  ✅ Success: {hcpcs[:2]}{"..." if len(hcpcs) > 2 else ""}, freq={freq} mo')
            results.append({'policy_id': policy_id, 'success': True, 'skipped': False})
            extracted_count += 1
        else:
            print(f'  ❌ Failed after 3 attempts')
            results.append({'policy_id': policy_id, 'success': False, 'skipped': False})
        
        print()
        time.sleep(4)  # Rate limiting
    
    success_count = sum(1 for r in results if r['success'])
    new_count = sum(1 for r in results if r['success'] and not r.get('skipped', False))
    
    print('='*80)
    print(f'EXTRACTION COMPLETE')
    print(f'New extractions: {new_count}')
    print(f'Total successful: {success_count}/{len(results)}')
    print('='*80)
    
    return results

if __name__ == '__main__':
    main()
