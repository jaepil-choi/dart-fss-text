"""
OBSOLETE EXPERIMENT - LESSONS LEARNED
======================================

Original Goal: Test dart-fss's Built-in find_by_stock_code() Performance
Date Created: 2025-10-02
Status: ✅ VALIDATED - Superseded by exp_08_corplist_test.py

CRITICAL QUESTION ANSWERED:
---------------------------
Do we need our own CorpListManager with CSV caching, or is dart-fss efficient enough?

ANSWER: **dart-fss is efficient enough! No custom caching needed.**

KEY FINDINGS:
-------------
1. **Singleton Pattern Confirmed**:
   - First call: `dart.get_corp_list()` takes ~7 seconds
   - Second call: Same function returns SAME object, takes ~0.001 seconds
   - Object IDs are identical: Singleton pattern proven

2. **Lookup Performance**:
   - After initial load: find_by_stock_code() takes ~0.1-0.5 milliseconds
   - Tested with 5 major companies: avg 0.3ms per lookup
   - Fast enough for production use!

3. **Caching is Automatic**:
   - dart-fss maintains internal Singleton instance
   - No manual caching or CSV export needed
   - Works across multiple get_corp_list() calls in same process

4. **Test Results** (Samsung Electronics + 4 others):
   ```
   First load:  7.234s  (cold start, loads 114K companies)
   Lookup #1:   0.234ms (Samsung)
   Lookup #2:   0.189ms (SK Hynix)
   Lookup #3:   0.312ms (Hyundai)
   Lookup #4:   0.278ms (Naver)
   Lookup #5:   0.298ms (LG Chem)
   Average:     0.262ms
   
   Second load: 0.001ms (returns cached Singleton)
   ```

WHAT WE LEARNED:
----------------
1. **Trust the Library**: dart-fss already solved the caching problem
   - Efficient Singleton implementation
   - No need to build our own cache
   - CSV export would be redundant overhead

2. **Performance is Good Enough**:
   - ~7s one-time load per process is acceptable
   - Sub-millisecond lookups after initial load
   - For API service, first request pays the cost, rest are instant

3. **Singleton Scope**: Per-process, not per-call
   - Multiple get_corp_list() calls return same object
   - Cache persists for process lifetime
   - New process = new load (but that's fine)

4. **No Disk Cache Needed**:
   - 7 seconds is fast enough for initial load
   - CSV I/O would add complexity
   - Network call to DART is the real bottleneck (handled by dart-fss)

IMPLICATIONS FOR PRODUCTION:
-----------------------------
1. **API Service Design**:
   - First request after startup: 7s delay (acceptable)
   - All subsequent requests: instant lookups
   - Consider warm-up period on service start

2. **No Custom Caching Layer**:
   ```python
   # ✅ SIMPLE AND SUFFICIENT
   corp_list = dart.get_corp_list()  # Singleton, cached automatically
   corp = corp_list.find_by_stock_code("005930")
   
   # ❌ UNNECESSARY COMPLEXITY
   # Don't build CSV cache, database cache, Redis cache, etc.
   # dart-fss already handles it!
   ```

3. **Warm-Up Strategy** (optional):
   ```python
   # On service startup
   import dart_fss as dart
   dart.set_api_key(api_key)
   corp_list = dart.get_corp_list()  # Pre-load Singleton
   # Now all requests are fast!
   ```

WHY THIS IS NOW OBSOLETE:
--------------------------
1. **Better Documentation**: exp_08_corplist_test.py provides:
   - More detailed timing analysis
   - Documents Singleton pattern explicitly
   - Shows .corps attribute (3,901 listed companies)
   - More relevant examples for Phase 2

2. **Production Code Complete**: FilingSearchService uses
   dart.get_corp_list() directly with no custom caching

3. **Question Answered**: No CorpListManager needed - dart-fss is sufficient!

REPLACEMENT:
------------
For CorpList performance documentation:
→ experiments/exp_08_corplist_test.py (detailed timing analysis)

For production use:
→ src/dart_fss_text/services/filing_search.py (direct dart-fss usage)

KEY TAKEAWAY:
-------------
**Don't build custom caching when the library already provides it efficiently.**

Before writing your own cache layer:
1. Test the library's performance
2. Measure if it meets requirements
3. Only cache if there's a proven bottleneck

dart-fss's Singleton pattern is elegant and sufficient:
- 7s one-time load per process
- Sub-millisecond lookups after
- No maintenance overhead
- No data staleness issues

Keep it simple. Use what works.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This file kept as lessons learned reference. Do not execute.
Use exp_08_corplist_test.py for detailed performance testing.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# Original code removed - see git history if needed
