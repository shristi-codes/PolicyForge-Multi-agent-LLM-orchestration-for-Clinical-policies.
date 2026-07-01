#!/usr/bin/env python3
"""
Improved LLM Extraction with Few-Shot Prompting

Uses examples to guide the LLM toward better extractions.
"""

import sys
sys.path.insert(0, '.')
import json
import requests
import time
from pathlib import Path
from src.schema import PolicyCriteria

API_KEY = "f7aoZhlIpeTRvtIuee2pqSrppCFKhGQ3"
API_URL = "https://api.mistral.ai/v1/chat/completions"

def create_few_shot_prompt(policy_text: str, policy_id: str) -> str:
    """Create prompt with few-shot examples."""
    
    return f"""You are a Medicare policy analyst. Extract coverage criteria from policy text.

EXAMPLE 1:
Policy Text: "Medicare covers bone mass measurements once every 23 months for qualified individuals. Covered codes: 77080, 77081. Eligible beneficiaries include: estrogen-deficient women at clinical risk for osteoporosis, individuals with vertebral abnormalities, individuals receiving long-term glucocorticoid therapy, individuals with primary hyperparathyroidism, individuals being monitored to assess response to FDA-approved osteoporosis drug therapy."

Extraction:
{{
  "policy_id": "NCD_150.3",
  "frequency_limit_months": 23,
  "target_hcpcs_codes": ["77080", "77081"],
  "age_min": null,
  "age_max": null,
  "eligible_conditions": [
    "Estrogen-deficient women at clinical risk for osteoporosis",
    "Individuals with vertebral abnormalities",
    "Individuals receiving long-term glucocorticoid therapy",
    "Individuals with primary hyperparathyroidism",
    "Individuals being monitored to assess response to FDA-approved osteoporosis drug therapy"
  ],
  "eligible_icd10_diagnoses": [],
  "exclusions": [],
  "citations": []
}}

EXAMPLE 2:
Policy Text: "Medicare covers diabetes screening tests. Eligible individuals include those with hypertension, dyslipidemia, obesity (BMI ≥30), or pre-diabetes. Two tests within 12-month period are covered. Covered tests include fasting glucose (82947), glucose tolerance (82950, 82951), and HbA1c (83036)."

Extraction:
{{
  "policy_id": "Diabetes_Screening",
  "frequency_limit_months": 6,
  "target_hcpcs_codes": ["82947", "82950", "82951", "83036"],
  "age_min": null,
  "age_max": null,
  "eligible_conditions": [
    "Hypertension",
    "Dyslipidemia",
    "Obesity (BMI ≥ 30)"
  ],
  "eligible_icd10_diagnoses": [],
  "exclusions": [],
  "citations": []
}}

NOW EXTRACT FROM THIS POLICY:

Policy ID: {policy_id}
Policy Text:
{policy_text[:5000]}

IMPORTANT:
- Extract frequency_limit_months as a number (if "twice per year" = 6, "once every 23 months" = 23)
- List ALL HCPCS/CPT codes mentioned
- List conditions exactly as stated in policy
- Return ONLY valid JSON matching the schema above
- If information is not found, use null or []

Return JSON:"""

def extract_with_improved_prompt(policy_text: str, policy_id: str, retry=3) -> PolicyCriteria:
    """Extract with improved few-shot prompt."""
    
    prompt = create_few_shot_prompt(policy_text, policy_id)
    
    for attempt in range(retry):
        try:
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "mistral-large-latest",
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.1  # Lower temperature for more consistent extraction
            }
            
            response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 429:
                if attempt < retry - 1:
                    wait_time = (attempt + 1) * 10
                    print(f'  Rate limited, waiting {wait_time}s...')
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception("Rate limit exceeded")
            
            response.raise_for_status()
            
            result = response.json()
            result_text = result['choices'][0]['message']['content']
            criteria_dict = json.loads(result_text)
            return PolicyCriteria(**criteria_dict)
            
        except Exception as e:
            if attempt < retry - 1:
                print(f'  Error (attempt {attempt+1}): {str(e)[:100]}')
                time.sleep(5)
            else:
                print(f'  Final error: {e}')
                return None
    
    return None

def main():
    print('='*80)
    print('IMPROVED LLM EXTRACTION (Few-Shot Prompting)')
    print('='*80)
    print()
    
    policies = [
        ('NCD_150.3', 'data/policies/NCD_150.3.txt'),
        ('NCD_210.3', 'data/policies/NCD_210.3.txt'),
        ('Diabetes_Screening', 'data/policies/CFR_410.18_Diabetes_Screening.txt'),
        ('Cardiac_Rehab', 'data/policies/CFR_410.49_Cardiac_Rehab.txt')
    ]
    
    successes = 0
    
    for i, (policy_id, policy_path) in enumerate(policies):
        print(f'[{i+1}/4] {policy_id}')
        
        with open(policy_path) as f:
            policy_text = f.read()
        
        criteria = extract_with_improved_prompt(policy_text, policy_id)
        
        if criteria:
            output_path = Path(f'data/policies/{policy_id}_automated_v2.json')
            with output_path.open('w') as f:
                json.dump(criteria.model_dump(), f, indent=2)
            
            print(f'  ✓ Extracted: {criteria.frequency_limit_months} months, {len(criteria.target_hcpcs_codes)} codes')
            successes += 1
        else:
            print(f'  ✗ Failed')
        
        # Rate limit prevention
        if i < len(policies) - 1:
            time.sleep(3)
        print()
    
    print('='*80)
    print(f'Successfully extracted {successes}/4 policies with improved prompts')
    print('='*80)

if __name__ == '__main__':
    main()
