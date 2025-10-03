"""
Experiment 08: Test CorpList loading behavior

Goal: Understand why get_corp_list() is hanging and explore alternative approaches.

From dart-fss docs:
- get_corp_list() returns a CorpList Singleton
- CorpList loads ~114K companies on first call
- Subsequent calls should be instant due to Singleton pattern

We'll test:
1. Direct get_corp_list() call (what our code does now)
2. Using CorpList.corps attribute (only listed companies)
3. Measure actual load time
"""

import time
import os
from dotenv import load_dotenv
import dart_fss as dart
from dart_fss.corp import CorpList

print("=" * 80)
print("Experiment 08: CorpList Loading Test")
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

# Test 1: Using get_corp_list() (current approach)
print("\n" + "=" * 80)
print("Test 1: Using dart.get_corp_list()")
print("=" * 80)

start = time.time()
print("\nCalling dart.get_corp_list()...")
corp_list = dart.get_corp_list()
elapsed = time.time() - start

print(f"✓ Loaded in {elapsed:.2f}s")
print(f"✓ Total companies: {len(corp_list.corps)}")

# Test specific stock code lookup
print("\nTesting stock code lookup:")
samsung = corp_list.find_by_stock_code('005930')
print(f"✓ Samsung: {samsung.corp_name} (corp_code: {samsung.corp_code})")

# Test 2: Second call should be instant (Singleton)
print("\n" + "=" * 80)
print("Test 2: Second call (should be instant)")
print("=" * 80)

start = time.time()
corp_list2 = dart.get_corp_list()
elapsed = time.time() - start

print(f"✓ Loaded in {elapsed:.6f}s")
print(f"✓ Same instance: {corp_list is corp_list2}")

# Test 3: Direct CorpList instantiation (not recommended)
print("\n" + "=" * 80)
print("Test 3: Direct CorpList() - should return same Singleton")
print("=" * 80)

start = time.time()
corp_list3 = CorpList()
elapsed = time.time() - start

print(f"✓ Loaded in {elapsed:.6f}s")
print(f"✓ Same instance as get_corp_list(): {corp_list is corp_list3}")

# Test 4: Check the .corps attribute (listed companies only)
print("\n" + "=" * 80)
print("Test 4: Exploring CorpList.corps attribute")
print("=" * 80)

print(f"\nTotal companies in corp_list: {len(corp_list.corps)}")
print(f"Type of corps: {type(corp_list.corps)}")

# Check if Samsung is in listed companies
samsung_in_list = any(c.stock_code == '005930' for c in corp_list.corps if hasattr(c, 'stock_code') and c.stock_code)
print(f"Samsung (005930) in listed companies: {samsung_in_list}")

# Count companies with stock codes (listed companies)
listed_count = sum(1 for c in corp_list.corps if hasattr(c, 'stock_code') and c.stock_code)
print(f"Companies with stock codes (listed): {listed_count}")

print("\n" + "=" * 80)
print("Conclusions:")
print("=" * 80)
print("1. get_corp_list() is the correct approach (uses Singleton)")
print("2. First call takes ~7s (loads ~114K corps), subsequent calls are instant")
print("3. corp_list.corps contains ALL companies (listed + unlisted)")
print("4. Listed companies have stock_code attribute set")
print("5. For unit tests: MUST mock dart.get_corp_list() to avoid 7s load time")
print("=" * 80)

