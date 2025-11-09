#!/usr/bin/env python3
"""
Filter Unmatched Business Lookup Results
=======================================

This script filters the comprehensive business lookup details file to extract
only businesses that did NOT get a direct match during the lookup process.
These are businesses where the search didn't find an exact match.

Usage:
    python filter_unmatched_businesses.py [input_file] [output_file]

Examples:
    python filter_unmatched_businesses.py business_lookup_details_20251106_003018.txt
    python filter_unmatched_businesses.py input.txt unmatched_companies.txt
"""

import os
import sys
import re
from datetime import datetime
from typing import List, Dict, Optional

def parse_business_entry(entry_text: str) -> Optional[Dict[str, str]]:
    """
    Parse a single business lookup entry to extract key information.
    
    Args:
        entry_text: Text content of a single business lookup entry
        
    Returns:
        Dictionary containing parsed business information, or None if parsing fails
    """
    try:
        business_info = {}
        
        # Extract business lookup number and name from header
        header_match = re.search(r'BUSINESS LOOKUP #(\d+): (.+?)(?:\n|$)', entry_text)
        if header_match:
            business_info['LOOKUP_NUMBER'] = header_match.group(1)
            business_info['SEARCH_NAME'] = header_match.group(2).strip()
        
        # Extract detailed company information section
        detailed_section = re.search(
            r'DETAILED COMPANY INFORMATION \(Result #1\)\n=+\n\n(.*?)\n\n=+', 
            entry_text, 
            re.DOTALL
        )
        
        if detailed_section:
            detailed_content = detailed_section.group(1)
            
            # Parse key-value pairs from detailed section
            for line in detailed_content.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().upper()
                    value = value.strip()
                    if key and value:
                        business_info[key] = value
        
        # Extract match information
        match_found = re.search(r'MATCH FOUND: (YES|NO)', entry_text)
        if match_found:
            business_info['MATCH_FOUND'] = match_found.group(1)
        
        confidence_match = re.search(r'CONFIDENCE: (\d+%)', entry_text)
        if confidence_match:
            business_info['CONFIDENCE'] = confidence_match.group(1)
        
        closest_match = re.search(r'CLOSEST MATCH: (.+?)(?:\n|$)', entry_text)
        if closest_match:
            business_info['CLOSEST_MATCH'] = closest_match.group(1).strip()
        
        # Check for direct match indicators in debug information
        debug_section = re.search(
            r'MATCHING DEBUG INFORMATION\n-+\n(.*?)\n-+', 
            entry_text, 
            re.DOTALL
        )
        
        if debug_section:
            debug_content = debug_section.group(1)
            
            # Look for direct match confirmation
            if "✅ Direct match found" in debug_content:
                business_info['DIRECT_MATCH'] = True
            elif "❌ No direct match found" in debug_content:
                business_info['DIRECT_MATCH'] = False
            else:
                # If no explicit direct match info, assume no direct match
                business_info['DIRECT_MATCH'] = False
        else:
            # If no debug section, assume no direct match
            business_info['DIRECT_MATCH'] = False
        
        return business_info
        
    except Exception as e:
        print(f"Error parsing business entry: {e}")
        return None

def extract_business_entries(file_content: str) -> List[str]:
    """
    Extract individual business lookup entries from the file content.
    
    Args:
        file_content: Full content of the business lookup details file
        
    Returns:
        List of individual business entry texts
    """
    # Split by business lookup headers
    entries = re.split(r'(?=================================================================================\nBUSINESS LOOKUP #\d+:)', file_content)
    
    # Remove the header section (first split result)
    if entries and not entries[0].startswith('BUSINESS LOOKUP #'):
        entries = entries[1:]
    
    # Clean up entries and add back the separator line
    cleaned_entries = []
    for entry in entries:
        if entry.strip():
            if not entry.startswith('='):
                entry = '=' * 80 + '\n' + entry
            cleaned_entries.append(entry.strip())
    
    return cleaned_entries

def filter_unmatched_businesses(entries: List[str]) -> List[Dict[str, str]]:
    """
    Filter business entries to find those without direct matches.
    
    Args:
        entries: List of business entry texts
        
    Returns:
        List of parsed business info dictionaries for businesses without direct matches
    """
    unmatched_businesses = []
    
    print(f"Processing {len(entries)} business entries to find unmatched businesses...")
    
    for i, entry in enumerate(entries, 1):
        try:
            business_info = parse_business_entry(entry)
            
            if business_info:
                # Check if this business did NOT get a direct match
                direct_match = business_info.get('DIRECT_MATCH', False)
                
                if not direct_match:
                    business_info['_ORIGINAL_ENTRY'] = entry  # Store original entry for output
                    unmatched_businesses.append(business_info)
                    search_name = business_info.get('SEARCH_NAME', 'Unknown')
                    match_found = business_info.get('MATCH_FOUND', 'Unknown')
                    confidence = business_info.get('CONFIDENCE', 'N/A')
                    print(f"  ❌ Unmatched #{len(unmatched_businesses)}: {search_name} - Match: {match_found}, Confidence: {confidence}")
                else:
                    print(f"  ✅ Entry #{i}: {business_info.get('SEARCH_NAME', 'Unknown')} - Has direct match (skipped)")
            else:
                print(f"  ❌ Entry #{i}: Failed to parse")
                
        except Exception as e:
            print(f"  ❌ Entry #{i}: Error processing - {e}")
    
    return unmatched_businesses

