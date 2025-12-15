from flask import Flask, render_template, request, jsonify, send_file, redirect
from flask_cors import CORS
import pandas as pd
import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename
import io
import re
import logging
import time
from functools import lru_cache
from dotenv import load_dotenv
from core.database import BrandDatabaseV2 as BrandDatabase
from core.config import get_database_config, get_web_config, get_enrichment_config, ensure_directories
from core.market_insights import MarketInsightsAnalyzer
from core.pdf_generator import MarketInsightsPDFGenerator

# Load environment variables from .env file
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Import brand enrichment system
try:
    from enrichment.orchestrator import IntegratedEnrichmentSystem
    ENRICHMENT_AVAILABLE = True
except ImportError:
    ENRICHMENT_AVAILABLE = False
    print("Warning: Brand enrichment module not available")

# Load configuration
web_config = get_web_config()
db_config = get_database_config()
enrichment_config = get_enrichment_config()

# Ensure all directories exist
ensure_directories()

app = Flask(__name__, 
           template_folder=web_config['template_folder'],
           static_folder=web_config['static_folder'])
CORS(app)

UPLOAD_FOLDER = web_config['upload_folder']
MATCHED_FOLDER = web_config['matched_folder']
IMPORTER_VERSIONS_FILE = 'importer_versions.json'

# Initialize brand database (SQLite version)
brand_db = BrandDatabase(db_config['sqlite_path'], db_config['json_backup_path'])

# Cache configuration
FILTER_CACHE_TTL = 600  # 10 minutes cache for filter counts (increased)
BRAND_LIST_CACHE_TTL = 120  # 2 minutes for brand list queries
ALL_BRANDS_CACHE_TTL = 300  # 5 minutes for get_all_brands calls
STATS_CACHE_TTL = 180  # 3 minutes for statistics

# Database version tracking for cache invalidation
db_version = {
    'version': int(time.time() * 1000),  # Millisecond timestamp
    'last_modified': datetime.now().isoformat()
}

filter_cache = {
    'counts': None,
    'timestamp': 0,
    'db_version': 0
}
brand_list_cache = {
    'data': None,
    'timestamp': 0,
    'query_hash': None,
    'db_version': 0
}
all_brands_cache = {
    'data': None,
    'timestamp': 0,
    'db_version': 0
}
stats_cache = {
    'data': None,
    'timestamp': 0,
    'db_version': 0
}

def invalidate_all_caches():
    """
    Invalidate all caches when database is modified
    This ensures UI always shows fresh data after consolidations, merges, updates
    """
    global filter_cache, brand_list_cache, all_brands_cache, stats_cache, db_version

    # Update database version to invalidate all caches
    db_version['version'] = int(time.time() * 1000)
    db_version['last_modified'] = datetime.now().isoformat()

    # Clear all cache data
    filter_cache = {'counts': None, 'timestamp': 0, 'db_version': 0}
    brand_list_cache = {'data': None, 'timestamp': 0, 'query_hash': None, 'db_version': 0}
    all_brands_cache = {'data': None, 'timestamp': 0, 'db_version': 0}
    stats_cache = {'data': None, 'timestamp': 0, 'db_version': 0}

    logger.info(f"🔄 All caches invalidated - DB version: {db_version['version']}")

def get_cached_all_brands():
    """Get all brands with caching to avoid repeated database calls"""
    global all_brands_cache, db_version
    current_time = time.time()

    # Check if cache is valid (both time-based AND version-based)
    cache_valid = (
        all_brands_cache['data'] and
        (current_time - all_brands_cache['timestamp']) < ALL_BRANDS_CACHE_TTL and
        all_brands_cache['db_version'] == db_version['version']
    )

    if cache_valid:
        return all_brands_cache['data']

    # Cache miss - reload from database
    all_brands_cache['data'] = brand_db.get_all_brands()
    all_brands_cache['timestamp'] = current_time
    all_brands_cache['db_version'] = db_version['version']
    return all_brands_cache['data']

def get_cached_statistics():
    """Get database statistics with caching"""
    global stats_cache, db_version
    current_time = time.time()

    # Check if cache is valid (both time-based AND version-based)
    cache_valid = (
        stats_cache['data'] and
        (current_time - stats_cache['timestamp']) < STATS_CACHE_TTL and
        stats_cache['db_version'] == db_version['version']
    )

    if cache_valid:
        return stats_cache['data']

    # Cache miss - reload from database
    stats_cache['data'] = brand_db.get_statistics()
    stats_cache['timestamp'] = current_time
    stats_cache['db_version'] = db_version['version']
    return stats_cache['data']

def get_cached_filter_counts():
    """Get filter counts with caching"""
    global filter_cache, db_version
    current_time = time.time()

    # Check if cache is valid (both time-based AND version-based)
    cache_valid = (
        filter_cache['counts'] and
        (current_time - filter_cache['timestamp']) < FILTER_CACHE_TTL and
        filter_cache['db_version'] == db_version['version']
    )

    if cache_valid:
        return filter_cache['counts']

    # Cache miss - reload from database
    if hasattr(brand_db, 'get_filter_counts'):
        filter_cache['counts'] = brand_db.get_filter_counts()
        filter_cache['timestamp'] = current_time
        filter_cache['db_version'] = db_version['version']
    else:
        # Fallback to calculating counts from cached brands
        all_brands = get_cached_all_brands()
        counts = {
            'importers': {},
            'alcoholTypes': {},
            'producers': {},
            'countries': {},
            'websiteStatus': {'has_website': 0, 'verified': 0, 'no_website': 0}
        }
        
        for brand in all_brands:
            # Count countries
            for country in brand.get('countries', []):
                counts['countries'][country] = counts['countries'].get(country, 0) + 1
            
            # Count alcohol types
            for class_type in brand.get('class_types', []):
                counts['alcoholTypes'][class_type] = counts['alcoholTypes'].get(class_type, 0) + 1
            
            # Count importers
            for importer in brand.get('importers', []):
                if isinstance(importer, dict):
                    name = importer.get('owner_name', '')
                    if name:
                        counts['importers'][name] = counts['importers'].get(name, 0) + 1
            
            # Count producers
            for producer in brand.get('producers', []):
                if isinstance(producer, dict):
                    name = producer.get('owner_name', '')
                    if name:
                        counts['producers'][name] = counts['producers'].get(name, 0) + 1
            
            # Count website status
            has_website = bool(brand.get('website') or brand.get('enrichment'))
            if has_website:
                counts['websiteStatus']['has_website'] += 1
                enrichment = brand.get('enrichment', {})
                if enrichment.get('verified'):
                    counts['websiteStatus']['verified'] += 1
            else:
                counts['websiteStatus']['no_website'] += 1
        
        filter_cache['counts'] = counts
        filter_cache['timestamp'] = current_time
    
    return filter_cache['counts']

def invalidate_filter_cache():
    """
    Invalidate all caches when data changes
    DEPRECATED: Redirects to invalidate_all_caches() for comprehensive cache clearing with versioning
    """
    # Call the new comprehensive cache invalidation with versioning
    invalidate_all_caches()

def get_query_hash(params):
    """Generate a hash for query parameters to use as cache key"""
    import hashlib
    # Sort params for consistent hashing
    sorted_params = sorted(params.items())
    param_str = str(sorted_params)
    return hashlib.md5(param_str.encode()).hexdigest()

# Initialize enrichment system if available
enrichment_system = None
if ENRICHMENT_AVAILABLE:
    # Get Apollo API key from environment (optional)
    apollo_key = os.getenv('APOLLO_API_KEY')
    
    # Detect environment for fast mode
    environment = os.getenv('FLASK_ENV', 'development')
    
    enrichment_system = IntegratedEnrichmentSystem(
        apollo_api_key=apollo_key,
        environment=environment
    )
    
    if environment == 'development':
        print("🚀 Brand enrichment system initialized in FAST MODE (development)")
        print("   Searches will complete in < 2 seconds with basic results")
    else:
        print("🔒 Brand enrichment system initialized in PRODUCTION MODE")
    
    if apollo_key:
        print("✅ Apollo integration enabled for contact discovery")
    else:
        print("⚠️ Apollo integration disabled (FREE FEATURES ONLY)")
        print("   Set APOLLO_API_KEY environment variable for Apollo contact discovery")

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Helper functions for consistent responses
def success_response(data=None, message=None, status_code=200):
    """Create a consistent success response"""
    response = {'success': True}
    if message:
        response['message'] = message
    if data is not None:
        if isinstance(data, dict):
            response.update(data)
        else:
            response['data'] = data
    return jsonify(response), status_code

def error_response(error, status_code=500):
    """Create a consistent error response"""
    if isinstance(error, Exception):
        error_msg = str(error)
    else:
        error_msg = error
    
    logger.error(f"Error response: {error_msg}")
    return jsonify({
        'success': False,
        'error': error_msg
    }), status_code

def paginate_results(items, page=1, per_page=50):
    """Helper function for pagination"""
    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page
    
    return {
        'items': items[start:end],
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    }

def get_importer_version_from_filename(filename):
    match = re.match(r'^(\d+)_', filename)
    if match:
        return match.group(1)
    return None

def load_importer_versions():
    versions_file = os.path.join(DATA_FOLDER, IMPORTER_VERSIONS_FILE)
    if os.path.exists(versions_file):
        with open(versions_file, 'r') as f:
            return json.load(f)
    return {
        'current_version': None,
        'versions': []
    }

def save_importer_versions(versions_data):
    versions_file = os.path.join(DATA_FOLDER, IMPORTER_VERSIONS_FILE)
    with open(versions_file, 'w') as f:
        json.dump(versions_data, f, indent=2)

def load_importers_data():
    try:
        versions_data = load_importer_versions()
        if versions_data['current_version']:
            importers_file = os.path.join(DATA_FOLDER, f"importers_{versions_data['current_version']}.csv")
            if os.path.exists(importers_file):
                try:
                    return pd.read_csv(importers_file, on_bad_lines='skip')
                except Exception as e:
                    print(f"Error reading importers file {importers_file}: {e}")
                    # Try with different separator or encoding
                    try:
                        return pd.read_csv(importers_file, encoding='latin-1', on_bad_lines='skip')
                    except Exception as e2:
                        print(f"Error reading importers file with latin-1 encoding: {e2}")
    except Exception as e:
        print(f"Error in load_importers_data: {e}")
    return pd.DataFrame()

def save_importers_data(df, version=None, original_filename=None):
    if version is None:
        version = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    importers_file = os.path.join(DATA_FOLDER, f'importers_{version}.csv')
    df.to_csv(importers_file, index=False)
    
    versions_data = load_importer_versions()
    
    version_entry = {
        'version': version,
        'filename': original_filename or f'importers_{version}.csv',
        'uploaded': datetime.now().isoformat(),
        'row_count': len(df),
        'column_count': len(df.columns)
    }
    
    versions_data['versions'].append(version_entry)
    versions_data['current_version'] = version
    
    save_importer_versions(versions_data)
    
    return version

def match_ttb_with_importers(ttb_df, importers_df):
    if importers_df.empty or ttb_df.empty:
        return pd.DataFrame()
    
    permit_columns_ttb = [col for col in ttb_df.columns if 'permit' in col.lower()]
    
    if 'Permit_Number' in importers_df.columns:
        permit_col_importers = 'Permit_Number'
    else:
        permit_columns_importers = [col for col in importers_df.columns if 'permit' in col.lower()]
        if not permit_columns_importers:
            return pd.DataFrame()
        permit_col_importers = permit_columns_importers[0]
    
    if not permit_columns_ttb:
        return pd.DataFrame()
    
    permit_col_ttb = permit_columns_ttb[0]
    
    ttb_df[permit_col_ttb] = ttb_df[permit_col_ttb].astype(str).str.strip().str.upper()
    importers_df[permit_col_importers] = importers_df[permit_col_importers].astype(str).str.strip().str.upper()
    
    matched_df = pd.merge(
        ttb_df,
        importers_df,
        left_on=permit_col_ttb,
        right_on=permit_col_importers,
        how='left',
        suffixes=('', '_importer')
    )
    
    matched_df['Match_Status'] = matched_df[permit_col_importers].notna().map({True: 'Matched', False: 'Unmatched'})
    
    return matched_df

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test_filters')
def test_filters():
    """Test page for filter aggregation"""
    return send_file('test_filters.html')

