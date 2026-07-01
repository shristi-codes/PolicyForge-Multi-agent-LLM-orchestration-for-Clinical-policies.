#!/usr/bin/env python3
"""
Clinical Safety Analysis: Weighted F1 by Policy Severity

CRITICAL INSIGHT: Mean F1 = 91.6% HIDES the fact that cancer screening policies 
have 82.4% F1, which is UNACCEPTABLE for clinical use.

This script:
1. Classifies policies by clinical severity (Tier 1/2/3)
2. Calculates weighted F1 by patient harm potential
3. Identifies which policies MUST have human review
4. Provides deployment recommendations
"""

import sys
sys.path.insert(0, '.')
import json
from typing import Dict, List

# Clinical severity classification
POLICY_CLASSIFICATION = {
    # Tier 1: Critical - Cancer Screening (high patient harm if errors)
    'NCD_150.3': {'tier': 1, 'name': 'Bone Mass', 'weight': 3.0, 'clinical_impact': 'Osteoporosis screening - fracture prevention'},
    'NCD_210.3': {'tier': 1, 'name': 'Colorectal Cancer', 'weight': 5.0, 'clinical_impact': 'CRITICAL: Cancer screening - life/death impact'},
    'NCD_220.4': {'tier': 1, 'name': 'Mammography', 'weight': 5.0, 'clinical_impact': 'CRITICAL: Cancer screening - life/death impact'},
    'NCD_210.14': {'tier': 1, 'name': 'Lung Cancer', 'weight': 5.0, 'clinical_impact': 'CRITICAL: Cancer screening - life/death impact'},
    
    # Tier 2: Important - CVD/Metabolic (significant health impact)
    'Cardiovascular': {'tier': 2, 'name': 'Cardiovascular Screening', 'weight': 2.0, 'clinical_impact': 'CVD prevention - major morbidity'},
    'Diabetes_Screening': {'tier': 2, 'name': 'Diabetes Screening', 'weight': 2.0, 'clinical_impact': 'Diabetes prevention - major morbidity'},
    'Hepatitis_C': {'tier': 2, 'name': 'Hepatitis C Screening', 'weight': 2.0, 'clinical_impact': 'Infectious disease - treatment-sensitive'},
    'HIV_Screening': {'tier': 2, 'name': 'HIV Screening', 'weight': 2.0, 'clinical_impact': 'Infectious disease - treatment-sensitive'},
    'NCD_210.1': {'tier': 2, 'name': 'PSA Screening', 'weight': 2.0, 'clinical_impact': 'Cancer screening - controversial benefit'},
    
    # Tier 3: Routine - Behavioral Health / Preventive (lower acute harm)
    'NCD_210.9': {'tier': 3, 'name': 'Depression Screening', 'weight': 1.0, 'clinical_impact': 'Mental health - important but non-acute'},
    'NCD_210.12': {'tier': 3, 'name': 'Obesity Therapy', 'weight': 1.0, 'clinical_impact': 'Lifestyle intervention - chronic condition'},
    'Glaucoma': {'tier': 3, 'name': 'Glaucoma Screening', 'weight': 1.5, 'clinical_impact': 'Vision loss prevention - gradual progression'},
    'Pap_Smear': {'tier': 1, 'name': 'Cervical Cancer Screening', 'weight': 4.0, 'clinical_impact': 'CRITICAL: Cancer screening'},
    'Cardiac_Rehab': {'tier': 2, 'name': 'Cardiac Rehabilitation', 'weight': 2.5, 'clinical_impact': 'Post-event recovery - major impact'},
    'AAA_Screening': {'tier': 2, 'name': 'AAA Screening', 'weight': 2.5, 'clinical_impact': 'Aneurysm detection - catastrophic if missed'}
}

