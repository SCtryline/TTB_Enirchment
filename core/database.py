"""
SQLite-based Brand Database - Backward Compatible Migration
Maintains exact same API as original BrandDatabase class
"""

import sqlite3
import json
import os
from datetime import datetime
import pandas as pd
from typing import Dict, List, Optional, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BrandDatabaseV2:
    def __init__(self, db_path='data/brands.db', json_backup_path='data/brands_db.json'):
        """
        Initialize SQLite database with backward compatibility
        
        Args:
            db_path: Path to SQLite database file
            json_backup_path: Path to original JSON file for backup
        """
        self.db_path = db_path
        self.json_backup_path = json_backup_path
        self.conn = None
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Initialize database
        self._connect()
        self._create_tables()
        self._create_indexes()
        
        # Load existing data structure for compatibility
        self.db = self._load_as_dict()
    
    def _connect(self):
        """Establish database connection"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrency
        self.conn.execute('PRAGMA journal_mode = WAL')
        self.conn.execute('PRAGMA foreign_keys = ON')
    
    def _create_tables(self):
        """Create all necessary tables preserving JSON structure"""
        self.conn.executescript('''
            -- Brands table
            CREATE TABLE IF NOT EXISTS brands (
                brand_name TEXT PRIMARY KEY,
                created_date TEXT NOT NULL,
                permit_numbers TEXT, -- JSON array
                countries TEXT, -- JSON array  
                class_types TEXT, -- JSON array
                importers TEXT, -- JSON object {permit: importer_data}
                producers TEXT DEFAULT '{}', -- JSON object {permit: producer_data}
                brand_permits TEXT DEFAULT '[]', -- JSON array of brand's own permits
                enrichment_data TEXT, -- JSON object (website, founders, etc)
                website TEXT, -- Legacy website field (for compatibility)
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            
            -- SKUs table
            CREATE TABLE IF NOT EXISTS skus (
                ttb_id TEXT PRIMARY KEY,
                brand_name TEXT NOT NULL,
                permit_no TEXT,
                serial_number TEXT,
                completed_date TEXT,
                fanciful_name TEXT,
                origin TEXT,
                origin_desc TEXT,
                class_type TEXT,
                class_type_desc TEXT,
                added_date TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (brand_name) REFERENCES brands (brand_name)
            );
            
            -- Master importers table
            CREATE TABLE IF NOT EXISTS master_importers (
                permit_number TEXT PRIMARY KEY,
                owner_name TEXT,
                operating_name TEXT,
                street TEXT,
                city TEXT,
                state TEXT,
                zip TEXT,
                county TEXT,
                industry_type TEXT,
                added_date TEXT,
                brands TEXT, -- JSON array of associated brands
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Spirit producers table
            CREATE TABLE IF NOT EXISTS spirit_producers (
                permit_number TEXT PRIMARY KEY,
                owner_name TEXT,
                operating_name TEXT,
                street TEXT,
                city TEXT,
                state TEXT,
                zip TEXT,
                county TEXT,
                industry_type TEXT,
                added_date TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Wine producers table  
            CREATE TABLE IF NOT EXISTS wine_producers (
                permit_number TEXT PRIMARY KEY,
                owner_name TEXT,
                operating_name TEXT,
                street TEXT,
                city TEXT,
                state TEXT,
                zip TEXT,
                county TEXT,
                industry_type TEXT,
                added_date TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Upload history table
            CREATE TABLE IF NOT EXISTS upload_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                upload_date TEXT NOT NULL,
                total_records INTEGER,
                matched_records INTEGER,
                new_brands INTEGER,
                new_skus INTEGER,
                updated_skus INTEGER,
                file_type TEXT, -- 'cola', 'importer', 'spirit_producer', 'wine_producer'
                metadata TEXT -- JSON for additional data
            );
            
            -- Legacy importers table (for compatibility)
            CREATE TABLE IF NOT EXISTS importers (
                permit_number TEXT PRIMARY KEY,
                data TEXT -- JSON representation for compatibility
            );
        ''')
        self.conn.commit()
    
    def _create_indexes(self):
        """Create performance indexes and migrate schema"""
        # Add new columns for three-tier permit classification
        try:
            self.conn.execute('ALTER TABLE brands ADD COLUMN producers TEXT DEFAULT "{}"')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            self.conn.execute('ALTER TABLE brands ADD COLUMN brand_permits TEXT DEFAULT "[]"')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        self.conn.executescript('''
            -- Brand indexes
            CREATE INDEX IF NOT EXISTS idx_brands_created_date ON brands(created_date);
            CREATE INDEX IF NOT EXISTS idx_brands_updated_at ON brands(updated_at);
            
            -- New indexes for filter performance
            CREATE INDEX IF NOT EXISTS idx_brands_website ON brands(website);
            CREATE INDEX IF NOT EXISTS idx_brands_enrichment_not_null ON brands(brand_name) 
                WHERE enrichment_data IS NOT NULL;
            CREATE INDEX IF NOT EXISTS idx_brands_countries_not_null ON brands(brand_name) 
                WHERE countries IS NOT NULL;
            CREATE INDEX IF NOT EXISTS idx_brands_class_types_not_null ON brands(brand_name) 
                WHERE class_types IS NOT NULL;
            CREATE INDEX IF NOT EXISTS idx_brands_importers_not_null ON brands(brand_name) 
                WHERE importers IS NOT NULL;
            CREATE INDEX IF NOT EXISTS idx_brands_producers_not_null ON brands(brand_name) 
                WHERE producers IS NOT NULL;
            
            -- JSON extraction indexes for common queries (SQLite 3.38.0+)
            -- These will speed up JSON queries significantly
            CREATE INDEX IF NOT EXISTS idx_brands_verified ON brands(
                json_extract(enrichment_data, '$.website.verification_status')
            ) WHERE enrichment_data IS NOT NULL;
            
            -- SKU indexes
            CREATE INDEX IF NOT EXISTS idx_skus_brand_name ON skus(brand_name);
            CREATE INDEX IF NOT EXISTS idx_skus_permit_no ON skus(permit_no);
            CREATE INDEX IF NOT EXISTS idx_skus_class_type ON skus(class_type);
            CREATE INDEX IF NOT EXISTS idx_skus_origin ON skus(origin);
            CREATE INDEX IF NOT EXISTS idx_skus_completed_date ON skus(completed_date);
            
            -- Importer indexes
            CREATE INDEX IF NOT EXISTS idx_master_importers_owner_name ON master_importers(owner_name);
            CREATE INDEX IF NOT EXISTS idx_master_importers_operating_name ON master_importers(operating_name);
            CREATE INDEX IF NOT EXISTS idx_master_importers_state ON master_importers(state);
            
            -- Producer indexes
            CREATE INDEX IF NOT EXISTS idx_spirit_producers_owner_name ON spirit_producers(owner_name);
            CREATE INDEX IF NOT EXISTS idx_wine_producers_owner_name ON wine_producers(owner_name);
            
            -- Upload history indexes
            CREATE INDEX IF NOT EXISTS idx_upload_history_date ON upload_history(upload_date);
            CREATE INDEX IF NOT EXISTS idx_upload_history_type ON upload_history(file_type);
        ''')
        self.conn.commit()
    
    def _load_as_dict(self) -> Dict[str, Any]:
        """
        Load database as dictionary structure for API compatibility
        This maintains the same data structure as the original JSON version
        """
        result = {
            'brands': {},
            'importers': {},
            'skus': {},
            'upload_history': [],
            'master_importers': {},
            'spirit_producers': {},
            'wine_producers': {}
        }
        
        try:
            # Load brands
            cursor = self.conn.execute('''
                SELECT brand_name, created_date, permit_numbers, countries, 
                       class_types, importers, enrichment_data, website
                FROM brands
            ''')
            
            for row in cursor:
                brand_data = {
                    'brand_name': row['brand_name'],
                    'created_date': row['created_date'],
                    'permit_numbers': json.loads(row['permit_numbers'] or '[]'),
                    'countries': json.loads(row['countries'] or '[]'),
                    'class_types': json.loads(row['class_types'] or '[]'),
                    'importers': json.loads(row['importers'] or '{}'),
                    'skus': []  # Will be populated below
                }
                
                # Add enrichment data if present
                if row['enrichment_data']:
                    brand_data['enrichment'] = json.loads(row['enrichment_data'])
                
                # Add legacy website field if present
                if row['website']:
                    brand_data['website'] = json.loads(row['website']) if row['website'].startswith('{') else row['website']
                
                result['brands'][row['brand_name']] = brand_data
            
            # Load SKUs and associate with brands
            cursor = self.conn.execute('SELECT * FROM skus')
            for row in cursor:
                sku_data = dict(row)
                sku_data.pop('updated_at', None)  # Remove internal field
                
                # Add to skus dict
                result['skus'][row['ttb_id']] = sku_data
                
                # Add to brand's SKUs list
                if row['brand_name'] in result['brands']:
                    result['brands'][row['brand_name']]['skus'].append(row['ttb_id'])
            
            # Load master importers
            cursor = self.conn.execute('SELECT * FROM master_importers')
            for row in cursor:
                importer_data = dict(row)
                importer_data.pop('updated_at', None)
                if importer_data['brands']:
                    importer_data['brands'] = json.loads(importer_data['brands'])
                else:
                    importer_data['brands'] = []
                
                result['master_importers'][row['permit_number']] = importer_data
            
            # Load spirit producers
            cursor = self.conn.execute('SELECT * FROM spirit_producers')
            for row in cursor:
                producer_data = dict(row)
                producer_data.pop('updated_at', None)
                result['spirit_producers'][row['permit_number']] = producer_data
            
            # Load wine producers
            cursor = self.conn.execute('SELECT * FROM wine_producers')
            for row in cursor:
                producer_data = dict(row)
                producer_data.pop('updated_at', None)
                result['wine_producers'][row['permit_number']] = producer_data
            
            # Load upload history
            cursor = self.conn.execute('SELECT * FROM upload_history ORDER BY upload_date')
            result['upload_history'] = []
            for row in cursor:
                history_item = dict(row)
                history_item.pop('id', None)  # Remove auto-increment ID
                history_item.pop('updated_at', None)
                if history_item['metadata']:
                    history_item.update(json.loads(history_item['metadata']))
                result['upload_history'].append(history_item)
            
            logger.info(f"Loaded {len(result['brands'])} brands, {len(result['skus'])} SKUs, {len(result['master_importers'])} importers")
            
        except Exception as e:
            logger.error(f"Error loading database as dict: {e}")
            # Return empty structure on error
            pass
        
        return result
    
    def save_database(self, db=None):
        """
        Save database - no-op for SQLite as changes are committed immediately
        Maintains API compatibility with original version
        """
        if db is not None:
            logger.warning("save_database() called with db parameter - ignoring (SQLite auto-commits)")
        
        # Refresh in-memory dict representation
        self.db = self._load_as_dict()
        
        # Create JSON backup
        try:
            backup_path = self.json_backup_path + '.backup'
            with open(backup_path, 'w') as f:
                json.dump(self.db, f, indent=2)
            logger.info(f"JSON backup saved to {backup_path}")
        except Exception as e:
            logger.error(f"Failed to create JSON backup: {e}")
    
    def load_database(self):
        """
        Reload database - refresh in-memory dict representation
        Maintains API compatibility
        """
        self.db = self._load_as_dict()
    
    def reload_database(self):
        """Reload database connection to get latest changes"""
        try:
            # Commit any pending changes
            if self.conn:
                self.conn.commit()
            # Reload the dictionary representation
            self.db = self._load_as_dict()
            logger.info("Database reloaded successfully")
            return True
        except Exception as e:
            logger.error(f"Error reloading database: {e}")
            return False
    
    # === BACKWARD COMPATIBILITY METHODS ===
    # All existing methods from original BrandDatabase class will be implemented
    
    def ensure_db_exists(self):
        """Compatibility method - database is created in __init__"""
        pass
    
    def initialize_database(self):
        """Compatibility method - database is initialized in __init__"""
        pass
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def __del__(self):
        """Cleanup on deletion"""
        self.close()
    
    # === ALL EXISTING API METHODS ===
    # Complete implementation of all methods from original BrandDatabase
    
    def process_cola_file(self, cola_df, importers_df, filename):
        """Process a COLA CSV file and update the database"""
        upload_record = {
            'filename': filename,
            'upload_date': datetime.now().isoformat(),
            'total_records': len(cola_df),
            'matched_records': 0,
            'new_brands': 0,
            'new_skus': 0,
            'updated_skus': 0
        }
        
        # Clean and prepare the data
        cola_df['Permit No.'] = cola_df['Permit No.'].astype(str).str.strip().str.upper()
        cola_df['Brand Name'] = cola_df['Brand Name'].astype(str).str.strip()
        cola_df['TTB ID'] = cola_df['TTB ID'].astype(str).str.strip()
        
        # Process each COLA record
        for _, cola_row in cola_df.iterrows():
            permit_no = str(cola_row['Permit No.'])
            
            # Try to match with master importers first
            importer_data = self.get_master_importer(permit_no)
            
            if importer_data:
                # Create a combined row with COLA and importer data
                combined_row = cola_row.to_dict()
                combined_row.update({
                    'Permit_Number': importer_data['permit_number'],
                    'Owner_Name': importer_data['owner_name'],
                    'Operating_Name': importer_data['operating_name'],
                    'Street': importer_data['street'],
                    'City': importer_data['city'],
                    'State': importer_data['state']
                })
                upload_record['matched_records'] += 1
            else:
                # No match found, process without importer data
                combined_row = cola_row.to_dict()
            
            self.process_record(pd.Series(combined_row), upload_record)
        
        # Update upload history
        self.conn.execute('''
            INSERT INTO upload_history (
                filename, upload_date, total_records, matched_records,
                new_brands, new_skus, updated_skus, file_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            filename, upload_record['upload_date'], upload_record['total_records'],
            upload_record['matched_records'], upload_record['new_brands'],
            upload_record['new_skus'], upload_record['updated_skus'], 'cola'
        ))
        self.conn.commit()
        
        # Refresh in-memory representation
        self.db = self._load_as_dict()
        
        return upload_record
    
    def process_record(self, row, upload_record):
        """Process a single record and update brands/SKUs"""
        brand_name = str(row['Brand Name'])
        ttb_id = str(row['TTB ID'])
        permit_no = str(row['Permit No.'])
        
        # Skip if brand name is empty or 'nan'
        if not brand_name or brand_name == 'nan':
            return
        
        # Create brand if it doesn't exist
        cursor = self.conn.execute('SELECT brand_name FROM brands WHERE brand_name = ?', (brand_name,))
        if not cursor.fetchone():
            self.conn.execute('''
                INSERT INTO brands (brand_name, created_date, permit_numbers, countries, class_types, importers, producers, brand_permits)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                brand_name, datetime.now().isoformat(), 
                json.dumps([permit_no]), json.dumps([]), json.dumps([]), json.dumps({}), json.dumps({}), json.dumps([])
            ))
            upload_record['new_brands'] += 1
        
        # Get current brand data
        cursor = self.conn.execute('''
            SELECT permit_numbers, countries, class_types, importers, producers, brand_permits 
            FROM brands WHERE brand_name = ?
        ''', (brand_name,))
        brand_row = cursor.fetchone()
        
        if brand_row:
            permit_numbers = json.loads(brand_row['permit_numbers'] or '[]')
            countries = set(json.loads(brand_row['countries'] or '[]'))
            class_types = set(json.loads(brand_row['class_types'] or '[]'))
            importers = json.loads(brand_row['importers'] or '{}')
            producers = json.loads(brand_row['producers'] or '{}')
            brand_permits = json.loads(brand_row['brand_permits'] or '[]')
            
            # Add permit number if not already there
            if permit_no not in permit_numbers:
                permit_numbers.append(permit_no)
            
            # Three-tier permit classification logic:
            # 1. Try to match with importers (XX-I-XXXXX permits)
            # 2. Try to match with producers (DSP-, BWN-, BR- permits)  
            # 3. Otherwise it's the brand's own independent permit
            
            # Only add to importers if we have matched importer data (Permit_Number exists)
            if row.get('Permit_Number') and pd.notna(row.get('Permit_Number')):
                # This is a real importer match - add to importers field
                importer_permit = str(row.get('Permit_Number'))
                if importer_permit not in importers:
                    importers[importer_permit] = {
                        'permit_number': importer_permit,
                        'owner_name': str(row.get('Owner_Name', '')),
                        'operating_name': str(row.get('Operating_Name', '')),
                        'city': str(row.get('City', '')),
                        'state': str(row.get('State', '')),
                        'address': str(row.get('Street', ''))
                    }
            else:
                # No importer match found - try producer matching (step 2)
                current_permit = str(row.get('Permit No.'))
                producer_data = None
                
                # Try to match with spirit producers
                if current_permit in self.db.get('spirit_producers', {}):
                    producer_data = self.db['spirit_producers'][current_permit].copy()
                    producer_data['producer_type'] = 'spirit_producer'
                # Try to match with wine producers
                elif current_permit in self.db.get('wine_producers', {}):
                    producer_data = self.db['wine_producers'][current_permit].copy()
                    producer_data['producer_type'] = 'wine_producer'
                
                if producer_data:
                    # This is a producer relationship - add to producers field
                    if current_permit not in producers:
                        producers[current_permit] = producer_data
                else:
                    # No producer match either - this is the brand's own permit (step 3)
                    if current_permit not in brand_permits:
                        brand_permits.append(current_permit)
            
            # Add country and class type
            origin_desc = str(row.get('Origin Desc', ''))
            if origin_desc and origin_desc != 'nan':
                countries.add(origin_desc)
            
            class_type_desc = str(row.get('Class Type Desc', ''))
            if class_type_desc and class_type_desc != 'nan':
                class_types.add(class_type_desc)
            
            # Update brand record
            self.conn.execute('''
                UPDATE brands 
                SET permit_numbers = ?, countries = ?, class_types = ?, importers = ?, producers = ?, brand_permits = ?
                WHERE brand_name = ?
            ''', (
                json.dumps(permit_numbers), json.dumps(list(countries)), 
                json.dumps(list(class_types)), json.dumps(importers), 
                json.dumps(producers), json.dumps(brand_permits), brand_name
            ))
        
        # Process SKU
        cursor = self.conn.execute('SELECT ttb_id FROM skus WHERE ttb_id = ?', (ttb_id,))
        if not cursor.fetchone():
            # Insert new SKU
            self.conn.execute('''
                INSERT INTO skus (
                    ttb_id, brand_name, permit_no, serial_number, completed_date,
                    fanciful_name, origin, origin_desc, class_type, class_type_desc, added_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ttb_id, brand_name, permit_no,
                str(row.get('Serial Number', '')),
                str(row.get('Completed Date', '')),
                str(row.get('Fanciful Name', '')),
                str(row.get('Origin', '')),
                str(row.get('Origin Desc', '')),
                str(row.get('Class Type', '')),
                str(row.get('Class Type Desc', '')),
                datetime.now().isoformat()
            ))
            upload_record['new_skus'] += 1
        else:
            # Update existing SKU with new data
            self.conn.execute('''
                UPDATE skus SET
                    brand_name = ?, permit_no = ?, serial_number = ?, completed_date = ?,
                    fanciful_name = ?, origin = ?, origin_desc = ?, class_type = ?, class_type_desc = ?,
                    updated_at = ?
                WHERE ttb_id = ?
            ''', (
                brand_name, permit_no,
                str(row.get('Serial Number', '')),
                str(row.get('Completed Date', '')),
                str(row.get('Fanciful Name', '')),
                str(row.get('Origin', '')),
                str(row.get('Origin Desc', '')),
                str(row.get('Class Type', '')),
                str(row.get('Class Type Desc', '')),
                datetime.now().isoformat(),
                ttb_id
            ))
            upload_record['updated_skus'] += 1
    
    def get_brand_data(self, brand_name):
        """Get detailed data for a specific brand"""
        cursor = self.conn.execute('''
            SELECT brand_name, countries, class_types, importers, producers, brand_permits, enrichment_data, website, apollo_data, apollo_status, apollo_company_id
            FROM brands WHERE brand_name = ?
        ''', (brand_name,))
        
        brand_row = cursor.fetchone()
        if not brand_row:
            return None
        
        # Get SKUs for this brand
        cursor = self.conn.execute('SELECT * FROM skus WHERE brand_name = ?', (brand_name,))
        skus = []
        for sku_row in cursor:
            sku_data = dict(sku_row)
            sku_data.pop('updated_at', None)
            skus.append(sku_data)
        
        # Get three-tier permit classification data
        importers_data = json.loads(brand_row['importers'] or '{}')
        producers_data = json.loads(brand_row['producers'] or '{}')
        brand_permits = json.loads(brand_row['brand_permits'] or '[]')
        
        # Filter importer objects (only real importers with XX-I-XXXXX permits)
        importer_list = []
        unmatched_permits_detail = []  # Collect permits that aren't real importers
        
        for importer_info in (importers_data.values() if importers_data else []):
            permit_number = importer_info.get('permit_number', '')
            if permit_number and '-I-' in permit_number:
                # This is a real importer permit
                importer_list.append(importer_info)
            elif permit_number and permit_number not in ['', 'nan']:
                # This is a permit that was incorrectly classified as importer
                unmatched_permits_detail.append(permit_number)
        
        # Convert producer data to list
        producer_list = list(producers_data.values()) if producers_data else []
        
        # Fallback: Get producer data by matching permit numbers from SKUs (for existing data)
        if not producer_list:
            producer_list = self._get_producers_for_brand(skus)
        
        # Add unmatched permits (that were incorrectly in importers) to brand_permits
        for permit in unmatched_permits_detail:
            if permit not in brand_permits:
                brand_permits.append(permit)
        
        # Safely parse enrichment_data
        enrichment = None
        if brand_row['enrichment_data']:
            try:
                enrichment = json.loads(brand_row['enrichment_data'])
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Warning: Could not parse enrichment_data for {brand_name}: {e}")
                enrichment = None
        
        # Safely parse website data
        website = None
        if brand_row['website']:
            try:
                website = json.loads(brand_row['website'])
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Warning: Could not parse website data for {brand_name}: {e}")
                website = None

        # Safely parse Apollo data
        apollo_data = None
        if brand_row['apollo_data']:
            try:
                apollo_data = json.loads(brand_row['apollo_data'])
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Warning: Could not parse apollo_data for {brand_name}: {e}")
                apollo_data = None
        
        brand_data = {
            'brand_name': brand_row['brand_name'],
            'summary': {
                'countries': json.loads(brand_row['countries'] or '[]'),
                'importers': importer_list,
                'producers': producer_list,
                'brand_permits': brand_permits,
                'class_types': json.loads(brand_row['class_types'] or '[]'),
                'total_skus': len(skus)
            },
            'website': website,
            'enrichment': enrichment,
            'apollo_data': apollo_data,
            'apollo_status': brand_row['apollo_status'],
            'apollo_company_id': brand_row['apollo_company_id'],
            'skus': skus
        }
        
        return brand_data
    
    def _get_producers_for_brand(self, skus):
        """Get producers for a brand by matching SKU permit numbers"""
        producers = []
        seen_permits = set()
        
        # Collect unique permit numbers from SKUs
        for sku in skus:
            permit_no = sku.get('permit_no')
            if permit_no and permit_no not in seen_permits:
                seen_permits.add(permit_no)
                
                # Try direct match first
                producer_data = None
                producer_type = None
                
                # Direct match with spirit producers
                if permit_no in self.db.get('spirit_producers', {}):
                    producer_data = self.db['spirit_producers'][permit_no].copy()
                    producer_type = 'spirit_producer'
                # Direct match with wine producers
                elif permit_no in self.db.get('wine_producers', {}):
                    producer_data = self.db['wine_producers'][permit_no].copy()
                    producer_type = 'wine_producer'
                # Convert DSP format: DSP-TX-20010 -> TX-S-20010
                elif permit_no.startswith('DSP-'):
                    parts = permit_no.split('-')
                    if len(parts) >= 3:
                        converted_permit = f'{parts[1]}-S-{parts[2]}'
                        if converted_permit in self.db.get('spirit_producers', {}):
                            producer_data = self.db['spirit_producers'][converted_permit].copy()
                            producer_data['original_permit'] = permit_no
                            producer_data['converted_permit'] = converted_permit
                            producer_type = 'spirit_producer'
                # Convert BWN format: BWN-CA-21001 -> CA-W-21001 (if wine producers follow similar pattern)
                elif permit_no.startswith('BWN-'):
                    parts = permit_no.split('-')
                    if len(parts) >= 3:
                        converted_permit = f'{parts[1]}-W-{parts[2]}'
                        if converted_permit in self.db.get('wine_producers', {}):
                            producer_data = self.db['wine_producers'][converted_permit].copy()
                            producer_data['original_permit'] = permit_no
                            producer_data['converted_permit'] = converted_permit
                            producer_type = 'wine_producer'
                
                if producer_data and producer_type:
                    producer_data['matched_via'] = producer_type
                    producers.append(producer_data)
        
        return producers
    
    def get_producer_data(self, permit_number, producer_type='auto'):
        """Get detailed data for a specific producer"""
        producer_data = None
        
        # Auto-detect producer type if not specified
        if producer_type == 'auto':
            if permit_number in self.db.get('spirit_producers', {}):
                producer_data = self.db['spirit_producers'][permit_number].copy()
                producer_type = 'spirit_producer'
            elif permit_number in self.db.get('wine_producers', {}):
                producer_data = self.db['wine_producers'][permit_number].copy()
                producer_type = 'wine_producer'
        elif producer_type == 'spirit_producer':
            producer_data = self.db.get('spirit_producers', {}).get(permit_number)
        elif producer_type == 'wine_producer':
            producer_data = self.db.get('wine_producers', {}).get(permit_number)
        
        if not producer_data:
            return None
        
        # Get brands produced by this producer
        brands_list = []
        for brand_name, brand_data in self.db.get('brands', {}).items():
            brand_skus = brand_data.get('skus', [])
            for sku in brand_skus:
                if sku.get('permit_no') == permit_number:
                    brands_list.append({
                        'brand_name': brand_name,
                        'sku_count': len([s for s in brand_skus if s.get('permit_no') == permit_number])
                    })
                    break
        
        producer_full_data = producer_data.copy()
        producer_full_data['producer_type'] = producer_type
        producer_full_data['brands'] = brands_list
        producer_full_data['total_brands'] = len(brands_list)
        
        return producer_full_data
    
    def get_all_brands(self):
        """Get a list of all brands with summary info"""
        cursor = self.conn.execute('''
            SELECT b.brand_name, b.countries, b.class_types, b.importers, b.producers, b.brand_permits,
                   b.enrichment_data, b.website,
                   COUNT(s.ttb_id) as sku_count
            FROM brands b
            LEFT JOIN skus s ON b.brand_name = s.brand_name
            GROUP BY b.brand_name
            ORDER BY b.brand_name
        ''')
        
        brands_list = []
        for row in cursor:
            # Parse three-tier permit classification data
            importers_data = json.loads(row['importers'] or '{}')
            producers_data = json.loads(row['producers'] or '{}')
            brand_permits = json.loads(row['brand_permits'] or '[]')
            
            # Get importer objects (only real importers with XX-I-XXXXX permits)
            importer_objects = []
            unmatched_permits = []  # Collect permits that aren't real importers
            
            for importer_info in importers_data.values():
                permit_number = importer_info.get('permit_number', '')
                if permit_number and '-I-' in permit_number:
                    # This is a real importer permit
                    importer_objects.append(importer_info)
                elif permit_number and permit_number not in ['', 'nan']:
                    # This is a permit that was incorrectly classified as importer
                    unmatched_permits.append(permit_number)
            
            # Get producer objects (from matched producers)
            producer_objects = []
            for producer_info in producers_data.values():
                if producer_info.get('permit_number'):  # Only include if has permit
                    producer_objects.append(producer_info)
            
            # Fallback: Get producer information from SKU matching (for existing data)
            if not producer_objects:
                sku_cursor = self.conn.execute('''
                    SELECT permit_no FROM skus WHERE brand_name = ?
                ''', (row['brand_name'],))
                skus = [{'permit_no': sku_row['permit_no']} for sku_row in sku_cursor]
                
                producers_list = self._get_producers_for_brand(skus)
                producer_objects = producers_list
            
            # Add unmatched permits (that were incorrectly in importers) to brand_permits
            for permit in unmatched_permits:
                if permit not in brand_permits:
                    brand_permits.append(permit)
            
            # Parse enrichment data
            enrichment = None
            if row['enrichment_data']:
                try:
                    enrichment = json.loads(row['enrichment_data'])
                except:
                    pass
            elif row['website']:
                try:
                    enrichment = json.loads(row['website']) if row['website'].startswith('{') else {'website': row['website']}
                except:
                    enrichment = {'website': row['website']}
            
            brand_data = {
                'brand_name': row['brand_name'],
                'countries': json.loads(row['countries'] or '[]'),
                'class_types': json.loads(row['class_types'] or '[]'),
                'importers': importer_objects,
                'producers': producer_objects,
                'brand_permits': brand_permits,
                'total_skus': row['sku_count'] or 0
            }
            
            if enrichment:
                brand_data['enrichment'] = enrichment
            
            brands_list.append(brand_data)
        
        return brands_list
    
    def get_filtered_brands(self, search='', filters=None, page=1, per_page=24, sort='name', direction='asc'):
        """
        Optimized database-level filtering for brands
        
        Args:
            search: Search term for brand names
            filters: Dict with filter arrays (importers, alcoholTypes, producers, countries, websiteStatus)
            page: Page number for pagination
            per_page: Results per page
            sort: Sort field
            direction: Sort direction (asc/desc)
            
        Returns:
            Dict with brands list, pagination info, and filter counts
        """
        filters = filters or {}
        
        # Build the base query with JOINs
        base_query = '''
            SELECT DISTINCT b.brand_name, b.countries, b.class_types, b.importers, 
                   b.producers, b.brand_permits, b.enrichment_data, b.website,
                   COUNT(DISTINCT s.ttb_id) as sku_count
            FROM brands b
            LEFT JOIN skus s ON b.brand_name = s.brand_name
        '''
        
        where_clauses = []
        params = []
        
        # Search filter (brand name)
        if search:
            where_clauses.append("LOWER(b.brand_name) LIKE LOWER(?)")
            params.append(f'%{search}%')
        
        # Countries filter - use JSON extract for array fields
        if filters.get('countries'):
            country_conditions = []
            for country in filters['countries']:
                country_conditions.append("b.countries LIKE ?")
                params.append(f'%"{country}"%')
            if country_conditions:
                where_clauses.append(f"({' OR '.join(country_conditions)})")
        
        # Alcohol types filter
        if filters.get('alcoholTypes'):
            type_conditions = []
            for alcohol_type in filters['alcoholTypes']:
                type_conditions.append("LOWER(b.class_types) LIKE LOWER(?)")
                params.append(f'%{alcohol_type}%')
            if type_conditions:
                where_clauses.append(f"({' OR '.join(type_conditions)})")
        
        # Website status filter - check both website field and enrichment_data field
        if filters.get('websiteStatus'):
            website_conditions = []
            for status in filters['websiteStatus']:
                if status == 'has_website':
                    # Check both website field and enrichment_data for manual entries
                    website_conditions.append("""(
                        (b.website IS NOT NULL AND b.website != '') OR
                        (b.enrichment_data LIKE '%"url":%' OR b.enrichment_data LIKE '%manual_override%')
                    )""")
                elif status == 'verified':
                    # Check both website field and enrichment_data for verified status
                    website_conditions.append("""(
                        b.website LIKE '%"verification_status": "verified"%' OR
                        b.enrichment_data LIKE '%"verification_status": "verified"%' OR
                        b.enrichment_data LIKE '%"verified": true%'
                    )""")
                elif status == 'no_website':
                    # No website in either field
                    website_conditions.append("""(
                        (b.website IS NULL OR b.website = '') AND
                        (b.enrichment_data IS NULL OR 
                         (b.enrichment_data NOT LIKE '%"url":%' AND b.enrichment_data NOT LIKE '%manual_override%'))
                    )""")
            if website_conditions:
                where_clauses.append(f"({' OR '.join(website_conditions)})")
        
        # Importers filter - check JSON field
        if filters.get('importers'):
            importer_conditions = []
            for importer in filters['importers']:
                importer_conditions.append("b.importers LIKE ?")
                params.append(f'%"{importer}"%')
            if importer_conditions:
                where_clauses.append(f"({' OR '.join(importer_conditions)})")
        
        # Producers filter - need to check SKUs for producer permits
        if filters.get('producers'):
            producer_conditions = []
            for producer in filters['producers']:
                # Extract permit type and state from producer name like "Bonded Winery (CA)"
                if '(' in producer and producer.endswith(')'):
                    # Parse "Bonded Winery (CA)" -> type="BWN", state="CA"
                    type_part = producer.split(' (')[0]
                    state_part = producer.split('(')[1].rstrip(')')
                    
                    type_map = {
                        'Distilled Spirits Producer': 'DSP',
                        'Bonded Winery': 'BWN',
                        'Brewer': 'BR',
                        'Beer Growler': 'BG'
                    }
                    
                    permit_prefix = type_map.get(type_part, type_part)
                    permit_pattern = f"{permit_prefix}-{state_part}-%"
                    
                    producer_conditions.append("""
                        b.brand_name IN (
                            SELECT DISTINCT brand_name 
                            FROM skus 
                            WHERE permit_no LIKE ?
                        )
                    """)
                    params.append(permit_pattern)
            
            if producer_conditions:
                where_clauses.append(f"({' OR '.join(producer_conditions)})")
        
        # Build final query with WHERE clause
        if where_clauses:
            base_query += ' WHERE ' + ' AND '.join(where_clauses)
        
        base_query += ' GROUP BY b.brand_name'
        
        # Add sorting
        sort_map = {
            'name': 'b.brand_name',
            'skus': 'sku_count',
            'created': 'b.created_date'
        }
        sort_column = sort_map.get(sort, 'b.brand_name')
        base_query += f' ORDER BY {sort_column} {direction.upper()}'
        
        # Get total count for pagination
        count_query = f"SELECT COUNT(DISTINCT b.brand_name) FROM brands b LEFT JOIN skus s ON b.brand_name = s.brand_name"
        if where_clauses:
            count_query += ' WHERE ' + ' AND '.join(where_clauses)
        
        total_count = self.conn.execute(count_query, params).fetchone()[0]
        
        # Add pagination
        offset = (page - 1) * per_page
        base_query += f' LIMIT ? OFFSET ?'
        params.extend([per_page, offset])
        
        # Execute query
        cursor = self.conn.execute(base_query, params)
        
        brands_list = []
        for row in cursor:
            # Parse JSON fields
            importers_data = json.loads(row['importers'] or '{}')
            producers_data = json.loads(row['producers'] or '{}')
            brand_permits = json.loads(row['brand_permits'] or '[]')
            
            # Process importers (same logic as get_all_brands)
            importer_objects = []
            for importer_info in importers_data.values():
                permit_number = importer_info.get('permit_number', '')
                if permit_number and '-I-' in permit_number:
                    importer_objects.append(importer_info)
            
            # Process producers
            producer_objects = []
            for producer_info in producers_data.values():
                producer_objects.append(producer_info)
            
            brand_data = {
                'brand_name': row['brand_name'],
                'countries': json.loads(row['countries'] or '[]'),
                'class_types': json.loads(row['class_types'] or '[]'),
                'importers': importer_objects,
                'producers': producer_objects,
                'brand_permits': brand_permits,
                'sku_count': row['sku_count'],
                'enrichment': json.loads(row['enrichment_data'] or '{}'),
                'website': row['website']
            }
            brands_list.append(brand_data)
        
        # Calculate pagination info
        total_pages = (total_count + per_page - 1) // per_page
        
        return {
            'brands': brands_list,
            'pagination': {
                'page': page,
                'pages': total_pages,
                'total': total_count,
                'per_page': per_page,
                'has_prev': page > 1,
                'has_next': page < total_pages
            }
        }
    
    def get_filter_counts(self):
        """
        Get counts for all filter options - optimized with SQL aggregation
        Used for populating filter sidebar with counts
        """
        filter_counts = {
            'importers': {},
            'alcoholTypes': {},
            'producers': {},
            'countries': {},
            'websiteStatus': {
                'has_website': 0,
                'verified': 0,
                'no_website': 0
            }
        }
        
        # Get all brands data in one query
        cursor = self.conn.execute('''
            SELECT brand_name, countries, class_types, importers, website, enrichment_data
            FROM brands
        ''')
        
        for row in cursor:
            # Count countries
            countries = json.loads(row['countries'] or '[]')
            for country in countries:
                filter_counts['countries'][country] = filter_counts['countries'].get(country, 0) + 1
            
            # Count alcohol types
            class_types = json.loads(row['class_types'] or '[]')
            for class_type in class_types:
                filter_counts['alcoholTypes'][class_type] = filter_counts['alcoholTypes'].get(class_type, 0) + 1
            
            # Count importers
            importers = json.loads(row['importers'] or '{}')
            for importer_data in importers.values():
                if importer_data.get('permit_number', '').count('-I-'):
                    name = importer_data.get('owner_name', '')
                    if name:
                        filter_counts['importers'][name] = filter_counts['importers'].get(name, 0) + 1
            
            # Count website status - check both website field and enrichment_data field for manual entries
            has_website = False
            is_verified = False
            
            # Check main website field
            if row['website']:
                has_website = True
                website_data = json.loads(row['website'] or '{}')
                if website_data.get('verification_status') == 'verified':
                    is_verified = True
            
            # Also check enrichment_data field for manual websites
            if row['enrichment_data']:
                enrichment_data = json.loads(row['enrichment_data'] or '{}')
                
                # Check for direct URL in enrichment data
                if enrichment_data.get('url') or enrichment_data.get('source') == 'manual_override':
                    has_website = True
                    if enrichment_data.get('verification_status') == 'verified':
                        is_verified = True
                
                # Also check nested website structure
                if enrichment_data.get('website'):
                    website_nested = enrichment_data['website']
                    if website_nested.get('url'):
                        has_website = True
                        if website_nested.get('verified') == True or website_nested.get('verification_status') == 'verified':
                            is_verified = True
            
            if has_website:
                filter_counts['websiteStatus']['has_website'] += 1
                if is_verified:
                    filter_counts['websiteStatus']['verified'] += 1
            else:
                filter_counts['websiteStatus']['no_website'] += 1
        
        # Count producers from SKUs table - producers are identified by non-importer permit types
        producer_cursor = self.conn.execute('''
            SELECT permit_no, brand_name, COUNT(*) as brand_count
            FROM skus 
            WHERE permit_no NOT LIKE '%-I-%'
            AND permit_no IS NOT NULL 
            AND permit_no != ''
            GROUP BY permit_no, brand_name
            ORDER BY permit_no
        ''')
        
        producers_by_permit = {}
        for row in producer_cursor:
            permit_no = row['permit_no']
            if permit_no not in producers_by_permit:
                # Extract producer name from permit - use permit prefix as producer identifier
                # DSP-XX-##### = Distilled Spirits Producer (State XX)
                # BWN-XX-##### = Bonded Winery (State XX)  
                # BR-XX-##### = Brewer (State XX)
                parts = permit_no.split('-')
                if len(parts) >= 3:
                    permit_type = parts[0]
                    state = parts[1]
                    
                    type_names = {
                        'DSP': 'Distilled Spirits Producer',
                        'BWN': 'Bonded Winery', 
                        'BR': 'Brewer',
                        'BG': 'Beer Growler'
                    }
                    
                    producer_name = f"{type_names.get(permit_type, permit_type)} ({state})"
                    producers_by_permit[permit_no] = producer_name
        
        # Count unique brands per producer type
        for permit_no, producer_name in producers_by_permit.items():
            brand_count = self.conn.execute('''
                SELECT COUNT(DISTINCT brand_name) as brand_count 
                FROM skus WHERE permit_no = ?
            ''', (permit_no,)).fetchone()['brand_count']
            
            filter_counts['producers'][producer_name] = filter_counts['producers'].get(producer_name, 0) + brand_count
        
        return filter_counts
    
    def get_master_importer(self, permit_number):
        """Get master importer data by permit number"""
        cursor = self.conn.execute('''
            SELECT * FROM master_importers WHERE permit_number = ?
        ''', (permit_number,))
        
        row = cursor.fetchone()
        if row:
            importer_data = dict(row)
            importer_data.pop('updated_at', None)
            if importer_data['brands']:
                importer_data['brands'] = json.loads(importer_data['brands'])
            else:
                importer_data['brands'] = []
            return importer_data
        
        return None
    
    def verify_brand_website(self, brand_name, verified=True):
        """Manually verify or reject a brand website with learning integration"""
        cursor = self.conn.execute('''
            SELECT enrichment_data FROM brands WHERE brand_name = ?
        ''', (brand_name,))
        
        row = cursor.fetchone()
        if row and row['enrichment_data']:
            enrichment_data = json.loads(row['enrichment_data'])
            
            if 'website' in enrichment_data:
                # Store website data for learning before potential removal
                website_data = enrichment_data['website'].copy()
                
                if verified:
                    enrichment_data['website']['verification_status'] = 'verified'
                    enrichment_data['website']['confidence'] = 1.0
                    enrichment_data['website']['needs_review'] = False
                    enrichment_data['website']['verified_date'] = datetime.now().isoformat()
                    user_action = 'verified'
                    
                    # Update database with verified enrichment
                    self.conn.execute('''
                        UPDATE brands SET enrichment_data = ? WHERE brand_name = ?
                    ''', (json.dumps(enrichment_data), brand_name))
                else:
                    # When rejected, remove the enrichment data entirely
                    user_action = 'rejected'
                    
                    # Remove enrichment data entirely (set to NULL)
                    self.conn.execute('''
                        UPDATE brands SET enrichment_data = NULL WHERE brand_name = ?
                    ''', (brand_name,))
                
                self.conn.commit()
                
                # Record learning feedback if enrichment system is available
                try:
                    from brand_enrichment.integrated_enrichment import IntegratedEnrichmentSystem
                    enrichment = IntegratedEnrichmentSystem()
                    enrichment.record_website_feedback(brand_name, website_data, user_action)
                except Exception as e:
                    logger.error(f"Learning feedback error: {e}")
                
                # Refresh in-memory representation
                self.db = self._load_as_dict()
                return True
        
        return False
    
    def flag_brand_website(self, brand_name, reason=None):
        """Flag a brand website for review with learning integration"""
        cursor = self.conn.execute('''
            SELECT enrichment_data FROM brands WHERE brand_name = ?
        ''', (brand_name,))
        
        row = cursor.fetchone()
        if row and row['enrichment_data']:
            enrichment_data = json.loads(row['enrichment_data'])
            
            if 'website' in enrichment_data:
                enrichment_data['website']['verification_status'] = 'flagged'
                enrichment_data['website']['needs_review'] = True
                enrichment_data['website']['flag_reason'] = reason or 'Manual review requested'
                enrichment_data['website']['flagged_date'] = datetime.now().isoformat()
                
                # Update database
                self.conn.execute('''
                    UPDATE brands SET enrichment_data = ? WHERE brand_name = ?
                ''', (json.dumps(enrichment_data), brand_name))
                self.conn.commit()
                
                # Refresh in-memory representation
                self.db = self._load_as_dict()
                return True
        
        return False
    
    def process_importer_csv(self, df, filename):
        """Process importer CSV file"""
        upload_record = {
            'filename': filename,
            'upload_date': datetime.now().isoformat(),
            'total_records': len(df),
            'new_importers': 0,
            'updated_importers': 0,
            'file_type': 'importer'
        }
        
        for _, row in df.iterrows():
            permit_number = str(row.get('Permit Number', '')).strip()
            if not permit_number or permit_number == 'nan':
                continue
            
            # Check if importer exists
            cursor = self.conn.execute('''
                SELECT permit_number FROM master_importers WHERE permit_number = ?
            ''', (permit_number,))
            
            if cursor.fetchone():
                upload_record['updated_importers'] += 1
            else:
                upload_record['new_importers'] += 1
            
            # Insert or replace importer
            self.conn.execute('''
                INSERT OR REPLACE INTO master_importers (
                    permit_number, owner_name, operating_name, street, city, 
                    state, zip, county, industry_type, added_date, brands
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                permit_number,
                str(row.get('Owner Name', '')),
                str(row.get('Operating Name', '')),
                str(row.get('Street', '')),
                str(row.get('City', '')),
                str(row.get('State', '')),
                str(row.get('Zip', '')),
                str(row.get('County', '')),
                str(row.get('Industry Type', 'Importer (Alcohol)')),
                datetime.now().isoformat(),
                json.dumps([])  # Empty brands list initially
            ))
        
        # Add to upload history
        metadata = {k: v for k, v in upload_record.items() 
                   if k not in ['filename', 'upload_date', 'file_type']}
        
        self.conn.execute('''
            INSERT INTO upload_history (
                filename, upload_date, total_records, file_type, metadata
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            filename, upload_record['upload_date'], 
            upload_record['total_records'], 'importer', json.dumps(metadata)
        ))
        
        self.conn.commit()
        
        # Refresh in-memory representation
        self.db = self._load_as_dict()
        
        return upload_record
        return upload_record
    
    # === ADDITIONAL MISSING METHODS ===
    
    def get_all_importers(self):
        """Get all importers"""
        cursor = self.conn.execute('SELECT * FROM master_importers ORDER BY owner_name')
        importers = []
        for row in cursor:
            importer_data = dict(row)
            importer_data.pop('updated_at', None)
            if importer_data['brands']:
                importer_data['brands'] = json.loads(importer_data['brands'])
            else:
                importer_data['brands'] = []
            importers.append(importer_data)
        return importers
    
    def get_importer_data(self, permit_number):
        """Get importer data by permit number"""
        return self.get_master_importer(permit_number)
    
    def get_statistics(self):
        """Get database statistics"""
        stats = {}
        
        cursor = self.conn.execute('SELECT COUNT(*) FROM brands')
        stats['total_brands'] = cursor.fetchone()[0]
        
        cursor = self.conn.execute('SELECT COUNT(*) FROM skus')
        stats['total_skus'] = cursor.fetchone()[0]
        
        cursor = self.conn.execute('SELECT COUNT(*) FROM master_importers')
        stats['total_importers'] = cursor.fetchone()[0]
        
        cursor = self.conn.execute('''
            SELECT COUNT(*) FROM master_importers 
            WHERE brands IS NOT NULL AND brands != '[]'
        ''')
        stats['active_importers'] = cursor.fetchone()[0]
        
        # Count brands with websites (all enriched brands now have consistent structure)
        cursor = self.conn.execute('''
            SELECT COUNT(*) FROM brands
            WHERE enrichment_data IS NOT NULL
            AND json_extract(enrichment_data, '$.url') IS NOT NULL
            AND json_extract(enrichment_data, '$.url') != ''
        ''')
        stats['brands_with_websites'] = cursor.fetchone()[0]
        
        return stats
    
    def search_brands(self, query):
        """Search brands by name"""
        cursor = self.conn.execute('''
            SELECT brand_name FROM brands 
            WHERE brand_name LIKE ? 
            ORDER BY brand_name LIMIT 100
        ''', (f'%{query}%',))
        
        return [row['brand_name'] for row in cursor]
    
    def get_brand_website(self, brand_name):
        """Get brand website data"""
        cursor = self.conn.execute('''
            SELECT enrichment_data FROM brands WHERE brand_name = ?
        ''', (brand_name,))
        
        row = cursor.fetchone()
        if row and row['enrichment_data']:
            enrichment = json.loads(row['enrichment_data'])
            return enrichment.get('website')
        return None
    
    def update_brand_website(self, brand_name, website_data):
        """Update brand website data"""
        cursor = self.conn.execute('''
            SELECT enrichment_data FROM brands WHERE brand_name = ?
        ''', (brand_name,))
        
        row = cursor.fetchone()
        if row:
            enrichment_data = json.loads(row['enrichment_data'] or '{}')
            enrichment_data['website'] = website_data
            
            self.conn.execute('''
                UPDATE brands SET enrichment_data = ? WHERE brand_name = ?
            ''', (json.dumps(enrichment_data), brand_name))
            self.conn.commit()
            
            self.db = self._load_as_dict()
            return True
        return False
    
    def update_brand_enrichment(self, brand_name, enrichment_data):
        """Update full enrichment data for a brand (automatic enrichment)"""
        cursor = self.conn.execute('SELECT enrichment_data FROM brands WHERE brand_name = ?', (brand_name,))
        row = cursor.fetchone()
        
        if row is not None:
            self.conn.execute('''
                UPDATE brands SET enrichment_data = ? WHERE brand_name = ?
            ''', (json.dumps(enrichment_data), brand_name))
            self.conn.commit()
            
            self.db = self._load_as_dict()
            return True
        return False

    def add_manual_website_entry(self, brand_name, website_data):
        """Add a manual website entry (separate from automatic enrichment)"""
        cursor = self.conn.execute('SELECT manual_websites FROM brands WHERE brand_name = ?', (brand_name,))
        row = cursor.fetchone()
        
        if row is not None:
            existing_manual = json.loads(row['manual_websites'] or '[]')
            
            # Add timestamp and entry ID
            website_data['entry_id'] = f"manual_{len(existing_manual) + 1}"
            website_data['added_date'] = datetime.now().isoformat()
            website_data['entry_type'] = 'manual'
            
            existing_manual.append(website_data)
            
            self.conn.execute('''
                UPDATE brands SET manual_websites = ? WHERE brand_name = ?
            ''', (json.dumps(existing_manual), brand_name))
            self.conn.commit()
            
            self.db = self._load_as_dict()
            return True
        return False
    
    def get_brand_all_websites(self, brand_name):
        """Get both automatic and manual website entries for a brand"""
        cursor = self.conn.execute('''
            SELECT enrichment_data, manual_websites FROM brands WHERE brand_name = ?
        ''', (brand_name,))
        row = cursor.fetchone()
        
        if not row:
            return {'automatic': None, 'manual': []}
        
        result = {'automatic': None, 'manual': []}
        
        # Get automatic enrichment
        if row['enrichment_data']:
            try:
                automatic_data = json.loads(row['enrichment_data'])
                result['automatic'] = automatic_data
            except:
                pass
        
        # Get manual entries
        if row['manual_websites']:
            try:
                manual_data = json.loads(row['manual_websites'])
                result['manual'] = manual_data
            except:
                pass
        
        return result
    
    def get_websites_needing_review(self):
        """Get websites that need review"""
        cursor = self.conn.execute('''
            SELECT brand_name, enrichment_data FROM brands 
            WHERE enrichment_data IS NOT NULL
            AND json_extract(enrichment_data, '$.website.needs_review') = 1
        ''')
        
        websites = []
        for row in cursor:
            enrichment = json.loads(row['enrichment_data'])
            if enrichment.get('website', {}).get('needs_review'):
                websites.append({
                    'brand_name': row['brand_name'],
                    'website': enrichment['website']
                })
        
        return websites
    
    def update_importers_list(self, importers_data):
        """Update importers list (bulk operation)"""
        for permit_number, importer_info in importers_data.items():
            self.conn.execute('''
                INSERT OR REPLACE INTO master_importers (
                    permit_number, owner_name, operating_name, street, city, 
                    state, zip, county, industry_type, added_date, brands
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                permit_number,
                importer_info.get('owner_name'),
                importer_info.get('operating_name'),
                importer_info.get('street'),
                importer_info.get('city'),
                importer_info.get('state'),
                importer_info.get('zip'),
                importer_info.get('county'),
                importer_info.get('industry_type'),
                importer_info.get('added_date'),
                json.dumps(importer_info.get('brands', []))
            ))
        
        self.conn.commit()
        self.db = self._load_as_dict()
    
    def get_all_producers(self):
        """Get all producers (spirits and wine) with their brands"""
        producers = []
        
        # Get spirit producers
        cursor = self.conn.execute('SELECT * FROM spirit_producers')
        for row in cursor:
            producer_data = dict(row)
            producer_data.pop('updated_at', None)
            producer_data['type'] = 'Spirit'
            producers.append(producer_data)
        
        # Get wine producers
        cursor = self.conn.execute('SELECT * FROM wine_producers')
        for row in cursor:
            producer_data = dict(row)
            producer_data.pop('updated_at', None)
            producer_data['type'] = 'Wine'
            producers.append(producer_data)
        
        return producers
    
    def get_spirit_producer(self, permit_number):
        """Get spirit producer by permit number"""
        cursor = self.conn.execute('''
            SELECT * FROM spirit_producers WHERE permit_number = ?
        ''', (permit_number,))
        
        row = cursor.fetchone()
        if row:
            producer_data = dict(row)
            producer_data.pop('updated_at', None)
            return producer_data
        return None
    
    def get_wine_producer(self, permit_number):
        """Get wine producer by permit number"""
        cursor = self.conn.execute('''
            SELECT * FROM wine_producers WHERE permit_number = ?
        ''', (permit_number,))
        
        row = cursor.fetchone()
        if row:
            producer_data = dict(row)
            producer_data.pop('updated_at', None)
            return producer_data
        return None
    
    def process_spirit_producer_file(self, df, filename):
        """Process spirit producer CSV file"""
        upload_record = {
            'filename': filename,
            'upload_date': datetime.now().isoformat(),
            'total_records': len(df),
            'new_producers': 0,
            'updated_producers': 0,
            'file_type': 'spirit_producer'
        }
        
        for _, row in df.iterrows():
            permit_number = str(row.get('Permit Number', '')).strip()
            if not permit_number or permit_number == 'nan':
                continue
            
            cursor = self.conn.execute('''
                SELECT permit_number FROM spirit_producers WHERE permit_number = ?
            ''', (permit_number,))
            
            if cursor.fetchone():
                upload_record['updated_producers'] += 1
            else:
                upload_record['new_producers'] += 1
            
            self.conn.execute('''
                INSERT OR REPLACE INTO spirit_producers (
                    permit_number, owner_name, operating_name, street, city, 
                    state, zip, county, industry_type, added_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                permit_number,
                str(row.get('Owner Name', '')),
                str(row.get('Operating Name', '')),
                str(row.get('Street', '')),
                str(row.get('City', '')),
                str(row.get('State', '')),
                str(row.get('Zip', '')),
                str(row.get('County', '')),
                str(row.get('Industry Type', 'Spirit Producer')),
                datetime.now().isoformat()
            ))
        
        self.conn.commit()
        self.db = self._load_as_dict()
        return upload_record
    
    def process_wine_producer_file(self, df, filename):
        """Process wine producer CSV file"""
        upload_record = {
            'filename': filename,
            'upload_date': datetime.now().isoformat(),
            'total_records': len(df),
            'new_producers': 0,
            'updated_producers': 0,
            'file_type': 'wine_producer'
        }
        
        for _, row in df.iterrows():
            permit_number = str(row.get('Permit Number', '')).strip()
            if not permit_number or permit_number == 'nan':
                continue
            
            cursor = self.conn.execute('''
                SELECT permit_number FROM wine_producers WHERE permit_number = ?
            ''', (permit_number,))
            
            if cursor.fetchone():
                upload_record['updated_producers'] += 1
            else:
                upload_record['new_producers'] += 1
            
            self.conn.execute('''
                INSERT OR REPLACE INTO wine_producers (
                    permit_number, owner_name, operating_name, street, city, 
                    state, zip, county, industry_type, added_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                permit_number,
                str(row.get('Owner Name', '')),
                str(row.get('Operating Name', '')),
                str(row.get('Street', '')),
                str(row.get('City', '')),
                str(row.get('State', '')),
                str(row.get('Zip', '')),
                str(row.get('County', '')),
                str(row.get('Industry Type', 'Wine Producer')),
                datetime.now().isoformat()
            ))
        
        self.conn.commit()
        self.db = self._load_as_dict()
        return upload_record
    
    def consolidate_brands(self, canonical_name, brands_to_merge):
        """
        Consolidate multiple brands into one canonical brand in the database
        
        This method:
        1. Collects all data from brands to merge 
        2. Creates new consolidated brand entry
        3. Removes old brand entries
        4. Updates all SKU brand references
        5. Commits changes atomically
        """
        try:
            # Start transaction
            self.conn.execute('BEGIN TRANSACTION')
            
            # Collect data from all brands
            merged_data = {
                'countries': set(),
                'class_types': set(),
                'permit_numbers': [],
                'enrichment_data': None,
                'importers': {},
                'producers': {},
                'brand_permits': []
            }
            
            # Get all brand data
            for brand_name in brands_to_merge:
                cursor = self.conn.execute('''
                    SELECT permit_numbers, countries, class_types, enrichment_data, importers, producers, brand_permits
                    FROM brands WHERE brand_name = ?
                ''', (brand_name,))
                
                result = cursor.fetchone()
                if result:
                    # Merge permit numbers
                    if result[0]:
                        permits = json.loads(result[0])
                        if isinstance(permits, list):
                            merged_data['permit_numbers'].extend(permits)
                    
                    # Merge countries
                    if result[1]:
                        countries = json.loads(result[1])
                        if isinstance(countries, list):
                            merged_data['countries'].update(countries)
                    
                    # Merge class types
                    if result[2]:
                        class_types = json.loads(result[2])
                        if isinstance(class_types, list):
                            merged_data['class_types'].update(class_types)
                    
                    # Preserve enrichment data (prefer verified)
                    if result[3]:
                        enrichment = json.loads(result[3])
                        if not merged_data['enrichment_data'] or enrichment.get('verification_status') == 'verified':
                            merged_data['enrichment_data'] = enrichment
                    
                    # Merge importers
                    if result[4]:
                        importers = json.loads(result[4])
                        if isinstance(importers, dict):
                            merged_data['importers'].update(importers)
                    
                    # Merge producers  
                    if result[5]:
                        producers = json.loads(result[5])
                        if isinstance(producers, dict):
                            merged_data['producers'].update(producers)
                    
                    # Merge brand permits
                    if result[6]:
                        brand_permits = json.loads(result[6])
                        if isinstance(brand_permits, list):
                            merged_data['brand_permits'].extend(brand_permits)
            
            # Remove duplicates and convert to JSON
            merged_data['permit_numbers'] = list(set(merged_data['permit_numbers']))
            merged_data['countries'] = list(merged_data['countries'])
            merged_data['class_types'] = list(merged_data['class_types'])
            merged_data['brand_permits'] = list(set(merged_data['brand_permits']))
            
            # Create consolidated brand entry
            self.conn.execute('''
                INSERT OR REPLACE INTO brands (
                    brand_name, created_date, permit_numbers, countries, class_types, 
                    enrichment_data, importers, producers, brand_permits
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                canonical_name,
                datetime.now().isoformat(),
                json.dumps(merged_data['permit_numbers']),
                json.dumps(merged_data['countries']),
                json.dumps(merged_data['class_types']),
                json.dumps(merged_data['enrichment_data']) if merged_data['enrichment_data'] else None,
                json.dumps(merged_data['importers']) if merged_data['importers'] else None,
                json.dumps(merged_data['producers']) if merged_data['producers'] else None,
                json.dumps(merged_data['brand_permits'])
            ))
            
            # Update all SKU brand references
            for old_brand in brands_to_merge:
                if old_brand != canonical_name:
                    self.conn.execute('''
                        UPDATE skus SET brand_name = ? WHERE brand_name = ?
                    ''', (canonical_name, old_brand))
                    
                    # Delete old brand entry
                    self.conn.execute('''
                        DELETE FROM brands WHERE brand_name = ?
                    ''', (old_brand,))
            
            # Commit transaction
            self.conn.commit()
            
            # Refresh in-memory cache
            self.db = self._load_as_dict()
            
            logger.info(f"✅ Database consolidation completed: {brands_to_merge} → {canonical_name}")
            
            return {
                'success': True,
                'canonical_name': canonical_name,
                'brands_merged': brands_to_merge,
                'countries_count': len(merged_data['countries']),
                'class_types_count': len(merged_data['class_types']),
                'permits_count': len(merged_data['permit_numbers']) + len(merged_data['brand_permits'])
            }
            
        except Exception as e:
            # Rollback on error
            self.conn.rollback()
            logger.error(f"Error consolidating brands: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def reset_database(self):
        """Reset the database - WARNING: This will clear all data"""
        try:
            logger.warning("🚨 Database reset requested - clearing all data")
            
            # Clear all tables
            self.conn.execute('DELETE FROM brands')
            self.conn.execute('DELETE FROM skus')
            self.conn.execute('DELETE FROM master_importers')
            self.conn.commit()
            
            # Reset in-memory cache
            self.db = {
                'brands': {},
                'skus': {},
                'master_importers': {}
            }
            
            # Save empty JSON backup
            self.save_json_backup()
            
            logger.info("✅ Database reset complete")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting database: {e}")
            self.conn.rollback()
            raise
    
    def get_brands_paginated_optimized(self, page=1, per_page=24, search='', filters=None):
        """
        Optimized method to get paginated brands with filtering
        Uses SQL for filtering instead of Python post-processing
        """
        try:
            offset = (page - 1) * per_page
            filters = filters or {}
            
            # Build WHERE clauses
            where_clauses = []
            params = []
            
            # Search filter
            if search:
                where_clauses.append("brand_name LIKE ?")
                params.append(f"%{search}%")
            
            # Website status filter
            if 'websiteStatus' in filters:
                status = filters['websiteStatus']
                if status == 'has_website':
                    where_clauses.append("(enrichment_data IS NOT NULL OR website IS NOT NULL)")
                elif status == 'no_website':
                    where_clauses.append("(enrichment_data IS NULL AND website IS NULL)")
                elif status == 'verified':
                    where_clauses.append(
                        "json_extract(enrichment_data, '$.website.verification_status') = 'verified'"
                    )
            
            # Build final WHERE clause
            where_sql = ""
            if where_clauses:
                where_sql = "WHERE " + " AND ".join(where_clauses)
            
            # Count total matching records
            count_sql = f"SELECT COUNT(*) FROM brands {where_sql}"
            cursor = self.conn.execute(count_sql, params)
            total_count = cursor.fetchone()[0]
            
            # Get paginated results with all needed data
            query_sql = f'''
                SELECT b.brand_name, b.countries, b.class_types, b.importers, b.producers,
                       b.enrichment_data, b.website, b.created_date,
                       COUNT(s.ttb_id) as sku_count
                FROM brands b
                LEFT JOIN skus s ON b.brand_name = s.brand_name
                {where_sql}
                GROUP BY b.brand_name
                ORDER BY b.brand_name
                LIMIT ? OFFSET ?
            '''
            params.extend([per_page, offset])
            
            cursor = self.conn.execute(query_sql, params)
            brands = []
            
            for row in cursor:
                brand_data = {
                    'brand_name': row['brand_name'],
                    'countries': json.loads(row['countries'] or '[]'),
                    'class_types': json.loads(row['class_types'] or '[]'),
                    'sku_count': row['sku_count'],
                    'created_date': row['created_date']
                }
                
                # Parse importers
                if row['importers']:
                    importers_data = json.loads(row['importers'])
                    brand_data['importers'] = [
                        {'permit': k, 'owner_name': v.get('owner_name', '')}
                        for k, v in importers_data.items()
                        if isinstance(v, dict)
                    ]
                else:
                    brand_data['importers'] = []
                
                # Parse producers
                if row['producers']:
                    producers_data = json.loads(row['producers'])
                    brand_data['producers'] = [
                        {'permit': k, 'owner_name': v.get('owner_name', '')}
                        for k, v in producers_data.items()
                        if isinstance(v, dict)
                    ]
                else:
                    brand_data['producers'] = []
                
                # Parse enrichment
                if row['enrichment_data']:
                    enrichment = json.loads(row['enrichment_data'])
                    brand_data['enrichment'] = {
                        'confidence': enrichment.get('confidence', 0),
                        'url': enrichment.get('website', {}).get('url', ''),
                        'verified': enrichment.get('website', {}).get('verification_status') == 'verified'
                    }
                elif row['website']:
                    brand_data['website'] = row['website']
                
                brands.append(brand_data)
            
            return {
                'brands': brands,
                'total': total_count,
                'page': page,
                'per_page': per_page,
                'total_pages': (total_count + per_page - 1) // per_page
            }
            
        except Exception as e:
            logger.error(f"Error getting paginated brands: {e}")
            return {
                'brands': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'total_pages': 0
            }
    
    def get_filter_counts(self):
        """
        Optimized method to get filter counts using database aggregation
        Returns counts for all filter categories used in the UI
        """
        try:
            counts = {
                'importers': {},
                'alcoholTypes': {},
                'producers': {},
                'countries': {},
                'websiteStatus': {'has_website': 0, 'verified': 0, 'no_website': 0}
            }
            
            # Get website status counts using SQL
            cursor = self.conn.execute('''
                SELECT 
                    CASE 
                        WHEN enrichment_data IS NOT NULL OR website IS NOT NULL THEN 'has_website'
                        ELSE 'no_website'
                    END as status,
                    COUNT(*) as count
                FROM brands
                GROUP BY status
            ''')
            
            for row in cursor:
                if row['status'] == 'has_website':
                    counts['websiteStatus']['has_website'] = row['count']
                else:
                    counts['websiteStatus']['no_website'] = row['count']
            
            # Get verified count
            cursor = self.conn.execute('''
                SELECT COUNT(*) as count
                FROM brands
                WHERE enrichment_data IS NOT NULL 
                AND json_extract(enrichment_data, '$.website.verification_status') = 'verified'
            ''')
            verified_count = cursor.fetchone()
            if verified_count:
                counts['websiteStatus']['verified'] = verified_count['count']
            
            # For JSON columns, we need to parse and aggregate
            # This is still more efficient than loading all brands into memory
            cursor = self.conn.execute('''
                SELECT countries, class_types, importers, producers
                FROM brands
                WHERE countries IS NOT NULL 
                   OR class_types IS NOT NULL 
                   OR importers IS NOT NULL 
                   OR producers IS NOT NULL
            ''')
            
            for row in cursor:
                # Count countries
                if row['countries']:
                    try:
                        countries = json.loads(row['countries'])
                        for country in countries:
                            counts['countries'][country] = counts['countries'].get(country, 0) + 1
                    except:
                        pass
                
                # Count alcohol types
                if row['class_types']:
                    try:
                        class_types = json.loads(row['class_types'])
                        for class_type in class_types:
                            counts['alcoholTypes'][class_type] = counts['alcoholTypes'].get(class_type, 0) + 1
                    except:
                        pass
                
                # Count importers
                if row['importers']:
                    try:
                        importers = json.loads(row['importers'])
                        for permit, importer_data in importers.items():
                            if isinstance(importer_data, dict):
                                name = importer_data.get('owner_name', '')
                                if name:
                                    counts['importers'][name] = counts['importers'].get(name, 0) + 1
                    except:
                        pass
                
                # Count producers
                if row['producers']:
                    try:
                        producers = json.loads(row['producers'])
                        for permit, producer_data in producers.items():
                            if isinstance(producer_data, dict):
                                name = producer_data.get('owner_name', '')
                                if name:
                                    counts['producers'][name] = counts['producers'].get(name, 0) + 1
                    except:
                        pass
            
            return counts
            
        except Exception as e:
            logger.error(f"Error getting filter counts: {e}")
            return {
                'importers': {},
                'alcoholTypes': {},
                'producers': {},
                'countries': {},
                'websiteStatus': {'has_website': 0, 'verified': 0, 'no_website': 0}
            }
    
    def reload_from_disk(self):
        """Reload database from disk (hot-reload functionality)"""
        try:
            logger.info("🔄 Reloading database from disk...")
            
            # Re-initialize connection to get latest data
            self.conn.close()
            # Use check_same_thread=False to avoid threading issues with Flask
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            
            # Reload in-memory cache
            self.db = self._load_as_dict()
            
            # Get stats for confirmation
            cursor = self.conn.execute('''
                SELECT 
                    (SELECT COUNT(*) FROM brands) as brand_count,
                    (SELECT COUNT(*) FROM skus) as sku_count,
                    (SELECT COUNT(*) FROM master_importers) as importer_count
            ''')
            stats = cursor.fetchone()
            
            logger.info(f"✅ Database reloaded: {stats['brand_count']} brands, {stats['sku_count']} SKUs, {stats['importer_count']} importers")
            
            return True

        except Exception as e:
            logger.error(f"Error reloading database: {e}")
            raise

    def update_brand_apollo_data(self, brand_name, apollo_data):
        """Update Apollo enrichment data for a brand"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check if apollo_data column exists, if not add it
            cursor.execute("PRAGMA table_info(brands)")
            columns = [col[1] for col in cursor.fetchall()]

            if 'apollo_data' not in columns:
                cursor.execute('ALTER TABLE brands ADD COLUMN apollo_data TEXT')
            if 'apollo_status' not in columns:
                cursor.execute('ALTER TABLE brands ADD COLUMN apollo_status TEXT DEFAULT "not_started"')
            if 'apollo_company_id' not in columns:
                cursor.execute('ALTER TABLE brands ADD COLUMN apollo_company_id TEXT')

            # Update Apollo data
            # Prepare apollo_data for storage
            apollo_data_to_store = apollo_data.get('apollo_data')
            if apollo_data_to_store:
                apollo_data_json = json.dumps(apollo_data_to_store)
            else:
                apollo_data_json = None

            cursor.execute('''
                UPDATE brands
                SET apollo_data = ?,
                    apollo_status = ?,
                    apollo_company_id = ?
                WHERE brand_name = ?
            ''', (
                apollo_data_json,
                apollo_data.get('apollo_status', 'not_started'),
                apollo_data.get('apollo_company_id'),
                brand_name
            ))

            rows_affected = cursor.rowcount
            conn.commit()
            conn.close()

            if rows_affected == 0:
                logger.warning(f"No brand found with name: {brand_name}")
                return False

            logger.info(f"Successfully updated Apollo data for brand: {brand_name}")
            return True

        except Exception as e:
            logger.error(f"Error updating Apollo data for {brand_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def get_brands_for_apollo_enrichment(self):
        """Get brands with websites that don't have Apollo data yet"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check if apollo_status column exists
            cursor.execute("PRAGMA table_info(brands)")
            columns = [col[1] for col in cursor.fetchall()]

            if 'apollo_status' not in columns:
                # Column doesn't exist, all brands with websites are candidates
                cursor.execute('''
                    SELECT brand_name, countries, class_types, enrichment_data,
                           importers, producers
                    FROM brands
                    WHERE json_extract(enrichment_data, '$.url') IS NOT NULL
                    AND json_extract(enrichment_data, '$.url') != ''
                    LIMIT 100
                ''')
            else:
                # Get brands with websites but no Apollo data
                cursor.execute('''
                    SELECT brand_name, countries, class_types, enrichment_data,
                           importers, producers
                    FROM brands
                    WHERE json_extract(enrichment_data, '$.url') IS NOT NULL
                    AND json_extract(enrichment_data, '$.url') != ''
                    AND (apollo_status IS NULL OR apollo_status = 'not_started')
                    LIMIT 100
                ''')

            results = []
            for row in cursor.fetchall():
                results.append({
                    'name': row[0],
                    'countries': json.loads(row[1]) if row[1] else [],
                    'class_types': json.loads(row[2]) if row[2] else [],
                    'enrichment_data': json.loads(row[3]) if row[3] else {},
                    'importers': json.loads(row[4]) if row[4] else [],
                    'producers': json.loads(row[5]) if row[5] else []
                })

            conn.close()
            return results

        except Exception as e:
            logger.error(f"Error getting brands for Apollo enrichment: {e}")
            return []
