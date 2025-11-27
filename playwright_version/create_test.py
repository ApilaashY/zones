#!/usr/bin/env python3

"""
Test script to run a small concurrent batch and verify HTML content is being appended to text files.
"""
import json
import sys
import os
from pathlib import Path

# Test with just a few companies
test_companies = [
    "AIDEZ PROPERTIES INC",  # We know this one works
    "A2 HOLDINGS INC", 
    "AAA1947 CANADA INC"
]

def create_test_geojson():
    """Create a small test GeoJSON with just a few companies."""
    test_data = {
        "type": "FeatureCollection", 
        "features": []
    }
    
    for i, company in enumerate(test_companies):
        feature = {
            "type": "Feature",
            "properties": {
                "OWNER": company,
                "PROPERTY_ID": f"test_{i}"
            },
            "geometry": {
                "type": "Point", 
                "coordinates": [-79.0, 43.0]
            }
        }
        test_data["features"].append(feature)
    
    # Save test GeoJSON
    with open("test_geojson.json", "w") as f:
        json.dump(test_data, f)
    
    return "test_geojson.json"

if __name__ == "__main__":
    print("🔬 Creating test environment...")
    
    # Create test GeoJSON
    test_file = create_test_geojson()
    print(f"✅ Created test GeoJSON: {test_file}")
    
    # Update the process script to use our test file
    print(f"🚀 Run the following command to test with {len(test_companies)} companies:")
    print(f"python process_geojson_concurrent.py --geojson {test_file}")
    print("This will process a small batch to verify HTML cleaning works correctly.")