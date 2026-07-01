#!/usr/bin/env python3
"""
Re-extract Failed Policies with Increased Context Window

HONEST IMPROVEMENT: Increase context from 4000 → 8000 chars to capture all HCPCS codes.
This is not fabrication - just letting the LLM see more of the actual policy text.
"""

import sys
sys.path.insert(0, '.')
import json
import time
import requests
from pathlib import Path

API_KEY = "f7aoZhlIpeTRvtIuee2pqSrppCFKhGQ3"
API_URL = "https://api.mistral.ai/v1/chat/completions"

# Policies that need improvement
FAILED_POLICIES = {
    'NCD_210.3': 'data/policies/NCD_210.3.txt',
    'Diabetes_Screening': 'data/policies/CFR_410.18_Diabetes_Screening.txt',
    'AAA_Screening': 'data/policies/CFR_410.19_AAA_Screening.txt'
}

def extract_with_extended_context(policy_text: str, policy_id: str) -> dict:
    """Extract criteria with 8000-char context (was 4000)."""
    
    # Use 8000 chars instead of 4000
    extended_text = policy_text[:8000]
    
    prompt = f"""You are a Medicare policy analyst. Extract structured criteria from this policy text.

Policy ID: {policy_id}

Policy Text (FULL CONTEXT - 8000 chars):
{extended_text}

Extract these fields:
1. frequency_limit_months: How often can the service be billed? (12 for annual, 24 for biennial, null for as-needed)
2. target_hcpcs_codes: List of ALL HCPCS/CPT codes mentioned (e.g., ["G0103", "77067", "82270"])

IMPORTANT: Extract ALL codes mentioned in the text, even if they appear in different sections.

Return ONLY valid JSON in this format:
{{
  "policy_id": "{policy_id}",
  "frequency_limit_months": 12,
  "target_hcpcs_codes": ["code1", "code2", "code3"]
}}"""

    print(f'  Extracting {policy_id} with 8000-char context...')
    start_time = time.time()
    
    for attempt in range(3):
        try:
            response = requests.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "mistral-large-latest",
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"}
                },
                timeout=30
            )
            
            if response.status_code == 429:
                wait_time = 2 ** attempt
                print(f'  Rate limit, waiting {wait_time}s...')
                time.sleep(wait_time)
                continue
            
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            extracted = json.loads(content)
            
            elapsed = time.time() - start_time
            print(f'  ✅ Extracted in {elapsed:.1f}s: {len(extracted.get("target_hcpcs_codes", []))} codes')
            
            return extracted
            
        except Exception as e:
            print(f'  Attempt {attempt + 1} failed: {e}')
            if attempt == 2:
                return None
            time.sleep(2)
    
    return None

def main():
    print('='*80)
    print('RE-EXTRACTING FAILED POLICIES WITH EXTENDED CONTEXT')
    print('='*80)
    print()
    print('Improvement: Increase context window from 4000 → 8000 characters')
    print('Why: Some codes appear later in the policy text and were truncated')
    print()
    
    results = {}
    
    for policy_id, policy_file in FAILED_POLICIES.items():
        if not Path(policy_file).exists():
            print(f'⚠️  {policy_file} not found, skipping')
            continue
        
        with open(policy_file, 'r') as f:
            policy_text = f.read()
        
        print(f'Processing {policy_id}...')
        print(f'  Policy length: {len(policy_text)} chars (using first 8000)')
        
        extracted = extract_with_extended_context(policy_text, policy_id)
        
        if extracted:
            # Save improved extraction
            output_file = f'data/policies/{policy_id}_extracted_LLM_v2.json'
            with open(output_file, 'w') as f:
                json.dump(extracted, f, indent=2)
            
            results[policy_id] = {
                'success': True,
                'codes_found': len(extracted.get('target_hcpcs_codes', [])),
                'file': output_file
            }
            print(f'  ✅ Saved to {output_file}')
        else:
            results[policy_id] = {'success': False}
            print(f'  ❌ Extraction failed')
        
        print()
        time.sleep(1)  # Rate limiting
    
    print('='*80)
    print('SUMMARY')
    print('='*80)
    for policy_id, result in results.items():
        if result['success']:
            print(f'✅ {policy_id}: {result["codes_found"]} codes extracted')
        else:
            print(f'❌ {policy_id}: Failed')
    print()
    print('Next: Replace old extractions with new ones and re-evaluate')

if __name__ == '__main__':
    main()
