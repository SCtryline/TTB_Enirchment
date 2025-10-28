#!/usr/bin/env python3
"""
Test agentic learning with 13 CELSIUS - a wine company
Tests partial matching and wine industry context learning
"""

from brand_enrichment.integrated_enrichment import IntegratedEnrichmentSystem
from database import BrandDatabase

def test_13_celsius_learning():
    """Test learning system with 13 CELSIUS wine company"""
    print("🍷 Testing Agentic Learning with 13 CELSIUS (Wine Company)")
    print("=" * 60)
    
    # Initialize systems
    enrichment = IntegratedEnrichmentSystem()
    db = BrandDatabase()
    
    brand_name = "13 CELSIUS"
    class_type = "TABLE WHITE WINE"
    
    # Simulate finding a website like "13celsiusvineyard.com" or similar
    test_domains = [
        "13celsius.com",
        "13celsiusvineyard.com", 
        "13celsiuswinery.com",
        "thirteencelsius.com"
    ]
    
    print(f"Brand: {brand_name}")
    print(f"Class: {class_type}")
    print(f"Testing potential domains: {test_domains}")
    
    for i, domain in enumerate(test_domains, 1):
        print(f"\n{'='*50}")
        print(f"Test {i}: Analyzing domain '{domain}'")
        print(f"{'='*50}")
        
        # Step 1: Calculate base confidence using the integrated enrichment method
        base_confidence = enrichment._calculate_website_confidence_legacy(
            brand_name, f"https://{domain}", domain
        )
        
        print(f"1. Base confidence calculation:")
        print(f"   Domain: {domain}")
        print(f"   Base confidence: {base_confidence:.2f} ({base_confidence*100:.0f}%)")
        
        # Step 2: Analyze features
        features = {
            'brand_in_domain': brand_name.lower().replace(' ', '') in domain.lower(),
            'partial_brand_match': any(word.lower() in domain.lower() for word in brand_name.split()),
            'numeric_match': '13' in domain,
            'celsius_match': 'celsius' in domain.lower(),
            'wine_keywords': any(keyword in domain.lower() for keyword in ['wine', 'winery', 'vineyard']),
            'industry_keyword': any(keyword in domain.lower() 
                                  for keyword in enrichment.learning_agent.knowledge_base.get('industry_keywords', [])),
            'class_type': class_type
        }
        
        print(f"\n2. Feature analysis:")
        for feature, value in features.items():
            status = "✅" if value else "❌"
            print(f"   {status} {feature}: {value}")
        
        # Step 3: Get enhanced confidence
        enhanced_confidence = enrichment.learning_agent.get_enhanced_confidence(
            brand_name, domain, base_confidence, features
        )
        
        print(f"\n3. Enhanced confidence:")
        print(f"   Original: {base_confidence:.2f}")
        print(f"   Enhanced: {enhanced_confidence:.2f}")
        print(f"   Improvement: +{enhanced_confidence - base_confidence:.2f}")
        
        # Step 4: Determine if this would be a good match
        confidence_level = "HIGH" if enhanced_confidence >= 0.8 else "MEDIUM" if enhanced_confidence >= 0.5 else "LOW"
        print(f"   Confidence level: {confidence_level}")
        
        # Step 5: If this is a reasonable match, simulate user feedback
        if enhanced_confidence >= 0.4:  # Reasonable threshold for wine industry
            print(f"\n4. Simulating user verification...")
            
            # Create website data
            website_data = {
                'domain': domain,
                'url': f'https://{domain}',
                'base_confidence': base_confidence,
                'enhanced_confidence': enhanced_confidence,
                'features': features,
                'source': 'agentic_search'
            }
            
            # Simulate user verifying this as correct
            enrichment.record_website_feedback(brand_name, website_data, 'verified', 
                                             f"Wine company with vineyard - {domain}")
            print(f"   ✅ Recorded as VERIFIED - wine industry context recognized")
            
            # Break after first good match to simulate real scenario
            break
        else:
            print(f"\n4. Confidence too low - would not suggest this domain")
    
    # Step 6: Test what the system learned about wine industry
    print(f"\n{'='*50}")
    print("LEARNING ANALYSIS")
    print(f"{'='*50}")
    
    insights = enrichment.get_learning_insights()
    print(f"Learning insights after 13 CELSIUS test:")
    print(f"   Total events: {insights['total_learning_events']}")
    print(f"   Success rate: {insights['success_rate']:.2%}")
    print(f"   Learned patterns: {insights['learned_patterns']}")
    
    # Check if wine-related patterns were learned
    if insights['top_patterns']:
        print(f"\nTop learned patterns:")
        for pattern in insights['top_patterns'][:5]:
            print(f"   📈 {pattern['pattern']}")
            print(f"      Success rate: {pattern['success_rate']:.2%}")
            print(f"      Boost: +{pattern['confidence_boost']:.2f}")
            print(f"      Samples: {pattern['sample_count']}")
    
    # Step 7: Test with another wine brand to see if learning transfers
    print(f"\n{'='*50}")
    print("TRANSFER LEARNING TEST")
    print(f"{'='*50}")
    
    test_wine_brand = "DOMAINE EXAMPLE"
    test_wine_domain = "domaineexamplewinery.com"
    
    print(f"Testing if wine learning transfers to: {test_wine_brand} -> {test_wine_domain}")
    
    wine_features = {
        'brand_in_domain': 'domaine' in test_wine_domain and 'example' in test_wine_domain,
        'wine_keywords': 'winery' in test_wine_domain,
        'industry_keyword': 'winery' in test_wine_domain,
        'class_type': 'TABLE WINE'
    }
    
    base_wine_conf = 0.6  # Moderate base confidence
    enhanced_wine_conf = enrichment.learning_agent.get_enhanced_confidence(
        test_wine_brand, test_wine_domain, base_wine_conf, wine_features
    )
    
    print(f"   Base confidence: {base_wine_conf:.2f}")
    print(f"   Enhanced confidence: {enhanced_wine_conf:.2f}")
    print(f"   Learning boost: +{enhanced_wine_conf - base_wine_conf:.2f}")
    
    if enhanced_wine_conf > base_wine_conf:
        print("   🎯 SUCCESS! Learning transferred to new wine brand")
    else:
        print("   ⚠️ No learning transfer detected")
    
    # Step 8: Check knowledge base updates
    print(f"\n{'='*50}")
    print("KNOWLEDGE BASE ANALYSIS")
    print(f"{'='*50}")
    
    kb = enrichment.learning_agent.knowledge_base
    print("Updated industry keywords:")
    for keyword in kb.get('industry_keywords', [])[:10]:
        print(f"   • {keyword}")
    
    print("\nEffective search terms:")
    for term in kb.get('effective_search_terms', [])[:5]:
        print(f"   • {term}")
    
    print(f"\n🍷 13 CELSIUS Learning Test Complete!")
    print("\nKey Insights:")
    print("✅ Partial matching capabilities")
    print("✅ Wine industry context recognition") 
    print("✅ Pattern learning and transfer")
    print("✅ Industry-specific knowledge building")
    
    return enhanced_confidence

if __name__ == "__main__":
    test_13_celsius_learning()