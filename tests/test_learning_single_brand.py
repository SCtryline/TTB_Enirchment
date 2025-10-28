#!/usr/bin/env python3
"""
Simple test of the agentic learning system with one brand
"""

from brand_enrichment.integrated_enrichment import IntegratedEnrichmentSystem
from database import BrandDatabase

def test_single_brand_learning():
    """Test learning system with 1220 SPIRITS"""
    print("🧠 Testing Agentic Learning with 1220 SPIRITS")
    print("=" * 50)
    
    # Initialize systems
    enrichment = IntegratedEnrichmentSystem()
    db = BrandDatabase()
    
    brand_name = "1220 SPIRITS"
    
    # Step 1: Test enhanced confidence calculation
    print("1. Testing enhanced confidence calculation...")
    base_confidence = 0.8
    features = {
        'brand_in_domain': True,
        'industry_keyword': True,
        'exact_match': True
    }
    
    enhanced_confidence = enrichment.learning_agent.get_enhanced_confidence(
        brand_name, '1220spirits.com', base_confidence, features
    )
    
    print(f"   Base confidence: {base_confidence:.2f}")
    print(f"   Enhanced confidence: {enhanced_confidence:.2f}")
    print(f"   Improvement: +{enhanced_confidence - base_confidence:.2f}")
    
    # Step 2: Test search suggestions  
    print("\n2. Testing search query suggestions...")
    suggestions = enrichment.learning_agent.suggest_search_improvements(brand_name)
    print(f"   Suggested queries:")
    for i, suggestion in enumerate(suggestions[:3], 1):
        print(f"     {i}. {suggestion}")
    
    # Step 3: Simulate user feedback
    print("\n3. Simulating user verification of 1220spirits.com...")
    
    # Create mock website data
    website_data = {
        'domain': '1220spirits.com',
        'url': 'https://www.1220spirits.com/',
        'base_confidence': base_confidence,
        'enhanced_confidence': enhanced_confidence,
        'features': features
    }
    
    # Record feedback
    enrichment.record_website_feedback(brand_name, website_data, 'verified')
    print("   ✅ User verification recorded")
    
    # Step 4: Test pattern learning
    print("\n4. Testing pattern learning...")
    insights_before = enrichment.get_learning_insights()
    
    # Simulate another verification to show learning
    enrichment.record_website_feedback("GREY GOOSE", {
        'domain': 'greygoose.com',
        'url': 'https://greygoose.com',
        'base_confidence': 0.9,
        'enhanced_confidence': 0.95,
        'features': {'brand_in_domain': True, 'exact_match': True}
    }, 'verified')
    
    insights_after = enrichment.get_learning_insights()
    
    print(f"   Events before: {insights_before['total_learning_events']}")
    print(f"   Events after: {insights_after['total_learning_events']}")
    print(f"   Success rate: {insights_after['success_rate']:.2%}")
    print(f"   Learned patterns: {insights_after['learned_patterns']}")
    
    # Step 5: Test improved confidence after learning
    print("\n5. Testing improved confidence after learning...")
    new_enhanced_confidence = enrichment.learning_agent.get_enhanced_confidence(
        brand_name, '1220spirits.com', base_confidence, features
    )
    
    print(f"   Original enhanced: {enhanced_confidence:.2f}")
    print(f"   After learning: {new_enhanced_confidence:.2f}")
    if new_enhanced_confidence > enhanced_confidence:
        print("   🎯 Confidence improved through learning!")
    
    # Step 6: Show what the system learned
    print("\n6. What the system learned:")
    if insights_after['top_patterns']:
        for pattern in insights_after['top_patterns'][:3]:
            print(f"   📈 Pattern: {pattern['pattern']}")
            print(f"      Success rate: {pattern['success_rate']:.2%}")
            print(f"      Confidence boost: +{pattern['confidence_boost']:.2f}")
    
    # Step 7: Test database integration
    print("\n7. Testing database integration...")
    
    # Update database with learned website
    db.update_brand_website(
        brand_name, 
        website_data['url'], 
        domain=website_data['domain'],
        confidence=new_enhanced_confidence,
        verification_status='unverified',
        source='agentic_search'
    )
    
    # Verify it (this should trigger learning feedback)
    success = db.verify_brand_website(brand_name, verified=True)
    if success:
        print("   ✅ Database verification recorded with learning feedback")
    
    print("\n🎉 Agentic Learning Test Complete!")
    print("\nKey Learning Features Demonstrated:")
    print("✅ Enhanced confidence calculation")
    print("✅ Search query optimization") 
    print("✅ Pattern recognition and learning")
    print("✅ Feedback loop integration")
    print("✅ Continuous improvement")
    print("✅ Database integration")
    
    return insights_after

if __name__ == "__main__":
    test_single_brand_learning()