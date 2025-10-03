"""
Experiment 10: XML Structure Exploration with SECTION-N Hierarchy

Date: 2025-10-03
Status: Testing SECTION-N + TITLE hierarchy approach (NOT USERMARK)

Objectives:
1. Build section index using SECTION-N + TITLE tags
2. Map sections to toc.yaml structure (section_code mapping)
3. Extract "II. 사업의 내용" (020000) with full content
4. Validate approach on sample.xml and full XML (155K lines)
5. Measure performance and coverage

Strategy:
- Layer 1: Lightweight section indexing (fast scan)
- Layer 2: On-demand section extraction
- Layer 3: Detailed content parsing (paragraphs, tables, subsections)

Success Criteria:
- Section index builds successfully
- ≥90% title mapping accuracy
- ≥90% coverage rate on full XML
- Performance: < 1s indexing, < 0.2s extraction per section
"""

from pathlib import Path
from lxml import etree
import yaml
import json
import time
from typing import Dict, List, Optional, Any

# === CONFIGURATION ===

FULL_XML = Path('experiments/data/xml_sample/20240312000736.xml')
TOC_CONFIG = Path('config/toc.yaml')
OUTPUT_DIR = Path('experiments/data/')

TARGET_SECTION_CODE = '020000'  # "II. 사업의 내용"

# NOTE: sample.xml is truncated (837 lines) - DO NOT use for analysis!
# Use FULL_XML (20240312000736.xml) which is the complete 155K line document


# === STEP 1: Load TOC Mapping ===

def load_toc_mapping() -> Dict[str, str]:
    """
    Load toc.yaml and create title → section_code mapping.
    
    Returns:
        {
            'I. 회사의 개요': '010000',
            '1. 회사의 개요': '010100',
            'II. 사업의 내용': '020000',
            ...
        }
    """
    if not TOC_CONFIG.exists():
        raise FileNotFoundError(f"TOC config not found: {TOC_CONFIG}")
    
    with open(TOC_CONFIG, 'r', encoding='utf-8') as f:
        toc = yaml.safe_load(f)
    
    mapping = {}
    
    def traverse(sections: List[Dict], parent_code: str = ''):
        """Recursively traverse TOC structure."""
        for section in sections:
            code = section['section_code']
            name = section['section_name']
            mapping[name] = code
            
            # Recursively process children
            if section.get('children'):
                traverse(section['children'], code)
    
    # Process A001 sections
    if 'A001' in toc:
        traverse(toc['A001'])
    else:
        raise ValueError("A001 not found in toc.yaml")
    
    return mapping


def map_title_to_section_code(title: str, toc_mapping: Dict[str, str]) -> Optional[str]:
    """
    Map XML title to section_code using toc.yaml.
    
    Fallback strategy:
    1. Exact match in toc.yaml
    2. Normalized match (remove extra whitespace)
    3. Contains match (fuzzy)
    4. Return None if no match
    
    Args:
        title: Section title from XML
        toc_mapping: Dictionary from load_toc_mapping()
    
    Returns:
        section_code or None
    """
    # Exact match
    if title in toc_mapping:
        return toc_mapping[title]
    
    # Normalized match (remove extra spaces)
    normalized_title = ' '.join(title.split())
    if normalized_title in toc_mapping:
        return toc_mapping[normalized_title]
    
    # Fuzzy match (contains) - bidirectional
    for toc_title, code in toc_mapping.items():
        # Check if titles contain each other (handles minor variations)
        if title in toc_title or toc_title in title:
            return code
    
    # No match found
    return None


# === STEP 2: Build Section Index ===

