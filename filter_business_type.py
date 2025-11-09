#!/usr/bin/env python3
"""
Filter Business Lookup Results by Business Type
==============================================

This script filters the comprehensive business lookup details file to extract
only companies with a specific business type (default: "Not-for-Profit Corporation").

Usage:
    python filter_business_type.py [input_file] [business_type] [output_file]

Examples:
    python filter_business_type.py business_lookup_details_20251106_003018.txt
    python filter_business_type.py input.txt "Not-for-Profit Corporation" nonprofit_corps.txt
    python filter_business_type.py input.txt "Ontario Business Corporation" regular_corps.txt
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

def filter_by_business_type(entries: List[str], target_business_type: str) -> List[Dict[str, str]]:
    """
    Filter business entries by business type.
    
    Args:
        entries: List of business entry texts
        target_business_type: Business type to filter for
        
    Returns:
        List of parsed business info dictionaries that match the target type
    """
    filtered_businesses = []
    
    print(f"Filtering for business type: '{target_business_type}'")
    print(f"Processing {len(entries)} business entries...")
    
    for i, entry in enumerate(entries, 1):
        try:
            business_info = parse_business_entry(entry)
            
            if business_info:
                business_type = business_info.get('BUSINESS TYPE', '').strip()
                
                # Check if business type matches (case-insensitive)
                if business_type.lower() == target_business_type.lower():
                    business_info['_ORIGINAL_ENTRY'] = entry  # Store original entry for output
                    filtered_businesses.append(business_info)
                    print(f"  ✅ Match #{len(filtered_businesses)}: {business_info.get('SEARCH_NAME', 'Unknown')} - {business_type}")
                else:
                    print(f"  ⏭️  Entry #{i}: {business_info.get('SEARCH_NAME', 'Unknown')} - {business_type} (skipped)")
            else:
                print(f"  ❌ Entry #{i}: Failed to parse")
                
        except Exception as e:
            print(f"  ❌ Entry #{i}: Error processing - {e}")
    
    return filtered_businesses

def create_filtered_report(filtered_businesses: List[Dict[str, str]], 
                          output_file: str, 
                          target_business_type: str,
                          original_file: str) -> None:
    """
    Create a new report file with only the filtered businesses summary.
    
    Args:
        filtered_businesses: List of filtered business information
        output_file: Path to output file
        target_business_type: Business type that was filtered for
        original_file: Name of the original file
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write("=" * 80 + "\n")
            f.write(f"FILTERED BUSINESS LOOKUP REPORT - {target_business_type.upper()}\n")
            f.write("=" * 80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Source file: {original_file}\n")
            f.write(f"Business type filter: {target_business_type}\n")
            f.write(f"Total matching businesses: {len(filtered_businesses)}\n")
            f.write("=" * 80 + "\n\n")
            
            # Write summary
            if filtered_businesses:
                f.write("SUMMARY OF FILTERED BUSINESSES\n")
                f.write("-" * 80 + "\n")
                for i, business in enumerate(filtered_businesses, 1):
                    company_name = business.get('COMPANY NAME', business.get('SEARCH_NAME', 'Unknown'))
                    status = business.get('STATUS', 'Unknown')
                    address = business.get('ADDRESS', 'Unknown')
                    f.write(f"{i:3d}. {company_name}\n")
                    f.write(f"     Status: {status} | Address: {address}\n")
                f.write("\n" + "=" * 80 + "\n")
        
        print(f"\n✅ Filtered report created: {os.path.abspath(output_file)}")
        print(f"   Found {len(filtered_businesses)} businesses of type '{target_business_type}'")
        print(f"   Report type: Summary only")
        
    except Exception as e:
        print(f"❌ Error creating filtered report: {e}")

def main():
    """Main function."""
    # Parse command line arguments
    if len(sys.argv) < 2:
        print("Usage: python filter_business_type.py <input_file> [business_type] [output_file]")
        print("\nExamples:")
        print("  python filter_business_type.py business_lookup_details_20251106_003018.txt")
        print("  python filter_business_type.py input.txt 'Not-for-Profit Corporation'")
        print("  python filter_business_type.py input.txt 'Ontario Business Corporation' regular_corps.txt")
        sys.exit(1)
    
    input_file = sys.argv[1]
    business_type = sys.argv[2] if len(sys.argv) > 2 else "Not-for-Profit Corporation"
    
    # Generate output filename if not provided
    if len(sys.argv) > 3:
        output_file = sys.argv[3]
    else:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        safe_type = re.sub(r'[^\w\-_]', '_', business_type.lower().replace(' ', '_'))
        output_file = f"{base_name}_filtered_{safe_type}.txt"
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"❌ Error: Input file '{input_file}' not found!")
        sys.exit(1)
    
    print("=" * 60)
    print("BUSINESS LOOKUP FILTER")
    print("=" * 60)
    print(f"Input file: {input_file}")
    print(f"Business type filter: '{business_type}'")
    print(f"Output file: {output_file}")
    print(f"Report type: Summary only")
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
        
        # Filter by business type
        print("\nFiltering by business type...")
        filtered_businesses = filter_by_business_type(entries, business_type)
        
        # Create filtered report
        print(f"\nCreating filtered report...")
        create_filtered_report(filtered_businesses, output_file, business_type, input_file)
        
        print("\n" + "=" * 60)
        print("FILTERING COMPLETE")
        print("=" * 60)
        
        if filtered_businesses:
            print(f"✅ Successfully filtered {len(filtered_businesses)} businesses")
            print(f"📄 Report saved to: {os.path.abspath(output_file)}")
        else:
            print(f"⚠️  No businesses found matching type: '{business_type}'")
            print("Available business types in the file:")
            
            # Show available business types
            all_types = set()
            for entry in entries[:10]:  # Check first 10 entries for types
                business_info = parse_business_entry(entry)
                if business_info and 'BUSINESS TYPE' in business_info:
                    all_types.add(business_info['BUSINESS TYPE'])
            
            for btype in sorted(all_types):
                print(f"  - {btype}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()