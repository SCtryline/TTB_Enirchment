"""
Configuration for Brand Consolidation with White Label Support
Enhanced with producer attribution and production relationship tracking
"""

# Main consolidation configuration
CONSOLIDATION_CONFIG = {
    'enabled': True,                    # Master switch
    'auto_approve_threshold': 1.0,      # 100% confidence required for auto-approval
    'min_confidence_display': 0.5,      # Don't show <50% matches
    'preserve_original': True,          # Keep original data intact
    'training_mode': True,              # Enable training system
    'batch_size': 100,                  # Process in batches
    'cache_ttl': 3600,                  # Cache for 1 hour
    'white_label_detection': True,      # Enable white label detection
    'producer_attribution': True,       # Show "Made by" badges
    'historical_tracking': True,        # Track producer changes over time
}

# Producer relationship types and display
PRODUCER_RELATIONSHIPS = {
    'primary_producer': {
        'label': 'Primary Producer',
        'badge_style': 'primary',
        'confidence_weight': 1.0,
        'display_priority': 1
    },
    'secondary_producer': {
        'label': 'Secondary Producer', 
        'badge_style': 'secondary',
        'confidence_weight': 0.8,
        'display_priority': 2
    },
    'former_producer': {
        'label': 'Former Producer',
        'badge_style': 'inactive',
        'confidence_weight': 0.3,
        'display_priority': 3
    },
    'contract_producer': {
        'label': 'Contract Producer',
        'badge_style': 'contract',
        'confidence_weight': 0.9,
        'display_priority': 1
    },
    'unknown_producer': {
        'label': 'Producer Unknown',
        'badge_style': 'unknown',
        'confidence_weight': 0.1,
        'display_priority': 4
    }
}

# White label brand indicators
WHITE_LABEL_BRANDS = {
    'retail_stores': [
        'KIRKLAND', 'KIRKLAND SIGNATURE', 'COSTCO',
        'KROGER', 'KROGER SELECT', 'SIMPLE TRUTH',
        'SAFEWAY', 'LUCERNE', 'O ORGANICS',
        'WALMART', 'GREAT VALUE', 'EQUATE',
        'TARGET', 'GOOD & GATHER', 'EVERSPRING',
        'TRADER JOES', 'TRADER JOE', 'TJS',
        'WHOLE FOODS', '365', 'WHOLE FOODS MARKET',
        'ALDI', 'SIMPLY NATURE', 'LIVEWELL',
        'WEGMANS', 'WEIS', 'GIANT', 'STOP & SHOP'
    ],
    'private_label_indicators': [
        'PRIVATE LABEL', 'STORE BRAND', 'HOUSE BRAND',
        'EXCLUSIVE', 'SIGNATURE', 'SELECT', 'CHOICE',
        'PREMIUM', 'FINEST', 'BEST', 'VALUE'
    ],
    'contract_indicators': [
        'BOTTLED FOR', 'PRODUCED FOR', 'DISTILLED FOR',
        'MADE FOR', 'PRIVATE LABEL', 'CONTRACT BOTTLED',
        'CO-PACKED', 'CUSTOM BLEND'
    ]
}

# Product terms for different alcohol categories
PRODUCT_TERMS = {
    'tequila': [
        'BLANCO', 'REPOSADO', 'ANEJO', 'EXTRA ANEJO', 'CRISTALINO', 
        'JOVEN', 'PLATA', 'GOLD', 'SILVER', 'ADDITIVE FREE', 'ORGANIC'
    ],
    'whiskey': [
        'SINGLE BARREL', 'CASK STRENGTH', 'BARREL PROOF', 'STRAIGHT', 
        'BOURBON', 'RYE', 'WHEAT', 'BOTTLED IN BOND', 'SMALL BATCH',
        'SINGLE MALT', 'RESERVE', 'SELECT', 'KENTUCKY STRAIGHT',
        'TENNESSEE', 'CANADIAN', 'IRISH', 'SCOTCH', 'BLENDED'
    ],
    'vodka': [
        'PREMIUM', 'ULTRA', 'PURE', 'ORIGINAL', 'CLASSIC', 'PLATINUM',
        'ORGANIC', 'GLUTEN FREE', 'FILTERED', 'DISTILLED'
    ],
    'gin': [
        'LONDON DRY', 'PLYMOUTH', 'OLD TOM', 'NAVY STRENGTH', 
        'CONTEMPORARY', 'BOTANICAL', 'PREMIUM', 'CRAFT'
    ],
    'rum': [
        'WHITE', 'SILVER', 'GOLD', 'DARK', 'SPICED', 'AGED', 
        'PREMIUM', 'RESERVE', 'CAPTAIN', 'ADMIRAL'
    ],
    'wine': [
        'CABERNET', 'CHARDONNAY', 'PINOT NOIR', 'SAUVIGNON', 'MERLOT', 
        'ZINFANDEL', 'ROSE', 'BLANC', 'ROUGE', 'RESERVE', 'ESTATE',
        'VINTAGE', 'DESSERT', 'ICE WINE', 'PORT', 'SHERRY'
    ],
    'general': [
        'RESERVE', 'LIMITED EDITION', 'RELEASE', 'VINTAGE', 'ESTATE', 
        'SELECT', 'PREMIUM', 'SPECIAL', 'COLLECTION', 'SERIES',
        'EXTRA', 'ULTRA', 'SUPER', 'FINEST', 'ORIGINAL', 'CLASSIC',
        'SIGNATURE', 'ARTISAN', 'CRAFT', 'HANDCRAFTED', 'SMALL BATCH'
    ],
    'size_volume': [
        'LITER', 'ML', '750', '1.75', '375', '50ML', '100ML', '200ML',
        'MAGNUM', 'DOUBLE MAGNUM', 'SPLIT', 'HALF BOTTLE', 'MINI'
    ],
    'age_statements': [
        r'\d{1,2}\s*YEAR(?:S)?(?:\s+OLD)?', r'\d{1,2}\s*YR(?:S)?(?:\s+OLD)?', 
        r'\d{1,2}\s*YO', r'\d{1,2}\s*ANOS?', r'AGED\s+\d{1,2}\s*YEAR(?:S)?'
    ],
    'proof_abv': [
        r'\d{2,3}(?:\.\d)?\s*PROOF', r'\d{1,2}(?:\.\d)?\s*%\s*ABV?',
        r'\d{2,3}°', 'BARREL PROOF', 'CASK STRENGTH', 'NAVY STRENGTH'
    ]
}

