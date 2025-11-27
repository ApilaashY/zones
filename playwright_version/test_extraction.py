#!/usr/bin/env python3

"""
Quick test script to verify the extract_company_info_from_html function
returns cleaned content correctly.
"""
import sys
import os
import asyncio
from pathlib import Path

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the function we want to test
from process_geojson_concurrent import extract_company_info_from_html

# Test the function with mock HTML content
test_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Company Search Results</title>
</head>
<body>
    <div class="search-results">
        <h2>ABSOLUTE HOLDINGS INC.</h2>
        <p>Status: Active</p>
        <p>Business Type: Ontario Business Corporation</p>
        <p>Incorporation Date: January 1, 2020</p>
        <p>Location: Toronto, Ontario, Canada</p>
        <p>Ontario Corporation Number: 123456789</p>
    </div>
    <script>
        // Some JavaScript that should be removed
        console.log("This should be cleaned out");
    </script>
</body>
</html>
"""

def test_extract_function():
    print("Testing extract_company_info_from_html function...")
    
    try:
        company_info, cleaned_content = extract_company_info_from_html(
            test_html, 
            "ABSOLUTE HOLDINGS INC", 
            "test_output.txt"
        )
        
        print("✅ Function executed successfully!")
        print(f"📊 Company Info: {company_info}")
        print(f"🧹 Cleaned Content Length: {len(cleaned_content)} characters")
        print(f"📝 Cleaned Content Preview (first 200 chars):")
        print(cleaned_content[:200])
        print("..." if len(cleaned_content) > 200 else "")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_extract_function()