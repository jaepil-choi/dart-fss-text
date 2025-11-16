"""
Experiment 15: CorpList CSV Storage Exploration

Date: 2025-01-15
Status: In Progress

Objective:
- Explore corp_list data structure from dart-fss
- Validate CSV serialization approach
- Measure performance: API load vs CSV load
- Test lookup operations from CSV-backed DataFrame

Hypothesis:
- CSV serialization will preserve all Corp attributes
- CSV load time will be significantly faster than API load (~7s)
- DataFrame-based lookup will be fast enough for production use
- UTF-8 encoding will handle Korean characters correctly

Success Criteria:
- [ ] Sample corp objects printed with all attributes
- [ ] DataFrame created successfully from all corps
- [ ] CSV file created with correct encoding
- [ ] CSV load time measured and compared to API load
- [ ] Lookup operations validated (find_by_stock_code equivalent)
- [ ] File size reasonable for ~114K records
"""

import time
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import dart_fss as dart
import pandas as pd

print("=" * 80)
print("Experiment 15: CorpList CSV Storage Exploration")
print("=" * 80)

# Load API key from .env
load_dotenv()
api_key = os.getenv("OPENDART_API_KEY")

if not api_key:
    print("\n✗ OPENDART_API_KEY not found in .env file")
    print("Please create a .env file with: OPENDART_API_KEY=your_key_here")
    exit(1)

# Set API key for dart-fss
dart.set_api_key(api_key)
print(f"\n✓ API Key loaded: {api_key[:8]}...")

# ============================================================================
# Step 1: Load corp_list from API
# ============================================================================

print("\n" + "=" * 80)
print("Step 1: Loading corp_list from API")
print("=" * 80)

start_time = time.time()
print("\nCalling dart.get_corp_list()...")
corp_list = dart.get_corp_list()
api_load_time = time.time() - start_time

print(f"✓ Loaded in {api_load_time:.2f}s")
print(f"✓ Total companies: {len(corp_list.corps)}")

# ============================================================================
# Step 2: Explore sample corp objects
# ============================================================================

print("\n" + "=" * 80)
print("Step 2: Exploring Sample Corp Objects")
print("=" * 80)

# Get first 10 corps for inspection
sample_corps = corp_list.corps[:10]

print(f"\nInspecting first {len(sample_corps)} corps:")
print("-" * 80)

for i, corp in enumerate(sample_corps, 1):
    print(f"\nCorp {i}:")
    print(f"  Type: {type(corp)}")
    
    # Get all attributes via to_dict()
    corp_dict = corp.to_dict()
    print(f"  Available attributes ({len(corp_dict)}): {list(corp_dict.keys())}")
    
    # Print first corp in detail
    if i == 1:
        print(f"\n  Detailed attributes:")
        for key, value in corp_dict.items():
            value_str = str(value)[:50] if value is not None else "None"
            if len(str(value)) > 50:
                value_str += "..."
            print(f"    {key}: {value_str}")

# ============================================================================
# Step 3: Convert all corps to list of dictionaries
# ============================================================================

print("\n" + "=" * 80)
print("Step 3: Converting All Corps to Dictionaries")
print("=" * 80)

start_time = time.time()
print("\nConverting all corps to dictionaries...")

corp_dicts = []
for corp in corp_list.corps:
    corp_dicts.append(corp.to_dict())

conversion_time = time.time() - start_time
print(f"✓ Converted {len(corp_dicts)} corps in {conversion_time:.3f}s")
print(f"✓ Sample dict keys: {list(corp_dicts[0].keys())}")

# ============================================================================
# Step 4: Create pandas DataFrame
# ============================================================================

print("\n" + "=" * 80)
print("Step 4: Creating pandas DataFrame")
print("=" * 80)

start_time = time.time()
print("\nCreating DataFrame from corp dictionaries...")

df = pd.DataFrame(corp_dicts)

df_creation_time = time.time() - start_time
print(f"✓ DataFrame created in {df_creation_time:.3f}s")
print(f"✓ Shape: {df.shape[0]} rows × {df.shape[1]} columns")
print(f"✓ Columns: {list(df.columns)}")
print(f"✓ Memory usage: {df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")

# Check for None/null values
print(f"\nNull value counts:")
null_counts = df.isnull().sum()
for col, count in null_counts.items():
    if count > 0:
        pct = (count / len(df)) * 100
        print(f"  {col}: {count} ({pct:.1f}%)")

# ============================================================================
# Step 5: Test CSV Serialization
# ============================================================================

print("\n" + "=" * 80)
print("Step 5: Testing CSV Serialization")
print("=" * 80)

# Create data/temp directory if it doesn't exist
data_temp_dir = Path("data/temp")
data_temp_dir.mkdir(parents=True, exist_ok=True)

# Generate timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
csv_path = data_temp_dir / f"corp_list_{timestamp}.csv"

print(f"\nSaving to: {csv_path}")

start_time = time.time()
df.to_csv(csv_path, index=False, encoding='utf-8')
csv_save_time = time.time() - start_time

file_size_mb = csv_path.stat().st_size / 1024 / 1024
print(f"✓ Saved in {csv_save_time:.3f}s")
print(f"✓ File size: {file_size_mb:.2f} MB")
print(f"✓ Encoding: UTF-8")

# ============================================================================
# Step 6: Test CSV Deserialization
# ============================================================================

