"""
OBSOLETE EXPERIMENT - LESSONS LEARNED
======================================

Original Goal: Investigate Corp Object Info and Attributes
Date Created: 2025-10-02
Status: ✅ FINDINGS DOCUMENTED - Superseded by exp_05 and exp_08

WHAT THIS EXPERIMENT INVESTIGATED:
-----------------------------------
Detailed inspection of individual Corp object attributes and methods:
1. Explore all available attributes via dir()
2. Test attribute access patterns
3. Validate data types and nullable fields
4. Document public methods vs internal methods

KEY FINDINGS:
-------------
1. **Public Attributes** (via Corp.to_dict()):
   - corp_code: str (8 digits, unique ID)
   - corp_name: str (Korean name)
   - corp_eng_name: str (English name)
   - stock_code: str or None (6 digits if listed)
   - modify_date: str (last update date)
   - corp_cls: str or None ('Y'=KOSPI, 'K'=KOSDAQ, 'N'=KONEX)
   - market_type: str or None (redundant with corp_cls)
   - sector: str or None (industry sector)
   - product: str or None (main products)
   - trading_halt: bool or None (trading suspended?)
   - issue: str or None (special remarks)

2. **Public Methods**:
   - find_by_stock_code(stock_code): Lookup by 6-digit code
   - search_filings(**kwargs): Search company filings
   - to_dict(): Convert to dictionary
   - __repr__(): String representation

3. **Attribute Nullability**:
   - Always present: corp_code, corp_name, corp_eng_name, modify_date
   - Sometimes None: stock_code (unlisted), corp_cls, sector, product
   - Rarely present: trading_halt, issue

4. **Data Access Pattern**:
   ```python
   corp = corp_list.find_by_stock_code("005930")
   
   # Direct attribute access
   print(corp.corp_name)  # "삼성전자"
   print(corp.stock_code)  # "005930"
   
   # Dict access (for serialization)
   data = corp.to_dict()
   print(data['corp_name'])  # "삼성전자"
   ```

WHAT WE LEARNED:
----------------
1. **Use Direct Attributes**: Cleaner than dict access
   ```python
   # ✅ GOOD
   corp.corp_name
   corp.stock_code
   
   # ❌ UNNECESSARY
   corp.to_dict()['corp_name']
   ```

2. **Handle None Values**: Not all fields are always present
   ```python
   sector = corp.sector if corp.sector else "Unknown"
   market = corp.corp_cls if corp.corp_cls else "Unlisted"
   ```

3. **Don't Rely on Private Methods**: Stick to public API
   - Use documented methods only
   - Private methods (starting with _) may change
   - Public API is stable across dart-fss versions

4. **Attribute Access is Fast**: No performance penalty
   - Direct attribute access (not properties)
   - No network calls involved
   - Data already in memory from get_corp_list()

WHY THIS IS NOW OBSOLETE:
--------------------------
1. **Findings Incorporated**: exp_05_corp_list_mapping.py documented
   complete schema with data completeness statistics

2. **Production Code Uses Direct Access**: FilingSearchService uses:
   ```python
   corp = corp_list.find_by_stock_code(stock_code)
   corp.corp_code
   corp.corp_name
   corp.search_filings(...)
   ```

3. **Better Documentation**: exp_08_corplist_test.py focuses on the
   actual usage patterns needed for production

REPLACEMENT:
------------
For Corp schema:
→ experiments/exp_05_corp_list_mapping.py
→ experiments/FINDINGS.md

For production patterns:
→ src/dart_fss_text/services/filing_search.py

KEY TAKEAWAY:
-------------
**Use direct attribute access on Corp objects - it's clean and efficient.**

```python
# ✅ GOOD - Direct access
corp.corp_name
corp.stock_code
corp.corp_code

# ❌ BAD - Unnecessary dict conversion
data = corp.to_dict()
name = data['corp_name']
```

Only use .to_dict() when you need to serialize the entire object (e.g., for
JSON output, database storage, etc.).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This file kept as lessons learned reference. Do not execute.
Findings incorporated into exp_05 and production code.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# Original code removed - see git history if needed
