"""
Experiment 3: End-to-End Pipeline

Goal: Test complete workflow from search to storage
- Search filings
- Filter by report type
- Download documents
- Unzip and organize
- Save results
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
print("EXPERIMENT 3: END-TO-END PIPELINE")
print("=" * 80)

# Setup
print("\n[Setup] Loading environment configuration...")
load_dotenv()
api_key = os.getenv("OPENDART_API_KEY")

if not api_key:
    raise ValueError("OPENDART_API_KEY not found in .env file")

dart.set_api_key(api_key=api_key)
print(f"✓ API Key configured: {api_key[:10]}***")


def download_and_store_filings(
    stock_code: str,
    start_date: str,
    end_date: str,
    report_filter: list = None,
    max_downloads: int = 3
):
    """
    Full pipeline: Search → Filter → Download → Store
    """
    print(f"\n[Pipeline] Starting pipeline for stock code {stock_code}")
    print(f"  Date range: {start_date} to {end_date}")
    print(f"  Max downloads: {max_downloads}")
    
    # 1. Search filings
    print("\n[1/4] Searching filings...")
    corp_list = dart.get_corp_list()
    corp = corp_list.find_by_stock_code(stock_code)
    
    if not corp:
        raise ValueError(f"No company found with stock code {stock_code}")
    
    print(f"  ✓ Company: {corp.corp_name}")
    
    filings = corp.search_filings(
        bgn_de=start_date.replace('-', ''),
        end_de=end_date.replace('-', '')
    )
    print(f"  ✓ Found {len(filings)} total filings")
    
    # 2. Filter by report type
    print("\n[2/4] Filtering by report type...")
    if report_filter:
        print(f"  Filter: {report_filter}")
        filings = [f for f in filings if any(r in f.report_nm for r in report_filter)]
        print(f"  ✓ Filtered to {len(filings)} matching filings")
    
    download_count = min(max_downloads, len(filings))
    print(f"\n[3/4] Downloading and extracting {download_count} filings...")
    
    # 3. Download and store
    results = []
    start_time = time.time()
    
    for i, filing in enumerate(filings[:max_downloads], 1):
        print(f"\n  [{i}/{download_count}] Processing: {filing.rcept_no}")
        print(f"      Report: {filing.report_nm}")
        print(f"      Date: {filing.rcept_dt}")
        
        try:
            # Create organized directory structure
            stock_dir = Path(f"./experiments/data/raw/{stock_code}")
            stock_dir.mkdir(parents=True, exist_ok=True)
            
            # Download
            zip_path = stock_dir / f"{filing.rcept_no}.zip"
            
            if not zip_path.exists():
                print(f"      Downloading...")
                dl_start = time.time()
                filings_api.download_document(
                    path=str(stock_dir) + "/",
                    rcept_no=filing.rcept_no
                )
                dl_elapsed = time.time() - dl_start
                size_mb = zip_path.stat().st_size / (1024 * 1024)
                print(f"      ✓ Downloaded: {filing.rcept_no}.zip ({size_mb:.2f} MB in {dl_elapsed:.2f}s)")
            else:
                size_mb = zip_path.stat().st_size / (1024 * 1024)
                print(f"      ⊙ Already exists: {filing.rcept_no}.zip ({size_mb:.2f} MB)")
            
            # Unzip
            extract_dir = stock_dir / filing.rcept_no
            extract_dir.mkdir(exist_ok=True)
            
            print(f"      Extracting...")
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(extract_dir)
            
            xml_file = extract_dir / f"{filing.rcept_no}.xml"
            if xml_file.exists():
                xml_size_mb = xml_file.stat().st_size / (1024 * 1024)
                print(f"      ✓ Extracted: {xml_file.name} ({xml_size_mb:.2f} MB)")
            else:
                print(f"      ✗ XML file not found!")
            
            # Store result
            results.append({
                "rcept_no": filing.rcept_no,
                "report_nm": filing.report_nm,
                "rcept_dt": filing.rcept_dt,
                "zip_path": str(zip_path),
                "xml_path": str(xml_file),
                "zip_size_mb": round(size_mb, 2),
                "xml_size_mb": round(xml_size_mb, 2) if xml_file.exists() else 0,
                "status": "success"
            })
            
        except Exception as e:
            print(f"      ✗ Error: {e}")
            results.append({
                "rcept_no": filing.rcept_no,
                "report_nm": filing.report_nm,
                "status": "failed",
                "error": str(e)
            })
    
    total_elapsed = time.time() - start_time
    print(f"\n  Pipeline execution time: {total_elapsed:.2f}s")
    
    return results


# Run pipeline
print("\n[Execution] Running full pipeline...")
# Note: Using 2023-2024 range to capture annual reports filed in March 2024
pipeline_results = download_and_store_filings(
    stock_code="005930",
    start_date="2023-01-01",
    end_date="2024-12-31",
    report_filter=["사업보고서", "반기보고서"],
    max_downloads=2  # Reduced to 2 for faster testing
)

# Save results
print("\n[4/4] Saving pipeline results...")
output_file = Path("./experiments/data/pipeline_results.json")
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(pipeline_results, f, indent=2, ensure_ascii=False)

success_count = len([r for r in pipeline_results if r['status'] == 'success'])
failed_count = len([r for r in pipeline_results if r['status'] == 'failed'])

print(f"✓ Results saved to {output_file}")

print("\n" + "=" * 80)
print("✅ EXPERIMENT 3 COMPLETE: End-to-end pipeline successful!")
print("=" * 80)

print(f"\nPipeline Summary:")
print(f"  - Success: {success_count}")
print(f"  - Failed: {failed_count}")
print(f"  - Total processed: {len(pipeline_results)}")

if success_count > 0:
    total_zip_size = sum(r.get('zip_size_mb', 0) for r in pipeline_results if r['status'] == 'success')
    total_xml_size = sum(r.get('xml_size_mb', 0) for r in pipeline_results if r['status'] == 'success')
    print(f"  - Total ZIP size: {total_zip_size:.2f} MB")
    print(f"  - Total XML size: {total_xml_size:.2f} MB")

print("\nResults details:")
for i, result in enumerate(pipeline_results, 1):
    status_icon = "✓" if result['status'] == 'success' else "✗"
    print(f"  {status_icon} {i}. {result['rcept_no']} - {result['status']}")
    if result['status'] == 'failed':
        print(f"      Error: {result.get('error', 'Unknown error')}")