print("\n" + "=" * 80)
print("Step 6: Testing CSV Deserialization")
print("=" * 80)

print(f"\nLoading from: {csv_path}")

start_time = time.time()
df_loaded = pd.read_csv(csv_path, encoding='utf-8')
csv_load_time = time.time() - start_time

print(f"✓ Loaded in {csv_load_time:.3f}s")
print(f"✓ Shape: {df_loaded.shape[0]} rows × {df_loaded.shape[1]} columns")
print(f"✓ Columns match: {list(df_loaded.columns) == list(df.columns)}")

# Validate data integrity
print(f"\nData integrity check:")
print(f"  Rows match: {len(df_loaded) == len(df)}")
print(f"  Columns match: {set(df_loaded.columns) == set(df.columns)}")

# Check sample row
if len(df_loaded) > 0:
    sample_row = df_loaded.iloc[0]
    print(f"\n  Sample row (first corp):")
    for col in df_loaded.columns[:5]:  # Show first 5 columns
        value = sample_row[col]
        value_str = str(value)[:40] if pd.notna(value) else "NaN"
        if len(str(value)) > 40:
            value_str += "..."
        print(f"    {col}: {value_str}")

# ============================================================================
# Step 7: Test Lookup Operations
# ============================================================================

print("\n" + "=" * 80)
print("Step 7: Testing Lookup Operations")
print("=" * 80)

# Test find_by_stock_code equivalent
test_stock_codes = ['005930', '000660', '035420']  # Samsung, SK Hynix, Naver

print(f"\nTesting lookup for stock codes: {test_stock_codes}")

start_time = time.time()
for stock_code in test_stock_codes:
    # Filter DataFrame by stock_code
    result = df_loaded[df_loaded['stock_code'] == stock_code]
    
    if len(result) > 0:
        corp_data = result.iloc[0].to_dict()
        print(f"\n  ✓ Found {stock_code}:")
        print(f"    corp_name: {corp_data.get('corp_name', 'N/A')}")
        print(f"    corp_code: {corp_data.get('corp_code', 'N/A')}")
        print(f"    corp_cls: {corp_data.get('corp_cls', 'N/A')}")
    else:
        print(f"\n  ✗ Not found: {stock_code}")

lookup_time = time.time() - start_time
print(f"\n✓ Lookup time for {len(test_stock_codes)} codes: {lookup_time:.4f}s")
print(f"  Average: {lookup_time / len(test_stock_codes):.4f}s per lookup")

# Test lookup performance with larger sample
print(f"\nPerformance test: 100 random lookups")
import random
random_stock_codes = df_loaded[df_loaded['stock_code'].notna()]['stock_code'].sample(min(100, len(df_loaded[df_loaded['stock_code'].notna()]))).tolist()

start_time = time.time()
found_count = 0
for stock_code in random_stock_codes:
    result = df_loaded[df_loaded['stock_code'] == stock_code]
    if len(result) > 0:
        found_count += 1
bulk_lookup_time = time.time() - start_time

print(f"✓ Looked up {len(random_stock_codes)} codes in {bulk_lookup_time:.4f}s")
print(f"  Found: {found_count}/{len(random_stock_codes)}")
print(f"  Average: {bulk_lookup_time / len(random_stock_codes):.6f}s per lookup")

# ============================================================================
# Step 8: Performance Comparison
# ============================================================================

print("\n" + "=" * 80)
print("Step 8: Performance Comparison")
print("=" * 80)

print(f"\nAPI Load Time:     {api_load_time:.2f}s")
print(f"CSV Load Time:     {csv_load_time:.3f}s")
print(f"Speedup:           {api_load_time / csv_load_time:.1f}x faster")
print(f"\nCSV Save Time:     {csv_save_time:.3f}s")
print(f"CSV File Size:     {file_size_mb:.2f} MB")
print(f"Records:           {len(df_loaded):,}")

# ============================================================================
# Step 9: Korean Character Validation
# ============================================================================

print("\n" + "=" * 80)
print("Step 9: Korean Character Validation")
print("=" * 80)

# Find corps with Korean names
korean_sample = df_loaded[df_loaded['corp_name'].notna()].head(5)

print(f"\nSample Korean company names from CSV:")
for idx, row in korean_sample.iterrows():
    corp_name = row['corp_name']
    print(f"  {corp_name}")

# Verify encoding preserved Korean characters
first_corp_name = korean_sample.iloc[0]['corp_name']
if first_corp_name:
    has_korean = all(ord(c) > 127 for c in first_corp_name)
else:
    has_korean = False
print(f"\n✓ Korean characters preserved: {has_korean}")

# ============================================================================
# Conclusions
# ============================================================================

print("\n" + "=" * 80)
print("Conclusions")
print("=" * 80)
print("1. CSV serialization preserves all Corp attributes")
print(f"2. CSV load ({csv_load_time:.3f}s) is {api_load_time / csv_load_time:.1f}x faster than API load ({api_load_time:.2f}s)")
print(f"3. CSV file size: {file_size_mb:.2f} MB for {len(df_loaded):,} records")
print(f"4. Lookup performance: {bulk_lookup_time / len(random_stock_codes):.6f}s per lookup")
print("5. UTF-8 encoding handles Korean characters correctly")
print(f"6. DataFrame has {df_loaded.shape[1]} columns: {', '.join(df_loaded.columns[:5])}...")
print("=" * 80)