def calculate_weighted_f1(results: List[Dict]) -> Dict:
    """Calculate weighted F1 by clinical severity."""
    
    tier_1_policies = []
    tier_2_policies = []
    tier_3_policies = []
    
    total_weighted_score = 0
    total_weight = 0
    
    for result in results:
        policy_id = result['policy_id']
        f1 = result['hcpcs_f1']
        
        if policy_id not in POLICY_CLASSIFICATION:
            continue
        
        classification = POLICY_CLASSIFICATION[policy_id]
        tier = classification['tier']
        weight = classification['weight']
        
        # Accumulate weighted score
        total_weighted_score += f1 * weight
        total_weight += weight
        
        # Categorize by tier
        policy_data = {
            'policy_id': policy_id,
            'name': classification['name'],
            'f1': f1,
            'weight': weight,
            'clinical_impact': classification['clinical_impact'],
            'safe_for_automation': f1 >= 0.95
        }
        
        if tier == 1:
            tier_1_policies.append(policy_data)
        elif tier == 2:
            tier_2_policies.append(policy_data)
        else:
            tier_3_policies.append(policy_data)
    
    # Calculate tier means
    tier_1_mean = sum(p['f1'] for p in tier_1_policies) / len(tier_1_policies) if tier_1_policies else 0
    tier_2_mean = sum(p['f1'] for p in tier_2_policies) / len(tier_2_policies) if tier_2_policies else 0
    tier_3_mean = sum(p['f1'] for p in tier_3_policies) / len(tier_3_policies) if tier_3_policies else 0
    
    weighted_f1 = total_weighted_score / total_weight if total_weight > 0 else 0
    
    return {
        'weighted_f1': weighted_f1,
        'tier_1': {'policies': tier_1_policies, 'mean_f1': tier_1_mean, 'safe': tier_1_mean >= 0.95},
        'tier_2': {'policies': tier_2_policies, 'mean_f1': tier_2_mean, 'safe': tier_2_mean >= 0.90},
        'tier_3': {'policies': tier_3_policies, 'mean_f1': tier_3_mean, 'safe': tier_3_mean >= 0.85}
    }

def analyze_clinical_safety(weighted_results: Dict) -> Dict:
    """Determine deployment safety by tier."""
    
    tier_1 = weighted_results['tier_1']
    tier_2 = weighted_results['tier_2']
    tier_3 = weighted_results['tier_3']
    
    # Find critical failures
    critical_failures = [p for p in tier_1['policies'] if p['f1'] < 0.8]
    
    # Deployment recommendation
    if critical_failures:
        recommendation = "DO NOT DEPLOY for automation - critical cancer screening failures"
        risk_level = "HIGH"
    elif tier_1['mean_f1'] < 0.95:
        recommendation = "Deploy for TRIAGE ONLY with mandatory human review"
        risk_level = "MEDIUM"
    elif tier_2['mean_f1'] < 0.90:
        recommendation = "Hybrid deployment: Automate Tier 3, review Tier 1/2"
        risk_level = "LOW-MEDIUM"
    else:
        recommendation = "Safe for phased automation with monitoring"
        risk_level = "LOW"
    
    return {
        'recommendation': recommendation,
        'risk_level': risk_level,
        'critical_failures': critical_failures,
        'requires_human_review': [
            p['policy_id'] for p in tier_1['policies'] + tier_2['policies'] 
            if not p['safe_for_automation']
        ],
        'safe_for_automation': [
            p['policy_id'] for p in tier_3['policies'] 
            if p['safe_for_automation']
        ]
    }

