"""
Batch Enrichment System
Processes brands based on priority ranking with Apollo API or manual enrichment
"""

import time
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
from enrichment.ranking_system import EnrichmentRankingSystem
from enrichment.orchestrator import IntegratedEnrichmentSystem
from core.database import BrandDatabaseV2

logger = logging.getLogger(__name__)

class BatchEnrichmentProcessor:
    """Processes enrichment queue based on priority rankings"""

    def __init__(self, db_path: str = 'data/brands.db', use_apollo: bool = False):
        self.db_path = db_path
        self.use_apollo = use_apollo
        self.ranking_system = EnrichmentRankingSystem(db_path)
        self.enrichment_system = IntegratedEnrichmentSystem(db_path)
        self.brand_db = BrandDatabaseV2(db_path)

        # Rate limiting settings
        self.DELAY_BETWEEN_BRANDS = 3  # Seconds between brands
        self.DELAY_BETWEEN_TIERS = 30  # Seconds between tier processing
        self.MAX_FAILURES = 3  # Max consecutive failures before stopping

    def process_tier(self, tier: int, limit: Optional[int] = None) -> Dict:
        """
        Process brands in a specific tier

        Args:
            tier: Tier number (1-5)
            limit: Maximum number of brands to process

        Returns:
            Processing statistics
        """
        logger.info(f"Processing Tier {tier} brands")

        # Get queue for this tier
        queue = self.ranking_system.get_enrichment_queue(tier, exclude_enriched=True)

        if not queue:
            logger.info(f"No unenriched brands in Tier {tier}")
            return {
                'tier': tier,
                'total_brands': 0,
                'processed': 0,
                'successful': 0,
                'failed': 0,
                'skipped': 0
            }

        # Apply limit if specified
        if limit:
            queue = queue[:limit]

        stats = {
            'tier': tier,
            'total_brands': len(queue),
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'results': []
        }

        consecutive_failures = 0

        for i, brand_info in enumerate(queue, 1):
            brand_name = brand_info['brand_name']

            logger.info(f"[{i}/{len(queue)}] Processing: {brand_name} (Score: {brand_info['score']})")

            try:
                # Check if already enriched (double-check)
                brand = self.brand_db.get_brand(brand_name)
                if brand and brand.get('enrichment_data'):
                    logger.info(f"  Skipped: Already enriched")
                    stats['skipped'] += 1
                    continue

                # Attempt enrichment
                if self.use_apollo:
                    result = self._enrich_with_apollo(brand_name, brand_info)
                else:
                    result = self._enrich_with_search(brand_name, brand_info)

                if result['success']:
                    logger.info(f"  Success: {result.get('message', 'Enrichment completed')}")
                    stats['successful'] += 1
                    consecutive_failures = 0
                else:
                    logger.warning(f"  Failed: {result.get('error', 'Unknown error')}")
                    stats['failed'] += 1
                    consecutive_failures += 1

                stats['processed'] += 1
                stats['results'].append({
                    'brand_name': brand_name,
                    'success': result['success'],
                    'details': result
                })

                # Check for too many failures
                if consecutive_failures >= self.MAX_FAILURES:
                    logger.error(f"Too many consecutive failures ({self.MAX_FAILURES}), stopping batch")
                    break

            except Exception as e:
                logger.error(f"  Error processing {brand_name}: {e}")
                stats['failed'] += 1
                consecutive_failures += 1

            # Rate limiting
            if i < len(queue):
                time.sleep(self.DELAY_BETWEEN_BRANDS)

        return stats

    def _enrich_with_search(self, brand_name: str, brand_info: Dict) -> Dict:
        """Enrich using web search"""
        try:
            # Use the integrated enrichment system
            result = self.enrichment_system.enrich_brand(
                brand_name=brand_name,
                fast_mode=True  # Use fast mode for batch processing
            )

            if result.get('website'):
                # Save enrichment data
                enrichment_data = {
                    'url': result['website']['url'],
                    'domain': result['website']['domain'],
                    'confidence': result['website']['confidence'],
                    'source': 'batch_search',
                    'verification_status': 'pending',
                    'updated_date': datetime.now().isoformat(),
                    'title': result['website'].get('title'),
                    'description': result['website'].get('description'),
                    'ranking_score': brand_info['score'],
                    'ranking_tier': brand_info['tier']
                }

                self.brand_db.update_brand(brand_name, {
                    'enrichment_data': json.dumps(enrichment_data)
                })

                return {
                    'success': True,
                    'message': f"Found website: {result['website']['url']}",
                    'website': result['website']
                }

            return {
                'success': False,
                'error': 'No website found'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _enrich_with_apollo(self, brand_name: str, brand_info: Dict) -> Dict:
        """Enrich using Apollo API (placeholder for future implementation)"""
        # This would integrate with Apollo API when available
        # For now, return not implemented
        return {
            'success': False,
            'error': 'Apollo API integration not yet implemented'
        }

    def process_priority_queue(
        self,
        tiers: Optional[List[int]] = None,
        limit_per_tier: Optional[int] = None
    ) -> Dict:
        """
        Process multiple tiers in priority order

        Args:
            tiers: List of tiers to process (default: [1, 2])
            limit_per_tier: Max brands per tier

        Returns:
            Complete processing statistics
        """
        if tiers is None:
            tiers = [1, 2]  # Default to high priority tiers only

        overall_stats = {
            'start_time': datetime.now().isoformat(),
            'tiers_processed': [],
            'total_processed': 0,
            'total_successful': 0,
            'total_failed': 0,
            'total_skipped': 0
        }

        for tier in tiers:
            logger.info(f"\n{'='*60}")
            logger.info(f"Starting Tier {tier} processing")
            logger.info(f"{'='*60}")

            tier_stats = self.process_tier(tier, limit_per_tier)

            overall_stats['tiers_processed'].append(tier_stats)
            overall_stats['total_processed'] += tier_stats['processed']
            overall_stats['total_successful'] += tier_stats['successful']
            overall_stats['total_failed'] += tier_stats['failed']
            overall_stats['total_skipped'] += tier_stats['skipped']

            # Delay between tiers
            if tier != tiers[-1] and tier_stats['processed'] > 0:
                logger.info(f"Waiting {self.DELAY_BETWEEN_TIERS} seconds before next tier...")
                time.sleep(self.DELAY_BETWEEN_TIERS)

        overall_stats['end_time'] = datetime.now().isoformat()

        # Log summary
        logger.info("\n" + "="*60)
        logger.info("BATCH ENRICHMENT COMPLETE")
        logger.info("="*60)
        logger.info(f"Total Processed: {overall_stats['total_processed']}")
        logger.info(f"Successful: {overall_stats['total_successful']}")
        logger.info(f"Failed: {overall_stats['total_failed']}")
        logger.info(f"Skipped: {overall_stats['total_skipped']}")

        return overall_stats

    def get_queue_status(self) -> Dict:
        """Get current queue status for all tiers"""
        status = {}

        for tier in range(1, 6):
            queue = self.ranking_system.get_enrichment_queue(tier, exclude_enriched=True)
            tier_name, description = self.ranking_system.get_tier(
                90 if tier == 1 else 70 if tier == 2 else 50 if tier == 3 else 30 if tier == 4 else 20
            )

            status[f'tier_{tier}'] = {
                'description': description,
                'pending_count': len(queue),
                'top_brands': [
                    {
                        'name': b['brand_name'],
                        'score': b['score'],
                        'sku_count': b['sku_count']
                    }
                    for b in queue[:5]
                ]
            }

        return status


def main():
    """Command-line interface for batch enrichment"""
    import argparse

    parser = argparse.ArgumentParser(description='Batch Enrichment Processor')
    parser.add_argument('--tier', type=int, help='Process specific tier (1-5)')
    parser.add_argument('--limit', type=int, help='Limit number of brands to process')
    parser.add_argument('--apollo', action='store_true', help='Use Apollo API (when available)')
    parser.add_argument('--status', action='store_true', help='Show queue status only')

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    processor = BatchEnrichmentProcessor(use_apollo=args.apollo)

    if args.status:
        # Show queue status
        status = processor.get_queue_status()
        print("\nEnrichment Queue Status:")
        print("=" * 60)

        for tier_key, tier_info in status.items():
            print(f"\n{tier_key.upper()}: {tier_info['description']}")
            print(f"Pending: {tier_info['pending_count']} brands")

            if tier_info['top_brands']:
                print("Top brands in queue:")
                for brand in tier_info['top_brands']:
                    print(f"  - {brand['name']} (Score: {brand['score']}, SKUs: {brand['sku_count']})")

    elif args.tier:
        # Process specific tier
        stats = processor.process_tier(args.tier, args.limit)
        print(f"\nTier {args.tier} Processing Complete:")
        print(f"  Processed: {stats['processed']}")
        print(f"  Successful: {stats['successful']}")
        print(f"  Failed: {stats['failed']}")

    else:
        # Process priority queue (Tier 1 & 2 by default)
        stats = processor.process_priority_queue(
            tiers=[1, 2],
            limit_per_tier=args.limit
        )
        print("\nBatch Processing Complete!")
        print(f"Total Successful: {stats['total_successful']}")
        print(f"Total Failed: {stats['total_failed']}")


if __name__ == "__main__":
    main()