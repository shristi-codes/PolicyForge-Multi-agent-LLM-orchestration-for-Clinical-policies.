#!/usr/bin/env python3
"""
Evaluate LLM Extraction Accuracy Against Manual Gold Standards

Real evaluation comparing LLM-extracted criteria vs. hand-labeled ground truth.
"""

import sys
sys.path.insert(0, '.')
import json
from pathlib import Path

def normalize_hcpcs_extraction(llm_data):
    """
    Normalize HCPCS extraction to handle different schemas.
    
    Handles:
    1. Flat format: {"target_hcpcs_codes": ["code1", "code2"]}
    2. Nested format: {"sections": [{"target_hcpcs_codes": ["code1"]}, ...]}
    """
    # Check for nested sections format (like NCD 210.3)
    if 'sections' in llm_data:
        all_codes = []
        for section in llm_data['sections']:
            codes = section.get('target_hcpcs_codes', [])
            all_codes.extend(codes)
        return all_codes
    
    # Standard flat format
    return llm_data.get('target_hcpcs_codes', [])

def calculate_f1(extracted, gold):
    """Calculate F1 score for list comparison."""
    if not gold and not extracted:
        return 1.0
    if not gold or not extracted:
        return 0.0
    
    extracted_set = set(extracted)
    gold_set = set(gold)
    
    true_positives = len(extracted_set & gold_set)
    false_positives = len(extracted_set - gold_set)
    false_negatives = len(gold_set - extracted_set)
    
    if true_positives == 0:
        return 0.0
    
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    
    if precision + recall == 0:
        return 0.0
    
    return 2 * (precision * recall) / (precision + recall)

def main():
    print('='*80)
    print('LLM EXTRACTION ACCURACY EVALUATION')
    print('='*80)
    print()
    print('Comparing LLM-extracted criteria against manual gold standards...')
    print()
    
    # Load gold standards
    with open('eval/gold_standards_15_policies.json', 'r') as f:
        gold_data = json.load(f)
    
    results = []
    hcpcs_scores = []
    frequency_matches = []
    
    for gold_policy in gold_data['policies']:
        policy_id = gold_policy['policy_id']
        
        # Map policy IDs to LLM extraction files
        file_mapping = {
            'NCD_150.3': 'data/policies/NCD_150.3_extracted_LLM.json',
            'NCD_210.3': 'data/policies/NCD_210.3_extracted_LLM.json',
            'Diabetes_Screening': 'data/policies/Diabetes_Screening_extracted_LLM.json',
            'Cardiac_Rehab': 'data/policies/Cardiac_Rehab_extracted_LLM.json',
            'NCD_220.4': 'data/policies/NCD_220.4_extracted_LLM.json',
            'NCD_210.1': 'data/policies/NCD_210.1_extracted_LLM.json',
            'Cardiovascular': 'data/policies/Cardiovascular_extracted_LLM.json',
            'Glaucoma': 'data/policies/Glaucoma_extracted_LLM.json',
            'Pap_Smear': 'data/policies/Pap_Smear_extracted_LLM.json',
            'Hepatitis_C': 'data/policies/Hepatitis_C_extracted_LLM.json',
            'Lung_Cancer': 'data/policies/Lung_Cancer_extracted_LLM.json',
            'AAA_Screening': 'data/policies/AAA_Screening_extracted_LLM.json',
            'HIV_Screening': 'data/policies/HIV_Screening_extracted_LLM.json',
            'Depression_Screening': 'data/policies/Depression_Screening_extracted_LLM.json',
            'Obesity_Therapy': 'data/policies/Obesity_Therapy_extracted_LLM.json'
        }
        
        llm_file = file_mapping.get(policy_id)
        
        if not llm_file or not Path(llm_file).exists():
            print(f'⚠️  {policy_id}: LLM extraction file not found')
            continue
        
        with open(llm_file, 'r') as f:
            llm_data = json.load(f)
        
        # Extract fields
        gold_hcpcs = gold_policy['gold_criteria']['target_hcpcs_codes']
        
        # Normalize LLM extraction (handle nested schemas)
        llm_hcpcs = normalize_hcpcs_extraction(llm_data)
        
        gold_freq = gold_policy['gold_criteria']['frequency_limit_months']
        llm_freq = llm_data.get('frequency_limit_months')
        
        # Calculate metrics
        hcpcs_f1 = calculate_f1(llm_hcpcs, gold_hcpcs)
        freq_match = 1.0 if gold_freq == llm_freq else 0.0
        
        hcpcs_scores.append(hcpcs_f1)
        frequency_matches.append(freq_match)
        
        result = {
            'policy_id': policy_id,
            'policy_name': gold_policy['policy_name'],
            'hcpcs_f1': round(hcpcs_f1, 3),
            'frequency_match': freq_match,
            'gold_hcpcs_count': len(gold_hcpcs),
            'llm_hcpcs_count': len(llm_hcpcs),
            'gold_frequency': gold_freq,
            'llm_frequency': llm_freq
        }
        results.append(result)
        
        status = '✅' if hcpcs_f1 >= 0.8 and freq_match == 1.0 else '⚠️'
        print(f'{status} {policy_id}: HCPCS F1={hcpcs_f1:.3f}, Freq Match={freq_match:.0f}')
    
    # Calculate aggregate metrics
    mean_hcpcs_f1 = sum(hcpcs_scores) / len(hcpcs_scores) if hcpcs_scores else 0
    freq_accuracy = sum(frequency_matches) / len(frequency_matches) if frequency_matches else 0
    
    print()
    print('='*80)
    print('AGGREGATE RESULTS')
    print('='*80)
    print(f'Policies Evaluated: {len(results)}')
    print(f'Mean HCPCS F1: {mean_hcpcs_f1:.3f}')
    print(f'Frequency Accuracy: {freq_accuracy:.3f} ({int(sum(frequency_matches))}/{len(frequency_matches)})')
    print()
    
    # Breakdown by performance
    excellent = [r for r in results if r['hcpcs_f1'] >= 0.9]
    good = [r for r in results if 0.7 <= r['hcpcs_f1'] < 0.9]
    needs_improvement = [r for r in results if r['hcpcs_f1'] < 0.7]
    
    print(f'Excellent (F1 >= 0.9): {len(excellent)} policies')
    print(f'Good (0.7 <= F1 < 0.9): {len(good)} policies')
    print(f'Needs Improvement (F1 < 0.7): {len(needs_improvement)} policies')
    print()
    
    # Save results
    output = {
        'evaluation_date': '2026-07-01',
        'method': 'LLM extraction vs. manual gold standards',
        'aggregate_metrics': {
            'policies_evaluated': len(results),
            'mean_hcpcs_f1': round(mean_hcpcs_f1, 3),
            'frequency_accuracy': round(freq_accuracy, 3),
            'excellent_count': len(excellent),
            'good_count': len(good),
            'needs_improvement_count': len(needs_improvement)
        },
        'per_policy_results': results,
        'note': 'Real evaluation comparing LLM vs. manual extraction'
    }
    
    with open('eval/results/llm_vs_manual_15_policies.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print('='*80)
    print('✅ Evaluation complete')
    print('='*80)
    print()
    print('Results saved to: eval/results/llm_vs_manual_15_policies.json')
    print()
    print('KEY FINDINGS:')
    print(f'- LLM achieves {mean_hcpcs_f1:.1%} F1 on HCPCS extraction')
    print(f'- LLM matches frequency correctly {freq_accuracy:.1%} of the time')
    print(f'- {len(excellent)} policies have excellent extraction (F1 >= 0.9)')

if __name__ == '__main__':
    main()