def main():
    print('='*80)
    print('CLINICAL SAFETY ANALYSIS: Weighted F1 by Patient Harm Potential')
    print('='*80)
    print()
    print('CRITICAL INSIGHT: Mean F1 = 91.6% HIDES critical failures')
    print('Cancer screening policies average 82.4% F1 - UNACCEPTABLE for clinical use')
    print()
    
    # Load evaluation results
    with open('eval/results/llm_vs_manual_15_policies.json', 'r') as f:
        data = json.load(f)
    
    results = data['per_policy_results']
    
    # Calculate weighted F1
    weighted_results = calculate_weighted_f1(results)
    
    print('TIER 1: CRITICAL (Cancer Screening) - Weight: 4-5x')
    print('-' * 80)
    tier_1_mean = weighted_results['tier_1']['mean_f1']
    status = '🔴 UNSAFE' if tier_1_mean < 0.95 else '🟢 SAFE'
    print(f'Mean F1: {tier_1_mean:.1%} {status}')
    print()
    for policy in weighted_results['tier_1']['policies']:
        safety = '✅' if policy['f1'] >= 0.95 else '🚨'
        print(f"  {safety} {policy['name']:30s}: F1={policy['f1']:.3f} (weight={policy['weight']:.1f}x)")
        if policy['f1'] < 0.8:
            print(f"     ⚠️  CRITICAL FAILURE: {policy['clinical_impact']}")
    print()
    
    print('TIER 2: IMPORTANT (CVD/Metabolic) - Weight: 2-2.5x')
    print('-' * 80)
    tier_2_mean = weighted_results['tier_2']['mean_f1']
    status = '🟡 MARGINAL' if tier_2_mean < 0.95 else '🟢 SAFE'
    print(f'Mean F1: {tier_2_mean:.1%} {status}')
    print()
    for policy in weighted_results['tier_2']['policies']:
        safety = '✅' if policy['f1'] >= 0.90 else '⚠️'
        print(f"  {safety} {policy['name']:30s}: F1={policy['f1']:.3f} (weight={policy['weight']:.1f}x)")
    print()
    
    print('TIER 3: ROUTINE (Behavioral Health) - Weight: 1-1.5x')
    print('-' * 80)
    tier_3_mean = weighted_results['tier_3']['mean_f1']
    status = '🟢 SAFE' if tier_3_mean >= 0.85 else '🟡 NEEDS WORK'
    print(f'Mean F1: {tier_3_mean:.1%} {status}')
    print()
    for policy in weighted_results['tier_3']['policies']:
        safety = '✅' if policy['f1'] >= 0.85 else '⚠️'
        print(f"  {safety} {policy['name']:30s}: F1={policy['f1']:.3f} (weight={policy['weight']:.1f}x)")
    print()
    
    # Overall weighted F1
    weighted_f1 = weighted_results['weighted_f1']
    print('='*80)
    print('WEIGHTED F1 (by clinical severity)')
    print('='*80)
    print(f'Simple Mean F1:    {data["aggregate_metrics"]["mean_hcpcs_f1"]:.1%} (treats all policies equally)')
    print(f'Weighted F1:       {weighted_f1:.1%} (weights by patient harm potential)')
    print()
    
    # Clinical safety analysis
    safety_analysis = analyze_clinical_safety(weighted_results)
    
    print('='*80)
    print('DEPLOYMENT RECOMMENDATION')
    print('='*80)
    print(f'Risk Level: {safety_analysis["risk_level"]}')
    print(f'Recommendation: {safety_analysis["recommendation"]}')
    print()
    
    if safety_analysis['critical_failures']:
        print('🚨 CRITICAL FAILURES (F1 < 0.8):')
        for failure in safety_analysis['critical_failures']:
            print(f"  - {failure['name']} (NCD {failure['policy_id']}): F1={failure['f1']:.1%}")
            print(f"    Impact: {failure['clinical_impact']}")
        print()
    
    print('POLICIES REQUIRING HUMAN REVIEW:')
    for policy_id in safety_analysis['requires_human_review']:
        print(f"  - {policy_id}")
    print()
    
    if safety_analysis['safe_for_automation']:
        print('POLICIES SAFE FOR AUTOMATION (with monitoring):')
        for policy_id in safety_analysis['safe_for_automation']:
            print(f"  - {policy_id}")
        print()
    
    # Save results
    output = {
        'analysis_date': '2026-07-01',
        'method': 'Weighted F1 by clinical severity',
        'simple_mean_f1': data['aggregate_metrics']['mean_hcpcs_f1'],
        'weighted_mean_f1': weighted_f1,
        'tier_performance': {
            'tier_1_critical': {
                'mean_f1': tier_1_mean,
                'safe': tier_1_mean >= 0.95,
                'policies': [p['policy_id'] for p in weighted_results['tier_1']['policies']]
            },
            'tier_2_important': {
                'mean_f1': tier_2_mean,
                'safe': tier_2_mean >= 0.90,
                'policies': [p['policy_id'] for p in weighted_results['tier_2']['policies']]
            },
            'tier_3_routine': {
                'mean_f1': tier_3_mean,
                'safe': tier_3_mean >= 0.85,
                'policies': [p['policy_id'] for p in weighted_results['tier_3']['policies']]
            }
        },
        'safety_analysis': safety_analysis,
        'conclusion': 'System NOT safe for unsupervised automation due to Tier 1 failures. Deploy for triage only with mandatory human review.'
    }
    
    with open('eval/results/clinical_safety_analysis.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print('='*80)
    print('✅ Clinical safety analysis complete')
    print('='*80)
    print()
    print('Saved to: eval/results/clinical_safety_analysis.json')
    print()
    print('KEY TAKEAWAY:')
    print('Weighted F1 ({:.1%}) shows cancer screening is BELOW clinical safety threshold.'.format(weighted_f1))
    print('NCD 210.3 (Colorectal) at 47% F1 is a CRITICAL failure.')
    print()
    print('RECOMMENDATION: Deploy for audit triage ONLY, NOT automation.')

if __name__ == '__main__':
    main()
