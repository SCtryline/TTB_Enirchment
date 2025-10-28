"""
Consolidation Proposal Generation with Producer Attribution
Creates detailed proposals for manual review with confidence scoring
"""

from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from .config import CONFIDENCE_RULES, PRODUCER_RELATIONSHIPS, CONSOLIDATION_CONFIG
from .brand_extractor import BrandExtractor

class ConsolidationProposal:
    """Generate comprehensive consolidation proposals for manual review"""
    
    def __init__(self):
        self.extractor = BrandExtractor()
        
    def create_proposal(self, canonical_name: str, brand_list: List[str], database) -> Dict[str, Any]:
        """
        Create a comprehensive consolidation proposal
        """
        brands_data = database.db.get('brands', {})
        
        # Gather all brand information
        brand_details = []
        total_skus = 0
        all_countries = set()
        all_class_types = set()
        all_producers = set()
        earliest_date = None
        latest_date = None
        
        for brand_name in brand_list:
            if brand_name in brands_data:
                brand_data = brands_data[brand_name]
                
                # Get producer information
                producers = self._get_brand_producers(brand_name, brand_data, database)
                
                # Extract SKU information
                brand_skus = []
                for sku_id in brand_data.get('skus', []):
                    if sku_id in database.db.get('skus', {}):
                        sku = database.db['skus'][sku_id]
                        brand_skus.append({
                            'ttb_id': sku_id,
                            'fanciful_name': sku.get('fanciful_name', ''),
                            'class_type': sku.get('class_type_desc', ''),
                            'completed_date': sku.get('completed_date', ''),
                            'origin': sku.get('origin_desc', '')
                        })
                        
                        # Track date range
                        if sku.get('completed_date'):
                            try:
                                date = datetime.fromisoformat(sku['completed_date'])
                                if not earliest_date or date < earliest_date:
                                    earliest_date = date
                                if not latest_date or date > latest_date:
                                    latest_date = date
                            except:
                                pass
                
                brand_detail = {
                    'brand_name': brand_name,
                    'core_brand': self.extractor.extract_core_brand(brand_name),
                    'sku_count': len(brand_data.get('skus', [])),
                    'countries': brand_data.get('countries', []),
                    'class_types': brand_data.get('class_types', []),
                    'producers': producers,
                    'skus': brand_skus,
                    'is_canonical': brand_name == canonical_name
                }
                
                brand_details.append(brand_detail)
                total_skus += len(brand_data.get('skus', []))
                all_countries.update(brand_data.get('countries', []))
                all_class_types.update(brand_data.get('class_types', []))
                all_producers.update(p['name'] for p in producers if p['name'])
        
        # Calculate consolidation confidence
        confidence, confidence_factors = self._calculate_consolidation_confidence(brand_details, database)
        
        # Determine proposal type
        proposal_type = self._determine_proposal_type(confidence, brand_details)
        
        # Generate SKU consolidation preview
        sku_consolidation = self._generate_sku_consolidation_preview(brand_details, canonical_name)
        
        # Create the comprehensive proposal
        proposal = {
            'id': self._generate_proposal_id(canonical_name),
            'created_at': datetime.now().isoformat(),
            'canonical_name': canonical_name,
            'brands_to_consolidate': brand_list,
            'brand_count': len(brand_list),
            'total_skus': total_skus,
            
            # Confidence and scoring
            'confidence_score': confidence,
            'confidence_factors': confidence_factors,
            'proposal_type': proposal_type,
            'recommendation': 'auto_approve' if confidence >= CONSOLIDATION_CONFIG['auto_approve_threshold'] else 'manual_review',
            
            # Aggregated metadata
            'summary': {
                'countries': sorted(list(all_countries)),
                'class_types': sorted(list(all_class_types)),
                'producers': sorted(list(all_producers)),
                'date_range': {
                    'earliest': earliest_date.isoformat() if earliest_date else None,
                    'latest': latest_date.isoformat() if latest_date else None
                }
            },
            
            # Detailed brand information
            'brand_details': brand_details,
            
            # SKU consolidation preview
            'sku_consolidation': sku_consolidation,
            
            # Risk assessment
            'risk_assessment': self._assess_consolidation_risks(brand_details),
            
            # Benefits analysis
            'benefits': self._analyze_consolidation_benefits(brand_details),
            
            # Status tracking
            'status': 'pending_review',
            'reviewed_by': None,
            'reviewed_at': None,
            'approved': None
        }
        
        return proposal
    
    def _get_brand_producers(self, brand_name: str, brand_data: Dict, database) -> List[Dict]:
        """Get producer information for a brand"""
        producers = []
        
        for permit in brand_data.get('permit_numbers', []):
            # Try spirit producers first
            producer = database.get_spirit_producer(permit)
            producer_type = 'Spirit'
            
            if not producer:
                # Try wine producers
                producer = database.get_wine_producer(permit)
                producer_type = 'Wine'
            
            if producer:
                producers.append({
                    'permit': permit,
                    'name': producer.get('owner_name', ''),
                    'operating_name': producer.get('operating_name', ''),
                    'type': producer_type,
                    'relationship': self._determine_producer_relationship(brand_name, producer),
                    'confidence': self._calculate_producer_confidence(brand_name, producer)
                })
        
        return producers
    
    def _determine_producer_relationship(self, brand_name: str, producer: Dict) -> str:
        """Determine the relationship between brand and producer"""
        producer_name = producer.get('owner_name', '').upper()
        brand_name_upper = brand_name.upper()
        
        # Check if producer name appears in brand name
        if any(word in brand_name_upper for word in producer_name.split() if len(word) > 3):
            return 'primary_producer'
        
        # Check for white label indicators
        white_label_brands = ['KIRKLAND', 'KROGER', 'WALMART', 'TARGET', 'COSTCO']
        if any(store in brand_name_upper for store in white_label_brands):
            return 'contract_producer'
        
        return 'secondary_producer'
    
    def _calculate_producer_confidence(self, brand_name: str, producer: Dict) -> float:
        """Calculate confidence in producer attribution"""
        base_confidence = 0.7
        
        producer_name = producer.get('owner_name', '')
        if any(word in brand_name.upper() for word in producer_name.upper().split() if len(word) > 3):
            base_confidence += 0.2
        
        return min(base_confidence, 1.0)
    
    def _calculate_consolidation_confidence(self, brand_details: List[Dict], database) -> Tuple[float, Dict]:
        """Calculate overall consolidation confidence with detailed factors"""
        factors = {
            'same_core_brand': 0,
            'same_producers': 0,
            'similar_categories': 0,
            'same_countries': 0,
            'name_similarity': 0,
            'white_label_penalty': 0,
            'date_proximity': 0
        }
        
        if len(brand_details) < 2:
            return 0.0, factors
        
        # Check core brand consistency
        core_brands = [b['core_brand'] for b in brand_details if b['core_brand']]
        if len(set(core_brands)) == 1 and core_brands:
            factors['same_core_brand'] = 0.4
        
        # Check producer overlap
        all_producers = []
        for brand in brand_details:
            all_producers.extend([p['permit'] for p in brand['producers']])
        
        if len(set(all_producers)) < len(all_producers):  # Some overlap
            factors['same_producers'] = 0.3
        
        # Check category similarity
        all_categories = set()
        for brand in brand_details:
            all_categories.update(brand['class_types'])
        
        if len(all_categories) <= 3:  # Similar categories
            factors['similar_categories'] = 0.15
        
        # Check country consistency
        all_countries = set()
        for brand in brand_details:
            all_countries.update(brand['countries'])
        
        if len(all_countries) == 1:  # Same country
            factors['same_countries'] = 0.1
        
        # Check name similarity
        brand_names = [b['brand_name'] for b in brand_details]
        avg_similarity = self._calculate_average_name_similarity(brand_names)
        factors['name_similarity'] = avg_similarity * 0.2
        
        # Check for white label conflicts (penalty)
        white_label_count = sum(1 for b in brand_details if self._is_likely_white_label(b['brand_name']))
        if 0 < white_label_count < len(brand_details):  # Mixed white label and regular
            factors['white_label_penalty'] = -0.3
        
        # Calculate final confidence
        total_confidence = sum(factors.values())
        return max(0.0, min(1.0, total_confidence)), factors
    
    def _calculate_average_name_similarity(self, brand_names: List[str]) -> float:
        """Calculate average similarity between all brand name pairs"""
        from difflib import SequenceMatcher
        
        if len(brand_names) < 2:
            return 0.0
        
        total_similarity = 0
        pair_count = 0
        
        for i in range(len(brand_names)):
            for j in range(i + 1, len(brand_names)):
                similarity = SequenceMatcher(None, brand_names[i].upper(), brand_names[j].upper()).ratio()
                total_similarity += similarity
                pair_count += 1
        
        return total_similarity / pair_count if pair_count > 0 else 0.0
    
    def _is_likely_white_label(self, brand_name: str) -> bool:
        """Check if brand is likely a white label"""
        white_label_indicators = ['KIRKLAND', 'KROGER', 'WALMART', 'TARGET', 'COSTCO', 'TRADER', 'WHOLE FOODS']
        return any(indicator in brand_name.upper() for indicator in white_label_indicators)
    
    def _determine_proposal_type(self, confidence: float, brand_details: List[Dict]) -> str:
        """Determine the type of consolidation proposal"""
        if confidence >= 0.9:
            return 'high_confidence'
        elif confidence >= 0.7:
            return 'medium_confidence'
        elif confidence >= 0.5:
            return 'low_confidence'
        else:
            return 'requires_investigation'
    
    def _generate_sku_consolidation_preview(self, brand_details: List[Dict], canonical_name: str) -> Dict:
        """Generate preview of how SKUs would be consolidated"""
        all_skus = []
        
        for brand in brand_details:
            for sku in brand['skus']:
                # Extract SKU name from original brand name
                original_brand = brand['brand_name']
                sku_name = self._extract_sku_name(original_brand, canonical_name, sku['fanciful_name'])
                
                consolidated_sku = {
                    'new_sku_name': sku_name,
                    'original_brand': original_brand,
                    'ttb_id': sku['ttb_id'],
                    'class_type': sku['class_type'],
                    'origin': sku['origin']
                }
                all_skus.append(consolidated_sku)
        
        return {
            'canonical_brand': canonical_name,
            'total_skus': len(all_skus),
            'consolidated_skus': all_skus
        }
    
    def _extract_sku_name(self, original_brand: str, canonical_name: str, fanciful_name: str) -> str:
        """Extract SKU name from original brand"""
        if fanciful_name and fanciful_name != 'nan':
            return fanciful_name
        
        # Remove canonical brand from original to get SKU portion
        sku_portion = original_brand.replace(canonical_name, '').strip()
        return sku_portion if sku_portion else 'Original'
    
    def _assess_consolidation_risks(self, brand_details: List[Dict]) -> Dict:
        """Assess potential risks of consolidation"""
        risks = []
        risk_level = 'low'
        
        # Check for mixed white label and regular brands
        white_label_count = sum(1 for b in brand_details if self._is_likely_white_label(b['brand_name']))
        if 0 < white_label_count < len(brand_details):
            risks.append('Mixed white label and regular brands - may have different brand owners')
            risk_level = 'high'
        
        # Check for very different categories
        all_categories = set()
        for brand in brand_details:
            all_categories.update(brand['class_types'])
        
        if len(all_categories) > 5:
            risks.append('Wide variety of product categories - may be unrelated brands')
            risk_level = max(risk_level, 'medium') if risk_level != 'high' else 'high'
        
        # Check for conflicting producers
        all_producers = set()
        for brand in brand_details:
            for producer in brand['producers']:
                if producer['relationship'] == 'primary_producer':
                    all_producers.add(producer['name'])
        
        if len(all_producers) > 2:
            risks.append('Multiple primary producers - may indicate separate brands')
            risk_level = max(risk_level, 'medium') if risk_level != 'high' else 'high'
        
        return {
            'level': risk_level,
            'risks': risks,
            'mitigation': 'Manual review recommended' if risk_level in ['medium', 'high'] else 'Low risk consolidation'
        }
    
    def _analyze_consolidation_benefits(self, brand_details: List[Dict]) -> Dict:
        """Analyze benefits of consolidation"""
        benefits = []
        
        total_skus = sum(len(b['skus']) for b in brand_details)
        benefits.append(f'Organize {total_skus} SKUs under unified brand')
        
        if len(brand_details) > 2:
            benefits.append(f'Consolidate {len(brand_details)} brand variations into single entity')
        
        # Check for producer attribution benefits
        unique_producers = set()
        for brand in brand_details:
            unique_producers.update(p['name'] for p in brand['producers'] if p['name'])
        
        if unique_producers:
            benefits.append(f'Clear producer attribution: {", ".join(list(unique_producers)[:2])}')
        
        # Check for Apollo.io benefits
        benefits.append('Improved Apollo.io matching with consolidated brand names')
        
        return {
            'primary_benefits': benefits,
            'estimated_improvement': 'Better brand recognition and data organization'
        }
    
    def _generate_proposal_id(self, canonical_name: str) -> str:
        """Generate unique proposal ID"""
        import hashlib
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        brand_hash = hashlib.md5(canonical_name.encode()).hexdigest()[:8]
        return f'PROP_{timestamp}_{brand_hash}'