def create_unmatched_report(unmatched_businesses: List[Dict[str, str]], 
                           output_file: str, 
                           original_file: str) -> None:
    """
    Create a new report file with only the unmatched businesses.
    
    Args:
        unmatched_businesses: List of unmatched business information
        output_file: Path to output file
        original_file: Name of the original file
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write("=" * 80 + "\n")
            f.write("UNMATCHED BUSINESS LOOKUP REPORT\n")
            f.write("=" * 80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Source file: {original_file}\n")
            f.write(f"Total unmatched businesses: {len(unmatched_businesses)}\n")
            f.write("Filter: Businesses without direct matches only\n")
            f.write("=" * 80 + "\n\n")
            
            # Write summary
            if unmatched_businesses:
                f.write("SUMMARY OF UNMATCHED BUSINESSES\n")
                f.write("-" * 80 + "\n")
                for i, business in enumerate(unmatched_businesses, 1):
                    search_name = business.get('SEARCH_NAME', 'Unknown')
                    company_name = business.get('COMPANY NAME', business.get('CLOSEST_MATCH', 'Unknown'))
                    status = business.get('STATUS', 'Unknown')
                    address = business.get('ADDRESS', 'Unknown')
                    match_found = business.get('MATCH_FOUND', 'Unknown')
                    confidence = business.get('CONFIDENCE', 'N/A')
                    
                    f.write(f"{i:3d}. SEARCHED FOR: {search_name}\n")
                    f.write(f"     FOUND: {company_name}\n")
                    f.write(f"     Status: {status} | Address: {address}\n")
                    f.write(f"     Match Found: {match_found} | Confidence: {confidence}\n")
                    f.write(f"\n")
                    
                f.write("=" * 80 + "\n\n")
            
            # Write detailed entries
            f.write("DETAILED BUSINESS INFORMATION\n")
            f.write("=" * 80 + "\n\n")
            
            for business in unmatched_businesses:
                original_entry = business.get('_ORIGINAL_ENTRY', '')
                if original_entry:
                    f.write(original_entry + "\n\n\n")
        
        print(f"\n✅ Unmatched businesses report created: {os.path.abspath(output_file)}")
        print(f"   Found {len(unmatched_businesses)} businesses without direct matches")
        
    except Exception as e:
        print(f"❌ Error creating unmatched businesses report: {e}")

def main():
    """Main function."""
    # Parse command line arguments
    if len(sys.argv) < 2:
        print("Usage: python filter_unmatched_businesses.py <input_file> [output_file]")
        print("\nExamples:")
        print("  python filter_unmatched_businesses.py business_lookup_details_20251106_003018.txt")
        print("  python filter_unmatched_businesses.py input.txt unmatched_companies.txt")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    # Generate output filename if not provided
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_file = f"{base_name}_unmatched_businesses.txt"
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"❌ Error: Input file '{input_file}' not found!")
        sys.exit(1)
    
    print("=" * 60)
    print("UNMATCHED BUSINESS FILTER")
    print("=" * 60)
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    print(f"Filter: Businesses without direct matches")
    print("-" * 60)
    
    try:
        # Read the input file
        print("Reading input file...")
        with open(input_file, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        # Extract individual business entries
        print("Extracting business entries...")
        entries = extract_business_entries(file_content)
        print(f"Found {len(entries)} business entries")
        
        # Filter for unmatched businesses
        print("\nFiltering for unmatched businesses...")
        unmatched_businesses = filter_unmatched_businesses(entries)
        
        # Create unmatched businesses report
        print(f"\nCreating unmatched businesses report...")
        create_unmatched_report(unmatched_businesses, output_file, input_file)
        
        print("\n" + "=" * 60)
        print("FILTERING COMPLETE")
        print("=" * 60)
        
        if unmatched_businesses:
            print(f"✅ Successfully found {len(unmatched_businesses)} unmatched businesses")
            print(f"📄 Report saved to: {os.path.abspath(output_file)}")
        else:
            print(f"✅ No unmatched businesses found - all searches had direct matches!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()