# Common brand name patterns to recognize
BRAND_PATTERNS = {
    'possessive': [r"([A-Z\s]+)'S\s+", r"([A-Z\s]+)S'\s+"],  # "JACK'S PREMIUM"
    'company': [r"([A-Z\s]+)\s+(?:COMPANY|CORP|LLC|INC|LTD)(?:\s|$)"],
    'distillery': [r"([A-Z\s]+)\s+DISTILLERY(?:\s|$)"],
    'brewery': [r"([A-Z\s]+)\s+BREW(?:ERY|ING)(?:\s|$)"],
    'winery': [r"([A-Z\s]+)\s+WIN(?:ERY|ES)(?:\s|$)"],
    'numbered': [r"([A-Z\s]+)\s+(?:NO\.?\s*)?\d+(?:\s|$)"],  # "JACK DANIELS NO 7"
}

# Enhanced confidence scoring with white label awareness
CONFIDENCE_RULES = {
    'same_producer_same_brand_owner': 0.95,     # Clear consolidation case
    'same_producer_different_brand_owner': 0.20, # White label scenario - don't consolidate
    'same_brand_owner_different_producer': 0.85, # Brand moved production
    'same_brand_owner_same_producer': 0.98,     # Obvious consolidation
    'white_label_detection': -0.60,            # Major penalty for cross-brand-owner
    'producer_name_in_brand': 0.40,            # Producer name appears in brand
    'historical_producer_match': 0.30,         # Previously made by same producer
    'no_producer_data': 0.50,                  # Fallback to name matching only
}

# Brand page UI configuration
UI_CONFIG = {
    'show_producer_badges': True,
    'show_production_history': True,
    'show_contract_relationships': True,
    'historical_data_tab': True,
    'producer_confidence_display': True,
    'badge_styles': {
        'primary': {'bg': '#2563eb', 'text': 'white', 'icon': '🏭'},
        'secondary': {'bg': '#6b7280', 'text': 'white', 'icon': '🔧'}, 
        'inactive': {'bg': '#e5e7eb', 'text': '#6b7280', 'icon': '⏳'},
        'contract': {'bg': '#059669', 'text': 'white', 'icon': '🤝'},
        'unknown': {'bg': '#f3f4f6', 'text': '#6b7280', 'icon': '❓'}
    }
}

# Storage paths for enhanced data
STORAGE_PATHS = {
    'consolidated_brands': 'brand_consolidation/storage/consolidated_brands.json',
    'producer_relationships': 'brand_consolidation/storage/producer_relationships.json',
    'historical_changes': 'brand_consolidation/storage/historical_changes.json',
    'white_label_mappings': 'brand_consolidation/storage/white_label_mappings.json',
    'training_data': 'brand_consolidation/storage/training_data.json',
    'override_rules': 'brand_consolidation/storage/override_rules.json',
}

# Training mode with white label scenarios
TRAINING_CONFIG = {
    'enabled': True,
    'scenarios_per_session': 10,
    'white_label_scenarios': 3,  # Include white label cases in training
    'confidence_improvement_target': 0.10,
    'min_training_examples': 5,
    'max_training_examples': 50,
}

# API endpoints for enhanced consolidation system
CONSOLIDATION_ENDPOINTS = {
    'propose': '/consolidation/propose',
    'review': '/consolidation/review', 
    'approve': '/consolidation/approve',
    'training': '/consolidation/training',
    'export': '/consolidation/export',
    'status': '/consolidation/status',
    'producer_attribution': '/consolidation/producer_attribution',
    'historical_data': '/consolidation/historical',
}