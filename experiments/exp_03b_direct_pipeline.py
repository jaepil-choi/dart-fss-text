"""
Experiment 3B: Direct Pipeline Test (Using Known rcept_no)

Goal: Test download/extract pipeline with known document IDs
Since filing search returned limited results, we'll use known rcept_nos
"""

import os
import json
import time
import zipfile
from pathlib import Path
from dotenv import load_dotenv
import dart_fss as dart
from dart_fss.api import filings as filings_api

print("=" * 80)
print("EXPERIMENT 3B: DIRECT DOWNLOAD PIPELINE")
print("=" * 80)

# Setup
print("\n[Setup] Loading environment configuration...")
load_dotenv()
api_key = os.getenv("OPENDART_API_KEY")

if not api_key:
    raise ValueError("OPENDART_API_KEY not found in .env file")

dart.set_api_key(api_key=api_key)
print(f"✓ API Key configured: {api_key[:10]}***")

# Known documents to download (Samsung annual report)
test_documents = [
    {
        'rcept_no': '20250814003156',
        'stock_code': '005930',
        'report_nm': '사업보고서 (Annual Report)',
        'company': '삼성전자'
    }
]

print(f"\n[Pipeline] Processing {len(test_documents)} known document(s)...")

results = []
start_time = time.time()

for i, doc in enumerate(test_documents, 1):
    print(f"\n[{i}/{len(test_documents)}] Processing: {doc['rcept_no']}")
    print(f"  Company: {doc['company']}")
    print(f"  Report: {doc['report_nm']}")
    
    try:
        # Create organized directory structure
        stock_dir = Path(f"./experiments/data/raw/{doc['stock_code']}")
        stock_dir.mkdir(parents=True, exist_ok=True)
        
        # Download
        zip_path = stock_dir / f"{doc['rcept_no']}.zip"
        
        if not zip_path.exists():
            print(f"  Downloading...")
            dl_start = time.time()
            filings_api.download_document(
                path=str(stock_dir) + "/",
                rcept_no=doc['rcept_no']
            )
            dl_elapsed = time.time() - dl_start
            size_mb = zip_path.stat().st_size / (1024 * 1024)
            print(f"  ✓ Downloaded: {doc['rcept_no']}.zip ({size_mb:.2f} MB in {dl_elapsed:.2f}s)")
        else:
            size_mb = zip_path.stat().st_size / (1024 * 1024)
            print(f"  ⊙ Already exists: {doc['rcept_no']}.zip ({size_mb:.2f} MB)")
        
        # Unzip
        extract_dir = stock_dir / doc['rcept_no']
        extract_dir.mkdir(exist_ok=True)
        
        print(f"  Extracting...")
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(extract_dir)
        
        xml_file = extract_dir / f"{doc['rcept_no']}.xml"
        if xml_file.exists():
            xml_size_mb = xml_file.stat().st_size / (1024 * 1024)
            print(f"  ✓ Extracted: {xml_file.name} ({xml_size_mb:.2f} MB)")
        else:
            print(f"  ✗ XML file not found!")
            raise FileNotFoundError(f"XML not found: {xml_file}")
        
        # Quick XML validation with lxml
        print(f"  Validating XML...")
        try:
            from lxml import etree
            parser = etree.XMLParser(recover=True, encoding='utf-8')
            tree = etree.parse(str(xml_file), parser)
            root = tree.getroot()
            
            total_elements = len(list(root.iter()))
            p_tags = len(root.findall(".//P"))
            table_tags = len(root.findall(".//TABLE"))
            usermark_elems = len(root.findall(".//*[@USERMARK]"))
            
            print(f"  ✓ XML valid: {total_elements:,} elements, {usermark_elems:,} USERMARK, {table_tags:,} tables")
            
            # Store result
            results.append({
                "rcept_no": doc['rcept_no'],
                "stock_code": doc['stock_code'],
                "company": doc['company'],
                "report_nm": doc['report_nm'],
                "zip_path": str(zip_path),
                "xml_path": str(xml_file),
                "zip_size_mb": round(size_mb, 2),
                "xml_size_mb": round(xml_size_mb, 2),
                "xml_elements": total_elements,
                "xml_tables": table_tags,
                "xml_usermarks": usermark_elems,
                "status": "success"
            })
            
        except Exception as e:
            print(f"  ✗ XML validation failed: {e}")
            raise
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        results.append({
            "rcept_no": doc['rcept_no'],
            "status": "failed",
            "error": str(e)
        })

total_elapsed = time.time() - start_time

# Save results
print("\n[Saving] Saving pipeline results...")
output_file = Path("./experiments/data/direct_pipeline_results.json")
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"✓ Results saved to {output_file}")

print("\n" + "=" * 80)
print("✅ EXPERIMENT 3B COMPLETE: Direct pipeline successful!")
print("=" * 80)

success_count = len([r for r in results if r['status'] == 'success'])
failed_count = len([r for r in results if r['status'] == 'failed'])

print(f"\nPipeline Summary:")
print(f"  - Success: {success_count}")
print(f"  - Failed: {failed_count}")
print(f"  - Total processed: {len(results)}")
print(f"  - Total time: {total_elapsed:.2f}s")

if success_count > 0:
    total_zip_size = sum(r.get('zip_size_mb', 0) for r in results if r['status'] == 'success')
    total_xml_size = sum(r.get('xml_size_mb', 0) for r in results if r['status'] == 'success')
    total_elements = sum(r.get('xml_elements', 0) for r in results if r['status'] == 'success')
    print(f"  - Total ZIP size: {total_zip_size:.2f} MB")
    print(f"  - Total XML size: {total_xml_size:.2f} MB")
    print(f"  - Total XML elements: {total_elements:,}")

print("\nDetailed Results:")
for i, result in enumerate(results, 1):
    status_icon = "✓" if result['status'] == 'success' else "✗"
    print(f"  {status_icon} {i}. {result['rcept_no']} - {result.get('company', 'N/A')}")
    if result['status'] == 'success':
        print(f"      Tables: {result['xml_tables']:,}, USERMARK: {result['xml_usermarks']:,}")

