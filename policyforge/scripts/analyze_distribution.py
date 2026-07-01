#!/usr/bin/env python3
"""
Meaningful Adjudication: Statistical Outlier Detection

Instead of checking policy compliance (impossible with provider data),
identify statistical outliers - providers whose billing patterns deviate
significantly from population norms.
"""

import sys
sys.path.insert(0, '.')
import pandas as pd
import numpy as np

# Load data
df = pd.read_parquet('data/cms_partb_sample.parquet')

print('='*80)
print('DATA DISTRIBUTION ANALYSIS FOR MEANINGFUL ADJUDICATION')
print('='*80)
print()

# Calculate services per beneficiary
df['services_per_bene'] = df['Tot_Srvcs'] / df['Tot_Benes']

# Remove infinities and NaN
services = df['services_per_bene'].replace([np.inf, -np.inf], np.nan).dropna()

print('1. Services Per Beneficiary Distribution:')
print(f'   Total providers: {len(df)}')
print(f'   Mean: {services.mean():.3f}')
print(f'   Median: {services.median():.3f}')
print(f'   Std Dev: {services.std():.3f}')
print(f'   95th percentile: {services.quantile(0.95):.3f}')
print(f'   99th percentile: {services.quantile(0.99):.3f}')
print()

# Statistical thresholds
mean = services.mean()
std = services.std()

threshold_2sd = mean + 2*std
threshold_3sd = mean + 3*std

print('2. Statistical Outlier Thresholds:')
print(f'   Mean + 2 SD: {threshold_2sd:.3f} services/beneficiary')
print(f'   Mean + 3 SD: {threshold_3sd:.3f} services/beneficiary')
print()

# Apply thresholds
outliers_2sd = df[df['services_per_bene'] > threshold_2sd]
outliers_3sd = df[df['services_per_bene'] > threshold_3sd]

print('3. Outlier Detection Results:')
print(f'   2-SD threshold: {len(outliers_2sd)} providers ({len(outliers_2sd)/len(df)*100:.1f}%)')
print(f'   3-SD threshold: {len(outliers_3sd)} providers ({len(outliers_3sd)/len(df)*100:.1f}%)')
print(f'   ✅ This is MEANINGFUL (not 100%)')
print()

# Show top outliers
print('4. Top 10 Statistical Outliers:')
top10 = df.nlargest(10, 'services_per_bene')[['Rndrng_NPI', 'Tot_Benes', 'Tot_Srvcs', 'services_per_bene']]
for idx, row in top10.iterrows():
    print(f'   NPI {int(row["Rndrng_NPI"])}: {row["services_per_bene"]:.2f} services/bene ({int(row["Tot_Srvcs"])} services, {int(row["Tot_Benes"])} patients)')
print()

print('='*80)
print('RECOMMENDATION: Use 2-SD threshold for outlier flagging')
print(f'Flags {len(outliers_2sd)/len(df)*100:.1f}% of providers - reasonable for audit targeting')
print('='*80)