@app.route('/upload_spirit_producers', methods=['POST'])
def upload_spirit_producers():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Process the spirit producer file
            result = brand_db.process_spirit_producer_file(filepath)
            
            return jsonify({
                'success': True,
                'message': f'Successfully processed spirit producers file',
                'added': result['added'],
                'updated': result['updated'],
                'total': result['total']
            })
        else:
            return jsonify({'error': 'Invalid file type. Please upload a CSV file.'}), 400
            
    except Exception as e:
        print(f"Error uploading spirit producers: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/upload_wine_producers', methods=['POST'])
def upload_wine_producers():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Process the wine producer file
            result = brand_db.process_wine_producer_file(filepath)
            
            return jsonify({
                'success': True,
                'message': f'Successfully processed wine producers file',
                'added': result['added'],
                'updated': result['updated'],
                'total': result['total']
            })
        else:
            return jsonify({'error': 'Invalid file type. Please upload a CSV file.'}), 400
            
    except Exception as e:
        print(f"Error uploading wine producers: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_producer_stats', methods=['GET'])
def get_producer_stats():
    """Get statistics about producers in the database"""
    try:
        stats = {
            'spirit_producers': 0,
            'wine_producers': 0,
            'total_producers': 0
        }
        
        if hasattr(brand_db, 'db'):
            if 'spirit_producers' in brand_db.db:
                stats['spirit_producers'] = len(brand_db.db['spirit_producers'])
            if 'wine_producers' in brand_db.db:
                stats['wine_producers'] = len(brand_db.db['wine_producers'])
            stats['total_producers'] = stats['spirit_producers'] + stats['wine_producers']
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_all_producers', methods=['GET'])
def get_all_producers():
    """Get all producers with pagination and filtering"""
    try:
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 24)), 25000)
        search = request.args.get('search', '').strip().lower()
        producer_type = request.args.get('type', 'all')
        sort_by = request.args.get('sort', 'name')
        direction = request.args.get('direction', 'asc')
        
        producers = brand_db.get_all_producers()
        
        # Apply search filter
        if search:
            producers = [p for p in producers if (
                search in p.get('owner_name', '').lower() or
                search in p.get('operating_name', '').lower() or
                search in p.get('permit_number', '').lower() or
                search in p.get('city', '').lower() or
                search in p.get('state', '').lower()
            )]
        
        # Apply type filter
        if producer_type != 'all':
            producers = [p for p in producers if p.get('type') == producer_type]
        
        # Apply sorting
        reverse = direction == 'desc'
        if sort_by == 'name':
            producers.sort(key=lambda x: x.get('owner_name', '').lower(), reverse=reverse)
        elif sort_by == 'permit':
            producers.sort(key=lambda x: x.get('permit_number', '').lower(), reverse=reverse)
        elif sort_by == 'operating_name':
            producers.sort(key=lambda x: x.get('operating_name', '').lower(), reverse=reverse)
        elif sort_by == 'type':
            producers.sort(key=lambda x: x.get('type', '').lower(), reverse=reverse)
        elif sort_by == 'city':
            producers.sort(key=lambda x: x.get('city', '').lower(), reverse=reverse)
        elif sort_by == 'state':
            producers.sort(key=lambda x: x.get('state', '').lower(), reverse=reverse)
        
        # Apply pagination
        total_producers = len(producers)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_producers = producers[start_idx:end_idx]
        
        return jsonify({
            'producers': paginated_producers,
            'total': total_producers,
            'page': page,
            'per_page': per_page,
            'total_pages': (total_producers + per_page - 1) // per_page
        })
        
    except Exception as e:
        print(f"Error in get_all_producers: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/producers')
def producers_page():
    """Render the producers page"""
    return render_template('producers.html')

@app.route('/consolidation')
def consolidation_page():
    """Redirect to audit page (consolidation is now part of audit)"""
    return redirect('/audit')

@app.route('/audit')
def audit_page():
    """Render the comprehensive data audit page"""
    return render_template('audit.html')

@app.route('/brands')
def brands():
    return render_template('brands.html')

@app.route('/enrichment_rankings')
def enrichment_rankings():
    return render_template('enrichment_rankings.html')

@app.route('/importers')
def importers():
    return render_template('importers.html')

@app.route('/data')
def data():
    return render_template('data.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/market_insights')
def get_market_insights():
    """Get comprehensive market insights from the database with optional date filtering"""
    try:
        # Get date parameters from query string
        start_date = request.args.get('start_date')  # Expected format: YYYY-MM-DD
        end_date = request.args.get('end_date')      # Expected format: YYYY-MM-DD

        analyzer = MarketInsightsAnalyzer(db_path=db_config['sqlite_path'])
        insights = analyzer.get_comprehensive_insights(start_date=start_date, end_date=end_date)
        return jsonify({'success': True, 'data': insights})
    except Exception as e:
        logger.error(f"Error generating market insights: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard/export_pdf')
def export_dashboard_pdf():
    """Export dashboard as PDF with market insights"""
    try:
        # Get date parameters from query string
        start_date = request.args.get('start_date')  # Expected format: YYYY-MM-DD
        end_date = request.args.get('end_date')      # Expected format: YYYY-MM-DD

        # Get market insights with date filtering
        analyzer = MarketInsightsAnalyzer(db_path=db_config['sqlite_path'])
        insights = analyzer.get_comprehensive_insights(start_date=start_date, end_date=end_date)

        # Generate PDF
        pdf_generator = MarketInsightsPDFGenerator()
        pdf_buffer = pdf_generator.generate_pdf(insights)

        # Create filename with timestamp and date range if applicable
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if start_date and end_date:
            filename = f'TTB_Market_Insights_{start_date}_to_{end_date}_{timestamp}.pdf'
        else:
            filename = f'TTB_Market_Insights_{timestamp}.pdf'
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/brand/<brand_name>')
def brand_detail(brand_name):
    try:
        # Get brand data for the template
        brand_data = brand_db.get_brand_data(brand_name)
        if not brand_data:
            return render_template('404.html', message=f'Brand "{brand_name}" not found'), 404
        
        # Extract website information for the template
        automatic_website = None
        
        # Priority 1: Check if website data exists in the website field (JSON string)
        if brand_data.get('website'):
            try:
                import json
                if isinstance(brand_data['website'], str):
                    automatic_website = json.loads(brand_data['website'])
                else:
                    automatic_website = brand_data['website']
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Priority 2: Check enrichment_data.website (nested structure)
        if not automatic_website and brand_data.get('enrichment') and brand_data['enrichment'].get('website'):
            website_data = brand_data['enrichment']['website']
            automatic_website = {
                'url': website_data.get('url'),
                'website': website_data.get('url'),
                'domain': website_data.get('url', '').replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0] if website_data.get('url') else '',
                'confidence': website_data.get('confidence', 0.95),
                'final_confidence': website_data.get('confidence', 0.95),
                'verification_status': website_data.get('verification_status', 'verified' if website_data.get('verified') else 'unverified'),
                'manual_override': website_data.get('source') == 'manual' or website_data.get('manual_override', False),
                'source': website_data.get('source', 'manual'),
                'user_source': website_data.get('source', 'manual'),
                'approved_date': website_data.get('added_date', ''),
                'updated_date': website_data.get('updated_date', '')
            }
        
        # Priority 3: Check enrichment_data.url (direct structure)
        elif not automatic_website and brand_data.get('enrichment') and brand_data['enrichment'].get('url'):
            enrichment_data = brand_data['enrichment']
            automatic_website = {
                'url': enrichment_data.get('url'),
                'website': enrichment_data.get('url'),
                'domain': enrichment_data.get('domain', enrichment_data.get('url', '').replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0] if enrichment_data.get('url') else ''),
                'confidence': enrichment_data.get('confidence', 0.95),
                'final_confidence': enrichment_data.get('confidence', 0.95),
                'verification_status': enrichment_data.get('verification_status', 'verified' if enrichment_data.get('verified') else 'unverified'),
                'manual_override': enrichment_data.get('source') == 'manual_override' or enrichment_data.get('manual_override', False),
                'source': enrichment_data.get('source', 'manual'),
                'user_source': enrichment_data.get('user_source', enrichment_data.get('source', 'manual')),
                'approved_date': enrichment_data.get('verified_date', ''),
                'updated_date': enrichment_data.get('updated_date', '')
            }
        
        return render_template('brand_detail.html', brand_name=brand_name, brand=brand_data, automatic_website=automatic_website)
    except Exception as e:
        logger.error(f"Error loading brand detail for {brand_name}: {e}")
        return render_template('404.html', message='Brand not found'), 404

@app.route('/importer/<permit_number>')
def importer_detail(permit_number):
    """Show detailed information for a specific importer"""
    # Get the importer data from the database
    importer = brand_db.get_master_importer(permit_number)

    if not importer:
        # Try to create a basic importer object if not found
        importer = {'owner_name': 'Unknown', 'operating_name': 'Unknown', 'brands': []}

    return render_template('importer_detail.html',
                         permit_number=permit_number,
                         importer=importer)

@app.route('/producer/<permit_number>')
def producer_detail(permit_number):
    """Show detailed information for a specific producer"""
    try:
        # Get producer from either spirits or wine database
        producer = brand_db.get_spirit_producer(permit_number)
        if not producer:
            producer = brand_db.get_wine_producer(permit_number)
        
        if not producer:
            return render_template('404.html'), 404
        
        # For now, return basic info - we can enhance this later
        return render_template('producer_detail.html', producer=producer)
        
    except Exception as e:
        print(f"Error loading producer {permit_number}: {str(e)}")
        return render_template('404.html'), 404

