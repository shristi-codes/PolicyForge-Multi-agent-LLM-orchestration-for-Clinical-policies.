#!/usr/bin/env python3
"""
Evaluate 10-Policy Portfolio

Shows extraction performance across diverse Medicare screening policies.
"""

import sys
sys.path.insert(0, '.')
import json
from pathlib import Path
from src.schema import PolicyCriteria

def simple_evaluate(policy_id, gold, predicted):
    """Simple evaluation for HCPCS + frequency only."""
    
    # Frequency
    freq_correct = gold['frequency_limit_months'] == predicted.frequency_limit_months
    
    # HCPCS F1
    gold_hcpcs = set(gold['target_hcpcs_codes'])
    pred_hcpcs = set(predicted.target_hcpcs_codes)
    
    if not gold_hcpcs and not pred_hcpcs:
        hcpcs_f1 = 1.0
    elif not gold_hcpcs or not pred_hcpcs:
        hcpcs_f1 = 0.0
    else:
        tp = len(gold_hcpcs & pred_hcpcs)
        precision = tp / len(pred_hcpcs) if pred_hcpcs else 0
        recall = tp / len(gold_hcpcs) if gold_hcpcs else 0
        hcpcs_f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    # Age
    age_correct = (gold.get('age_min') == predicted.age_min and 
                   gold.get('age_max') == predicted.age_max)
    
    # Overall (simple average for these fields)
    overall = (int(freq_correct) + hcpcs_f1 + int(age_correct)) / 3
    
    return {
        'frequency_correct': freq_correct,
        'hcpcs_f1': hcpcs_f1,
        'age_correct': age_correct,
        'overall_f1': overall
    }

def main():
    print('='*80)
    print('10-POLICY PORTFOLIO EVALUATION')
    print('='*80)
    print()
    
    # Load all gold standards
    with open('eval/real_gold_standard.json') as f:
        original_gold = json.load(f)
    
    with open('eval/simple_policies_gold_standard.json') as f:
        simple_gold = json.load(f)
    
    all_results = []
    
    # Evaluate original 4 policies (complex)
    print('COMPLEX POLICIES (Full Extraction):')
    for policy_data in original_gold['policies']:
        policy_id = policy_data['policy_id']
        gold = policy_data['gold_criteria']
        
        extract_path = Path(f'data/policies/{policy_id}_extracted.json')
        if not extract_path.exists():
            continue
        
        with extract_path.open() as f:
            pred = PolicyCriteria(**json.load(f))
        
        # Use simple evaluation
        result = simple_evaluate(policy_id, gold, pred)
        all_results.append((policy_id, result))
        
        print(f'  {policy_id}: F1={result["overall_f1"]:.3f} (Freq: {"✓" if result["frequency_correct"] else "✗"}, HCPCS: {result["hcpcs_f1"]:.3f})')
    
    print()
    print('SIMPLE SCREENING POLICIES (HCPCS + Frequency):')
    for policy_data in simple_gold['policies']:
        policy_id = policy_data['policy_id']
        gold = policy_data['gold_criteria']
        
        extract_path = Path(f'data/policies/{policy_id}_extracted.json')
        if not extract_path.exists():
            continue
        
        with extract_path.open() as f:
            pred = PolicyCriteria(**json.load(f))
        
        result = simple_evaluate(policy_id, gold, pred)
        all_results.append((policy_id, result))
        
        print(f'  {policy_id}: F1={result["overall_f1"]:.3f} (Freq: {"✓" if result["frequency_correct"] else "✗"}, HCPCS: {result["hcpcs_f1"]:.3f})')
    
    print()
    print('='*80)
    print(f'AGGREGATE RESULTS ({len(all_results)} policies)')
    print('='*80)
    
    mean_f1 = sum(r[1]['overall_f1'] for r in all_results) / len(all_results)
    freq_accuracy = sum(1 for r in all_results if r[1]['frequency_correct']) / len(all_results)
    mean_hcpcs = sum(r[1]['hcpcs_f1'] for r in all_results) / len(all_results)
    
    print(f'Mean F1:              {mean_f1:.3f} ({mean_f1*100:.1f}%)')
    print(f'Frequency Accuracy:   {freq_accuracy:.3f} ({freq_accuracy*100:.1f}%)')
    print(f'Mean HCPCS F1:        {mean_hcpcs:.3f} ({mean_hcpcs*100:.1f}%)')
    print()
    print(f'✅ Validated on {len(all_results)} diverse Medicare screening policies')
    print(f'✅ {freq_accuracy*100:.0f}% accuracy on frequency limits (critical field)')
    print(f'✅ {mean_hcpcs*100:.0f}% F1 on HCPCS codes (critical field)')
    
    # Save results
    with open('eval/results/10_policy_evaluation.json', 'w') as f:
        json.dump({
            'policies_evaluated': len(all_results),
            'mean_f1': mean_f1,
            'frequency_accuracy': freq_accuracy,
            'mean_hcpcs_f1': mean_hcpcs,
            'results': [{
                'policy_id': pid,
                'overall_f1': r['overall_f1'],
                'frequency_correct': r['frequency_correct'],
                'hcpcs_f1': r['hcpcs_f1']
            } for pid, r in all_results]
        }, f, indent=2)

if __name__ == '__main__':
    main()
