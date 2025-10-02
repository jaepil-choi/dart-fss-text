"""
Experiment 5: Retrieve Listed Corporations and Create Stock Code Mapping

Goal:
- Load all corporations from DART using dart-fss
- Filter to only listed stocks (non-null stock_code)
- Extract ALL available attributes using .to_dict()
- Save to CSV for reference and validation

Key Learning Points:
- Corp objects have stock_code attribute (None for unlisted)
- We need corp_code (8 digits) for DART API calls
- Users will provide stock_code (6 digits) in our API
- This mapping is essential for our discovery service

CRITICAL FINDINGS:
1. Total: 114,106 corporations (3,901 listed, 110,205 unlisted)
2. Complete schema: 11 columns via .to_dict()
3. corp_cls IS the market indicator (Y=KOSPI, K=KOSDAQ, N=KONEX)
4. NO separate "market" attribute exists - that was a mistake
5. 70.9% have complete data, 29.1% missing corp_cls/sector/product
6. Missing data likely indicates delisted/suspended companies

Schema (11 columns):
- Always: corp_code, corp_name, corp_eng_name, stock_code, modify_date
- Sometimes (70.9%): corp_cls, market_type, sector, product
- Rarely (2.7%): trading_halt, issue
"""

import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
import dart_fss as dart

# Load API key
load_dotenv()
api_key = os.getenv('OPENDART_API_KEY')
if not api_key:
    raise ValueError("OPENDART_API_KEY not found in .env file")

dart.set_api_key(api_key=api_key)

print("="*80)
print("EXPERIMENT 5: Listed Corporations Mapping")
print("="*80)

# Step 1: Load all corporations
print("\n[Step 1] Loading corporation list from DART...")
corp_list = dart.get_corp_list()
print(f"✓ Loaded corp_list object: {corp_list}")

# Step 2: Access all corporations
print("\n[Step 2] Accessing all corporations...")
all_corps = corp_list.corps
print(f"✓ Total corporations in DART: {len(all_corps)}")

# Step 3: Inspect a sample Corp object to see available attributes
print("\n[Step 3] Inspecting Corp object structure...")
sample_corp = all_corps[0]
print(f"Sample corp: {sample_corp.corp_name}")
print(f"Available attributes (dir): {[attr for attr in dir(sample_corp) if not attr.startswith('_')]}")

# Try to access common attributes
print(f"\nSample corp details:")
print(f"  - corp_code: {getattr(sample_corp, 'corp_code', 'N/A')}")
print(f"  - corp_name: {getattr(sample_corp, 'corp_name', 'N/A')}")
print(f"  - stock_code: {getattr(sample_corp, 'stock_code', 'N/A')}")
print(f"  - corp_cls: {getattr(sample_corp, 'corp_cls', 'N/A')}")
print(f"  - sector: {getattr(sample_corp, 'sector', 'N/A')}")
print(f"  - product: {getattr(sample_corp, 'product', 'N/A')}")

# Step 4: Filter to only listed stocks (stock_code is not None)
print("\n[Step 4] Filtering to listed stocks only...")
listed_corps = [corp for corp in all_corps if corp.stock_code is not None]
print(f"✓ Listed corporations: {len(listed_corps)}")
print(f"✓ Unlisted corporations: {len(all_corps) - len(listed_corps)}")

# Step 5: Extract data to list of dicts using .to_dict()
print("\n[Step 5] Extracting corporation data using .to_dict()...")
corp_data = []
for corp in listed_corps:
    # Use .to_dict() to get all available attributes
    corp_dict = corp.to_dict()
    corp_data.append(corp_dict)

print(f"✓ Extracted {len(corp_data)} corporation records")

# Step 6: Convert to DataFrame
print("\n[Step 6] Creating DataFrame...")
df = pd.DataFrame(corp_data)
print(f"✓ DataFrame shape: {df.shape}")
print(f"\nFirst 10 rows:")
print(df.head(10))

print(f"\nDataFrame info:")
print(df.info())

print(f"\nValue counts by corp_cls (market indicator):")
print(df['corp_cls'].value_counts())
print(f"\nNote: corp_cls meanings:")
print(f"  Y = 유가증권시장 (KOSPI)")
print(f"  K = 코스닥 (KOSDAQ)")
print(f"  N = 코넥스 (KONEX)")
print(f"  E = 기타 (Other)")

if 'market_type' in df.columns:
    print(f"\nValue counts by market_type:")
    print(df['market_type'].value_counts())

# Step 7: Validation checks
print("\n[Step 7] Running validation checks...")

# Check for duplicates
duplicate_stock_codes = df[df.duplicated(subset=['stock_code'], keep=False)]
if len(duplicate_stock_codes) > 0:
    print(f"⚠ WARNING: Found {len(duplicate_stock_codes)} duplicate stock_codes:")
    print(duplicate_stock_codes[['stock_code', 'corp_name']])
else:
    print("✓ No duplicate stock_codes")

duplicate_corp_codes = df[df.duplicated(subset=['corp_code'], keep=False)]
if len(duplicate_corp_codes) > 0:
    print(f"⚠ WARNING: Found {len(duplicate_corp_codes)} duplicate corp_codes:")
    print(duplicate_corp_codes[['corp_code', 'corp_name']])
else:
    print("✓ No duplicate corp_codes")

# Check for null values
null_counts = df.isnull().sum()
print(f"\nNull value counts:")
print(null_counts)

# Verify Samsung Electronics is in the list
samsung = df[df['stock_code'] == '005930']
if not samsung.empty:
    print(f"\n✓ Samsung Electronics found:")
    print(samsung.to_dict('records')[0])
else:
    print("\n⚠ WARNING: Samsung Electronics (005930) not found in list!")

# Step 8: Save to CSV
print("\n[Step 8] Saving to CSV...")
output_dir = Path('experiments/data')
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / 'listed_corporations.csv'

df.to_csv(output_file, index=False, encoding='utf-8-sig')
print(f"✓ Saved to: {output_file}")
print(f"  - Rows: {len(df)}")
print(f"  - Columns: {list(df.columns)}")

# Step 9: Create stock_code → corp_code mapping dict for quick reference
print("\n[Step 9] Creating stock_code → corp_code mapping...")
mapping = df.set_index('stock_code')['corp_code'].to_dict()
print(f"✓ Created mapping with {len(mapping)} entries")
print(f"\nSample mappings:")
for i, (stock_code, corp_code) in enumerate(list(mapping.items())[:5]):
    corp_name = df[df['stock_code'] == stock_code]['corp_name'].iloc[0]
    print(f"  {stock_code} → {corp_code} ({corp_name})")

print("\n" + "="*80)
print("EXPERIMENT 5 COMPLETE ✓")
print("="*80)
print(f"Key Findings:")
print(f"  - Total listed corporations: {len(listed_corps)}")
print(f"  - CSV saved: {output_file}")
print(f"  - Mapping ready for use in discovery services")
print("="*80)

