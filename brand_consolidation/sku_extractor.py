"""
SKU Extractor - Minimal implementation for core testing
"""

class SKUExtractor:
    """Extract SKU information from brand names"""
    
    def extract_sku_from_brand_name(self, brand_name, canonical_brand):
        """Simple SKU extraction for testing"""
        # Remove canonical brand from full name
        sku = brand_name.replace(canonical_brand, '').strip()
        return sku if sku else "Original"