@app.route('/upload_importers', methods=['POST'])
def upload_importers():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            if filename.endswith('.csv'):
                # Try different encodings
                encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
                df = None
                for encoding in encodings:
                    try:
                        df = pd.read_csv(filepath, encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                if df is None:
                    return jsonify({'error': 'Unable to read CSV file. Please check the file encoding.'}), 400
            else:
                df = pd.read_excel(filepath)
            
            version = get_importer_version_from_filename(filename)
            if not version:
                version = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Update master importers list (handles deduplication)
            import_stats = brand_db.update_importers_list(df)
            
            # Invalidate filter cache after data update
            invalidate_filter_cache()
            
            # Save versioned file for reference
            saved_version = save_importers_data(df, version=version, original_filename=filename)
            
            versions_data = load_importer_versions()
            
            return jsonify({
                'message': f'Importers file uploaded successfully (Version: {saved_version})',
                'version': saved_version,
                'columns': df.columns.tolist(),
                'row_count': len(df),
                'new_importers': import_stats['new_importers'],
                'updated_importers': import_stats['updated_importers'],
                'total_master_importers': import_stats['total_importers'],
                'total_versions': len(versions_data['versions']),
                'is_update': len(versions_data['versions']) > 1
            }), 200
        
        return jsonify({'error': 'Invalid file type'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload_ttb', methods=['POST'])
def upload_ttb():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            if filename.endswith('.csv'):
                ttb_df = pd.read_csv(filepath)
            else:
                ttb_df = pd.read_excel(filepath)
            
            importers_df = load_importers_data()
            
            if importers_df.empty:
                return jsonify({'error': 'No importers data found. Please upload importers file first.'}), 400
            
            matched_df = match_ttb_with_importers(ttb_df, importers_df)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            matched_filename = f'matched_{timestamp}.csv'
            matched_filepath = os.path.join(MATCHED_FOLDER, matched_filename)
            matched_df.to_csv(matched_filepath, index=False)
            
            match_summary = {
                'total_ttb_records': len(ttb_df),
                'matched_records': len(matched_df[matched_df['Match_Status'] == 'Matched']) if not matched_df.empty else 0,
                'unmatched_records': len(matched_df[matched_df['Match_Status'] == 'Unmatched']) if not matched_df.empty else len(ttb_df),
                'filename': matched_filename,
                'timestamp': timestamp,
                'importer_version': load_importer_versions()['current_version']
            }
            
            return jsonify({
                'message': 'TTB file processed successfully',
                'match_summary': match_summary,
                'preview': matched_df.head(10).to_dict('records') if not matched_df.empty else []
            }), 200
        
        return jsonify({'error': 'Invalid file type'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload_cola', methods=['POST'])
def upload_cola():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Check file type by reading first few bytes
            with open(filepath, 'rb') as f:
                file_header = f.read(4)
            
            # Detect file type issues
            if file_header.startswith(b'PK'):
                return jsonify({'error': 'File appears to be a ZIP archive or Excel file (.xlsx). Please extract the CSV file first, or upload the file as .xlsx instead of .csv'}), 400
            elif file_header.startswith(b'\x00\x00\x00\x00') or b'\x00' in file_header[:20]:
                return jsonify({'error': 'File contains binary data and may be corrupted. Please check the file format and try again.'}), 400
            
            if filename.endswith('.csv'):
                # Multiple strategies to handle problematic CSV files
                cola_df = None
                last_error = None
                
                # Strategy 1: Try different encodings with standard parsing
                encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
                for encoding in encodings:
                    try:
                        cola_df = pd.read_csv(filepath, encoding=encoding)
                        print(f"Successfully loaded CSV with {encoding} encoding: {len(cola_df)} rows")
                        break
                    except Exception as e:
                        last_error = str(e)
                        continue
                
                # Strategy 2: If normal parsing fails, try with flexible options
                if cola_df is None:
                    print(f"Standard parsing failed. Trying flexible parsing...")
                    for encoding in encodings:
                        try:
                            # Try with more flexible parsing options
                            cola_df = pd.read_csv(
                                filepath, 
                                encoding=encoding, 
                                on_bad_lines='skip',
                                sep=None,  # Auto-detect separator
                                engine='python'  # More flexible parser
                            )
                            print(f"Successfully loaded CSV with flexible parsing ({encoding}): {len(cola_df)} rows")
                            break
                        except Exception as e:
                            continue
                
                # Strategy 3: Try with different separators
                if cola_df is None:
                    print(f"Flexible parsing failed. Trying different separators...")
                    separators = [',', ';', '\t', '|']
                    for sep in separators:
                        for encoding in encodings:
                            try:
                                cola_df = pd.read_csv(
                                    filepath, 
                                    encoding=encoding, 
                                    sep=sep,
                                    on_bad_lines='skip',
                                    engine='python'
                                )
                                if len(cola_df.columns) > 1:  # Make sure we got meaningful columns
                                    print(f"Successfully loaded CSV with separator '{sep}' and {encoding}: {len(cola_df)} rows")
                                    break
                            except Exception as e:
                                continue
                        if cola_df is not None and len(cola_df.columns) > 1:
                            break
                
                # Strategy 4: Last resort - try reading as text and cleaning
                if cola_df is None:
                    try:
                        print(f"All parsing methods failed. Attempting manual cleanup...")
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                        
                        # Clean up lines - remove empty lines, fix encoding issues
                        clean_lines = []
                        for i, line in enumerate(lines):
                            line = line.strip()
                            if line and not line.startswith('#'):  # Skip empty lines and comments
                                # Fix common issues
                                line = line.replace('\x00', '')  # Remove null bytes
                                line = line.replace('""', '"')    # Fix double quotes
                                clean_lines.append(line)
                        
                        # Write cleaned file temporarily
                        temp_filepath = filepath + '.cleaned'
                        with open(temp_filepath, 'w', encoding='utf-8') as f:
                            f.write('\n'.join(clean_lines))
                        
                        # Try to read cleaned file
                        cola_df = pd.read_csv(temp_filepath, on_bad_lines='skip')
                        print(f"Successfully loaded cleaned CSV: {len(cola_df)} rows")
                        
                        # Clean up temp file
                        os.remove(temp_filepath)
                        
                    except Exception as e:
                        last_error = f"All parsing strategies failed. Final error: {e}"
                
                if cola_df is None:
                    return jsonify({'error': f'Unable to read CSV file after trying multiple parsing strategies. Last error: {last_error}. The file may be corrupted or in an unsupported format.'}), 400
                
                # Debug: Show what columns we found
                print(f"CSV columns found: {list(cola_df.columns)}")
                
                # Check for required columns and suggest alternatives
                required_columns = ['Permit No.', 'Brand Name', 'TTB ID']
                important_columns = ['Class Type', 'Class Type Desc', 'Origin Desc']  # These are important but not required
                missing_columns = []
                column_mapping = {}
                
                # Smart column mapping for common variations
                column_variations = {
                    'Permit No.': ['permit', 'permit_no', 'permit_number', 'permitno'],
                    'Brand Name': ['brand', 'brand_name', 'brandname', 'name'],
                    'TTB ID': ['ttb', 'ttb_id', 'ttbid', 'id'],
                    'Class Type': ['class/type', 'class_type', 'alcohol_class', 'type_code'],
                    'Class Type Desc': ['class_type_desc', 'alcohol_type', 'beverage_type', 'class/type desc', 'class/type_desc'],
                    'Origin Desc': ['origin', 'country', 'origin_desc', 'location']
                }
                
                # Check all columns (required + important)
                all_columns_to_check = required_columns + important_columns
                
                for col_name in all_columns_to_check:
                    if col_name not in cola_df.columns:
                        # Look for similar column names
                        variations = column_variations.get(col_name, [])
                        found_match = False
                        
                        for actual_col in cola_df.columns:
                            actual_col_lower = actual_col.lower().strip()
                            col_name_lower = col_name.lower().strip()
                            
                            # Check for exact match (case insensitive)
                            if actual_col_lower == col_name_lower:
                                column_mapping[actual_col] = col_name
                                print(f"Exact match mapping '{actual_col}' to '{col_name}'")
                                found_match = True
                                break
                                
                            # Check variations
                            for variation in variations:
                                if variation in actual_col_lower:
                                    column_mapping[actual_col] = col_name
                                    print(f"Variation mapping '{actual_col}' to '{col_name}' (matched: {variation})")
                                    found_match = True
                                    break
                            if found_match:
                                break
                        
                        # Only add to missing if it's a required column and no mapping found
                        if not found_match and col_name in required_columns:
                            missing_columns.append(col_name)
                
                # Apply column mapping
                if column_mapping:
                    cola_df = cola_df.rename(columns=column_mapping)
                
                # Check if we still have missing required columns
                if missing_columns:
                    available_cols = list(cola_df.columns)
                    return jsonify({
                        'error': f'Missing required columns: {missing_columns}. Available columns: {available_cols}. Please ensure your CSV has columns named "Permit No.", "Brand Name", and "TTB ID".'
                    }), 400
                
                # Check for missing important columns (warn but don't block)
                missing_important = [col for col in important_columns if col not in cola_df.columns]
                if missing_important:
                    print(f"⚠️ Warning: Missing important columns: {missing_important}")
                    print("   - Without 'Class Type Desc': Alcohol types won't be captured")
                    print("   - Without 'Origin Desc': Countries/origins won't be captured")
                    print("   - Data will still be processed but some information may be missing")
            else:
                cola_df = pd.read_excel(filepath)
            
            importers_df = load_importers_data()
            
            # Allow COLA upload even without importers (they can be matched later)
            if importers_df.empty:
                print("No importers data found - processing COLA file without importer matching")
                importers_df = pd.DataFrame()  # Empty dataframe for processing
            
            # Get brands state before upload for learning
            brands_before = brand_db.db.get('brands', {}).copy()
            
            # Process COLA file and update brand database
            upload_record = brand_db.process_cola_file(cola_df, importers_df, filename)
            
            # Invalidate filter cache after data update
            invalidate_filter_cache()
            
            # Get brands state after upload
            brands_after = brand_db.db.get('brands', {})
            
            # Trigger agentic learning from upload
            learning_event = None
            try:
                from brand_consolidation.core import BrandConsolidator
                consolidator = BrandConsolidator(brand_db)
                learning_event = consolidator.learn_from_upload(brands_before, brands_after, filename)
                logger.info(f"🧠 Agentic learning triggered for upload: {filename}")
            except Exception as e:
                logger.error(f"Agentic learning failed for upload {filename}: {e}")
            
            # Get updated statistics
            stats = brand_db.get_statistics()
            
            response_data = {
                'message': 'COLA file processed successfully',
                'upload_summary': upload_record,
                'database_stats': stats
            }
            
            return jsonify(response_data), 200
        
        return jsonify({'error': 'Invalid file type'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_matched_files', methods=['GET'])
def get_matched_files():
    try:
        # Return upload history instead of matched files
        upload_history = brand_db.db.get('upload_history', [])
        
        # Convert to a format similar to the old matched files
        files = []
        for i, upload in enumerate(reversed(upload_history[-10:])):  # Last 10 uploads
            files.append({
                'filename': upload.get('filename', f'upload_{i+1}.csv'),
                'rows': upload.get('total_records', 0),
                'matched': upload.get('matched_records', 0),
                'new_brands': upload.get('new_brands', 0),
                'new_skus': upload.get('new_skus', 0),
                'created': upload.get('upload_date', ''),
                'type': 'COLA Upload'
            })
        
        return jsonify({'files': files, 'upload_history': True}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download_matched/<filename>', methods=['GET'])
def download_matched(filename):
    try:
        filepath = os.path.join(MATCHED_FOLDER, secure_filename(filename))
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True, download_name=filename)
        return jsonify({'error': 'File not found'}), 404
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_importers_status', methods=['GET'])
def get_importers_status():
    try:
        importers_df = load_importers_data()
        versions_data = load_importer_versions()
        
        if not importers_df.empty:
            return jsonify({
                'has_data': True,
                'row_count': len(importers_df),
                'columns': importers_df.columns.tolist(),
                'current_version': versions_data['current_version'],
                'total_versions': len(versions_data['versions']),
                'versions': versions_data['versions']
            }), 200
        return jsonify({'has_data': False}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_importer_versions', methods=['GET'])
def get_importer_versions():
    try:
        versions_data = load_importer_versions()
        return jsonify(versions_data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/set_importer_version/<version>', methods=['POST'])
def set_importer_version(version):
    try:
        versions_data = load_importer_versions()
        
        version_exists = any(v['version'] == version for v in versions_data['versions'])
        if not version_exists:
            return jsonify({'error': 'Version not found'}), 404
        
        versions_data['current_version'] = version
        save_importer_versions(versions_data)
        
        return jsonify({
            'message': f'Successfully switched to version {version}',
            'current_version': version
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_filter_counts', methods=['GET'])
def get_filter_counts():
    """Get counts for all filter options - cached for performance"""
    try:
        counts = get_cached_filter_counts()
        return jsonify(counts), 200
    except Exception as e:
        logger.error(f"Error getting filter counts: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_filter_data', methods=['GET'])
def get_filter_data():
    """Legacy alias for get_filter_counts for frontend compatibility"""
    return get_filter_counts()

@app.route('/get_all_brands', methods=['GET'])
def get_all_brands():
    """Optimized endpoint for getting filtered brands with database-level filtering"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 12))
        search = request.args.get('search', '').strip()
        sort = request.args.get('sort', 'name')
        direction = request.args.get('direction', 'asc')
        
        # Get filter parameters
        filters = {
            'importers': request.args.getlist('importers'),
            'alcoholTypes': request.args.getlist('alcoholTypes'),
            'producers': request.args.getlist('producers'),
            'countries': request.args.getlist('countries'),
            'websiteStatus': request.args.getlist('websiteStatus')
        }
        
        # Use optimized database method
        result = brand_db.get_filtered_brands(
            search=search,
            filters=filters,
            page=page,
            per_page=per_page,
            sort=sort,
            direction=direction
        )
        
        # Format brands for frontend compatibility
        formatted_brands = []
        for brand in result['brands']:
            formatted_brands.append({
                'brand_name': brand['brand_name'],
                'countries': brand['countries'],
                'class_types': brand['class_types'],
                'importers': brand['importers'],
                'producers': brand['producers'],
                'brand_permits': brand['brand_permits'],
                'sku_count': brand['sku_count'],
                'enrichment_data': brand['enrichment'],
                'website': brand['website']
            })
        
        # Calculate total SKUs from the brands
        total_skus = sum(brand.get('sku_count', 0) for brand in result['brands'])
        
        return jsonify({
            'brands': formatted_brands,
            'pagination': result['pagination'],
            'total_skus': total_skus
        })
        
    except Exception as e:
        logger.error(f"Error in get_all_brands: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_brand/<brand_name>', methods=['GET'])
def get_brand(brand_name):
    try:
        brand_data = brand_db.get_brand_data(brand_name)
        if brand_data:
            return jsonify(brand_data), 200
        return jsonify({'error': 'Brand not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_all_importers', methods=['GET'])
def get_all_importers():
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        search = request.args.get('search', '').strip()
        
        all_importers = brand_db.get_all_importers()
        
        # Filter importers if search query provided
        if search:
            all_importers = [i for i in all_importers 
                           if search.lower() in i['owner_name'].lower() 
                           or search.lower() in i['permit_number'].lower()]
        
        # Pagination
        total = len(all_importers)
        start = (page - 1) * per_page
        end = start + per_page
        importers = all_importers[start:end]
        
        return jsonify({
            'importers': importers,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page,
                'has_prev': page > 1,
                'has_next': end < total
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_importer/<permit_number>', methods=['GET'])
def get_importer(permit_number):
    try:
        importer_data = brand_db.get_importer_data(permit_number)
        if importer_data:
            return jsonify(importer_data), 200
        return jsonify({'error': 'Importer not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search_brands', methods=['GET'])
def search_brands():
    try:
        query = request.args.get('q', '')
        results = brand_db.search_brands(query)
        return jsonify({'results': results}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_database_stats', methods=['GET'])
def get_database_stats():
    """Get database statistics with caching"""
    try:
        stats = get_cached_statistics()
        return success_response(stats)
    except Exception as e:
        return error_response(e)

@app.route('/check_brand_cache', methods=['POST'])
def check_brand_cache():
    """Check if brand has cached enrichment data"""
    try:
        data = request.get_json()
        brand_name = data.get('brand_name')
        
        if not brand_name:
            return jsonify({'error': 'Brand name required'}), 400
        
        # Check if brand has website data
        website_data = brand_db.get_brand_website(brand_name)
        
        if website_data:
            return jsonify({
                'has_cache': True,
                'website': website_data
            }), 200
        else:
            return jsonify({'has_cache': False}), 200
            
    except Exception as e:
        logger.error(f"Error checking brand cache: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/manual_url_training', methods=['POST'])
def manual_url_training():
    """Add website manually to a brand for training"""
    try:
        data = request.get_json()
        brand_name = data.get('brand_name')
        website_url = data.get('website_url')
        confidence = float(data.get('confidence', 0.8))
        source = data.get('source', 'manual')
        notes = data.get('notes', '')
        
        if not brand_name or not website_url:
            return jsonify({'error': 'Brand name and website URL required'}), 400
        
        # Create website data structure
        website_data = {
            'url': website_url,
            'confidence': confidence,
            'source': source,
            'notes': notes,
            'verified': True,
            'added_date': datetime.now().isoformat(),
            'verification_status': 'verified'
        }
        
        # Update brand with website data
        success = brand_db.update_brand_website(brand_name, website_data)
        
        if success:
            # Invalidate filter cache since data changed
            invalidate_filter_cache()
            
            return jsonify({
                'success': True,
                'message': 'Website added successfully',
                'website': website_data
            }), 200
        else:
            return jsonify({'error': 'Failed to add website to brand'}), 500
            
    except Exception as e:
        logger.error(f"Error in manual URL training: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_apollo_status', methods=['GET'])
def get_apollo_status():
    """Get Apollo API status"""
    try:
        apollo_key = os.getenv('APOLLO_API_KEY')
        return jsonify({
            'has_key': bool(apollo_key),
            'status': 'enabled' if apollo_key else 'disabled'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/database_version', methods=['GET'])
def get_database_version():
    """
    Get current database version for UI cache-busting
    UI can poll this endpoint to detect when data has changed
    """
    global db_version
    return jsonify({
        'version': db_version['version'],
        'last_modified': db_version['last_modified'],
        'success': True
    }), 200, {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }

@app.route('/api/cache_status', methods=['GET'])
def get_cache_status():
    """Get cache status for debugging"""
    global filter_cache, brand_list_cache, all_brands_cache, stats_cache, db_version
    return jsonify({
        'db_version': db_version,
        'caches': {
            'filter': {
                'cached': filter_cache['counts'] is not None,
                'timestamp': filter_cache['timestamp'],
                'db_version': filter_cache['db_version'],
                'age_seconds': int(time.time() - filter_cache['timestamp']) if filter_cache['timestamp'] > 0 else None
            },
            'brand_list': {
                'cached': brand_list_cache['data'] is not None,
                'timestamp': brand_list_cache['timestamp'],
                'db_version': brand_list_cache['db_version'],
                'age_seconds': int(time.time() - brand_list_cache['timestamp']) if brand_list_cache['timestamp'] > 0 else None
            },
            'all_brands': {
                'cached': all_brands_cache['data'] is not None,
                'count': len(all_brands_cache['data']) if all_brands_cache['data'] else 0,
                'timestamp': all_brands_cache['timestamp'],
                'db_version': all_brands_cache['db_version'],
                'age_seconds': int(time.time() - all_brands_cache['timestamp']) if all_brands_cache['timestamp'] > 0 else None
            },
            'stats': {
                'cached': stats_cache['data'] is not None,
                'timestamp': stats_cache['timestamp'],
                'db_version': stats_cache['db_version'],
                'age_seconds': int(time.time() - stats_cache['timestamp']) if stats_cache['timestamp'] > 0 else None
            }
        }
    }), 200

@app.route('/debug_importers', methods=['GET'])
def debug_importers():
    """Debug endpoint for importer analysis"""
    try:
        stats = brand_db.get_statistics()
        return jsonify({
            'total_importers': stats.get('total_importers', 0),
            'active_importers': stats.get('active_importers', 0),
            'brands_with_importers': len([b for b in get_cached_all_brands() if b.get('importers')])
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_importer_metrics', methods=['GET'])
def get_importer_metrics():
    """Get real-time importer metrics with accurate brand counts"""
    try:
        # Get all importers
        all_importers = brand_db.get_all_importers()
        
        # Get all brands to count which belong to each importer (use cache)
        all_brands = get_cached_all_brands()
        
        # Count brands for each importer
        importer_metrics = {}
        
        for brand in all_brands:
            importers = brand.get('importers', [])
            for importer in importers:
                if isinstance(importer, dict):
                    permit_number = importer.get('permit_number', '')
                    if permit_number and '-I-' in permit_number:  # Real importer permits only
                        if permit_number not in importer_metrics:
                            importer_metrics[permit_number] = {
                                'permit_number': permit_number,
                                'owner_name': importer.get('owner_name', ''),
                                'operating_name': importer.get('operating_name', ''),
                                'brand_count': 0,
                                'brands': []
                            }
                        importer_metrics[permit_number]['brand_count'] += 1
                        importer_metrics[permit_number]['brands'].append(brand['brand_name'])
        
        # Convert to list and sort by brand count
        metrics_list = list(importer_metrics.values())
        metrics_list.sort(key=lambda x: x['brand_count'], reverse=True)
        
        return jsonify({
            'importers': metrics_list,
            'total_importers': len(all_importers),
            'active_importers': len(metrics_list)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting importer metrics: {e}")
        return jsonify({'error': str(e)}), 500

# Brand Enrichment Endpoints
@app.route('/enrichment/enrich_brand', methods=['POST'])
def enrich_brand():
    """Enrich a brand with website and contact information"""
    if not ENRICHMENT_AVAILABLE or not enrichment_system:
        return jsonify({'error': 'Enrichment system not available'}), 503
        
    try:
        data = request.get_json()
        brand_name = data.get('brand_name')
        class_type = data.get('class_type', '')
        skip_cache = data.get('skip_cache', False)
        
        if not brand_name:
            return jsonify({'error': 'Brand name is required'}), 400
            
        logger.info(f"Starting enrichment for brand: {brand_name}")
        
        # Use website-only enrichment for faster results, but include contact discovery
        # if Apollo API key is available
        apollo_key = os.getenv('APOLLO_API_KEY')
        if apollo_key:
            # Full enrichment with contact discovery
            enrichment_result = enrichment_system.enrich_brand_full_pipeline(
                brand_name, class_type, skip_cache
            )
        else:
            # Website-only enrichment
            enrichment_result = enrichment_system.enrich_brand_website_only(
                brand_name, class_type, skip_cache
            )
        
        if enrichment_result and enrichment_result.get('website'):
            # Save enrichment data to database
            website_data = enrichment_result['website']
            success = brand_db.update_brand_enrichment(brand_name, {
                'website': website_data,
                'enrichment_data': enrichment_result,
                'last_enriched': datetime.now().isoformat()
            })
            
            if success:
                # Invalidate filter cache since data changed
                invalidate_filter_cache()
                
                return jsonify({
                    'success': True,
                    'enrichment_data': enrichment_result,
                    'message': f'Successfully enriched {brand_name}'
                }), 200
            else:
                return jsonify({'error': 'Failed to save enrichment data'}), 500
        else:
            return jsonify({
                'success': False,
                'error': 'No enrichment data found',
                'enrichment_data': enrichment_result
            }), 200
            
    except Exception as e:
        logger.error(f"Error enriching brand {brand_name}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/enrichment/review/<brand_name>')
def enrichment_review(brand_name):
    """Review enrichment results for a brand"""
    try:
        # Get brand data
        brand = brand_db.get_brand_data(brand_name)
        if not brand:
            return render_template('404.html'), 404
            
        # Get enrichment data
        enrichment_data = brand.get('enrichment_data', {})
        website_data = brand.get('website', {})
        
        # Parse website data if it's a JSON string
        if isinstance(website_data, str):
            try:
                website_data = json.loads(website_data)
            except:
                website_data = {}
                
        # Parse enrichment data if it's a JSON string
        if isinstance(enrichment_data, str):
            try:
                enrichment_data = json.loads(enrichment_data)
            except:
                enrichment_data = {}
        
        return render_template('enrichment_review.html',
                             brand=brand,
                             brand_name=brand_name,
                             website_data=website_data,
                             enrichment_data=enrichment_data,
                             has_apollo=bool(os.getenv('APOLLO_API_KEY')))
                             
    except Exception as e:
        logger.error(f"Error loading enrichment review for {brand_name}: {e}")
        return render_template('404.html'), 404

@app.route('/enrichment/status', methods=['GET'])
def enrichment_status():
    """Check enrichment system status"""
    try:
        apollo_key = os.getenv('APOLLO_API_KEY')
        return jsonify({
            'available': ENRICHMENT_AVAILABLE and enrichment_system is not None,
            'has_apollo': bool(apollo_key),
            'environment': 'production',  # Always use production mode
            'features': {
                'website_discovery': True,
                'founder_discovery': bool(apollo_key),
                'contact_discovery': bool(apollo_key),
                'linkedin_discovery': bool(apollo_key)
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/enrichment/batch_rescore', methods=['POST'])
def batch_rescore_websites():
    """Batch re-score all existing website matches with current learning data"""
    try:
        if not ENRICHMENT_AVAILABLE or not enrichment_system:
            return jsonify({'error': 'Enrichment system not available'}), 503
        
        from enrichment.learning_system import AgenticLearningSystem
        
        # Initialize learning system
        learning_system = AgenticLearningSystem()
        
        # Get all brands with websites
        cursor = brand_db.conn.execute('''
            SELECT brand_name, enrichment_data, class_types
            FROM brands 
            WHERE enrichment_data IS NOT NULL 
            AND (
                json_extract(enrichment_data, '$.url') IS NOT NULL 
                OR json_extract(enrichment_data, '$.website.url') IS NOT NULL
            )
        ''')
        
        updated_count = 0
        total_count = 0
        updates = []
        
        for row in cursor:
            total_count += 1
            brand_name = row['brand_name']
            enrichment_data = json.loads(row['enrichment_data'])
            class_types = json.loads(row['class_types'] or '[]')
            
            # Extract website info from various formats
            website_info = None
            if 'website' in enrichment_data and isinstance(enrichment_data['website'], dict):
                website_info = enrichment_data['website']
            elif 'url' in enrichment_data:
                # Handle direct URL format
                website_info = {
                    'url': enrichment_data['url'],
                    'confidence': enrichment_data.get('confidence', 0.5),
                    'title': enrichment_data.get('title', ''),
                    'snippet': enrichment_data.get('snippet', '')
                }
            
            if website_info and 'url' in website_info:
                url = website_info['url']
                old_confidence = website_info.get('confidence', 0.5)
                
                # Extract domain from URL
                from urllib.parse import urlparse
                parsed_url = urlparse(url)
                domain = parsed_url.netloc.replace('www.', '')
                
                # Check for category mismatches (e.g., vodka brand with wine domain)
                category_penalty = 0
                if class_types:
                    # Check for spirits/vodka brands matching wine domains
                    is_spirits = any('VODKA' in ct.upper() or 'WHISKY' in ct.upper() or 'RUM' in ct.upper() 
                                    or 'GIN' in ct.upper() or 'TEQUILA' in ct.upper() for ct in class_types)
                    is_wine_domain = 'wine' in domain.lower() or 'vino' in domain.lower() or 'vineyard' in domain.lower()
                    
                    if is_spirits and is_wine_domain:
                        category_penalty = 0.3  # Significant penalty for category mismatch
                        logger.info(f"Category mismatch detected: {brand_name} (spirits) → {domain} (wine domain)")
                    
                    # Check for wine brands matching spirits domains
                    is_wine = any('WINE' in ct.upper() for ct in class_types)
                    is_spirits_domain = any(spirit in domain.lower() for spirit in ['vodka', 'whisky', 'whiskey', 'rum', 'gin', 'tequila', 'spirits', 'distill'])
                    
                    if is_wine and is_spirits_domain:
                        category_penalty = 0.3
                        logger.info(f"Category mismatch detected: {brand_name} (wine) → {domain} (spirits domain)")
                
                # Get enhanced confidence using learning patterns
                features = {
                    'domain': domain,
                    'title': website_info.get('title', ''),
                    'snippet': website_info.get('snippet', ''),
                    'source': website_info.get('source', 'unknown'),
                    'class_types': class_types
                }
                
                new_confidence = learning_system.get_enhanced_confidence(
                    brand_name, 
                    domain, 
                    old_confidence, 
                    features
                )
                
                # Apply category penalty
                new_confidence = max(0.1, new_confidence - category_penalty)
                
                # Only update if confidence changed significantly (>5% change)
                if abs(new_confidence - old_confidence) > 0.05:
                    # Update the enrichment data with new confidence
                    if 'website' in enrichment_data and isinstance(enrichment_data['website'], dict):
                        enrichment_data['website']['confidence'] = new_confidence
                        enrichment_data['website']['confidence_updated'] = datetime.now().isoformat()
                        enrichment_data['website']['original_confidence'] = old_confidence
                        if category_penalty > 0:
                            enrichment_data['website']['category_mismatch'] = True
                            enrichment_data['website']['needs_review'] = True
                    else:
                        enrichment_data['confidence'] = new_confidence
                        enrichment_data['confidence_updated'] = datetime.now().isoformat()
                        enrichment_data['original_confidence'] = old_confidence
                        if category_penalty > 0:
                            enrichment_data['category_mismatch'] = True
                            enrichment_data['needs_review'] = True
                    
                    # Update database
                    brand_db.conn.execute('''
                        UPDATE brands SET enrichment_data = ? WHERE brand_name = ?
                    ''', (json.dumps(enrichment_data), brand_name))
                    
                    updated_count += 1
                    updates.append({
                        'brand_name': brand_name,
                        'domain': domain,
                        'old_confidence': round(old_confidence, 2),
                        'new_confidence': round(new_confidence, 2),
                        'change': round(new_confidence - old_confidence, 2),
                        'category_mismatch': category_penalty > 0,
                        'class_types': class_types[:3] if class_types else []  # First 3 types for display
                    })
        
        brand_db.conn.commit()
        
        # Reload the in-memory database
        brand_db.db = brand_db._load_as_dict()
        
        # Sort updates by change magnitude (biggest changes first)
        updates.sort(key=lambda x: abs(x['change']), reverse=True)
        
        return jsonify({
            'success': True,
            'total_websites': total_count,
            'updated': updated_count,
            'updates': updates[:50],  # Return first 50 updates for review
            'message': f'Successfully re-scored {updated_count} out of {total_count} websites'
        }), 200
        
    except Exception as e:
        logger.error(f"Error in batch re-scoring: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/learning_insights')
def learning_insights_page():
    """Display the learning insights page or return JSON data"""
    
    # Check if JSON format requested
    if request.args.get('format') == 'json':
        try:
            from enrichment.learning_system import AgenticLearningSystem
            
            learning_system = AgenticLearningSystem()
            
            # Calculate insights
            insights = {
                'success': True,
                'insights': {
                    'total_learning_events': len(learning_system.learning_events),
                    'total_patterns': len(learning_system.domain_patterns),
                    'domain_patterns': len(learning_system.domain_patterns),
                    'relevance_patterns': len(learning_system.relevance_patterns),
                    'strategy_patterns': len(learning_system.strategy_patterns),
                    'verified_count': sum(1 for e in learning_system.learning_events if e.user_action == 'verified'),
                    'rejected_count': sum(1 for e in learning_system.learning_events if e.user_action == 'rejected'),
                    'flagged_count': sum(1 for e in learning_system.learning_events if e.user_action == 'flagged'),
                    'success_rate': 0,
                    'confidence_accuracy': 0,
                    'average_confidence': 0,
                    'learning_rate': 0,
                    'brands_by_type': {
                        'spirits': 0,
                        'wine': 0,
                        'beer': 0
                    },
                    'industry_patterns': 0
                }
            }
            
            # Calculate success rate
            if learning_system.learning_events:
                verified = sum(1 for e in learning_system.learning_events if e.user_action == 'verified')
                total = len(learning_system.learning_events)
                insights['insights']['success_rate'] = (verified / total) * 100 if total > 0 else 0
                
                # Average confidence
                confidences = [e.confidence_predicted for e in learning_system.learning_events if e.confidence_predicted]
                if confidences:
                    insights['insights']['average_confidence'] = sum(confidences) / len(confidences)
            
            return jsonify(insights), 200
            
        except Exception as e:
            logger.error(f"Error loading learning insights: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # Return HTML page
    return render_template('learning_insights.html')

@app.route('/learning_insights/export', methods=['GET'])
def export_learning_data():
    """Export all learning data to CSV files"""
    try:
        from enrichment.learning_system import AgenticLearningSystem
        import csv
        from io import StringIO
        import zipfile
        from io import BytesIO
        
        learning_system = AgenticLearningSystem()
        
        # Create a zip file in memory
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            
            # 1. Export Learning Events
            events_csv = StringIO()
            events_writer = csv.writer(events_csv)
            events_writer.writerow([
                'Timestamp', 'Event Type', 'Brand Name', 'Domain', 
                'Confidence Predicted', 'User Action', 'Feature Count'
            ])
            
            for event in learning_system.learning_events:
                events_writer.writerow([
                    event.timestamp,
                    event.event_type,
                    event.brand_name,
                    event.domain,
                    round(event.confidence_predicted, 3) if event.confidence_predicted else 0,
                    event.user_action,
                    len(event.features) if event.features else 0
                ])
            
            zip_file.writestr('learning_events.csv', events_csv.getvalue())
            
            # 2. Export Domain Patterns
            patterns_csv = StringIO()
            patterns_writer = csv.writer(patterns_csv)
            patterns_writer.writerow([
                'Pattern', 'Pattern Type', 'Success Rate', 
                'Confidence Boost', 'Sample Count', 'Last Updated'
            ])
            
            for pattern_key, pattern in learning_system.domain_patterns.items():
                patterns_writer.writerow([
                    pattern.pattern,
                    pattern.pattern_type,
                    round(pattern.success_rate, 3),
                    round(pattern.confidence_boost, 3),
                    pattern.sample_count,
                    pattern.last_updated
                ])
            
            zip_file.writestr('domain_patterns.csv', patterns_csv.getvalue())
            
            # 3. Export Relevance Patterns
            relevance_csv = StringIO()
            relevance_writer = csv.writer(relevance_csv)
            relevance_writer.writerow([
                'Term', 'Term Type', 'Success Rate', 
                'Sample Count', 'Contexts', 'Brand Examples', 'Last Updated'
            ])
            
            for pattern_key, pattern in learning_system.relevance_patterns.items():
                relevance_writer.writerow([
                    pattern.term,
                    pattern.term_type,
                    round(pattern.success_rate, 3),
                    pattern.sample_count,
                    ', '.join(pattern.contexts[:5]) if pattern.contexts else '',
                    ', '.join(pattern.brand_examples[:5]) if pattern.brand_examples else '',
                    pattern.last_updated
                ])
            
            zip_file.writestr('relevance_patterns.csv', relevance_csv.getvalue())
            
            # 4. Export Strategy Patterns
            strategy_csv = StringIO()
            strategy_writer = csv.writer(strategy_csv)
            strategy_writer.writerow([
                'Strategy Name', 'Success Rate', 'Average Confidence',
                'Sample Count', 'Example Brands'
            ])
            
            for strategy_key, strategy in learning_system.strategy_patterns.items():
                strategy_writer.writerow([
                    strategy.strategy_name,
                    round(strategy.success_rate, 3),
                    round(strategy.average_confidence, 3),
                    strategy.sample_count,
                    ', '.join(strategy.examples[:5]) if strategy.examples else ''
                ])
            
            zip_file.writestr('strategy_patterns.csv', strategy_csv.getvalue())
            
            # 5. Export Summary Statistics
            summary_csv = StringIO()
            summary_writer = csv.writer(summary_csv)
            summary_writer.writerow(['Metric', 'Value'])
            
            # Calculate statistics
            total_events = len(learning_system.learning_events)
            verified_count = sum(1 for e in learning_system.learning_events if e.user_action == 'verified')
            rejected_count = sum(1 for e in learning_system.learning_events if e.user_action == 'rejected')
            flagged_count = sum(1 for e in learning_system.learning_events if e.user_action == 'flagged')
            
            summary_writer.writerow(['Total Learning Events', total_events])
            summary_writer.writerow(['Verified Count', verified_count])
            summary_writer.writerow(['Rejected Count', rejected_count])
            summary_writer.writerow(['Flagged Count', flagged_count])
            summary_writer.writerow(['Domain Patterns', len(learning_system.domain_patterns)])
            summary_writer.writerow(['Relevance Patterns', len(learning_system.relevance_patterns)])
            summary_writer.writerow(['Strategy Patterns', len(learning_system.strategy_patterns)])
            summary_writer.writerow(['Knowledge Base Entries', len(learning_system.knowledge_base)])
            
            if total_events > 0:
                success_rate = (verified_count / total_events) * 100
                summary_writer.writerow(['Success Rate (%)', round(success_rate, 2)])
                
                confidences = [e.confidence_predicted for e in learning_system.learning_events if e.confidence_predicted]
                if confidences:
                    avg_confidence = sum(confidences) / len(confidences)
                    summary_writer.writerow(['Average Confidence', round(avg_confidence, 3)])
            
            summary_writer.writerow(['Export Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
            
            zip_file.writestr('summary_statistics.csv', summary_csv.getvalue())
        
        # Prepare the response
        zip_buffer.seek(0)
        
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'learning_data_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
        )
        
    except Exception as e:
        logger.error(f"Error exporting learning data: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/enrichment/rescore_stats', methods=['GET'])
def rescore_stats():
    """Get statistics about potential re-scoring impact"""
    try:
        if not ENRICHMENT_AVAILABLE or not enrichment_system:
            return jsonify({'error': 'Enrichment system not available'}), 503
        
        from enrichment.learning_system import AgenticLearningSystem
        
        # Initialize learning system
        learning_system = AgenticLearningSystem()
        
        # Get counts
        cursor = brand_db.conn.execute('''
            SELECT COUNT(*) as total_websites
            FROM brands 
            WHERE enrichment_data IS NOT NULL 
            AND (
                json_extract(enrichment_data, '$.url') IS NOT NULL 
                OR json_extract(enrichment_data, '$.website.url') IS NOT NULL
            )
        ''')
        total_websites = cursor.fetchone()[0]
        
        # Count potential category mismatches
        cursor = brand_db.conn.execute('''
            SELECT brand_name, enrichment_data, class_types
            FROM brands 
            WHERE enrichment_data IS NOT NULL 
            AND (
                json_extract(enrichment_data, '$.url') IS NOT NULL 
                OR json_extract(enrichment_data, '$.website.url') IS NOT NULL
            )
            AND class_types IS NOT NULL
        ''')
        
        category_mismatches = 0
        for row in cursor:
            enrichment_data = json.loads(row['enrichment_data'])
            class_types = json.loads(row['class_types'] or '[]')
            
            # Get URL
            url = None
            if 'website' in enrichment_data and isinstance(enrichment_data['website'], dict):
                url = enrichment_data['website'].get('url')
            elif 'url' in enrichment_data:
                url = enrichment_data['url']
            
            if url and class_types:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc.lower()
                
                # Check for mismatches
                is_spirits = any('VODKA' in ct.upper() or 'WHISKY' in ct.upper() or 'RUM' in ct.upper() 
                                or 'GIN' in ct.upper() or 'TEQUILA' in ct.upper() for ct in class_types)
                is_wine_domain = 'wine' in domain or 'vino' in domain or 'vineyard' in domain
                
                is_wine = any('WINE' in ct.upper() for ct in class_types)
                is_spirits_domain = any(spirit in domain for spirit in ['vodka', 'whisky', 'whiskey', 'rum', 'gin', 'tequila', 'spirits', 'distill'])
                
                if (is_spirits and is_wine_domain) or (is_wine and is_spirits_domain):
                    category_mismatches += 1
        
        # Get learning statistics
        stats = {
            'total_websites': total_websites,
            'potential_category_mismatches': category_mismatches,
            'learning_events': len(learning_system.learning_events),
            'domain_patterns': len(learning_system.domain_patterns),
            'relevance_patterns': len(learning_system.relevance_patterns),
            'strategy_patterns': len(learning_system.strategy_patterns),
            'knowledge_base_entries': len(learning_system.knowledge_base)
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error getting rescore stats: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# ==================== MISSING CRITICAL ENDPOINTS ====================
# Website Verification Endpoints

@app.route('/verify_website', methods=['POST'])
def verify_website():
    """Verify a brand's website and trigger learning system"""
    try:
        data = request.get_json()
        brand_name = data.get('brand_name')
        verified = data.get('verified', True)
        
        if not brand_name:
            return jsonify({'error': 'Brand name required'}), 400
        
        # Use existing verify method that includes learning integration
        success = brand_db.verify_brand_website(brand_name, verified)
        
        if success:
            # Invalidate filter cache since data changed
            invalidate_filter_cache()
            
            action = 'verified' if verified else 'rejected'
            return jsonify({
                'success': True,
                'message': f'Website {action} successfully',
                'brand_name': brand_name,
                'action': action
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'No website data found for brand'
            }), 404
            
    except Exception as e:
        logger.error(f"Error verifying website for {data.get('brand_name')}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/reject_website', methods=['POST'])
def reject_website():
    """Reject a brand's website (shortcut for verify with verified=False)"""
    try:
        data = request.get_json()
        brand_name = data.get('brand_name')
        
        if not brand_name:
            return jsonify({'error': 'Brand name required'}), 400
        
        # Call verify with verified=False
        success = brand_db.verify_brand_website(brand_name, verified=False)
        
        if success:
            invalidate_filter_cache()
            
            return jsonify({
                'success': True,
                'message': 'Website rejected successfully',
                'brand_name': brand_name
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'No website data found for brand'
            }), 404
            
    except Exception as e:
        logger.error(f"Error rejecting website for {data.get('brand_name')}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/flag_website', methods=['POST'])
def flag_website():
    """Flag a brand's website for review"""
    try:
        data = request.get_json()
        brand_name = data.get('brand_name')
        reason = data.get('reason', 'Flagged for manual review')
        
        if not brand_name:
            return jsonify({'error': 'Brand name required'}), 400
        
        success = brand_db.flag_brand_website(brand_name, reason)
        
        if success:
            invalidate_filter_cache()
            
            return jsonify({
                'success': True,
                'message': 'Website flagged for review',
                'brand_name': brand_name,
                'reason': reason
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'No website data found for brand'
            }), 404
            
    except Exception as e:
        logger.error(f"Error flagging website for {data.get('brand_name')}: {e}")
        return jsonify({'error': str(e)}), 500

# Apollo Enrichment Endpoints

@app.route('/apollo/enrich_brand', methods=['POST'])
def apollo_enrich_brand():
    """Start Apollo enrichment for a brand"""
    try:
        from enrichment.apollo_enrichment import ApolloEnrichmentSystem

        brand_name = request.json.get('brand_name')
        if not brand_name:
            return jsonify({'error': 'Brand name required'}), 400

        # Get brand data
        brand = brand_db.get_brand_data(brand_name)
        if not brand:
            return jsonify({'error': 'Brand not found'}), 404

        # Initialize Apollo system
        apollo = ApolloEnrichmentSystem()

        # Run enrichment
        result = apollo.enrich_brand(brand_name, brand)

        # Handle different result statuses
        if result['status'] == 'auto_completed':
            # Brand with website - auto-complete
            brand_db.update_brand_apollo_data(brand_name, {
                'apollo_data': {
                    'company': result['company'],
                    'contacts': result['contacts'][:10],  # Store top 10
                    'verification': {
                        'method': 'domain_match',
                        'confidence': 100,
                        'verified_date': result['enriched_date'],
                        'auto_verified': True
                    }
                },
                'apollo_status': 'verified',
                'apollo_company_id': result['company']['id']
            })

            return jsonify({
                'success': True,
                'status': 'auto_completed',
                'message': 'Brand enriched successfully via domain match',
                'company': result['company'],
                'top_contacts': result['contacts'][:2]
            })

        elif result['status'] == 'high_confidence_match':
            # 100% match but no website - needs approval
            return jsonify({
                'success': True,
                'status': 'needs_approval',
                'confidence': 100,
                'company': result['company'],
                'contacts_preview': result['contacts'][:2],
                'match_factors': result['match_factors'],
                'auto_complete_ready': True
            })

        elif result['status'] == 'recommendations':
            # Multiple possibilities - show top 5
            return jsonify({
                'success': True,
                'status': 'needs_selection',
                'recommendations': result['recommendations'],
                'message': result.get('message')
            })

        elif result['status'] == 'not_found':
            # No matches - flag for manual entry
            brand_db.update_brand_apollo_data(brand_name, {
                'apollo_status': 'not_found',
                'apollo_search_date': datetime.now().isoformat()
            })

            return jsonify({
                'success': False,
                'status': 'not_found',
                'message': result.get('message', 'No matches found in Apollo'),
                'requires_manual': True
            })

        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Unknown error')
            }), 500

    except Exception as e:
        logger.error(f"Apollo enrichment error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/apollo/approve_match', methods=['POST'])
def apollo_approve_match():
    """Approve an Apollo match for a brand"""
    try:
        from enrichment.apollo_enrichment import ApolloEnrichmentSystem

        brand_name = request.json.get('brand_name')
        company_id = request.json.get('company_id')
        company_data = request.json.get('company_data')

        if not all([brand_name, company_id, company_data]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Get full contact list for approved company
        apollo = ApolloEnrichmentSystem()
        contacts = apollo._get_company_contacts(company_id)
        ranked_contacts = apollo._rank_contacts(contacts)

        # Update database with approved match
        brand_db.update_brand_apollo_data(brand_name, {
            'apollo_data': {
                'company': company_data,
                'contacts': ranked_contacts[:10],  # Store top 10
                'verification': {
                    'method': 'manual_approval',
                    'confidence': request.json.get('confidence', 0),
                    'verified_date': datetime.now().isoformat(),
                    'verified_by': request.json.get('verified_by', 'system'),
                    'match_factors': request.json.get('match_factors', {})
                }
            },
            'apollo_status': 'verified',
            'apollo_company_id': company_id
        })

        return jsonify({
            'success': True,
            'message': 'Apollo match approved',
            'top_contacts': ranked_contacts[:2]
        })

    except Exception as e:
        logger.error(f"Apollo approval error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/apollo/get_contacts_preview', methods=['POST'])
def apollo_get_contacts_preview():
    """Get contact list preview WITHOUT revealing emails (no credits used)"""
    try:
        from enrichment.apollo_enrichment import ApolloEnrichmentSystem

        company_id = request.json.get('company_id')
        if not company_id:
            return jsonify({'error': 'Company ID required'}), 400

        apollo = ApolloEnrichmentSystem()

        # Get contact list with basic info only (no email revelation)
        contacts = apollo._get_contacts_list_preview(company_id, limit=50)

        if contacts:
            # Rank contacts by relevance
            ranked_contacts = apollo._rank_contacts(contacts)

            return jsonify({
                'success': True,
                'contacts': ranked_contacts,
                'count': len(ranked_contacts)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No contacts found for this company'
            }), 404

    except Exception as e:
        logger.error(f"Contact preview error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/apollo/unlock_contacts', methods=['POST'])
def apollo_unlock_contacts():
    """Unlock selected contacts and reveal their emails (credits charged)"""
    try:
        from enrichment.apollo_enrichment import ApolloEnrichmentSystem

        brand_name = request.json.get('brand_name')
        company_id = request.json.get('company_id')
        company_data = request.json.get('company_data')
        contact_ids = request.json.get('contact_ids', [])

        if not all([brand_name, company_id, contact_ids]):
            return jsonify({'error': 'Missing required fields'}), 400

        apollo = ApolloEnrichmentSystem()

        # Reveal emails for selected contacts only
        unlocked_contacts = apollo._reveal_contact_emails(contact_ids)
        ranked_contacts = apollo._rank_contacts(unlocked_contacts)

        # Save to database
        brand_db.update_brand_apollo_data(brand_name, {
            'apollo_data': {
                'company': company_data,
                'contacts': ranked_contacts,
                'verification': {
                    'method': 'manual_selection',
                    'confidence': request.json.get('confidence', 0),
                    'verified_date': datetime.now().isoformat(),
                    'match_factors': request.json.get('match_factors', {}),
                    'contacts_selected': len(contact_ids)
                }
            },
            'apollo_status': 'verified',
            'apollo_company_id': company_id
        })

        return jsonify({
            'success': True,
            'message': 'Contacts unlocked and saved',
            'contacts_unlocked': len(unlocked_contacts),
            'contacts_saved': len(ranked_contacts),
            'credits_used': len(contact_ids)  # 1 credit per contact
        })

    except Exception as e:
        logger.error(f"Contact unlock error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/apollo/manual_entry', methods=['POST'])
def apollo_manual_entry():
    """Manually enter company and contact data when Apollo doesn't have it"""
    try:
        brand_name = request.json.get('brand_name')
        company_data = request.json.get('company_data')
        contacts_data = request.json.get('contacts', [])

        if not brand_name or not company_data:
            return jsonify({'error': 'Brand name and company data required'}), 400

        # Store manual entry
        brand_db.update_brand_apollo_data(brand_name, {
            'apollo_data': {
                'company': company_data,
                'contacts': contacts_data,
                'verification': {
                    'method': 'manual_entry',
                    'entered_date': datetime.now().isoformat(),
                    'entered_by': request.json.get('entered_by', 'system'),
                    'notes': request.json.get('notes', '')
                }
            },
            'apollo_status': 'manual_entry'
        })

        return jsonify({
            'success': True,
            'message': 'Manual entry saved successfully'
        })

    except Exception as e:
        logger.error(f"Manual entry error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/apollo/batch_enrich', methods=['POST'])
def apollo_batch_enrich():
    """Batch enrich brands with websites (auto-complete only)"""
    try:
        from enrichment.apollo_enrichment import ApolloEnrichmentSystem

        # Get all brands with websites but no Apollo data
        brands_to_enrich = brand_db.get_brands_for_apollo_enrichment()

        apollo = ApolloEnrichmentSystem()
        results = {
            'enriched': [],
            'not_found': [],
            'errors': []
        }

        for brand in brands_to_enrich[:10]:  # Limit to 10 per batch
            try:
                result = apollo.enrich_brand(brand['name'], brand)

                if result['status'] == 'auto_completed':
                    # Auto-save for website matches
                    brand_db.update_brand_apollo_data(brand['name'], {
                        'apollo_data': {
                            'company': result['company'],
                            'contacts': result['contacts'][:10]
                        },
                        'apollo_status': 'verified',
                        'apollo_company_id': result['company']['id']
                    })
                    results['enriched'].append(brand['name'])
                else:
                    results['not_found'].append(brand['name'])

            except Exception as e:
                results['errors'].append({
                    'brand': brand['name'],
                    'error': str(e)
                })

        return jsonify({
            'success': True,
            'results': results,
            'summary': {
                'enriched': len(results['enriched']),
                'not_found': len(results['not_found']),
                'errors': len(results['errors'])
            }
        })

    except Exception as e:
        logger.error(f"Batch enrichment error: {e}")
        return jsonify({'error': str(e)}), 500

# Brand Consolidation Endpoints

# Cache for consolidation analysis (to avoid timeout)
consolidation_analysis_cache = {
    'normalization': None,
    'similarity': None,
    'timestamp': None,
    'max_age': 300  # 5 minutes cache
}

@app.route('/audit/brand_name_analysis', methods=['GET'])
def brand_name_analysis():
    """Get AI-powered brand consolidation opportunities (with caching)"""
    try:
        # Check cache first to avoid timeout
        if consolidation_analysis_cache['normalization'] and consolidation_analysis_cache['timestamp']:
            age = (datetime.now() - consolidation_analysis_cache['timestamp']).total_seconds()
            if age < consolidation_analysis_cache['max_age']:
                logger.info(f"Returning cached consolidation analysis (age: {age:.1f}s)")
                # Combine cached results with enhanced SKU/Brand analysis
                all_opportunities = (
                    (consolidation_analysis_cache['sku_brand'] or []) +
                    consolidation_analysis_cache['normalization'] +
                    (consolidation_analysis_cache['similarity'] or [])
                )

                return jsonify({
                    'normalization_opportunities': all_opportunities,
                    'total_count': len(all_opportunities),
                    'sku_brand_opportunities': len(consolidation_analysis_cache.get('sku_brand', [])),
                    'generated_at': consolidation_analysis_cache['timestamp'].isoformat(),
                    'cached': True
                }), 200
        
        logger.info("Generating fresh consolidation analysis...")
        
        # Import consolidator
        from brand_consolidation.core import BrandConsolidator
        
        # Initialize consolidator with current database
        consolidator = BrandConsolidator(brand_db)
        
        # Get all brands from database for analysis
        all_brands = {}
        for brand in get_cached_all_brands():
            brand_name = brand.get('brand_name')
            if brand_name:
                all_brands[brand_name] = brand
        
        # Get both types of consolidation opportunities with error handling
        normalization_analysis = []
        similarity_analysis = []

        try:
            normalization_analysis = consolidator._find_brand_name_normalization_opportunities(all_brands)
            logger.info(f"🔍 Legacy normalization found {len(normalization_analysis)} opportunities")
        except Exception as e:
            logger.error(f"Error in normalization analysis: {e}")
            import traceback
            logger.error(traceback.format_exc())

        try:
            similarity_analysis = consolidator._find_similar_brand_consolidation_opportunities(all_brands)
            logger.info(f"📝 Legacy similarity found {len(similarity_analysis)} opportunities")
        except Exception as e:
            logger.error(f"Error in similarity analysis: {e}")
            import traceback
            logger.error(traceback.format_exc())

        # NEW: Enhanced SKU vs Brand analysis (without signal timeout to avoid threading issues)
        sku_brand_analysis = []
        try:
            from brand_consolidation.sku_brand_analyzer import SKUBrandAnalyzer

            sku_analyzer = SKUBrandAnalyzer(brand_db)
            sku_brand_analysis = sku_analyzer.analyze_consolidation_opportunities(all_brands)
            logger.info(f"🎯 SKU/Brand analysis found {len(sku_brand_analysis)} opportunities")

        except Exception as e:
            logger.error(f"Error in SKU/Brand analysis: {e}")
            import traceback
            logger.error(traceback.format_exc())
            sku_brand_analysis = []

        # Cache the results
        consolidation_analysis_cache['normalization'] = normalization_analysis
        consolidation_analysis_cache['similarity'] = similarity_analysis
        consolidation_analysis_cache['sku_brand'] = sku_brand_analysis
        consolidation_analysis_cache['timestamp'] = datetime.now()

        # Combine all opportunities (prioritize SKU/Brand analysis)
        all_opportunities = sku_brand_analysis + normalization_analysis + similarity_analysis
        
        # Format response with enhanced SKU vs Brand information
        opportunities = []
        for suggestion in all_opportunities:
            # Enhanced formatting for new SKU/Brand analysis
            opportunity = {
                'proposal_id': suggestion.get('proposal_id'),
                'suggested_name': suggestion.get('suggested_name') or suggestion.get('canonical_name'),
                'current_brands': suggestion.get('brands_to_merge', []) or suggestion.get('current_brands', []) or suggestion.get('brands_to_consolidate', []),
                'brands_to_merge': suggestion.get('brands_to_merge', []) or suggestion.get('current_brands', []) or suggestion.get('brands_to_consolidate', []),
                'confidence': suggestion.get('confidence', 0.8),
                'reason': suggestion.get('reason', 'Consolidation opportunity detected') or suggestion.get('reasoning', ''),
                'analysis': suggestion.get('analysis', [])
            }

            # Add SKU vs Brand specific information if available
            if suggestion.get('type'):  # New enhanced analysis
                opportunity.update({
                    'consolidation_type': suggestion.get('consolidation_type', 'UNKNOWN'),
                    'hierarchy': suggestion.get('hierarchy', {}),
                    'url_evidence': suggestion.get('url_evidence', ''),
                    'domain': suggestion.get('domain', ''),
                    'analysis_type': suggestion.get('type', ''),
                    'is_sku_consolidation': suggestion.get('consolidation_type') == 'SKU_TO_BRAND',
                    'is_portfolio_company': suggestion.get('consolidation_type') == 'PORTFOLIO_BRANDS',
                    'similarity_scores': suggestion.get('similarity_scores', {}),
                    'enhanced_analysis': True
                })

                # Add specific reasoning based on type
                if suggestion.get('consolidation_type') == 'SKU_TO_BRAND':
                    opportunity['consolidation_description'] = f"🎯 SKU Consolidation: '{suggestion.get('canonical_name')}' appears to be the parent brand, others are product SKUs"
                elif suggestion.get('consolidation_type') == 'PORTFOLIO_BRANDS':
                    opportunity['consolidation_description'] = f"🏢 Portfolio Company: Multiple brands under same domain '{suggestion.get('domain', '')}'"
                else:
                    opportunity['consolidation_description'] = f"📝 Similar Names: Brand name variations detected"
            else:
                # Legacy analysis
                opportunity.update({
                    'enhanced_analysis': False,
                    'consolidation_description': opportunity['reason']
                })

            opportunities.append(opportunity)
        
        logger.info(f"Generated {len(opportunities)} consolidation opportunities (cached for 5 min)")
        
        return jsonify({
            'normalization_opportunities': opportunities,
            'total_count': len(opportunities),
            'sku_brand_opportunities': len(sku_brand_analysis),
            'legacy_opportunities': len(normalization_analysis) + len(similarity_analysis),
            'analysis_breakdown': {
                'sku_to_brand': len([o for o in sku_brand_analysis if o.get('consolidation_type') == 'SKU_TO_BRAND']),
                'portfolio_brands': len([o for o in sku_brand_analysis if o.get('consolidation_type') == 'PORTFOLIO_BRANDS']),
                'similar_names': len([o for o in sku_brand_analysis if o.get('consolidation_type') == 'SIMILAR_NAMES']),
                'legacy_analysis': len(normalization_analysis) + len(similarity_analysis)
            },
            'generated_at': datetime.now().isoformat(),
            'cached': False
        }), 200
        
    except ImportError as e:
        logger.error(f"Brand consolidation module not available: {e}")
        return jsonify({'error': 'Brand consolidation feature not available'}), 503
    except Exception as e:
        logger.error(f"Error analyzing brand names: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/audit/data_health', methods=['GET'])
def get_data_health():
    """Get data health metrics for audit dashboard"""
    try:
        brands = get_cached_all_brands()
        total_brands = len(brands)
        
        # Calculate health metrics
        brands_with_websites = sum(1 for b in brands if b.get('enrichment'))
        brands_with_importers = sum(1 for b in brands if b.get('importers'))
        brands_with_producers = sum(1 for b in brands if b.get('producers'))
        brands_with_countries = sum(1 for b in brands if b.get('countries'))
        
        # Calculate data quality issues
        potential_duplicates = 0  # Would need more sophisticated detection
        missing_critical_data = sum(1 for b in brands if not b.get('countries') or not b.get('class_types'))
        data_inconsistencies = 0  # Would need validation logic
        
        # Enrichment status
        enriched_count = brands_with_websites
        pending_count = total_brands - enriched_count
        
        # Calculate scores
        completeness_score = min(100, int((brands_with_websites / max(1, total_brands)) * 100))
        quality_score = max(0, 100 - int((missing_critical_data / max(1, total_brands)) * 100))
        enrichment_rate = int((enriched_count / max(1, total_brands)) * 100)
        overall_score = int((completeness_score + quality_score + enrichment_rate) / 3)
        
        # Get ranking statistics
        try:
            from enrichment.ranking_system import EnrichmentRankingSystem
            ranking_system = EnrichmentRankingSystem(db_config['sqlite_path'])
            ranking_stats = ranking_system.get_statistics()

            tier1_count = ranking_stats['tier_distribution'].get('tier_1', 0)
            tier2_count = ranking_stats['tier_distribution'].get('tier_2', 0)
            apollo_ready = ranking_stats.get('brands_with_websites', 0)
            strategic_partners = ranking_stats.get('strategic_partner_brands', 0)
            spirits_brands = ranking_stats.get('spirits_brands', 0)
        except Exception as e:
            logger.error(f"Error getting ranking stats: {e}")
            tier1_count = tier2_count = apollo_ready = strategic_partners = spirits_brands = 0

        # Get agentic learning insights
        agentic_insights = {
            'patterns_learned': 0,
            'success_rate': 0,
            'auto_consolidated': 0,
            'learning_accuracy': 0
        }

        try:
            # Try to get agentic consolidation insights
            import os
            learning_dir = 'data/consolidation_learning'
            if os.path.exists(learning_dir):
                patterns_file = os.path.join(learning_dir, 'consolidation_patterns.json')
                feedback_file = os.path.join(learning_dir, 'consolidation_feedback.json')

                if os.path.exists(patterns_file):
                    with open(patterns_file, 'r') as f:
                        patterns = json.load(f)
                        agentic_insights['patterns_learned'] = len(patterns)

                if os.path.exists(feedback_file):
                    with open(feedback_file, 'r') as f:
                        feedback = json.load(f)
                        if feedback:
                            approved = sum(1 for f in feedback if f.get('user_action') == 'approved')
                            total = len(feedback)
                            agentic_insights['success_rate'] = int((approved / max(1, total)) * 100)
                            agentic_insights['auto_consolidated'] = approved
                            agentic_insights['learning_accuracy'] = min(100, int((patterns_file and 85) or 0))
        except Exception as e:
            logger.error(f"Error getting agentic insights: {e}")

        return jsonify({
            'overview': {
                'overall_health_score': overall_score,
                'total_brands': total_brands,
                'status': 'Good' if overall_score >= 70 else 'Fair' if overall_score >= 40 else 'Poor'
            },
            'completeness': {
                'score': completeness_score,
                'website_coverage': round((brands_with_websites / max(1, total_brands)) * 100, 1),
                'brands_with_importers': brands_with_importers,
                'brands_with_countries': brands_with_countries
            },
            'quality': {
                'score': quality_score,
                'potential_duplicates': potential_duplicates,
                'missing_critical_data': missing_critical_data,
                'data_inconsistencies': data_inconsistencies
            },
            'enrichment': {
                'enrichment_rate': enrichment_rate,
                'total_enriched': enriched_count,
                'pending_enrichment': pending_count
            },
            'rankings': {
                'total_critical': tier1_count,
                'total_high': tier2_count,
                'apollo_ready': apollo_ready,
                'strategic_partners': strategic_partners,
                'spirits_brands': spirits_brands
            },
            'learning': {
                'patterns_learned': agentic_insights['patterns_learned'],
                'success_rate': agentic_insights['success_rate'],
                'auto_consolidated': agentic_insights['auto_consolidated'],
                'learning_accuracy': agentic_insights['learning_accuracy']
            },
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting data health: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/consolidation/approve_proposal', methods=['POST'])
def approve_consolidation():
    """🤖 Agentic Brand Consolidation - Execute a brand consolidation proposal with intelligent processing"""
    try:
        data = request.get_json()
        proposal_id = data.get('proposal_id')
        force_approval = data.get('force_approval', False)  # For manual override
        
        if not proposal_id:
            return jsonify({'error': 'Proposal ID required'}), 400
        
        # Import consolidator
        from brand_consolidation.core import BrandConsolidator
        
        # Initialize agentic consolidator
        consolidator = BrandConsolidator(brand_db)
        
        # Get all brands from database for analysis
        all_brands = {}
        for brand in get_cached_all_brands():
            brand_name = brand.get('brand_name')
            if brand_name:
                all_brands[brand_name] = brand
        
        # 🧠 AGENTIC STEP 1: Get comprehensive analysis including all types
        normalization_opportunities = consolidator._find_brand_name_normalization_opportunities(all_brands)
        similarity_opportunities = consolidator._find_similar_brand_consolidation_opportunities(all_brands)

        # Add SKU/Brand analysis if available
        sku_brand_opportunities = []
        try:
            from brand_consolidation.sku_brand_analyzer import SKUBrandAnalyzer
            sku_analyzer = SKUBrandAnalyzer(brand_db)
            sku_brand_opportunities = sku_analyzer.analyze_consolidation_opportunities(all_brands)
            logger.info(f"🎯 Found {len(sku_brand_opportunities)} SKU/Brand opportunities for approval")
        except Exception as e:
            logger.error(f"Error getting SKU/Brand opportunities for approval: {e}")

        # Combine all opportunities (prioritize SKU/Brand analysis)
        all_opportunities = sku_brand_opportunities + normalization_opportunities + similarity_opportunities

        # Find the matching proposal
        proposal = None
        for opp in all_opportunities:
            if opp.get('proposal_id') == proposal_id:
                proposal = opp
                break

        if not proposal:
            return jsonify({'error': f'Proposal {proposal_id} not found in current analysis'}), 404

        # 🤖 AGENTIC STEP 2: Enhanced confidence assessment for all proposal types
        confidence = proposal.get('confidence', 0.0)

        # Determine consolidation type from proposal ID
        if proposal_id.startswith('normalization_'):
            consolidation_type = 'normalization'
        elif proposal_id.startswith('sku_to_brand_'):
            consolidation_type = 'sku_to_brand'
        elif proposal_id.startswith('portfolio_'):
            consolidation_type = 'portfolio_company'
        elif proposal_id.startswith('similar_names_'):
            consolidation_type = 'similar_names'
        else:
            consolidation_type = 'similarity'
        
        # 🎯 AGENTIC STEP 3: Enhanced auto-approval logic for all consolidation types
        should_auto_approve = False
        if not force_approval:  # Only apply auto-logic if not manually forced
            if confidence >= 0.95:  # 95%+ confidence for any type
                should_auto_approve = True
                approval_reason = "🤖 Auto-approved: 95%+ confidence"
            elif confidence >= 0.90 and consolidation_type == 'sku_to_brand':
                should_auto_approve = True  # URL + domain match is very reliable
                approval_reason = "🎯 Auto-approved: SKU→Brand consolidation with 90%+ confidence"
            elif confidence >= 0.90 and consolidation_type == 'normalization':
                should_auto_approve = True  # Product name detection is very reliable
                approval_reason = "🤖 Auto-approved: Product name normalization with 90%+ confidence"
            elif confidence >= 0.85 and consolidation_type == 'portfolio_company':
                should_auto_approve = True  # Same domain for portfolio is strong signal
                approval_reason = "🏢 Auto-approved: Portfolio company with 85%+ confidence"
            elif proposal.get('same_domain') and confidence >= 0.85:
                should_auto_approve = True  # Same domain is very strong signal (legacy)
                approval_reason = "🤖 Auto-approved: Same domain with 85%+ confidence"
            else:
                approval_reason = "👤 Manual approval requested"
        else:
            should_auto_approve = True
            approval_reason = "👤 Force approved by user"
        
        # Extract consolidation data (handle all proposal formats)
        canonical_name = proposal.get('suggested_name') or proposal.get('canonical_name')
        brands_to_merge = (proposal.get('brands_to_merge') or
                          proposal.get('current_brands', []) or
                          proposal.get('brands_to_consolidate', []))
        
        if not canonical_name or not brands_to_merge:
            return jsonify({'error': 'Invalid proposal data structure'}), 400
        
        # 🧠 AGENTIC STEP 4: Intelligent data preservation strategy
        consolidation_strategy = consolidator._create_consolidation_strategy(brands_to_merge, all_brands)
        
        # Execute consolidation
        result = brand_db.consolidate_brands(canonical_name, brands_to_merge)
        
        if result and result.get('success'):
            # 🎉 AGENTIC STEP 5: Enhanced logging with strategy and reasoning
            consolidation_event = {
                'timestamp': datetime.now().isoformat(),
                'action': 'consolidation_approved',
                'proposal_id': proposal_id,
                'consolidation_type': consolidation_type,
                'approval_method': approval_reason,
                'confidence': confidence,
                'canonical_name': canonical_name,
                'brands_merged': brands_to_merge,
                'countries_count': result.get('countries_count', 0),
                'class_types_count': result.get('class_types_count', 0),
                'total_permits_preserved': result.get('permits_count', 0),
                'consolidation_strategy': consolidation_strategy,
                'user': 'agentic_system',
                'reasoning': proposal.get('reason', 'No specific reason provided')
            }
            
            # Save to consolidation history
            try:
                import os
                history_file = os.path.join('data', 'consolidation_history.json')
                history = []
                if os.path.exists(history_file):
                    with open(history_file, 'r') as f:
                        history = json.load(f)
                
                history.append(consolidation_event)
                
                with open(history_file, 'w') as f:
                    json.dump(history, f, indent=2)
            except Exception as e:
                logger.warning(f"Failed to save consolidation history: {e}")
            
            # Invalidate filter cache
            invalidate_filter_cache()
            
            # 🎉 Enhanced success response with agentic details
            merged_brands_str = ', '.join(brands_to_merge)
            
            return jsonify({
                'success': True,
                'message': f"🤖 {approval_reason}: {merged_brands_str} → {canonical_name}",
                'consolidation_result': {
                    'canonical_name': canonical_name,
                    'brands_merged': brands_to_merge,
                    'consolidation_type': consolidation_type,
                    'confidence': f"{confidence:.1%}",
                    'approval_method': approval_reason,
                    'auto_approved': should_auto_approve and not force_approval,
                    'countries_count': result.get('countries_count', 0),
                    'class_types_count': result.get('class_types_count', 0),
                    'permits_preserved': result.get('permits_count', 0),
                    'strategy_reasoning': consolidation_strategy.get('reasoning', [])
                }
            }), 200
        else:
            error_msg = result.get('error', 'Unknown consolidation error') if result else 'Consolidation returned no result'
            return jsonify({
                'success': False,
                'message': f'Consolidation failed: {error_msg}',
                'proposal_id': proposal_id,
                'canonical_name': canonical_name,
                'brands_to_merge': brands_to_merge
            }), 500
            
    except ImportError as e:
        logger.error(f"Brand consolidation module not available: {e}")
        return jsonify({'error': 'Brand consolidation feature not available'}), 503
    except Exception as e:
        logger.error(f"Error approving consolidation: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/consolidation/batch_process', methods=['POST'])
def batch_process_consolidation():
    """🤖 Agentic Batch Processing - Automatically process high-confidence consolidations"""
    try:
        data = request.get_json() or {}
        min_confidence = data.get('min_confidence', 0.95)  # Default to 95% confidence
        max_batch_size = data.get('max_batch_size', 10)    # Safety limit
        dry_run = data.get('dry_run', False)               # Preview mode
        
        # Import consolidator
        from brand_consolidation.core import BrandConsolidator
        consolidator = BrandConsolidator(brand_db)
        
        # Get all brands
        all_brands = {}
        for brand in get_cached_all_brands():
            brand_name = brand.get('brand_name')
            if brand_name:
                all_brands[brand_name] = brand
        
        # Get all consolidation opportunities
        normalization_opportunities = consolidator._find_brand_name_normalization_opportunities(all_brands)
        similarity_opportunities = consolidator._find_similar_brand_consolidation_opportunities(all_brands)
        all_opportunities = normalization_opportunities + similarity_opportunities
        
        # 🎯 Filter for high-confidence opportunities
        high_confidence_opportunities = [
            opp for opp in all_opportunities 
            if opp.get('confidence', 0.0) >= min_confidence
        ][:max_batch_size]
        
        if dry_run:
            # Preview mode - just show what would be processed
            return jsonify({
                'success': True,
                'dry_run': True,
                'opportunities_found': len(all_opportunities),
                'high_confidence_count': len(high_confidence_opportunities),
                'min_confidence_threshold': f"{min_confidence:.1%}",
                'would_process': [
                    {
                        'proposal_id': opp['proposal_id'],
                        'canonical_name': opp.get('suggested_name') or opp.get('canonical_name'),
                        'brands_to_merge': opp.get('brands_to_merge') or opp.get('current_brands'),
                        'confidence': f"{opp.get('confidence', 0):.1%}",
                        'reason': opp.get('reason', 'No reason provided')
                    }
                    for opp in high_confidence_opportunities
                ]
            })
        
        # 🤖 Process each high-confidence consolidation
        processed = []
        failed = []
        
        for opp in high_confidence_opportunities:
            try:
                proposal_id = opp['proposal_id']
                canonical_name = opp.get('suggested_name') or opp.get('canonical_name')
                brands_to_merge = opp.get('brands_to_merge') or opp.get('current_brands')
                confidence = opp.get('confidence', 0.0)
                
                # Execute consolidation
                result = brand_db.consolidate_brands(canonical_name, brands_to_merge)
                
                if result and result.get('success'):
                    processed.append({
                        'proposal_id': proposal_id,
                        'canonical_name': canonical_name,
                        'brands_merged': brands_to_merge,
                        'confidence': f"{confidence:.1%}",
                        'permits_preserved': result.get('permits_count', 0)
                    })
                else:
                    failed.append({
                        'proposal_id': proposal_id,
                        'canonical_name': canonical_name,
                        'error': result.get('error', 'Unknown error') if result else 'No result returned'
                    })
                    
            except Exception as e:
                failed.append({
                    'proposal_id': opp.get('proposal_id', 'unknown'),
                    'error': str(e)
                })
        
        # Invalidate cache after batch processing
        if processed:
            invalidate_filter_cache()
        
        return jsonify({
            'success': True,
            'batch_processing_complete': True,
            'total_opportunities': len(all_opportunities),
            'processed_count': len(processed),
            'failed_count': len(failed),
            'min_confidence_threshold': f"{min_confidence:.1%}",
            'successfully_processed': processed,
            'failed_consolidations': failed
        })
        
    except Exception as e:
        logger.error(f"Error in batch consolidation processing: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# Database Management Endpoints

@app.route('/reset_database', methods=['POST'])
def reset_database():
    """Reset the database (WARNING: This will clear all data)"""
    try:
        # Check for confirmation
        data = request.get_json() or {}
        confirm = data.get('confirm', False)
        
        if not confirm:
            return jsonify({
                'error': 'Confirmation required',
                'message': 'Send {"confirm": true} to reset database'
            }), 400
        
        # Reset the database
        brand_db.reset_database()
        
        # Clear filter cache
        invalidate_filter_cache()
        
        return jsonify({
            'success': True,
            'message': 'Database reset successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/reload_database', methods=['POST'])
def reload_database():
    """Reload database from disk (hot-reload)"""
    try:
        # Reload the database
        brand_db.reload_from_disk()
        
        # Clear filter cache
        invalidate_filter_cache()
        
        # Get stats directly from database
        stats = {
            'brands': len(brand_db.db.get('brands', {})),
            'skus': len(brand_db.db.get('skus', {})),
            'importers': len(brand_db.db.get('master_importers', {}))
        }
        
        return jsonify({
            'success': True,
            'message': 'Database reloaded successfully',
            'stats': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Error reloading database: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/audit/consolidation_history', methods=['GET'])
def get_consolidation_history():
    """Get history of all consolidation events from database"""
    try:
        cursor = brand_db.conn.cursor()

        # Get all consolidation history records
        cursor.execute("""
            SELECT
                id,
                old_brand_name,
                new_brand_name,
                consolidation_type,
                consolidation_reason,
                consolidation_date,
                sku_count_moved,
                enrichment_data_preserved,
                performed_by,
                notes
            FROM brand_consolidation_history
            ORDER BY consolidation_date DESC, id DESC
        """)

        rows = cursor.fetchall()

        history = []
        for row in rows:
            history.append({
                'id': row[0],
                'old_brand_name': row[1],
                'new_brand_name': row[2],
                'consolidation_type': row[3],
                'consolidation_reason': row[4],
                'consolidation_date': row[5],
                'sku_count_moved': row[6],
                'enrichment_data_preserved': bool(row[7]),
                'performed_by': row[8],
                'notes': row[9]
            })

        return success_response({
            'history': history,
            'total_count': len(history)
        })

    except Exception as e:
        logger.error(f"Error loading consolidation history: {e}")
        return error_response(e)

@app.route('/api/brand/<brand_name>/consolidation_history', methods=['GET'])
def get_brand_consolidation_history(brand_name):
    """Get consolidation history for a specific brand"""
    try:
        cursor = brand_db.conn.cursor()

        # Get consolidation history where this brand was either the old or new brand
        cursor.execute("""
            SELECT
                id,
                old_brand_name,
                new_brand_name,
                consolidation_type,
                consolidation_reason,
                consolidation_date,
                sku_count_moved,
                enrichment_data_preserved,
                performed_by,
                notes
            FROM brand_consolidation_history
            WHERE old_brand_name = ? OR new_brand_name = ?
            ORDER BY consolidation_date DESC, id DESC
        """, (brand_name, brand_name))

        rows = cursor.fetchall()

        history = []
        for row in rows:
            history.append({
                'id': row[0],
                'old_brand_name': row[1],
                'new_brand_name': row[2],
                'consolidation_type': row[3],
                'consolidation_reason': row[4],
                'consolidation_date': row[5],
                'sku_count_moved': row[6],
                'enrichment_data_preserved': bool(row[7]),
                'performed_by': row[8],
                'notes': row[9]
            })

        return jsonify({
            'success': True,
            'brand_name': brand_name,
            'history': history,
            'total_count': len(history)
        }), 200

    except Exception as e:
        logger.error(f"Error loading brand consolidation history: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================
# ENRICHMENT RANKING SYSTEM ENDPOINTS
# ============================================================

@app.route('/api/enrichment/rankings', methods=['GET'])
def get_enrichment_rankings():
    """Get enrichment priority rankings for all brands"""
    try:
        from enrichment.ranking_system import EnrichmentRankingSystem

        # Get query parameters
        limit = request.args.get('limit', type=int)
        tier = request.args.get('tier', type=int)
        exclude_enriched = request.args.get('exclude_enriched', 'true').lower() == 'true'

        # Initialize ranking system
        ranking_system = EnrichmentRankingSystem(db_config['sqlite_path'])

        # Get rankings
        if tier:
            rankings = ranking_system.get_enrichment_queue(tier, exclude_enriched)
        else:
            rankings = ranking_system.rank_all_brands(limit)

        return jsonify({
            'success': True,
            'rankings': rankings,
            'total': len(rankings)
        })

    except Exception as e:
        logger.error(f"Error getting enrichment rankings: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/enrichment/ranking/<brand_name>', methods=['GET'])
def get_brand_ranking(brand_name):
    """Get enrichment ranking for a specific brand"""
    try:
        from enrichment.ranking_system import EnrichmentRankingSystem

        # Get brand data
        brand = brand_db.get_brand_data(brand_name)
        if not brand:
            return jsonify({'error': 'Brand not found'}), 404

        # Get SKU count
        cursor = brand_db.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) as sku_count FROM skus WHERE brand_name = ?",
            (brand_name,)
        )
        sku_count = cursor.fetchone()[0]

        # Prepare brand data for scoring
        brand_data = {
            'brand_name': brand_name,
            'importers': json.dumps(brand.get('importers', {})),
            'producers': json.dumps(brand.get('producers', {})),
            'class_types': json.dumps(brand.get('class_types', [])),
            'countries': json.dumps(brand.get('countries', [])),
            'created_date': brand.get('created_date'),
            'updated_at': brand.get('updated_at'),
            'permit_numbers': json.dumps(brand.get('permit_numbers', [])),
            'brand_permits': json.dumps(brand.get('brand_permits', [])),
            'enrichment_data': brand.get('enrichment_data'),
            'sku_count': sku_count
        }

        # Initialize ranking system
        ranking_system = EnrichmentRankingSystem(db_config['sqlite_path'])

        # Calculate score
        score, breakdown = ranking_system.calculate_score(brand_data)
        tier, tier_description = ranking_system.get_tier(score)

        return jsonify({
            'success': True,
            'brand_name': brand_name,
            'score': score,
            'tier': tier,
            'tier_description': tier_description,
            'breakdown': breakdown,
            'sku_count': sku_count,
            'has_enrichment': bool(brand.get('enrichment_data'))
        })

    except Exception as e:
        logger.error(f"Error getting brand ranking: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/enrichment/ranking_stats', methods=['GET'])
def get_ranking_statistics():
    """Get overall enrichment ranking statistics"""
    try:
        from enrichment.ranking_system import EnrichmentRankingSystem

        # Initialize ranking system
        ranking_system = EnrichmentRankingSystem(db_config['sqlite_path'])

        # Get statistics
        stats = ranking_system.get_statistics()

        return jsonify({
            'success': True,
            'statistics': stats
        })

    except Exception as e:
        logger.error(f"Error getting ranking statistics: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/enrichment/priority_queue', methods=['GET'])
def get_priority_queue():
    """Get the priority queue for enrichment processing"""
    try:
        from enrichment.ranking_system import EnrichmentRankingSystem

        # Initialize ranking system
        ranking_system = EnrichmentRankingSystem(db_config['sqlite_path'])

        # Get queues for each tier
        queues = {}
        for tier in range(1, 6):
            queue = ranking_system.get_enrichment_queue(tier, exclude_enriched=True)
            queues[f'tier_{tier}'] = {
                'count': len(queue),
                'brands': queue[:10],  # First 10 for preview
                'description': ranking_system.get_tier(90 if tier == 1 else 70 if tier == 2 else 50 if tier == 3 else 30 if tier == 4 else 20)[1]
            }

        return jsonify({
            'success': True,
            'queues': queues
        })

    except Exception as e:
        logger.error(f"Error getting priority queue: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
