"""
Parallel Pipeline for DART Disclosure Data (Backfill Mode)

Provides multiprocess parallelization for processing existing XML files.
Uses ProcessPoolExecutor to achieve 6-8x speedup on CPU-bound XML parsing.

Key Features:
- Process-safe MongoDB connections (new client per worker)
- Statistics aggregation from worker results
- Configurable worker count (max_workers parameter)
- Real-time progress tracking
- Failure tracking with CSV export

Design:
- Each worker creates its own StorageService with isolated MongoDB connection
- No shared state between processes (all aggregation via return values)
- Optimized for backfill_only=True mode (local XML files only)

Usage:
    storage = StorageService()
    pipeline = BackfillPipelineParallel(storage_service=storage)

    stats = pipeline.download_and_parse(
        years=[2023, 2024],
        report_type="A001",
        max_workers=8,  # Configure parallel workers
        backfill_only=True
    )
"""

from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from collections import defaultdict
import logging

from dart_fss_text.api.pipeline import DisclosurePipeline, parse_xml_to_sections
from dart_fss_text.services.storage_service import StorageService
from dart_fss_text.models.requests import SearchFilingsRequest

logger = logging.getLogger(__name__)


def _process_existing_xml_worker(
    xml_info: Dict[str, Any],
    mongo_config: Dict[str, str],
    report_type: str,
    target_section_codes: Optional[List[str]]
) -> Dict[str, Any]:
    """
    Worker function for processing a single XML file in parallel.

    Runs in child process with isolated MongoDB connection.
    Creates new StorageService per worker to ensure process safety.

    Args:
        xml_info: Dictionary with XML file metadata:
            - xml_path: Path to XML file
            - rcept_no: Receipt number
            - rcept_dt: Receipt date (YYYYMMDD)
            - stock_code: Stock code (6 digits)
            - corp_code: Corporation code (8 digits)
            - corp_name: Company name
            - year: Filing year
        mongo_config: MongoDB connection configuration:
            - uri: MongoDB connection string
            - database: Database name
            - collection: Collection name
        report_type: Report type code (e.g., "A001")
        target_section_codes: Optional list of section codes to extract

    Returns:
        Result dictionary:
        {
            'success': bool,
            'stock_code': str,
            'year': int,
            'rcept_no': str,
            'stats': {
                'reports': int,
                'sections': int,
                'failed': int,
                'skipped': int
            },
            'failure': dict (only if success=False)
        }
    """
    # Create NEW MongoDB connection in this child process
    # CRITICAL: MongoClient is NOT fork-safe, must create per-process
    storage = StorageService(
        mongo_uri=mongo_config['uri'],
        database=mongo_config['database'],
        collection=mongo_config['collection']
    )

    try:
        xml_path = Path(xml_info['xml_path'])

        # Log start of processing
        start_msg = f"  → Processing {xml_info['rcept_no']} ({xml_info['stock_code']} - {xml_info['corp_name']})"
        print(start_msg)

        # Create mock filing object for parser
        class MockFiling:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        filing = MockFiling(
            rcept_no=xml_info['rcept_no'],
            rcept_dt=xml_info['rcept_dt'],
            corp_code=xml_info['corp_code'],
            stock_code=xml_info['stock_code'],
            corp_name=xml_info['corp_name'],
            report_nm=f"사업보고서 ({xml_info['year']})"
        )

        # Parse XML (CPU-bound - this is why we use multiprocessing)
        sections = parse_xml_to_sections(
            xml_path=xml_path,
            filing=filing,
            report_type=report_type,
            target_section_codes=target_section_codes
        )

        parse_msg = f"  ✓ Parsed {len(sections)} sections from {xml_info['rcept_no']}"
        print(parse_msg)

        # Insert to MongoDB (with BSON truncation handling)
        result = storage.insert_sections(sections)

        return {
            'success': True,
            'stock_code': xml_info['stock_code'],
            'year': xml_info['year'],
            'rcept_no': xml_info['rcept_no'],
            'stats': {
                'reports': 1,
                'sections': len(sections),
                'failed': 0,
                'skipped': 0
            }
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(
            f"Worker failed to process {xml_info['rcept_no']} "
            f"({xml_info['stock_code']} - {xml_info['corp_name']}): {error_msg}",
            exc_info=True
        )

        return {
            'success': False,
            'stock_code': xml_info['stock_code'],
            'year': xml_info['year'],
            'rcept_no': xml_info['rcept_no'],
            'stats': {
                'reports': 0,
                'sections': 0,
                'failed': 1,
                'skipped': 0
            },
            'failure': {
                'corp_code': xml_info['corp_code'],
                'stock_code': xml_info['stock_code'],
                'corp_name': xml_info['corp_name'],
                'rcept_no': xml_info['rcept_no'],
                'rcept_dt': xml_info['rcept_dt'],
                'year': str(xml_info['year']),
                'error': error_msg,
                'error_type': type(e).__name__
            }
        }

    finally:
        # Clean up MongoDB connection
        storage.close()


class BackfillPipelineParallel(DisclosurePipeline):
    """
    Parallel version of DisclosurePipeline optimized for backfill mode.

    Uses multiprocessing to parallelize XML parsing and MongoDB insertion.
    Designed for processing existing local XML files without API calls.

    Key Differences from DisclosurePipeline:
    - Parallel processing with configurable worker count
    - Process-safe MongoDB connections (new client per worker)
    - Return-based statistics aggregation (no shared state)
    - Optimized for backfill_only=True workflow

    Performance:
    - Expected speedup: 6-8x with 8 workers
    - Bottleneck: CPU-bound XML parsing
    - Resource usage: N workers × MongoDB connections

    Example:
        storage = StorageService()
        pipeline = BackfillPipelineParallel(storage_service=storage)

        stats = pipeline.download_and_parse(
            years=[2023, 2024],
            report_type="A001",
            max_workers=8,
            backfill_only=True
        )
    """

    def download_and_parse(
        self,
        stock_codes: Union[str, List[str]] = "all",
        years: Union[int, List[int]] = None,
        report_type: str = "A001",
        target_section_codes: Optional[List[str]] = None,
        skip_existing: bool = True,
        base_dir: str = "data",
        backfill_only: bool = True,
        max_workers: int = 8
    ) -> Dict[str, int]:
        """
        Parallel workflow for processing existing XML files.

        Args:
            stock_codes: Company stock codes ("all", single code, or list)
            years: Years to process (required)
            report_type: DART report type code (default: "A001")
            target_section_codes: Optional section codes to extract
            skip_existing: Skip combinations already in MongoDB (default: True)
            base_dir: Base directory for XML files (default: "data")
            backfill_only: Must be True for this parallel implementation
            max_workers: Number of parallel worker processes (default: 8)

        Returns:
            Statistics dictionary:
            {
                'reports': int,   # Reports successfully processed
                'sections': int,  # Total sections stored
                'failed': int,    # Failed operations
                'skipped': int    # Skipped (already in MongoDB)
            }

        Raises:
            ValueError: If backfill_only is False (not supported yet)
            ValueError: If years is None

        Example:
            # Process all companies, 2019-2025, with 8 workers
            stats = pipeline.download_and_parse(
                years=list(range(2019, 2026)),
                report_type="A001",
                target_section_codes=["020000", "020100"],
                max_workers=8,
                backfill_only=True
            )
        """
        # Validate parameters
        if years is None:
            raise ValueError(
                "years parameter is required. "
                "Example: years=[2023, 2024] or years=2024"
            )

        if not backfill_only:
            raise ValueError(
                "BackfillPipelineParallel currently only supports backfill_only=True. "
                "For live API downloads, use DisclosurePipeline."
            )

        # Normalize inputs
        stock_codes = self._normalize_stock_codes(stock_codes)
        years = self._normalize_years(years)

        logger.info(
            f"Starting parallel backfill: {len(stock_codes)} companies, "
            f"{len(years)} years, {max_workers} workers"
        )
        print(f"\n{'='*80}")
        print(f"PARALLEL BACKFILL MODE: {max_workers} workers")
        print(f"{'='*80}")

        # Prepare MongoDB config for workers (must be serializable)
        mongo_config = {
            'uri': self._storage.mongo_uri,
            'database': self._storage.database_name,
            'collection': self._storage.collection_name
        }

        # Build existing combinations set for skip-existing optimization
        existing_combinations = set()
        existing_rcept_nos = set()

        if skip_existing:
            logger.info("Building index of existing data in MongoDB...")
            print("  → Building index of existing data...")

            # Get existing company-year combinations
            pipeline_agg = [
                {'$group': {
                    '_id': {
                        'stock_code': '$stock_code',
                        'year': '$year'
                    }
                }}
            ]
            existing_docs = self._storage.collection.aggregate(pipeline_agg)
            existing_combinations = {
                (doc['_id']['stock_code'], doc['_id']['year'])
                for doc in existing_docs
            }

            # Get all existing rcept_no values (for per-filing check)
            # This is a single query that replaces thousands of individual count_documents calls
            existing_rcept_nos = set(
                self._storage.collection.distinct('rcept_no')
            )

            logger.info(
                f"Found {len(existing_combinations)} existing (stock_code, year) combinations, "
                f"{len(existing_rcept_nos)} existing rcept_no values in MongoDB"
            )
            print(f"  ✓ Found {len(existing_combinations)} existing company-year combinations")
            print(f"  ✓ Found {len(existing_rcept_nos):,} existing filings (rcept_no)")

        # Scan file system for all XML files to process
        xml_files_to_process = []

        print(f"\n  → Scanning file system for XML files...")
        skipped_company_years = 0
        scanned_company_years = 0

        for year in years:
            for stock_code in stock_codes:
                # Skip if already in MongoDB (company-year level)
                if skip_existing and (stock_code, str(year)) in existing_combinations:
                    skipped_company_years += 1
                    if skipped_company_years % 500 == 0:
                        print(f"    ⏭️  Skipped {skipped_company_years} company-years (already have data)...")
                    continue

                # Check for existing XML files
                data_dir = Path(base_dir) / str(year) / stock_code
                if not data_dir.exists():
                    continue

                scanned_company_years += 1

                # Get company name for logging
                corp_data = self._corp_list_service.find_by_stock_code(stock_code)
                corp_name = corp_data.get('corp_name', 'Unknown') if corp_data else 'Unknown'
                corp_code = corp_data.get('corp_code', stock_code) if corp_data else stock_code

                if scanned_company_years <= 10:  # Log first 10 scans
                    print(f"    📂 Scanning {stock_code} ({corp_name}) - {year}...")

                # Process each rcept_no directory
                for rcept_dir in sorted(data_dir.iterdir()):
                    if not rcept_dir.is_dir():
                        continue

                    rcept_no = rcept_dir.name

                    # Check if already in MongoDB (per-filing check)
                    # Fast set lookup instead of MongoDB query
                    if skip_existing and rcept_no in existing_rcept_nos:
                        logger.debug(f"Skipping {rcept_no} - already in MongoDB")
                        continue

                    # Find main XML file
                    main_xml = rcept_dir / f"{rcept_no}.xml"
                    if not main_xml.exists():
                        logger.warning(f"Main XML {rcept_no}.xml not found in {rcept_dir}")
                        continue

                    # Add to processing queue
                    rcept_dt = rcept_no[:8]  # Extract date from rcept_no
                    xml_files_to_process.append({
                        'xml_path': str(main_xml),
                        'rcept_no': rcept_no,
                        'rcept_dt': rcept_dt,
                        'stock_code': stock_code,
                        'corp_code': corp_code,
                        'corp_name': corp_name,
                        'year': year
                    })

        total_files = len(xml_files_to_process)
        logger.info(
            f"Found {total_files} XML files to process "
            f"(skipped {skipped_company_years} company-years, scanned {scanned_company_years} company-years)"
        )
        print(f"\n  📊 Scan Summary:")
        print(f"    - Company-years skipped (already have data): {skipped_company_years}")
        print(f"    - Company-years scanned (checking for new files): {scanned_company_years}")
        print(f"    - XML files found to process: {total_files}")

        if total_files == 0:
            print("\n  ℹ️  No new files to process")
            if skipped_company_years > 0:
                print(f"      (Skipped {skipped_company_years} company-years that already have data)")
            return self._init_statistics()

        # Process XML files in parallel
        print(f"\n{'='*80}")
        print(f"PROCESSING {total_files} FILES WITH {max_workers} WORKERS")
        print(f"{'='*80}\n")

        stats = self._init_statistics()
        failures_by_year = defaultdict(list)

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_xml = {
                executor.submit(
                    _process_existing_xml_worker,
                    xml_info,
                    mongo_config,
                    report_type,
                    target_section_codes
                ): xml_info
                for xml_info in xml_files_to_process
            }

            # Collect results as they complete (for real-time progress)
            processed = 0
            for future in as_completed(future_to_xml):
                result = future.result()

                # Aggregate statistics
                stats['reports'] += result['stats']['reports']
                stats['sections'] += result['stats']['sections']
                stats['failed'] += result['stats']['failed']
                stats['skipped'] += result['stats']['skipped']

                # Track failures
                if not result['success']:
                    year = result['year']
                    failures_by_year[year].append(result['failure'])

                # Progress update
                processed += 1
                if processed % 10 == 0 or not result['success']:
                    progress_msg = (
                        f"Progress: {processed}/{total_files} "
                        f"({stats['reports']} success, {stats['failed']} failed)"
                    )
                    print(progress_msg)
                    logger.info(progress_msg)

        # Final progress update
        print(f"\n{'='*80}")
        print(f"PARALLEL PROCESSING COMPLETE")
        print(f"{'='*80}")
        print(f"  ✓ Processed: {processed}/{total_files}")
        print(f"  ✓ Success: {stats['reports']}")
        print(f"  ✗ Failed: {stats['failed']}")
        print(f"  📊 Total sections: {stats['sections']}")

        # Save failure CSVs (in parent process only)
        for year, failures in failures_by_year.items():
            if failures:
                self._save_failures_csv(failures, year, base_dir)
                print(f"  📄 Saved failure CSV for year {year}: {len(failures)} failures")

        logger.info(
            f"Parallel backfill complete: {stats['reports']} reports, "
            f"{stats['sections']} sections, {stats['failed']} failures"
        )

        return stats
