"""
Market Insights Analytics Module
Generates comprehensive market insights from TTB COLA data
"""

import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime
import pandas as pd

class MarketInsightsAnalyzer:
    def __init__(self, db_path='data/database/brands.db'):
        self.db_path = db_path

    def _convert_date_format(self, date_str):
        """Convert between date formats (YYYY-MM-DD to M/D/YYYY and vice versa)"""
        if not date_str:
            return None

        # Try to parse YYYY-MM-DD format
        if '-' in date_str:
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                # Return in M/D/YYYY format for SQL comparison
                return dt.strftime('%-m/%-d/%Y') if hasattr(dt, 'strftime') else f"{dt.month}/{dt.day}/{dt.year}"
            except:
                pass

        return date_str

    def get_comprehensive_insights(self, start_date=None, end_date=None):
        """Generate comprehensive market insights from the database with optional date filtering"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Convert dates to M/D/YYYY format if provided (to match database format)
        if start_date:
            start_date = self._convert_date_format(start_date)
        if end_date:
            end_date = self._convert_date_format(end_date)

        insights = {
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'date_range': {
                'start': start_date if start_date else 'All time',
                'end': end_date if end_date else 'All time'
            },
            'overview': self._get_overview_metrics(cursor, start_date, end_date),
            'geographic_analysis': self._get_geographic_insights(cursor, start_date, end_date),
            'product_analysis': self._get_product_insights(cursor, start_date, end_date),
            'importer_analysis': self._get_importer_insights(cursor, start_date, end_date),
            'market_concentration': self._get_market_concentration(cursor, start_date, end_date),
            'growth_indicators': self._get_growth_indicators(cursor, start_date, end_date),
            'enrichment_quality': self._get_enrichment_metrics(cursor, start_date, end_date),
            'top_performers': self._get_top_performers(cursor, start_date, end_date),
            'trends': self._get_trend_analysis(cursor, start_date, end_date)
        }

        conn.close()
        return insights
    
    def _get_overview_metrics(self, cursor, start_date=None, end_date=None):
        """Get high-level overview metrics with optional date filtering"""
        metrics = {}

        # Build date filter for SKUs (which have completed_date)
        date_filter = ""
        if start_date and end_date:
            # Need to handle date comparison for M/D/YYYY format
            date_filter = f"""
                AND EXISTS (
                    SELECT 1 FROM skus
                    WHERE skus.brand_name = brands.brand_name
                    AND skus.completed_date != ''
                    AND date(substr(skus.completed_date, -4) || '-' ||
                           printf('%02d', CAST(substr(skus.completed_date, 1, instr(skus.completed_date, '/') - 1) AS INTEGER)) || '-' ||
                           printf('%02d', CAST(substr(skus.completed_date, instr(skus.completed_date, '/') + 1,
                                  instr(substr(skus.completed_date, instr(skus.completed_date, '/') + 1), '/') - 1) AS INTEGER)))
                        BETWEEN date(substr('{start_date}', -4) || '-' ||
                                printf('%02d', CAST(substr('{start_date}', 1, instr('{start_date}', '/') - 1) AS INTEGER)) || '-' ||
                                printf('%02d', CAST(substr('{start_date}', instr('{start_date}', '/') + 1,
                                       instr(substr('{start_date}', instr('{start_date}', '/') + 1), '/') - 1) AS INTEGER)))
                        AND date(substr('{end_date}', -4) || '-' ||
                                printf('%02d', CAST(substr('{end_date}', 1, instr('{end_date}', '/') - 1) AS INTEGER)) || '-' ||
                                printf('%02d', CAST(substr('{end_date}', instr('{end_date}', '/') + 1,
                                       instr(substr('{end_date}', instr('{end_date}', '/') + 1), '/') - 1) AS INTEGER)))
                )
            """

        # For simplicity, let's use a different approach - filter SKUs directly
        sku_date_filter = ""
        if start_date and end_date:
            # We'll filter in Python since SQLite date handling for M/D/YYYY is complex
            sku_date_filter = f" WHERE completed_date != ''"

        # Total brands (filtered by date if applicable)
        if start_date and end_date:
            cursor.execute(f"""
                SELECT COUNT(DISTINCT b.brand_name)
                FROM brands b
                WHERE EXISTS (
                    SELECT 1 FROM skus s
                    WHERE s.brand_name = b.brand_name
                    AND s.completed_date != ''
                )
            """)
        else:
            cursor.execute("SELECT COUNT(*) FROM brands")
        metrics['total_brands'] = cursor.fetchone()[0]

        # Total SKUs
        cursor.execute(f"SELECT COUNT(*) FROM skus {sku_date_filter}")
        all_skus = cursor.fetchall() if start_date and end_date else [(cursor.fetchone()[0],)]

        # Filter by date in Python if needed
        if start_date and end_date:
            cursor.execute("SELECT completed_date FROM skus WHERE completed_date != ''")
            filtered_count = 0
            for row in cursor.fetchall():
                try:
                    # Parse M/D/YYYY format
                    parts = row[0].split('/')
                    if len(parts) == 3:
                        month, day, year = int(parts[0]), int(parts[1]), int(parts[2])
                        sku_date = datetime(year, month, day)
                        start_dt = datetime.strptime(start_date.replace('/', '-'), '%m-%d-%Y') if '/' in start_date else datetime.strptime(start_date, '%Y-%m-%d')
                        end_dt = datetime.strptime(end_date.replace('/', '-'), '%m-%d-%Y') if '/' in end_date else datetime.strptime(end_date, '%Y-%m-%d')
                        if start_dt <= sku_date <= end_dt:
                            filtered_count += 1
                except:
                    pass
            metrics['total_skus'] = filtered_count
        else:
            cursor.execute("SELECT COUNT(*) FROM skus")
            metrics['total_skus'] = cursor.fetchone()[0]

        # Total importers (not filtered by date as they don't have approval dates)
        cursor.execute("SELECT COUNT(*) FROM master_importers")
        metrics['total_importers'] = cursor.fetchone()[0]
        
        # Active importers (with brands)
        cursor.execute("""
            SELECT COUNT(DISTINCT permit_number) 
            FROM master_importers 
            WHERE brands IS NOT NULL AND brands != '[]'
        """)
        metrics['active_importers'] = cursor.fetchone()[0]
        
        # Brands with websites (all enriched brands now have consistent structure)
        cursor.execute("""
            SELECT COUNT(*) FROM brands
            WHERE enrichment_data IS NOT NULL
            AND json_extract(enrichment_data, '$.url') IS NOT NULL
            AND json_extract(enrichment_data, '$.url') != ''
        """)
        metrics['brands_with_websites'] = cursor.fetchone()[0]

        # Average SKUs per brand
        cursor.execute("""
            SELECT AVG(sku_count)
            FROM (
                SELECT COUNT(*) as sku_count
                FROM skus
                GROUP BY brand_name
            )
        """)
        metrics['avg_skus_per_brand'] = round(cursor.fetchone()[0] or 0, 1)

        # Enrichment rate (percentage of brands with websites)
        metrics['enrichment_rate'] = round(
            (metrics['brands_with_websites'] / metrics['total_brands'] * 100)
            if metrics['total_brands'] else 0, 1
        )
        
        return metrics
    
    def _get_geographic_insights(self, cursor, start_date=None, end_date=None):
        """Analyze geographic distribution"""
        insights = {
            'top_countries': [],
            'top_states': [],
            'international_vs_domestic': {},
            'geographic_diversity_score': 0
        }

        # Get total brands for percentage calculations
        cursor.execute("SELECT COUNT(*) FROM brands")
        total_brands = cursor.fetchone()[0] or 1

        # Get all brands with their countries (process each brand individually)
        cursor.execute("""
            SELECT brand_name, countries
            FROM brands
            WHERE countries IS NOT NULL AND countries != '[]'
        """)

        country_counts = defaultdict(int)
        state_counts = defaultdict(int)
        us_states = ['CALIFORNIA', 'NEW YORK', 'TEXAS', 'FLORIDA', 'PENNSYLVANIA',
                     'OREGON', 'WASHINGTON', 'VIRGINIA', 'MICHIGAN', 'NEW JERSEY']

        brands_with_us = set()
        brands_without_us = set()

        for brand_name, countries_json in cursor.fetchall():
            try:
                countries = json.loads(countries_json)
                has_us = False

                for country in countries:
                    country_upper = country.upper()
                    if country_upper in us_states:
                        state_counts[country] += 1
                        has_us = True
                    elif country_upper in ['UNITED STATES', 'USA', 'U.S.', 'US']:
                        has_us = True
                    else:
                        country_counts[country] += 1

                # Track if this brand is US or international
                if has_us:
                    brands_with_us.add(brand_name)
                    country_counts['United States'] += 1
                else:
                    brands_without_us.add(brand_name)

            except:
                pass
        
        # Top countries
        insights['top_countries'] = [
            {'name': name, 'count': count, 'percentage': round(count/total_brands*100, 1)}
            for name, count in sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        # Top US states
        insights['top_states'] = [
            {'name': name, 'count': count, 'percentage': round(count/total_brands*100, 1)}
            for name, count in sorted(state_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        # International vs Domestic (using actual brand sets)
        us_total = len(brands_with_us)
        international_total = len(brands_without_us)
        total_with_countries = us_total + international_total

        insights['international_vs_domestic'] = {
            'domestic': us_total,
            'international': international_total,
            'domestic_percentage': round(us_total/total_with_countries*100, 1) if total_with_countries else 0,
            'international_percentage': round(international_total/total_with_countries*100, 1) if total_with_countries else 0
        }
        
        # Geographic diversity score (number of unique countries)
        insights['geographic_diversity_score'] = len(country_counts)
        
        return insights
    
    def _get_product_insights(self, cursor, start_date=None, end_date=None):
        """Analyze product types and categories"""
        insights = {
            'top_alcohol_types': [],
            'category_distribution': {},
            'sku_distribution': [],
            'product_diversity_score': 0
        }
        
        # Analyze class types
        cursor.execute("""
            SELECT class_types, COUNT(*) as count 
            FROM brands 
            WHERE class_types IS NOT NULL AND class_types != '[]'
            GROUP BY class_types 
            ORDER BY count DESC
        """)
        
        type_counts = defaultdict(int)
        for types_json, count in cursor.fetchall():
            try:
                types = json.loads(types_json)
                for type_name in types:
                    type_counts[type_name] += count
            except:
                pass
        
        # Top alcohol types
        total_typed = sum(type_counts.values())
        insights['top_alcohol_types'] = [
            {
                'type': type_name,
                'count': count,
                'percentage': round(count/total_typed*100, 1) if total_typed else 0
            }
            for type_name, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:15]
        ]
        
        # Category groupings
        categories = {
            'Wine': ['WINE', 'SPARKLING WINE', 'DESSERT WINE', 'APERITIF WINE'],
            'Beer': ['BEER', 'ALE', 'LAGER', 'STOUT', 'PORTER', 'IPA', 'WHEAT BEER'],
            'Spirits': ['WHISKY', 'VODKA', 'GIN', 'RUM', 'TEQUILA', 'BRANDY', 'LIQUEUR'],
            'Other': []
        }
        
        category_totals = defaultdict(int)
        for type_name, count in type_counts.items():
            categorized = False
            for category, keywords in categories.items():
                if any(keyword in type_name.upper() for keyword in keywords):
                    category_totals[category] += count
                    categorized = True
                    break
            if not categorized:
                category_totals['Other'] += count
        
        insights['category_distribution'] = dict(category_totals)
        
        # SKU distribution
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN sku_count = 1 THEN 'Single SKU'
                    WHEN sku_count BETWEEN 2 AND 5 THEN '2-5 SKUs'
                    WHEN sku_count BETWEEN 6 AND 10 THEN '6-10 SKUs'
                    WHEN sku_count BETWEEN 11 AND 20 THEN '11-20 SKUs'
                    WHEN sku_count BETWEEN 21 AND 50 THEN '21-50 SKUs'
                    ELSE '50+ SKUs'
                END as range_name,
                COUNT(*) as brand_count
            FROM (
                SELECT brand_name, COUNT(*) as sku_count
                FROM skus
                GROUP BY brand_name
            )
            GROUP BY range_name
            ORDER BY 
                CASE range_name
                    WHEN 'Single SKU' THEN 1
                    WHEN '2-5 SKUs' THEN 2
                    WHEN '6-10 SKUs' THEN 3
                    WHEN '11-20 SKUs' THEN 4
                    WHEN '21-50 SKUs' THEN 5
                    ELSE 6
                END
        """)
        
        insights['sku_distribution'] = [
            {'range': row[0], 'count': row[1]} 
            for row in cursor.fetchall()
        ]
        
        # Product diversity score
        insights['product_diversity_score'] = len(type_counts)
        
        return insights
    
    def _get_importer_insights(self, cursor, start_date=None, end_date=None):
        """Analyze importer concentration and patterns"""
        insights = {
            'concentration_analysis': [],
            'top_importers': [],
            'importer_efficiency': {},
            'market_share_distribution': {}
        }
        
        # Importer concentration
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN brand_count = 0 THEN 'No brands'
                    WHEN brand_count = 1 THEN '1 brand'
                    WHEN brand_count BETWEEN 2 AND 5 THEN '2-5 brands'
                    WHEN brand_count BETWEEN 6 AND 10 THEN '6-10 brands'
                    WHEN brand_count BETWEEN 11 AND 20 THEN '11-20 brands'
                    WHEN brand_count BETWEEN 21 AND 50 THEN '21-50 brands'
                    ELSE '50+ brands'
                END as range_name,
                COUNT(*) as importer_count
            FROM (
                SELECT permit_number, 
                       CASE 
                           WHEN brands IS NULL OR brands = '[]' THEN 0
                           ELSE json_array_length(brands)
                       END as brand_count
                FROM master_importers
            )
            GROUP BY range_name
        """)
        
        insights['concentration_analysis'] = [
            {'range': row[0], 'count': row[1]}
            for row in cursor.fetchall()
        ]
        
        # Top importers by brand count
        cursor.execute("""
            SELECT
                CASE
                    WHEN owner_name IS NOT NULL AND owner_name != '' THEN owner_name
                    WHEN operating_name IS NOT NULL AND operating_name != '' THEN operating_name
                    ELSE COALESCE(owner_name, operating_name, 'Unknown')
                END as company_name,
                permit_number,
                CASE
                    WHEN brands IS NULL OR brands = '[]' THEN 0
                    ELSE json_array_length(brands)
                END as brand_count
            FROM master_importers
            WHERE brands IS NOT NULL AND brands != '[]'
            ORDER BY brand_count DESC
            LIMIT 20
        """)
        
        top_importers = cursor.fetchall()
        total_brands = sum(row[2] for row in top_importers)
        
        insights['top_importers'] = [
            {
                'name': row[0],
                'permit': row[1],
                'brand_count': row[2],
                'market_share': round(row[2]/total_brands*100, 1) if total_brands else 0
            }
            for row in top_importers
        ]
        
        # Market share distribution (top 10 vs rest)
        if top_importers:
            top_10_brands = sum(row[2] for row in top_importers[:10])
            cursor.execute("""
                SELECT SUM(
                    CASE 
                        WHEN brands IS NULL OR brands = '[]' THEN 0
                        ELSE json_array_length(brands)
                    END
                )
                FROM master_importers
            """)
            all_brands = cursor.fetchone()[0] or 0
            
            insights['market_share_distribution'] = {
                'top_10_importers': top_10_brands,
                'others': all_brands - top_10_brands,
                'top_10_percentage': round(top_10_brands/all_brands*100, 1) if all_brands else 0
            }
        
        return insights
    
    def _get_market_concentration(self, cursor, start_date=None, end_date=None):
        """Calculate market concentration metrics"""
        insights = {
            'herfindahl_index': 0,
            'concentration_ratio_cr4': 0,
            'concentration_ratio_cr8': 0,
            'market_structure': 'Unknown'
        }
        
        # Get all importer brand counts
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN brands IS NULL OR brands = '[]' THEN 0
                    ELSE json_array_length(brands)
                END as brand_count
            FROM master_importers
            WHERE brands IS NOT NULL AND brands != '[]'
            ORDER BY brand_count DESC
        """)
        
        brand_counts = [row[0] for row in cursor.fetchall()]
        
        if brand_counts:
            total = sum(brand_counts)
            
            # Herfindahl-Hirschman Index (HHI)
            hhi = sum((count/total * 100)**2 for count in brand_counts)
            insights['herfindahl_index'] = round(hhi, 1)
            
            # Concentration ratios
            cr4 = sum(brand_counts[:4]) / total * 100 if len(brand_counts) >= 4 else 0
            cr8 = sum(brand_counts[:8]) / total * 100 if len(brand_counts) >= 8 else 0
            
            insights['concentration_ratio_cr4'] = round(cr4, 1)
            insights['concentration_ratio_cr8'] = round(cr8, 1)
            
            # Market structure classification
            if hhi < 1500:
                insights['market_structure'] = 'Competitive'
            elif hhi < 2500:
                insights['market_structure'] = 'Moderately Concentrated'
            else:
                insights['market_structure'] = 'Highly Concentrated'
        
        return insights
    
    def _get_growth_indicators(self, cursor, start_date=None, end_date=None):
        """Analyze growth and activity indicators"""
        insights = {
            'brands_per_importer': {},
            'skus_per_brand': {},
            'enrichment_progress': {}
        }
        
        # Average brands per active importer
        cursor.execute("""
            SELECT AVG(brand_count), MAX(brand_count), MIN(brand_count)
            FROM (
                SELECT 
                    CASE 
                        WHEN brands IS NULL OR brands = '[]' THEN 0
                        ELSE json_array_length(brands)
                    END as brand_count
                FROM master_importers
                WHERE brands IS NOT NULL AND brands != '[]'
            )
        """)
        
        avg_brands, max_brands, min_brands = cursor.fetchone()
        insights['brands_per_importer'] = {
            'average': round(avg_brands or 0, 1),
            'maximum': max_brands or 0,
            'minimum': min_brands or 0
        }
        
        # SKUs per brand statistics
        cursor.execute("""
            SELECT AVG(sku_count), MAX(sku_count), MIN(sku_count)
            FROM (
                SELECT COUNT(*) as sku_count
                FROM skus
                GROUP BY brand_name
            )
        """)
        
        avg_skus, max_skus, min_skus = cursor.fetchone()
        insights['skus_per_brand'] = {
            'average': round(avg_skus or 0, 1),
            'maximum': max_skus or 0,
            'minimum': min_skus or 0
        }
        
        return insights
    
    def _get_enrichment_metrics(self, cursor, start_date=None, end_date=None):
        """Analyze enrichment quality and coverage"""
        insights = {
            'coverage': {},
            'verification_status': {},
            'confidence_distribution': []
        }
        
        # Overall coverage
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN enrichment_data IS NOT NULL AND enrichment_data != '{}' THEN 1 ELSE 0 END) as enriched,
                SUM(CASE WHEN enrichment_data IS NOT NULL
                    AND json_extract(enrichment_data, '$.url') IS NOT NULL
                    AND json_extract(enrichment_data, '$.url') != '' THEN 1 ELSE 0 END) as with_website,
                SUM(CASE WHEN enrichment_data LIKE '%verified%true%' THEN 1 ELSE 0 END) as verified
            FROM brands
        """)
        
        total, enriched, with_website, verified = cursor.fetchone()
        insights['coverage'] = {
            'total_brands': total,
            'enriched_brands': enriched or 0,
            'brands_with_websites': with_website or 0,
            'verified_websites': verified or 0,
            'enrichment_rate': round((enriched or 0)/total*100, 1) if total else 0,
            'website_rate': round((with_website or 0)/total*100, 1) if total else 0,
            'verification_rate': round((verified or 0)/(enriched or 1)*100, 1) if enriched else 0
        }
        
        return insights
    
    def _get_top_performers(self, cursor, start_date=None, end_date=None):
        """Identify top performing brands and entities"""
        insights = {
            'brands_by_skus': [],
            'brands_by_countries': [],
            'multi_product_brands': []
        }
        
        # Top brands by SKU count
        cursor.execute("""
            SELECT brand_name, COUNT(*) as sku_count
            FROM skus
            GROUP BY brand_name
            ORDER BY sku_count DESC
            LIMIT 10
        """)
        
        insights['brands_by_skus'] = [
            {'name': row[0], 'sku_count': row[1]}
            for row in cursor.fetchall()
        ]
        
        # Brands with most countries
        cursor.execute("""
            SELECT brand_name, countries
            FROM brands
            WHERE countries IS NOT NULL AND countries != '[]'
        """)
        
        country_counts = []
        for brand_name, countries_json in cursor.fetchall():
            try:
                countries = json.loads(countries_json)
                if len(countries) > 1:
                    country_counts.append((brand_name, len(countries)))
            except:
                pass
        
        country_counts.sort(key=lambda x: x[1], reverse=True)
        insights['brands_by_countries'] = [
            {'name': name, 'country_count': count}
            for name, count in country_counts[:10]
        ]
        
        # Multi-product brands (diverse class types)
        cursor.execute("""
            SELECT brand_name, class_types
            FROM brands
            WHERE class_types IS NOT NULL AND class_types != '[]'
        """)
        
        type_counts = []
        for brand_name, types_json in cursor.fetchall():
            try:
                types = json.loads(types_json)
                if len(types) > 1:
                    type_counts.append((brand_name, len(types)))
            except:
                pass
        
        type_counts.sort(key=lambda x: x[1], reverse=True)
        insights['multi_product_brands'] = [
            {'name': name, 'product_types': count}
            for name, count in type_counts[:10]
        ]
        
        return insights
    
    def _get_trend_analysis(self, cursor, start_date=None, end_date=None):
        """Analyze trends and patterns"""
        insights = {
            'popular_keywords': [],
            'emerging_categories': [],
            'import_patterns': {}
        }
        
        # Popular keywords in brand names
        cursor.execute("SELECT brand_name FROM brands")
        all_brands = cursor.fetchall()
        
        word_counts = Counter()
        stop_words = {'THE', 'OF', 'AND', 'A', 'AN', 'IN', 'ON', 'AT', 'TO', 'FOR', 'BY', 'WITH'}
        
        for (brand_name,) in all_brands:
            words = brand_name.upper().split()
            for word in words:
                if len(word) > 3 and word not in stop_words:
                    word_counts[word] += 1
        
        insights['popular_keywords'] = [
            {'keyword': word, 'frequency': count}
            for word, count in word_counts.most_common(20)
        ]
        
        # Import patterns by permit type
        cursor.execute("""
            SELECT 
                SUBSTR(permit_number, INSTR(permit_number, '-') + 1, 1) as permit_type,
                COUNT(*) as count
            FROM master_importers
            WHERE permit_number IS NOT NULL
            GROUP BY permit_type
        """)
        
        permit_patterns = cursor.fetchall()
        insights['import_patterns'] = {
            'by_permit_type': [
                {'type': f'{row[0]}-permit', 'count': row[1]}
                for row in permit_patterns
            ]
        }
        
        return insights