"""
Experiment 1: Direct Document Download

Goal: Validate basic download mechanics with a known rcept_no
- Load API key from .env
- Download document by rcept_no
- Extract ZIP archive
- Quick XML sanity check
"""

import os
import time
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from dotenv import load_dotenv
import dart_fss as dart

print("=" * 80)
print("EXPERIMENT 1: DIRECT DOCUMENT DOWNLOAD")
print("=" * 80)

# Step 1.1: Environment Configuration
print("\n[Step 1.1] Loading environment configuration...")
load_dotenv()
api_key = os.getenv("OPENDART_API_KEY")

if not api_key:
    raise ValueError("OPENDART_API_KEY not found in .env file")

dart.set_api_key(api_key=api_key)
print(f"✓ API Key configured: {api_key[:10]}***")
print(f"✓ dart-fss version: {dart.__version__}")

# Step 1.2: Download Document by rcept_no
print("\n[Step 1.2] Downloading document...")
from dart_fss.api import filings

rcept_no = "20250814003156"  # Samsung Electronics
download_path = Path("./experiments/data/")
download_path.mkdir(parents=True, exist_ok=True)

print(f"Target rcept_no: {rcept_no}")
print(f"Download path: {download_path}")
print(f"Initiating download...")

start_time = time.time()

result = filings.download_document(
    path=str(download_path) + "/",
    rcept_no=rcept_no
)

elapsed = time.time() - start_time
print(f"✓ Download completed in {elapsed:.2f}s")
print(f"  Result: {result}")

# Verify file exists
zip_file = download_path / f"{rcept_no}.zip"
if zip_file.exists():
    size_mb = zip_file.stat().st_size / (1024 * 1024)
    print(f"✓ ZIP file created: {zip_file}")
    print(f"  Size: {size_mb:.2f} MB")
else:
    raise FileNotFoundError(f"Expected file not found: {zip_file}")

# Step 1.3: Extract ZIP Archive
print("\n[Step 1.3] Extracting ZIP archive...")
zip_path = download_path / f"{rcept_no}.zip"
extract_path = download_path / rcept_no

extract_path.mkdir(exist_ok=True)

print(f"Extracting {zip_path.name}...")
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    file_list = zip_ref.namelist()
    print(f"  Files in archive: {file_list}")
    zip_ref.extractall(extract_path)

# List extracted files
extracted_files = list(extract_path.glob("*"))
print(f"✓ Extracted {len(extracted_files)} file(s):")
for f in extracted_files:
    size_mb = f.stat().st_size / (1024 * 1024)
    print(f"  - {f.name} ({size_mb:.2f} MB)")

# Locate XML file
xml_file = extract_path / f"{rcept_no}.xml"
if xml_file.exists():
    print(f"✓ XML file found: {xml_file.name}")
else:
    xml_files = list(extract_path.glob("*.xml"))
    if xml_files:
        xml_file = xml_files[0]
        print(f"✓ XML file found (alternate name): {xml_file.name}")
    else:
        raise FileNotFoundError(f"No XML file found in {extract_path}")

# Step 1.4: Quick XML Sanity Check
print("\n[Step 1.4] Performing XML sanity check...")
print("Parsing XML...")

tree = None
root = None
parser_used = None

# Try standard ElementTree first
try:
    print("  Trying xml.etree.ElementTree parser...")
    tree = ET.parse(xml_file)
    root = tree.getroot()
    parser_used = "ElementTree"
    print(f"  ✓ Parsed with ElementTree")
except ET.ParseError as e:
    print(f"  ✗ ElementTree failed: {e}")
    
    # Try lxml if available
    try:
        print("  Trying lxml parser (more forgiving)...")
        from lxml import etree
        tree = etree.parse(str(xml_file))
        root = tree.getroot()
        parser_used = "lxml"
        print(f"  ✓ Parsed with lxml")
    except ImportError:
        print(f"  ✗ lxml not available, install with: poetry add lxml")
        raise
    except Exception as e:
        print(f"  ✗ lxml also failed: {e}")
        
        # Try lxml with recover mode (tolerates malformed XML)
        try:
            print("  Trying lxml with recover=True (very forgiving)...")
            from lxml import etree
            parser = etree.XMLParser(recover=True, encoding='utf-8')
            tree = etree.parse(str(xml_file), parser)
            root = tree.getroot()
            parser_used = "lxml (recover mode)"
            print(f"  ✓ Parsed with lxml in recover mode")
            print(f"  ⚠ Warning: Document has malformed XML, some data may be lost")
        except Exception as e2:
            print(f"  ✗ lxml recover mode also failed: {e2}")
            raise

if root is not None:
    print(f"✓ XML parsed successfully with {parser_used}")
    print(f"  Root tag: <{root.tag}>")
    print(f"  Root attributes: {root.attrib}")
    
    total_elements = len(list(root.iter()))
    print(f"  Total elements in tree: {total_elements:,}")
    
    # Quick check for expected element types
    p_tags = root.findall(".//P")
    table_tags = root.findall(".//TABLE")
    span_tags = root.findall(".//SPAN")
    usermark_elems = root.findall(".//*[@USERMARK]")
    
    print(f"  Element counts:")
    print(f"    <P> tags: {len(p_tags):,}")
    print(f"    <TABLE> tags: {len(table_tags):,}")
    print(f"    <SPAN> tags: {len(span_tags):,}")
    print(f"    Elements with USERMARK: {len(usermark_elems):,}")
else:
    raise RuntimeError("Failed to parse XML with any available parser")

print("\n" + "=" * 80)
print("✅ EXPERIMENT 1 COMPLETE: Download and extraction successful!")
print("=" * 80)
print(f"\nSummary:")
print(f"  - Download time: {elapsed:.2f}s")
print(f"  - File size: {size_mb:.2f} MB")
print(f"  - Total XML elements: {total_elements:,}")
print(f"  - USERMARK elements: {len(usermark_elems):,}")

