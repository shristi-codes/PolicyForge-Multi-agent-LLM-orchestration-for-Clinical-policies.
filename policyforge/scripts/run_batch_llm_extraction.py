#!/usr/bin/env python3
"""
Batch LLM Extraction - Extract all new policies at once
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
{policy_text[:4000]}

Extract these fields:
1. frequency_limit_months: How often can the service be billed? (12 for annual, 24 for biennial, 60 for 5-year, null for as-needed)
2. target_hcpcs_codes: List of HCPCS/CPT codes covered
3. age_min: Minimum age for coverage (null if none)
4. age_max: Maximum age for coverage (null if none)
5. eligible_conditions: List of medical conditions that qualify (brief)
6. exclusions: List of exclusions (brief)

Return ONLY valid JSON in this format:
{{
  "policy_id": "{policy_id}",
  "frequency_limit_months": 12,
  "target_hcpcs_codes": ["code1"],
  "age_min": null,
  "age_max": null,
  "eligible_conditions": ["brief description"],
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
            timeout=30
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
        print(f"  ❌ Error: {str(e)}")
        return None

def main():
    print('='*80)
    print('BATCH LLM EXTRACTION - Demonstrating Scale')
    print('='*80)
    print()
    
    policies_to_extract = [
        ('data/policies/CFR_410.17_Cardiovascular_Screening.txt', 'Cardiovascular'),
        ('data/policies/Glaucoma_Screening.txt', 'Glaucoma'),
        ('data/policies/Pap_Smear_Screening.txt', 'Pap_Smear'),
    ]
    
    results = []
    
    for policy_path, policy_id in policies_to_extract:
        if not Path(policy_path).exists():
            print(f'⚠️  Skipping {policy_id} - file not found')
            continue
            
        print(f'Extracting: {policy_id}')
        
        with open(policy_path) as f:
            policy_text = f.read()
        
        print(f'  🤖 Running LLM extraction...')
        extracted = extract_with_llm(policy_text, policy_id)
        
        if extracted:
            output_path = f'data/policies/{policy_id}_extracted_LLM.json'
            with open(output_path, 'w') as f:
                json.dump(extracted, f, indent=2)
            
            print(f'  ✅ Success: {extracted["target_hcpcs_codes"][:3]}{"..." if len(extracted["target_hcpcs_codes"]) > 3 else ""}, freq={extracted["frequency_limit_months"]} mo')
            results.append({'policy_id': policy_id, 'success': True})
        else:
            print(f'  ❌ Failed')
            results.append({'policy_id': policy_id, 'success': False})
        
        print()
        time.sleep(3)  # Rate limiting
    
    success_count = sum(1 for r in results if r['success'])
    print('='*80)
    print(f'BATCH COMPLETE: {success_count}/{len(results)} successful extractions')
    print('='*80)
    
    return results

if __name__ == '__main__':
    main()
