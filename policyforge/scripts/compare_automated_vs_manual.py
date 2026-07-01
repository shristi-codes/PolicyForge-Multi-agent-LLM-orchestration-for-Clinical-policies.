#!/usr/bin/env python3
"""
Compare Automated LLM Extraction vs. Manual Baseline

Evaluates whether automated extraction can match manual performance.
"""

import sys
sys.path.insert(0, '.')
import json
from pathlib import Path
from src.schema import PolicyCriteria
from eval.metrics import evaluate_extraction, load_gold_standard

def main():
    print('='*80)
    print('AUTOMATED vs. MANUAL EXTRACTION COMPARISON')
    print('='*80)
    print()
    
    # Load gold standard
    with open('eval/real_gold_standard.json') as f:
        gold_data = json.load(f)
    
    results = []
    
    for policy_data in gold_data['policies']:
        policy_id = policy_data['policy_id']
        gold = policy_data['gold_criteria']
        
        # Load manual extraction
        manual_path = Path(f'data/policies/{policy_id}_extracted.json')
        automated_path = Path(f'data/policies/{policy_id}_automated.json')
        
        if not manual_path.exists():
            print(f'⚠️  {policy_id}: No manual extraction')
            continue
        
        with manual_path.open() as f:
            manual_criteria = PolicyCriteria(**json.load(f))
        
        # Evaluate manual
        manual_metrics = evaluate_extraction(policy_id, gold, manual_criteria)
        
        # Evaluate automated (if available)
        if automated_path.exists():
            with automated_path.open() as f:
                auto_criteria = PolicyCriteria(**json.load(f))
            auto_metrics = evaluate_extraction(policy_id, gold, auto_criteria)
            
            print(f'📋 {policy_id}:')
            print(f'   Manual F1:     {manual_metrics.overall_f1:.3f}')
            print(f'   Automated F1:  {auto_metrics.overall_f1:.3f}')
            print(f'   Difference:    {auto_metrics.overall_f1 - manual_metrics.overall_f1:+.3f}')
            print(f'   % of Manual:   {(auto_metrics.overall_f1/manual_metrics.overall_f1)*100:.1f}%')
            print()
            
            results.append({
                'policy_id': policy_id,
                'manual_f1': manual_metrics.overall_f1,
                'automated_f1': auto_metrics.overall_f1,
                'ratio': auto_metrics.overall_f1 / manual_metrics.overall_f1
            })
        else:
            print(f'📋 {policy_id}:')
            print(f'   Manual F1:     {manual_metrics.overall_f1:.3f}')
            print(f'   Automated:     (rate limited)')
            print()
    
    if results:
        print('='*80)
        print('SUMMARY')
        print('='*80)
        avg_manual = sum(r['manual_f1'] for r in results) / len(results)
        avg_auto = sum(r['automated_f1'] for r in results) / len(results)
        avg_ratio = sum(r['ratio'] for r in results) / len(results)
        
        print(f'Policies compared: {len(results)}/4')
        print(f'Average Manual F1: {avg_manual:.3f}')
        print(f'Average Automated F1: {avg_auto:.3f}')
        print(f'Automated achieves {avg_ratio*100:.1f}% of manual performance')
        print()
        
        if avg_ratio >= 0.95:
            print('✅ Automated extraction matches manual baseline (>95%)')
        elif avg_ratio >= 0.90:
            print('✅ Automated extraction nearly matches manual (90-95%)')
        else:
            print('⚠️  Automated extraction needs tuning (<90% of manual)')
    
    # Save comparison
    with open('eval/results/automated_vs_manual_comparison.json', 'w') as f:
        json.dump({
            'policies_compared': len(results),
            'results': results,
            'avg_manual_f1': avg_manual if results else None,
            'avg_automated_f1': avg_auto if results else None,
            'automated_ratio': avg_ratio if results else None
        }, f, indent=2)

if __name__ == '__main__':
    main()
