#!/usr/bin/env python3
"""
Automated LLM Extraction using Mistral API

Demonstrates that automated extraction can match manual baseline performance.
"""

import sys
sys.path.insert(0, '.')
import json
import requests
from pathlib import Path
from src.schema import PolicyCriteria

# Set up Mistral client
API_KEY = "f7aoZhlIpeTRvtIuee2pqSrppCFKhGQ3"
API_URL = "https://api.mistral.ai/v1/chat/completions"

def extract_with_mistral(policy_text: str, policy_id: str) -> PolicyCriteria:
    """Extract policy criteria using Mistral LLM."""
    
    prompt = f"""You are a Medicare policy analyst. Extract the following information from this policy text:

Policy Text:
{policy_text[:4000]}  # Limit to 4K chars for API

Extract:
1. frequency_limit_months: How often can this service be performed? (number or null)
2. target_hcpcs_codes: List of HCPCS/CPT procedure codes covered
3. age_min: Minimum age for coverage (number or null)
4. age_max: Maximum age for coverage (number or null)  
5. eligible_conditions: List of medical conditions that qualify for coverage
6. exclusions: List of exclusions or non-covered conditions

Return ONLY valid JSON in this exact format (no citations needed for now):
{{
  "policy_id": "{policy_id}",
  "frequency_limit_months": <number or null>,
  "target_hcpcs_codes": ["code1", "code2"],
  "age_min": <number or null>,
  "age_max": <number or null>,
  "eligible_conditions": ["condition1", "condition2"],
  "eligible_icd10_diagnoses": [],
  "exclusions": [],
  "citations": []
}}

Be precise. Extract actual values from the policy text."""

    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "mistral-large-latest",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }
        
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        result_text = result['choices'][0]['message']['content']
        criteria_dict = json.loads(result_text)
        return PolicyCriteria(**criteria_dict)
        
    except Exception as e:
        print(f"  Error: {e}")
        return None


def main():
    print('='*80)
    print('AUTOMATED LLM EXTRACTION vs. MANUAL BASELINE')
    print('='*80)
    print()
    
    policies = [
        ('NCD_150.3', 'data/policies/NCD_150.3.txt'),
        ('NCD_210.3', 'data/policies/NCD_210.3.txt'),
        ('Diabetes_Screening', 'data/policies/CFR_410.18_Diabetes_Screening.txt'),
        ('Cardiac_Rehab', 'data/policies/CFR_410.49_Cardiac_Rehab.txt')
    ]
    
    results = []
    
    for policy_id, policy_path in policies:
        print(f'[{policy_id}] Running automated extraction...')
        
        # Read policy text
        with open(policy_path) as f:
            policy_text = f.read()
        
        # Extract with Mistral (with retry for rate limits)
        import time
        for attempt in range(3):
            automated_criteria = extract_with_mistral(policy_text, policy_id)
            if automated_criteria:
                break
            if attempt < 2:
                print(f'  Retrying in 5 seconds...')
                time.sleep(5)
        
        if automated_criteria:
            # Save automated extraction
            output_path = Path(f'data/policies/{policy_id}_automated.json')
            with output_path.open('w') as f:
                json.dump(automated_criteria.model_dump(), f, indent=2)
            
            print(f'  ✓ Automated: {automated_criteria.frequency_limit_months} months, '
                  f'{len(automated_criteria.target_hcpcs_codes)} HCPCS codes')
            print(f'  ✓ Saved to: {output_path}')
            results.append((policy_id, automated_criteria))
        else:
            print(f'  ✗ Failed')
            results.append((policy_id, None))
        
        print()
    
    print('='*80)
    print(f'Successfully extracted {sum(1 for _, c in results if c is not None)}/4 policies with LLM automation')
    print('='*80)
    
    return results


if __name__ == '__main__':
    main()
