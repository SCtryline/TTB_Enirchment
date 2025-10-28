"""
Brand Consolidation Module

Intelligently consolidates TTB brand registrations into proper brand → SKU hierarchies
with producer awareness for higher confidence matching.
"""

from .core import BrandConsolidator
from .brand_extractor import BrandExtractor
from .brand_matcher import BrandMatcher
from .sku_extractor import SKUExtractor
from .consolidation_proposal import ConsolidationProposal

__version__ = "1.0.0"
__all__ = [
    "BrandConsolidator",
    "BrandExtractor", 
    "BrandMatcher",
    "SKUExtractor",
    "ConsolidationProposal"
]