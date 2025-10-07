from dart_fss_text.services.storage_service import StorageService
from dart_fss_text.api import DisclosurePipeline, TextQuery
from dart_fss_text.config import get_app_config
from datetime import datetime


config = get_app_config()
print(f"  ✓ Config loaded")
print(f"    - MongoDB: {config.mongodb_uri}")
print(f"    - Database: {config.mongodb_database}")
print(f"    - Collection: {config.mongodb_collection}")
print(f"    - API Key: {'***' + config.opendart_api_key[-4:]}")

# 1. MongoDB 연결
storage = StorageService()
print(f"  ✓ Connected to MongoDB: {config.mongodb_database}.{config.mongodb_collection}")

with open("not_pennystock.txt", "r") as f:
    not_pennystock = f.read().splitlines()

print(f"  ✓ Not Pennystocks: {len(not_pennystock)}")

# years = list(range(2010, 2025))
years = [2023, 2024, 2025]
yers = years[::-1] # From the most recent year to the oldest year
print(f"  ✓ Years: {years}")

print("  - Clearing previous data...")
storage.collection.delete_many({})
print(f"  ✓ Collection cleared")

# 2. 보고서 다운로드 및 파싱
print("\n[Step 3] Initializing DisclosurePipeline...")
pipeline = DisclosurePipeline(storage_service=storage)
print(f"  ✓ DisclosurePipeline ready")

start_time = datetime.now()

stats = pipeline.download_and_parse(
    stock_codes=not_pennystock,  # 삼성전자, SK하이닉스
    years=years,
    report_type="A001",  # 사업보고서 (연간) --> config/types.yaml 참조
    target_section_codes=["020100"]  # Only extract "1. 사업의 개요" (Business Overview)
)

elapsed = (datetime.now() - start_time).total_seconds()
print(f"  ✓ Completed in {elapsed:.1f} seconds")

print()
print("  Statistics:")
print(f"    - Reports processed: {stats['reports']}")
print(f"    - Sections stored: {stats['sections']}")
print(f"    - Failed: {stats['failed']}")
print()