"""
Test the concurrent GeoJSON processor with just a few entries to verify formatting.
"""
import asyncio
from process_geojson_concurrent import process_owners_concurrent

async def test_small_batch():
    """Test with just a few known business names."""
    test_owners = {
        "A2 HOLDINGS INC",
        "UNION CO-OP",
        "MTD PRODUCTS LIMITED"
    }
    
    print(f"🧪 Testing concurrent processor with {len(test_owners)} test businesses...")
    
    results = await process_owners_concurrent(test_owners, 'test_owner_lookups')
    
    print(f"\n✅ Test completed!")
    print(f"📊 Results: {len(results)} businesses processed")
    
    for owner, result in results.items():
        status = "✅ Match" if result.get('match', False) else "❌ No match"
        confidence = result.get('confidence_score', 0) * 100
        print(f"   {status} - {owner} ({confidence:.0f}% confidence)")

if __name__ == "__main__":
    asyncio.run(test_small_batch())