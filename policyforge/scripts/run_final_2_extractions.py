#!/usr/bin/env python3
"""
Final 2 Policies - Complete extraction to 15 total
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
1. frequency_limit_months: How often (12=annual, null=varies)
2. target_hcpcs_codes: ALL HCPCS/CPT codes mentioned
3. age_min: Minimum age (null if none)
4. age_max: Maximum age (null if none)
5. eligible_conditions: Qualifying conditions (brief list)
6. exclusions: What's NOT covered (brief list)

Return ONLY valid JSON:
{{
  "policy_id": "{policy_id}",
  "frequency_limit_months": 12,
  "target_hcpcs_codes": ["G0444"],
  "age_min": null,
  "age_max": null,
  "eligible_conditions": ["description"],
  "eligible_icd10_diagnoses": [],
  "exclusions": ["exclusion"],
  "citations": []
}}"""

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
            print(f"  Rate limited, waiting 60s...")
            time.sleep(60)
            return extract_with_llm(policy_text, policy_id)
        
        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content']
        return json.loads(content)
        
    except Exception as e:
        print(f"  Error: {str(e)[:100]}")
        return None

def main():
    print('='*80)
    print('FINAL 2 POLICIES - Reaching 15 Total')
    print('='*80)
    print()
    
    policies = [
        ('data/policies/NCD_210.9_Depression_Screening.txt', 'Depression_Screening'),
        ('data/policies/NCD_210.12_Obesity_Behavioral_Therapy.txt', 'Obesity_Therapy'),
    ]
    
    for policy_path, policy_id in policies:
        print(f'Extracting: {policy_id}')
        
        with open(policy_path) as f:
            policy_text = f.read()
        
        print(f'  🤖 Running LLM extraction...')
        extracted = extract_with_llm(policy_text, policy_id)
        
        if extracted:
            output_path = f'data/policies/{policy_id}_extracted_LLM.json'
            with open(output_path, 'w') as f:
                json.dump(extracted, f, indent=2)
            
            hcpcs = extracted.get('target_hcpcs_codes', [])
            freq = extracted.get('frequency_limit_months', 'null')
            print(f'  ✅ Success: {hcpcs}, freq={freq} mo')
        else:
            print(f'  ❌ Failed')
        
        print()
        time.sleep(3)
    
    print('='*80)
    print('🎉 15 POLICIES COMPLETE!')
    print('='*80)

if __name__ == '__main__':
    main()
