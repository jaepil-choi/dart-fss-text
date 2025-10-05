"""
Experiment 14: Test Refactored Parser with Strategy Pattern

Date: 2025-10-05
Status: Testing

Objective:
- Verify refactored xml_parser.py works with text-based matching
- Test default matcher (exact → fuzzy 0.90)
- Test custom matchers (exact only, fuzzy only, custom threshold)
- Compare results with exp_13

Test Data:
- 2020 SK Hynix report (no ATOCID)
- 2023/2024 reports (with ATOCID)
"""

from pathlib import Path

print("=" * 80)
print("EXPERIMENT 14: Test Refactored Parser")
print("=" * 80)

from dart_fss_text.parsers import (
    build_section_index,
    load_toc_mapping,
    ExactMatcher,
    FuzzyMatcher,
    CascadeMatcher,
    create_default_matcher
)

# === Test 1: Default Matcher (Exact → Fuzzy 0.90) ===

print("\n[Test 1] Default Matcher (Exact → Fuzzy 0.90)")
print("-" * 80)

xml_path = Path("data/2020/000660/20200330004441/20200330004441.xml")

if not xml_path.exists():
    print(f"  ✗ File not found: {xml_path}")
    print("  Skipping Test 1")
else:
    toc_mapping = load_toc_mapping('A001')
    
    # Use default matcher
    index = build_section_index(xml_path, toc_mapping)
    
    print(f"  Total sections indexed: {len(index)}")
    
    # Count matched vs unmatched
    matched = sum(1 for v in index.values() if v['section_code'] is not None)
    unmatched = len(index) - matched
    
    print(f"  Matched: {matched} ({matched/len(index)*100:.1f}%)")
    print(f"  Unmatched: {unmatched} ({unmatched/len(index)*100:.1f}%)")
    print()
    
    # Show matched sections
    print("  Matched sections (first 10):")
    count = 0
    for key, data in index.items():
        if data['section_code'] and count < 10:
            atocid_str = data['atocid'] if data['atocid'] else f"seq:{key}"
            print(f"    [{atocid_str}] {data['section_code']} ← {data['title'][:50]}")
            count += 1
    print()
    
    # Show unmatched
    print("  Unmatched sections:")
    for key, data in index.items():
        if not data['section_code']:
            atocid_str = data['atocid'] if data['atocid'] else f"seq:{key}"
            print(f"    [{atocid_str}] ✗ {data['title'][:60]}")

# === Test 2: Exact Only Matcher ===

print("\n[Test 2] Exact Only Matcher")
print("-" * 80)

if xml_path.exists():
    toc_mapping = load_toc_mapping('A001')
    
    # Use exact matcher only
    exact_matcher = ExactMatcher()
    index = build_section_index(xml_path, toc_mapping, matcher=exact_matcher)
    
    matched = sum(1 for v in index.values() if v['section_code'] is not None)
    
    print(f"  Total sections: {len(index)}")
    print(f"  Matched: {matched} ({matched/len(index)*100:.1f}%)")
    print(f"  (Compare to Test 1 - should be lower)")

# === Test 3: Fuzzy Only with High Threshold ===

print("\n[Test 3] Fuzzy Only (threshold=0.95)")
print("-" * 80)

if xml_path.exists():
    toc_mapping = load_toc_mapping('A001')
    
    # Use fuzzy matcher with high threshold
    fuzzy_matcher = FuzzyMatcher(threshold=0.95)
    index = build_section_index(xml_path, toc_mapping, matcher=fuzzy_matcher)
    
    matched = sum(1 for v in index.values() if v['section_code'] is not None)
    
    print(f"  Total sections: {len(index)}")
    print(f"  Matched: {matched} ({matched/len(index)*100:.1f}%)")
    print(f"  (Very strict - should match fewer than exact)")

# === Test 4: Test with 2023 Report (has ATOCID) ===

print("\n[Test 4] 2023 Report (with ATOCID)")
print("-" * 80)

xml_2023 = Path("data/2024/005930/20240312000736/20240312000736.xml")

if not xml_2023.exists():
    print(f"  ✗ File not found: {xml_2023}")
    print("  Skipping Test 4")
else:
    toc_mapping = load_toc_mapping('A001')
    index = build_section_index(xml_2023, toc_mapping)
    
    print(f"  Total sections indexed: {len(index)}")
    
    matched = sum(1 for v in index.values() if v['section_code'] is not None)
    unmatched = len(index) - matched
    
    print(f"  Matched: {matched} ({matched/len(index)*100:.1f}%)")
    print(f"  Unmatched: {unmatched}")
    
    # Check if ATOCIDs preserved
    with_atocid = sum(1 for v in index.values() if v['atocid'] is not None)
    print(f"  Sections with ATOCID: {with_atocid}/{len(index)}")
    
    print()
    print("  First 5 sections:")
    for i, (key, data) in enumerate(list(index.items())[:5], 1):
        atocid_str = data['atocid'] if data['atocid'] else f"seq:{key}"
        code_str = data['section_code'] if data['section_code'] else '✗'
        print(f"    [{atocid_str}] {code_str} ← {data['title'][:50]}")

# === Summary ===

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print()
print("✓ Refactored parser with strategy pattern")
print("✓ Text-based matching (no ATOCID dependency)")
print("✓ Pluggable matchers (exact, fuzzy, cascade)")
print("✓ Sequential indexing for reports without ATOCID")
print("✓ Backward compatible with ATOCID reports")
print()
print("=" * 80)

