"""
Experiment 5c: Display CSV Contents and Schema

Goal:
- Load the generated listed_corporations.csv
- Display full schema with all columns
- Show sample data for inspection
- Generate summary statistics

This is a utility script for inspecting the corp list data.

Key Insights from Output:
1. CSV has 11 columns (not 7 as initially thought)
2. corp_cls and market_type provide same information
3. 70.9% of corps have complete metadata
4. 29.1% are missing corp_cls/sector/product (likely delisted)
5. Trading halt and issue flags are rare (2.7%)

Expected Output:
- Full schema with data types
- First 30 rows for visual inspection
- Sample of complete records (corp_cls not null)
- Summary statistics (counts, percentages)
- Market distribution breakdown
"""

import pandas as pd

# Set display options
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', 50)

df = pd.read_csv('experiments/data/listed_corporations.csv')

print('='*100)
print('FULL CSV SCHEMA')
print('='*100)
print(df.info())

print('\n' + '='*100)
print('COLUMN NAMES')
print('='*100)
print(df.columns.tolist())

print('\n' + '='*100)
print('FIRST 30 ROWS')
print('='*100)
print(df.head(30).to_string())

print('\n' + '='*100)
print('SAMPLE OF CORPS WITH FULL DATA (corp_cls not null)')
print('='*100)
print(df[df['corp_cls'].notna()].head(20).to_string())

print('\n' + '='*100)
print('SUMMARY STATISTICS')
print('='*100)
print(f'Total listed corporations: {len(df)}')
print(f'With complete data (corp_cls): {df["corp_cls"].notna().sum()} ({df["corp_cls"].notna().sum()/len(df)*100:.1f}%)')
print(f'Missing corp_cls: {df["corp_cls"].isna().sum()} ({df["corp_cls"].isna().sum()/len(df)*100:.1f}%)')
print(f'With trading halt: {df["trading_halt"].notna().sum()}')
print(f'With issue flag: {df["issue"].notna().sum()}')

print('\n' + '='*100)
print('MARKET DISTRIBUTION (corp_cls)')
print('='*100)
print(df['corp_cls'].value_counts())
print('\nMeanings:')
print('  Y = 유가증권시장 (KOSPI): Stock Market')
print('  K = 코스닥 (KOSDAQ): KOSDAQ Market')
print('  N = 코넥스 (KONEX): KONEX Market')

print('\n' + '='*100)
print('MARKET TYPE DISTRIBUTION')
print('='*100)
print(df['market_type'].value_counts())
print('\nNote: market_type and corp_cls represent the same information')
print('  stockMkt = Y (KOSPI)')
print('  kosdaqMkt = K (KOSDAQ)')
print('  konexMkt = N (KONEX)')