def build_section_index(xml_path: Path, toc_mapping: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    """
    Build lightweight index of all SECTION-N elements.
    Maps ATOCID → section metadata.
    
    Args:
        xml_path: Path to XML file
        toc_mapping: Dictionary from load_toc_mapping()
    
    Returns:
        {
            '3': {  # ATOCID from XML
                'level': 1,
                'title': 'I. 회사의 개요',
                'section_code': '010000',
                'tag': 'SECTION-1',
                'atocid': '3',
                'aclass': 'MANDATORY',
                'element': <Element SECTION-1>  # Reference for extraction
            },
            ...
        }
    """
    if not xml_path.exists():
        raise FileNotFoundError(f"XML file not found: {xml_path}")
    
    # Parse with recover mode for malformed XML
    parser = etree.XMLParser(recover=True, huge_tree=True, encoding='utf-8')
    tree = etree.parse(str(xml_path), parser)
    root = tree.getroot()
    
    index = {}
    
    # Find all SECTION-N tags (N=1,2,3,4,...)
    # Using XPath to get all sections at once
    sections = root.xpath("//SECTION-1 | //SECTION-2 | //SECTION-3 | //SECTION-4")
    
    for section in sections:
        level = int(section.tag.split('-')[1])
        
        # Extract title and ATOCID (ATOCID is on TITLE tag, not SECTION tag!)
        title_elem = section.find('TITLE')
        if title_elem is None:
            continue  # Skip sections without TITLE
        
        title = ''.join(title_elem.itertext()).strip()
        atocid = title_elem.get('ATOCID')  # Get ATOCID from TITLE, not SECTION
        
        # Skip sections without ATOCID (should be rare)
        if not atocid:
            continue
        
        # Map to section_code from toc.yaml
        section_code = map_title_to_section_code(title, toc_mapping)
        
        index[atocid] = {
            'level': level,
            'title': title,
            'section_code': section_code,
            'tag': section.tag,
            'atocid': atocid,
            'aclass': section.get('ACLASS'),
            'element': section  # Keep reference for later extraction
        }
    
    return index


# === STEP 3: Extract Section Content ===

def extract_section_by_code(
    section_index: Dict[str, Dict[str, Any]], 
    section_code: str
) -> Optional[Dict[str, Any]]:
    """
    Extract specific section by section_code (from toc.yaml).
    
    Args:
        section_index: Result from build_section_index()
        section_code: e.g., '020000' for "II. 사업의 내용"
    
    Returns:
        {
            'title': 'II. 사업의 내용',
            'section_code': '020000',
            'level': 1,
            'paragraphs': [...],
            'tables': [...],
            'subsections': [...]
        }
        or None if not found
    """
    # Find section by code
    target = None
    for atocid, metadata in section_index.items():
        if metadata['section_code'] == section_code:
            target = metadata
            break
    
    if not target:
        return None
    
    section_elem = target['element']
    parent_atocid = target['atocid']
    return parse_section_content(section_elem, section_index, section_code, parent_atocid)


def parse_section_content(
    section_elem: etree._Element,
    section_index: Dict[str, Dict[str, Any]],
    parent_code: str,
    parent_atocid: str
) -> Dict[str, Any]:
    """
    Parse section element into structured data.
    
    CRITICAL: XML structure is FLAT (all SECTION-N are siblings)!
    Hierarchy is reconstructed from:
    1. ATOCID sequence (defines order)
    2. Level numbers (SECTION-1 vs SECTION-2)
    3. TITLE text matching
    
    Args:
        section_elem: lxml Element for section
        section_index: Section index for looking up subsections
        parent_code: Section code of parent (for hierarchy)
        parent_atocid: ATOCID of parent section
    
    Returns:
        Structured section dictionary
    """
    result = {
        'title': '',
        'section_code': parent_code,
        'level': int(section_elem.tag.split('-')[1]),
        'atocid': parent_atocid,
        'paragraphs': [],
        'tables': [],
        'subsections': []
    }
    
    # Extract title
    title_elem = section_elem.find('TITLE')
    if title_elem is not None:
        result['title'] = ''.join(title_elem.itertext()).strip()
    
    # Extract ALL paragraphs (including nested - structure is flat!)
    for p in section_elem.findall('.//P'):
        text = ''.join(p.itertext()).strip()
        if text and not is_empty_paragraph(text):
            result['paragraphs'].append(text)
    
    # Extract ALL tables (including nested - structure is flat!)
    for table in section_elem.findall('.//TABLE[@ACLASS="NORMAL"]'):
        parsed_table = parse_table(table)
        if parsed_table['headers'] or parsed_table['rows']:
            result['tables'].append(parsed_table)
    
    # Find child sections from flat structure
    # Children are sections with:
    # 1. Higher level number (e.g., SECTION-2 is child of SECTION-1)
    # 2. ATOCID immediately following parent
    # 3. Before next same-or-higher level section
    parent_level = result['level']
    parent_atocid_num = int(parent_atocid)
    
    # Sort all sections by ATOCID
    sorted_sections = sorted(
        section_index.items(),
        key=lambda x: int(x[0]) if x[0].isdigit() else 0
    )
    
    # Find children: sections after parent with higher level
    for atocid, metadata in sorted_sections:
        atocid_num = int(atocid) if atocid.isdigit() else 0
        
        # Skip if before parent
        if atocid_num <= parent_atocid_num:
            continue
        
        section_level = metadata['level']
        
        # Stop if we hit a same-or-higher level (sibling or aunt)
        if section_level <= parent_level:
            break
        
        # This is a direct child if level is exactly parent+1
        if section_level == parent_level + 1:
            child_elem = metadata['element']
            child_code = metadata['section_code']
            child_section = parse_section_content(
                child_elem, section_index, child_code, atocid
            )
            result['subsections'].append(child_section)
    
    return result


def parse_table(table_elem: etree._Element) -> Dict[str, Any]:
    """
    Extract table with headers and rows.
    
    Args:
        table_elem: lxml Element for TABLE
    
    Returns:
        {
            'headers': [...],
            'rows': [[...], [...]],
            'context': '...'  # Surrounding text (if any)
        }
    """
    headers = []
    rows = []
    
    # Extract headers from THEAD
    thead = table_elem.find('THEAD')
    if thead is not None:
        for th in thead.findall('.//TH'):
            header_text = ''.join(th.itertext()).strip()
            headers.append(header_text)
    
    # Extract rows from TBODY
    tbody = table_elem.find('TBODY')
    if tbody is not None:
        for tr in tbody.findall('TR'):
            row = []
            for td in tr.findall('TD'):
                cell_text = ''.join(td.itertext()).strip()
                row.append(cell_text)
            if row:  # Skip empty rows
                rows.append(row)
    
    return {
        'headers': headers,
        'rows': rows,
        'context': ''  # Could extract context from preceding P tags if needed
    }


def is_empty_paragraph(text: str) -> bool:
    """
    Check if paragraph is empty or contains only whitespace/formatting.
    
    Args:
        text: Paragraph text
    
    Returns:
        True if empty, False otherwise
    """
    return not text or text.isspace() or text in ['', ' ', '\n', '\t']


# === STEP 4: Validation & Analysis ===

def validate_section_coverage(
    section_index: Dict[str, Dict[str, Any]],
    toc_mapping: Dict[str, str]
) -> Dict[str, Any]:
    """
    Compare extracted sections against toc.yaml structure.
    Reports missing sections and unmapped sections.
    
    Args:
        section_index: Result from build_section_index()
        toc_mapping: Dictionary from load_toc_mapping()
    
    Returns:
        Coverage statistics
    """
    expected_codes = set(toc_mapping.values())
    extracted_codes = set(
        s['section_code'] for s in section_index.values() 
        if s['section_code'] is not None
    )
    
    missing = expected_codes - extracted_codes
    unmapped = sum(1 for s in section_index.values() if s['section_code'] is None)
    
    return {
        'total_expected': len(expected_codes),
        'total_extracted': len(extracted_codes),
        'total_in_xml': len(section_index),
        'unmapped_count': unmapped,
        'missing_sections': sorted(list(missing)),
        'coverage_rate': len(extracted_codes) / len(expected_codes) if expected_codes else 0
    }


# === MAIN EXPERIMENT ===

def main():
    print("=" * 70)
    print("EXPERIMENT 10: XML Structure Exploration")
    print("Strategy: SECTION-N + TITLE hierarchy (NOT USERMARK)")
    print("=" * 70)
    
    results = {
        'experiment': 'exp_10_xml_structure_exploration',
        'date': '2025-10-03',
        'strategy': 'SECTION-N + TITLE hierarchy',
        'target_section': TARGET_SECTION_CODE
    }
    
    # Load TOC mapping
    print("\n[Step 1] Loading TOC mapping from config/toc.yaml...")
    try:
        toc_mapping = load_toc_mapping()
        print(f"  ✓ Loaded {len(toc_mapping)} section mappings")
        print(f"  Example: '{list(toc_mapping.keys())[0]}' → '{list(toc_mapping.values())[0]}'")
        results['toc_sections_count'] = len(toc_mapping)
    except Exception as e:
        print(f"  ✗ Failed to load TOC: {e}")
        return
    
    # Parse FULL XML (skip sample.xml - it's truncated)
    print("\n[Step 2] Parsing FULL XML (155K lines)...")
    if FULL_XML.exists():
        try:
            print(f"  File: {FULL_XML}")
            start_time = time.time()
            full_index = build_section_index(FULL_XML, toc_mapping)
            indexing_time = time.time() - start_time
            
            print(f"  ✓ Built index in {indexing_time:.3f}s")
            print(f"  ✓ Found {len(full_index)} sections in XML")
            
            # Display first few sections
            print("\n  First 10 sections:")
            for i, (atocid, metadata) in enumerate(list(full_index.items())[:10], 1):
                code_str = metadata['section_code'] or 'UNMAPPED'
                print(f"    {i}. Level {metadata['level']}: {metadata['title']}")
                print(f"       Code: {code_str}, ATOCID: {atocid}")
            
            # Extract target section from full XML
            print(f"\n[Step 3] Extracting target section {TARGET_SECTION_CODE} (II. 사업의 내용)...")
            start_time = time.time()
            full_target = extract_section_by_code(full_index, TARGET_SECTION_CODE)
            extraction_time = time.time() - start_time
            
            if full_target:
                print(f"  ✓ Extracted in {extraction_time:.3f}s")
                print(f"    Title: {full_target['title']}")
                print(f"    - Paragraphs: {len(full_target['paragraphs'])}")
                print(f"    - Tables: {len(full_target['tables'])}")
                print(f"    - Subsections: {len(full_target['subsections'])}")
                
                # Show subsection structure
                if full_target['subsections']:
                    print(f"\n  Subsections found:")
                    for i, sub in enumerate(full_target['subsections'][:10], 1):
                        print(f"    {i}. [{sub['section_code']}] {sub['title']}")
                        print(f"       Paragraphs: {len(sub['paragraphs'])}, Tables: {len(sub['tables'])}")
                    
                    if len(full_target['subsections']) > 10:
                        print(f"    ... and {len(full_target['subsections']) - 10} more")
                
                # Show text content preview (paragraphs)
                if full_target['paragraphs']:
                    print(f"\n  ✓ First paragraph preview:")
                    preview = full_target['paragraphs'][0][:200]
                    print(f"    {preview}...")
                else:
                    print(f"\n  ⚠ No direct paragraphs found (content may be in subsections)")
                
                # Show table preview (first table)
                if full_target['tables']:
                    print(f"\n  ✓ First table preview:")
                    table = full_target['tables'][0]
                    if table['headers']:
                        print(f"    Headers: {table['headers'][:5]}")
                    if table['rows']:
                        print(f"    First row: {table['rows'][0][:5]}")
                        print(f"    Total rows: {len(table['rows'])}")
                
                # Debug: Check raw element content
                print(f"\n  Debug: Checking section structure...")
                section_elem = None
                for atocid, metadata in full_index.items():
                    if metadata['section_code'] == TARGET_SECTION_CODE:
                        section_elem = metadata['element']
                        break
                
                if section_elem is not None:
                    # Count all P tags (including nested)
                    all_p_tags = section_elem.findall('.//P')
                    direct_p_tags = section_elem.findall('P')
                    subsection_tags = section_elem.findall('SECTION-2')
                    
                    print(f"    Total <P> tags (including nested): {len(all_p_tags)}")
                    print(f"    Direct <P> tags: {len(direct_p_tags)}")
                    print(f"    Direct <SECTION-2> tags: {len(subsection_tags)}")
                    
                    # Show first few P tag contents
                    if all_p_tags:
                        print(f"\n    First 3 paragraphs content:")
                        for i, p in enumerate(all_p_tags[:3], 1):
                            text = ''.join(p.itertext()).strip()
                            if text:
                                preview = text[:100].replace('\n', ' ')
                                print(f"      {i}. {preview}...")
                    
                    # Show subsection titles
                    if subsection_tags:
                        print(f"\n    Subsection <SECTION-2> titles:")
                        for i, sub in enumerate(subsection_tags[:5], 1):
                            title_elem = sub.find('TITLE')
                            if title_elem is not None:
                                title_text = ''.join(title_elem.itertext()).strip()
                                print(f"      {i}. {title_text}")
                
                results['target_section'] = {
                    'section_code': TARGET_SECTION_CODE,
                    'title': full_target['title'],
                    'paragraphs_count': len(full_target['paragraphs']),
                    'tables_count': len(full_target['tables']),
                    'subsections_count': len(full_target['subsections']),
                    'extraction_time_seconds': extraction_time
                }
            else:
                print(f"  ✗ Section {TARGET_SECTION_CODE} not found in full XML!")
                results['target_section'] = {'error': 'Section not found'}
            
            # Test extracting a specific subsection
            print("\n[Step 4] Testing subsection extraction (020100 - 사업의 개요)...")
            subsection_020100 = extract_section_by_code(full_index, '020100')
            if subsection_020100:
                print(f"  ✓ Extracted: {subsection_020100['title']}")
                print(f"    - Paragraphs: {len(subsection_020100['paragraphs'])}")
                print(f"    - Tables: {len(subsection_020100['tables'])}")
                print(f"    - Subsections: {len(subsection_020100['subsections'])}")
                
                print(f"\n  Full text content:")
                print("  " + "=" * 60)
                for i, para in enumerate(subsection_020100['paragraphs'], 1):
                    print(f"\n  [{i}] {para}")
                print("\n  " + "=" * 60)
                
                if subsection_020100['tables']:
                    print(f"\n  Tables found: {len(subsection_020100['tables'])}")
            else:
                print(f"  ✗ Section 020100 not found")
            
            # Validate coverage
            print("\n[Step 5] Validating XML coverage...")
            full_coverage = validate_section_coverage(full_index, toc_mapping)
            print(f"  ✓ Coverage: {full_coverage['coverage_rate']*100:.1f}%")
            print(f"    Expected: {full_coverage['total_expected']} sections")
            print(f"    Extracted: {full_coverage['total_extracted']} sections")
            print(f"    In XML: {full_coverage['total_in_xml']} sections")
            print(f"    Unmapped: {full_coverage['unmapped_count']} sections")
            
            if full_coverage['missing_sections']:
                print(f"  ⚠ Missing sections: {len(full_coverage['missing_sections'])}")
                # Show first 5 missing sections
                for code in full_coverage['missing_sections'][:5]:
                    # Find section name from toc_mapping
                    section_name = [k for k, v in toc_mapping.items() if v == code]
                    print(f"    - {code}: {section_name[0] if section_name else 'Unknown'}")
                if len(full_coverage['missing_sections']) > 5:
                    print(f"    ... and {len(full_coverage['missing_sections']) - 5} more")
            
            results['full_xml'] = {
                'file': str(FULL_XML),
                'indexing_time_seconds': indexing_time,
                'sections_found': len(full_index),
                'coverage': full_coverage
            }
            
        except Exception as e:
            print(f"  ✗ Error processing full XML: {e}")
            import traceback
            traceback.print_exc()
            results['full_xml'] = {'error': str(e)}
    else:
        print(f"  ⚠ Full XML not found at {FULL_XML}")
        print("    Expected file: experiments/data/xml_sample/20240312000736.xml")
        results['full_xml'] = {'error': 'File not found'}
    
    # Save results
    print("\n[Step 6] Saving results...")
    output_file = OUTPUT_DIR / 'exp_10_results.json'
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Results saved to {output_file}")
    except Exception as e:
        print(f"  ✗ Failed to save results: {e}")
    
    print("\n" + "=" * 70)
    print("EXPERIMENT 10 COMPLETE")
    print("=" * 70)
    
    # Summary
    print("\nSUMMARY:")
    if 'full_xml' in results and 'coverage' in results.get('full_xml', {}):
        coverage = results['full_xml']['coverage']
        print(f"  • Coverage Rate: {coverage['coverage_rate']*100:.1f}%")
        print(f"  • Sections Extracted: {coverage['total_extracted']}/{coverage['total_expected']}")
        print(f"  • Indexing Time: {results['full_xml']['indexing_time_seconds']:.3f}s")
        
        if 'target_section' in results and 'error' not in results['target_section']:
            print(f"  • Target Section: ✓ Extracted successfully")
            print(f"    - Content: {results['target_section']['paragraphs_count']} paragraphs, "
                  f"{results['target_section']['tables_count']} tables, "
                  f"{results['target_section']['subsections_count']} subsections")
        else:
            print(f"  • Target Section: ✗ Not found")
    else:
        print("  ⚠ Full XML processing incomplete")
    
    print("\nNext steps:")
    print("  1. Review exp_10_results.json for detailed metrics")
    print("  2. Inspect extracted content manually")
    print("  3. Document findings in FINDINGS.md")
    print("  4. Proceed to write unit tests (TDD)")


if __name__ == '__main__':
    main()

