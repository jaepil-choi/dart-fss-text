"""
Experiment 5b: Deep Investigation of Corp Object Schema

Goal:
- Investigate Corp.info() method to get complete metadata
- Understand what attributes are available
- Determine why corp_cls/sector/product are None for some corps

Key Findings:
1. Corp.to_dict() and Corp.info both return the same data
2. Attributes exist directly on Corp objects (hasattr returns True)
3. "market" attribute does NOT exist - corp_cls IS the market
4. Samsung has full data: corp_cls='Y', sector, product all populated
5. Incomplete corps (29%) have only: corp_code, corp_name, corp_eng_name, stock_code, modify_date
6. Most incomplete records have modify_date=20170630 (likely delisted before that date)

Validated Schema:
- corp_cls: Market indicator (Y/K/N/E), NOT a separate field
- market_type: Redundant with corp_cls (stockMkt=Y, kosdaqMkt=K, konexMkt=N)
- sector: Industry classification (Korean)
- product: Main products/services (Korean)
"""

import os
from dotenv import load_dotenv
import dart_fss as dart

# Load API key
load_dotenv()
api_key = os.getenv('OPENDART_API_KEY')
if not api_key:
    raise ValueError("OPENDART_API_KEY not found in .env file")

dart.set_api_key(api_key=api_key)

print("="*80)
print("EXPERIMENT 5b: Corp Object Schema Investigation")
print("="*80)

# Load corp list
print("\n[Step 1] Loading corporation list...")
corp_list = dart.get_corp_list()
all_corps = corp_list.corps
listed_corps = [corp for corp in all_corps if corp.stock_code is not None]

print(f"✓ Total listed corporations: {len(listed_corps)}")

# Investigate Samsung Electronics (known to have full data)
print("\n[Step 2] Investigating Samsung Electronics (005930)...")
samsung = [corp for corp in listed_corps if corp.stock_code == '005930'][0]
print(f"Corp object: {samsung}")
print(f"Type: {type(samsung)}")

# Check all attributes
print(f"\n[Step 3] Direct attributes:")
print(f"  - corp_code: {samsung.corp_code}")
print(f"  - corp_name: {samsung.corp_name}")
print(f"  - corp_eng_name: {samsung.corp_eng_name}")
print(f"  - stock_code: {samsung.stock_code}")
print(f"  - modify_date: {samsung.modify_date}")

# Try accessing corp_cls, sector, product directly
print(f"\n[Step 4] Checking corp_cls, sector, product attributes:")
print(f"  - hasattr(samsung, 'corp_cls'): {hasattr(samsung, 'corp_cls')}")
print(f"  - hasattr(samsung, 'sector'): {hasattr(samsung, 'sector')}")
print(f"  - hasattr(samsung, 'product'): {hasattr(samsung, 'product')}")
print(f"  - hasattr(samsung, 'market'): {hasattr(samsung, 'market')}")

if hasattr(samsung, 'corp_cls'):
    print(f"  - samsung.corp_cls: {samsung.corp_cls}")
if hasattr(samsung, 'sector'):
    print(f"  - samsung.sector: {samsung.sector}")
if hasattr(samsung, 'product'):
    print(f"  - samsung.product: {samsung.product}")
if hasattr(samsung, 'market'):
    print(f"  - samsung.market: {samsung.market}")

# Check .info() method
print(f"\n[Step 5] Investigating .info() method:")
print(f"  - hasattr(samsung, 'info'): {hasattr(samsung, 'info')}")
if hasattr(samsung, 'info'):
    print(f"  - Calling samsung.info()...")
    info = samsung.info
    print(f"  - Type of info: {type(info)}")
    print(f"  - Info contents: {info}")
    
    if isinstance(info, dict):
        print(f"\n  Info keys:")
        for key, value in info.items():
            print(f"    {key}: {value}")

# Check .to_dict() method
print(f"\n[Step 6] Investigating .to_dict() method:")
if hasattr(samsung, 'to_dict'):
    corp_dict = samsung.to_dict()
    print(f"  - Type: {type(corp_dict)}")
    print(f"  - Keys: {corp_dict.keys()}")
    print(f"\n  Full dict:")
    for key, value in corp_dict.items():
        print(f"    {key}: {value}")

# Now check a corp with None values
print("\n[Step 7] Investigating a corp with None corp_cls...")
# Find a corp with None corp_cls from first 100 listed
test_corp = None
for corp in listed_corps[:100]:
    if not hasattr(corp, 'corp_cls') or getattr(corp, 'corp_cls', None) is None:
        test_corp = corp
        break

if test_corp:
    print(f"Test corp: {test_corp.corp_name} ({test_corp.stock_code})")
    print(f"  - corp_code: {test_corp.corp_code}")
    
    if hasattr(test_corp, 'to_dict'):
        test_dict = test_corp.to_dict()
        print(f"\n  Full dict:")
        for key, value in test_dict.items():
            print(f"    {key}: {value}")
else:
    print("  All tested corps have corp_cls")

# Check all unique attribute names across multiple corps
print("\n[Step 8] Checking attribute consistency across multiple corps...")
sample_corps = listed_corps[:10]
all_attrs = set()
for corp in sample_corps:
    if hasattr(corp, 'to_dict'):
        all_attrs.update(corp.to_dict().keys())

print(f"  Unique attributes found across 10 corps: {sorted(all_attrs)}")

print("\n" + "="*80)
print("EXPERIMENT 5b COMPLETE ✓")
print("="*80)

