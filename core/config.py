"""
Centralized Configuration for TTB COLA Registry System
"""

import os

# Database Configuration
DATABASE_CONFIG = {
    'sqlite_path': 'data/database/brands.db',
    'json_backup_path': 'data/database/brands_db.json',
    'enable_wal_mode': True,
    'backup_on_changes': True
}

# Web Application Configuration
WEB_CONFIG = {
    'upload_folder': 'uploads',
    'matched_folder': 'matched',
    'max_content_length': 50 * 1024 * 1024,  # 50MB
    'allowed_extensions': {'csv', 'xlsx', 'xls'},
    'template_folder': 'web/templates',
    'static_folder': 'web/static'
}

# Brand Enrichment Configuration
ENRICHMENT_CONFIG = {
    'cache_folder': 'data/cache',
    'learning_folder': 'data/learning',
    'production_search_cache': 'data/cache/production_search_cache.json',
    'safe_search_cache': 'data/cache/safe_search_cache.json',
    'enrichment_results': 'data/cache/enrichment_results.json',
    'apollo_api_key': os.getenv('APOLLO_API_KEY'),
    'enable_proxy_rotation': False,
    'max_search_timeout': 120  # seconds
}

# Data Folder Structure
DATA_FOLDERS = [
    'data',
    'data/database', 
    'data/cache',
    'data/learning',
    'uploads',
    'matched'
]

# Learning System Configuration
LEARNING_CONFIG = {
    'events_file': 'data/learning/learning_events.json',
    'patterns_file': 'data/learning/domain_patterns.json',
    'knowledge_base_file': 'data/learning/knowledge_base.json',
    'confidence_threshold': 0.7,
    'learning_rate': 0.1
}

def ensure_directories():
    """Ensure all required directories exist"""
    for folder in DATA_FOLDERS:
        os.makedirs(folder, exist_ok=True)

def get_database_config():
    """Get database configuration"""
    return DATABASE_CONFIG.copy()

def get_web_config():
    """Get web application configuration"""
    return WEB_CONFIG.copy()

def get_enrichment_config():
    """Get enrichment system configuration"""
    return ENRICHMENT_CONFIG.copy()

def get_learning_config():
    """Get learning system configuration"""
    return LEARNING_CONFIG.copy()