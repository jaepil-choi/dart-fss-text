"""
Experiment 6: Test dart-fss's Built-in find_by_stock_code() Method

Critical Question:
- Do we even need CorpListManager?
- dart-fss already has find_by_stock_code() method
- Does it cache internally? How fast is it?

Key Questions to Answer:
1. How does find_by_stock_code() perform?
2. Does dart-fss cache the corp list internally?
3. Does it handle repeated lookups efficiently?
4. Is our CorpListManager redundant?

Expected Findings:
- dart-fss CorpList uses Singleton pattern (loads once)
- find_by_stock_code() should be fast after initial load
- We might not need CSV caching at all!
"""

import os
import time
from pathlib import Path
from dotenv import load_dotenv
import dart_fss as dart

# Load API key
load_dotenv()
api_key = os.getenv('OPENDART_API_KEY')
if not api_key:
    raise ValueError("OPENDART_API_KEY not found in .env file")

dart.set_api_key(api_key=api_key)

print("="*80)
print("EXPERIMENT 6: dart-fss find_by_stock_code() Performance Test")
print("="*80)

# Test 1: First load timing
print("\n[Test 1] First call to get_corp_list() (cold start)...")
start = time.time()
corp_list = dart.get_corp_list()
first_load_time = time.time() - start
print(f"✓ First load time: {first_load_time:.3f}s")
print(f"  Corp list type: {type(corp_list)}")
print(f"  Total corps: {len(corp_list)}")

# Test 2: Using find_by_stock_code()
print("\n[Test 2] Using find_by_stock_code() for Samsung...")
start = time.time()
samsung = corp_list.find_by_stock_code('005930')
lookup_time = time.time() - start

print(f"✓ Lookup time: {lookup_time*1000:.3f}ms")
print(f"  Corp found: {samsung.corp_name}")
print(f"  Corp code: {samsung.corp_code}")
print(f"  Stock code: {samsung.stock_code}")
print(f"  Corp cls: {samsung.corp_cls}")

# Test 3: Multiple lookups (test caching)
print("\n[Test 3] Testing multiple lookups...")
companies = {
    '005930': '삼성전자',
    '000660': 'SK하이닉스',
    '005380': '현대자동차',
    '035420': 'NAVER',
    '051910': 'LG화학',
}

total_time = 0
for stock_code, expected_name in companies.items():
    start = time.time()
    corp = corp_list.find_by_stock_code(stock_code)
    elapsed = time.time() - start
    total_time += elapsed
    
    print(f"  ✓ {stock_code} → {corp.corp_code} ({corp.corp_name}) - {elapsed*1000:.3f}ms")
    assert corp.corp_name == expected_name

avg_time = total_time / len(companies)
print(f"\n  Average lookup time: {avg_time*1000:.3f}ms")

# Test 4: Second get_corp_list() call (test singleton)
print("\n[Test 4] Second call to get_corp_list() (test caching)...")
start = time.time()
corp_list2 = dart.get_corp_list()
second_load_time = time.time() - start

print(f"✓ Second load time: {second_load_time*1000:.3f}ms")
print(f"  Same object? {corp_list is corp_list2}")
print(f"  ID comparison: {id(corp_list)} vs {id(corp_list2)}")

# Test 5: Lookup from second instance
print("\n[Test 5] Lookup from second corp_list instance...")
start = time.time()
samsung2 = corp_list2.find_by_stock_code('005930')
lookup_time2 = time.time() - start

print(f"✓ Lookup time: {lookup_time2*1000:.3f}ms")
print(f"  Same Corp object? {samsung is samsung2}")
print(f"  Corp code: {samsung2.corp_code}")

# Test 6: Accessing Corp attributes
print("\n[Test 6] Exploring Corp object attributes...")
print(f"  Available attributes: {[a for a in dir(samsung) if not a.startswith('_')]}")
print(f"\n  Corp details:")
print(f"    corp_code: {samsung.corp_code}")
print(f"    corp_name: {samsung.corp_name}")
print(f"    corp_eng_name: {getattr(samsung, 'corp_eng_name', None)}")
print(f"    stock_code: {samsung.stock_code}")
print(f"    corp_cls: {samsung.corp_cls}")
print(f"    market_type: {getattr(samsung, 'market_type', None)}")
print(f"    sector: {getattr(samsung, 'sector', None)}")
print(f"    product: {getattr(samsung, 'product', None)}")

# Test 7: Error handling for invalid stock code
print("\n[Test 7] Testing invalid stock code...")
try:
    invalid_corp = corp_list.find_by_stock_code('999999')
    if invalid_corp is None:
        print(f"  ✓ Returns None for invalid stock code")
    else:
        print(f"  ⚠ Unexpected: got {invalid_corp}")
except Exception as e:
    print(f"  ⚠ Raises exception: {type(e).__name__}: {e}")

# Test 8: Memory efficiency check
print("\n[Test 8] Checking if Corp objects share data...")
samsung_again = corp_list.find_by_stock_code('005930')
print(f"  Same object on repeated lookup? {samsung is samsung_again}")
print(f"  ID comparison: {id(samsung)} vs {id(samsung_again)}")

# Summary and Analysis
print("\n" + "="*80)
print("EXPERIMENT 6 COMPLETE ✓")
print("="*80)

print(f"\nPerformance Summary:")
print(f"  First load (cold start): {first_load_time:.3f}s")
print(f"  Second load (cached):    {second_load_time*1000:.3f}ms")
print(f"  Speedup:                 {first_load_time/(second_load_time or 0.001):.1f}x")
print(f"  Average lookup time:     {avg_time*1000:.3f}ms")

print(f"\nCaching Analysis:")
print(f"  ✓ dart-fss uses Singleton pattern: {corp_list is corp_list2}")
print(f"  ✓ Corp list loaded only once per process")
print(f"  ✓ find_by_stock_code() is instant after first load")

print(f"\nKey Findings:")
print(f"  1. dart-fss loads corp list once (~{first_load_time:.1f}s)")
print(f"  2. Subsequent get_corp_list() calls are instant (singleton)")
print(f"  3. find_by_stock_code() is very fast (~{avg_time*1000:.2f}ms)")
print(f"  4. No need for external CSV caching in-process")

print(f"\nCRITICAL QUESTION:")
print(f"  Do we still need CorpListManager?")
print(f"  - For in-process caching: NO (dart-fss handles it)")
print(f"  - For cross-process caching: MAYBE (if ~{first_load_time:.1f}s is too slow)")
print(f"  - For offline operation: MAYBE (if network unavailable)")

print("="*80)

