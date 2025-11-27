"""
Process GeoJSON owners using concurrent Playwright scraper for much faster performance.
"""
import json
import os
import sys
import time
from datetime import datetime
from typing import List, Dict, Set, Optional, Tuple
from concurrent_scraper import ConcurrentPlaywrightScraper, SearchResult
from tqdm import tqdm
import asyncio
import re
from bs4 import BeautifulSoup

# Configuration
SAVE_DEBUG_FILES = True
OUTPUT_FOLDER = 'business_lookup_output'
BATCH_SIZE = 5   # Number of businesses to process concurrently (reduced for stability)
MAX_CONCURRENT = 2  # Number of concurrent browser contexts (reduced for stability)

def ensure_output_folder():
    """Create the output folder if it doesn't exist."""
    if SAVE_DEBUG_FILES and not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        print(f"Created output folder: {OUTPUT_FOLDER}")

def get_output_path(filename: str) -> str:
    """Get the full path for an output file."""
    if SAVE_DEBUG_FILES:
        ensure_output_folder()
        return os.path.join(OUTPUT_FOLDER, filename)
    return filename

def is_private_owner(owner_name: str) -> bool:
    """
    Check if the owner name should be processed.
    Returns True if the owner is a private individual (should be processed),
    False if it's a corporation (should be skipped).
    """
    if not owner_name or not isinstance(owner_name, str):
        return False
    
    owner_upper = owner_name.upper().strip()
    
    # Skip empty or very short names
    if len(owner_upper) < 3:
        return False
    
    # Check for "LTD" or "LIMITED" in the name (case-insensitive)
    if 'LTD' in owner_upper or 'LIMITED' in owner_upper:
        return False
    
    # Split into words for more precise matching
    words = owner_upper.split()
    if not words:
        return False
    
    # Only exclude 'LTD' and 'LIMITED' as corporate indicators
    corporate_indicators = {'LTD', 'LIMITED'}
    if any(word in corporate_indicators for word in words):
        return False
    
    # Check for numbers in the name (often indicates a business)
    if any(word.isdigit() for word in words):
        numbers = [int(word) for word in words if word.isdigit()]
        if not any(1900 <= num <= 2100 for num in numbers):
            return False
    
    # Check for common business patterns like "123 MAIN ST" or "ABC 123"
    if len(words) >= 2:
        if words[0].isdigit() and len(words[0]) <= 4 and len(words[1]) > 2:
            return False
        if words[-1].isdigit() and len(words[-1]) <= 4 and len(words[-2]) > 2:
            return False
    
    # Common indicators of private ownership
    private_indicators = {'PRIVATE'}
    if any(word in private_indicators for word in words):
        return True
    
    # Check for name patterns like "Last, First" or "First Last"
    if 2 <= len(words) <= 4:
        if all(word[0].isupper() if word else False for word in words):
            vowels = {'A', 'E', 'I', 'O', 'U'}
            if all(any(c in vowels for c in word) for word in words if len(word) > 2):
                return True
    
    return False

def extract_owners_from_geojson(geojson_path: str, debug: bool = False) -> Set[str]:
    """Extract unique owner names from a GeoJSON file, excluding corporate names."""
    try:
        with open(geojson_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        owners = set()
        corporate_owners = set()
        private_owners = set()
        
        features = data.get('features', [])
        if not features and isinstance(data, dict) and 'type' in data and data['type'] == 'Feature':
            features = [data]
        
        for feature in features:
            if not isinstance(feature, dict) or 'properties' not in feature:
                continue
                
            props = feature.get('properties', {})
            owner = props.get('OWNERNAME', '').strip()
            
            if not owner:
                continue
                
            if is_private_owner(owner):
                private_owners.add(owner)
            else:
                corporate_owners.add(owner)
        
        if debug:
            with open('filtered_owners.txt', 'w', encoding='utf-8') as f:
                f.write("=== PRIVATE OWNERS (TO BE PROCESSED) ===\n\n")
                for i, owner in enumerate(sorted(private_owners), 1):
                    f.write(f"{i:4}. {owner}\n")
            
            with open('excluded_owners.txt', 'w', encoding='utf-8') as f:
                f.write("=== EXCLUDED CORPORATE OWNERS ===\n\n")
                f.write(f"Total excluded: {len(corporate_owners)}\n\n")
                
                exclusion_reasons = {
                    'LTD/LIMITED': [o for o in corporate_owners 
                                   if 'LTD' in o.upper() or 'LIMITED' in o.upper()]
                }
                
                for reason, owners_list in exclusion_reasons.items():
                    if owners_list:
                        f.write(f"\n=== {reason} ({len(owners_list)}) ===\n\n")
                        for i, owner in enumerate(sorted(owners_list), 1):
                            f.write(f"{i:4}. {owner}\n")
            
            print(f"\nDebug files created:")
            print(f"- filtered_owners.txt: {len(private_owners)} owners to be processed")
            print(f"- excluded_owners.txt: {len(corporate_owners)} excluded owners")
        
        return private_owners
        
    except Exception as e:
        print(f"Error processing GeoJSON file: {e}")
        return set()

def extract_company_info_from_html(html_content: str, business_name: str, report_file: str = None) -> tuple[Dict[str, str], str]:
    """Extract company information from HTML content using BeautifulSoup parsing"""
    if not html_content:
        return {}, ""
    
    try:
        # Import and use the clean_html function
        from clean_html import clean_html_content
        
        # Clean the HTML to extract structured data
        cleaned_content = clean_html_content(html_content)
        
        if not cleaned_content:
            return {}, ""
        
        # Parse the cleaned content with BeautifulSoup
        from bs4 import BeautifulSoup
        import re
        
        soup = BeautifulSoup(cleaned_content, 'html.parser')
        
        # Check if "No results found" or similar messages exist
        if "no results found" in cleaned_content.lower() or "no matches" in cleaned_content.lower():
            return {
                'COMPANY_NAME': business_name,
                'STATUS': 'No Results Found',
                'BUSINESS_TYPE': 'N/A',
                'INCORPORATION_DATE': 'N/A',
                'LOCATION': 'N/A',
                'ONTARIO_CORP_NUMBER': 'N/A'
            }, cleaned_content
        
        # Look for company links in the cleaned HTML
        # Find all links that contain company names and numbers
        company_links = soup.find_all('a', string=re.compile(r'.*\(\d+\)'))
        
        if company_links:
            # Take the first company result
            first_company = company_links[0]
            company_text = first_company.get_text().strip()
            
            # Extract company name and number
            # Pattern: "COMPANY NAME (NUMBER)"
            match = re.match(r'(.+?)\s*\((\d+)\)', company_text)
            if match:
                company_name = match.group(1).strip()
                corp_number = match.group(2).strip()
                
                # Find associated information (status, date, type, location)
                status = 'Active'  # Default
                business_type = 'N/A'
                incorporation_date = 'N/A'
                location = 'N/A'
                
                # Try to find status
                status_span = soup.find('span', class_='appMinimalValue', string=re.compile(r'Active|Inactive|Refer to Ministry'))
                if status_span:
                    status = status_span.get_text().strip()
                
                # Try to find business type
                business_type_spans = soup.find_all('span', string=re.compile(r'Co-operative|Corporation|Credit Union'))
                if business_type_spans:
                    business_type = business_type_spans[0].get_text().strip()
                
                # Try to find incorporation date
                date_spans = soup.find_all('span', string=re.compile(r'\w+ \d{1,2}, \d{4}'))
                if date_spans:
                    incorporation_date = date_spans[0].get_text().strip()
                
                # Try to find location
                location_divs = soup.find_all('div', class_='appAttrValue', string=re.compile(r'.*Ontario.*Canada'))
                if location_divs:
                    location = location_divs[0].get_text().strip()
                
                return {
                    'COMPANY_NAME': company_name,
                    'STATUS': status,
                    'BUSINESS_TYPE': business_type,
                    'INCORPORATION_DATE': incorporation_date,
                    'LOCATION': location,
                    'ONTARIO_CORP_NUMBER': corp_number
                }, cleaned_content
        
        # If no company links found, try alternative parsing
        # Look for spans with company names
        company_spans = soup.find_all('span', string=re.compile(r'.*\(\d+\)'))
        if company_spans:
            first_span = company_spans[0]
            company_text = first_span.get_text().strip()
            
            # Extract basic info
            match = re.match(r'(.+?)\s*\((\d+)\)', company_text)
            if match:
                company_name = match.group(1).strip()
                corp_number = match.group(2).strip()
                
                return {
                    'COMPANY_NAME': company_name,
                    'STATUS': 'Found',
                    'BUSINESS_TYPE': 'N/A',
                    'INCORPORATION_DATE': 'N/A',
                    'LOCATION': 'N/A',
                    'ONTARIO_CORP_NUMBER': corp_number
                }
        
        # If still no results, return empty dict (will be handled as no match)
        return {}, cleaned_content
        
    except Exception as e:
        print(f"Error parsing HTML for {business_name}: {e}")
        import traceback
        traceback.print_exc()
        return {}, ""

def is_company_match(search_term: str, company_info: Dict[str, str]) -> Tuple[bool, str, float]:
    """
    Check if the company information matches the search term.
    Returns (is_match, matched_name, confidence_score)
    """
    if not company_info:
        return False, "", 0.0
    
    company_name = company_info.get('COMPANY_NAME', '')
    if not company_name:
        return False, "", 0.0
    
    # Normalize names for comparison
    search_normalized = ' '.join(re.findall(r'\w+', search_term.lower()))
    company_normalized = ' '.join(re.findall(r'\w+', company_name.lower()))
    
    # Direct match
    if search_normalized in company_normalized or company_normalized in search_normalized:
        return True, company_name, 1.0
    
    # Check word overlap
    search_words = set(search_normalized.split())
    company_words = set(company_normalized.split())
    
    if len(search_words) > 0:
        overlap = len(search_words & company_words)
        confidence = overlap / len(search_words)
        
        if confidence >= 0.7:  # 70% word match threshold
            return True, company_name, confidence
    
    return False, company_name, 0.0

async def process_owners_concurrent(owners: Set[str], output_dir: str = 'owner_lookups') -> Dict[str, Dict]:
    """Process owners using concurrent Playwright scraper."""
    if SAVE_DEBUG_FILES:
        ensure_output_folder()
        output_dir = os.path.join(OUTPUT_FOLDER, 'owner_lookups')
    
    os.makedirs(output_dir, exist_ok=True)
    results = {}
    
    # Create comprehensive details file
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    details_file = os.path.join(output_dir, f'business_lookup_details_concurrent_{timestamp}.txt')
    
    owners_list = sorted(owners)
    total_owners = len(owners_list)
    
    print(f"\n🚀 Starting concurrent processing of {total_owners} owners...")
    print(f"📊 Batch size: {BATCH_SIZE}, Max concurrent: {MAX_CONCURRENT}")
    print(f"💾 Results will be saved to: {details_file}")
    
    with open(details_file, 'w', encoding='utf-8') as details_f:
        # Write header
        details_f.write("=" * 80 + "\n")
        details_f.write("CONCURRENT BUSINESS LOOKUP DETAILS - COMPREHENSIVE REPORT\n")
        details_f.write("=" * 80 + "\n")
        details_f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        details_f.write(f"Total owners to process: {total_owners}\n")
        details_f.write(f"Processing method: Concurrent Playwright (Batch size: {BATCH_SIZE})\n")
        details_f.write("=" * 80 + "\n\n")
        
        # Process in batches
        async with ConcurrentPlaywrightScraper(max_concurrent=MAX_CONCURRENT, headless=False) as scraper:
            for batch_start in range(0, total_owners, BATCH_SIZE):
                batch_end = min(batch_start + BATCH_SIZE, total_owners)
                batch = owners_list[batch_start:batch_end]
                batch_num = (batch_start // BATCH_SIZE) + 1
                total_batches = (total_owners + BATCH_SIZE - 1) // BATCH_SIZE
                
                print(f"\n⚡ Processing batch {batch_num}/{total_batches}: {len(batch)} owners")
                
                # Search all businesses in this batch concurrently
                search_results = await scraper.search_multiple_businesses(batch)
                
                # Process results
                for i, (owner, result) in enumerate(zip(batch, search_results)):
                    entry_num = batch_start + i + 1
                    
                    print(f"📝 Processing result {entry_num}/{total_owners}: {owner}")
                    
                    # Write section header
                    details_f.write("\n" + "=" * 80 + "\n")
                    details_f.write(f"BUSINESS LOOKUP #{entry_num}: {owner}\n")
                    details_f.write("=" * 80 + "\n\n")
                    
                    if not result.success:
                        details_f.write(f"SEARCH RESULTS FOR: {owner}\n")
                        details_f.write("-" * 80 + "\n")
                        details_f.write("STATUS: Search failed\n")
                        details_f.write(f"REASON: {result.error_message}\n")
                        details_f.write(f"SEARCH TIME: {result.search_time:.2f} seconds\n")
                        details_f.write("-" * 80 + "\n\n")
                        continue
                    
                    # Extract company info from HTML and get cleaned content
                    company_info, cleaned_content = extract_company_info_from_html(result.html_content, owner, details_file)
                    
                    # Append cleaned content to details file
                    if cleaned_content.strip():
                        details_f.write(f"\nCLEANED HTML CONTENT:\n")
                        details_f.write("-" * 80 + "\n")
                        details_f.write(cleaned_content)
                        details_f.write("\n" + "-" * 80 + "\n\n")
                    
                    if not company_info:
                        details_f.write(f"SEARCH RESULTS FOR: {owner}\n")
                        details_f.write("-" * 80 + "\n")
                        details_f.write("STATUS: No company information extracted\n")
                        details_f.write("REASON: Search completed but could not parse company details\n")
                        details_f.write(f"SEARCH TIME: {result.search_time:.2f} seconds\n")
                        details_f.write("-" * 80 + "\n\n")
                        continue
                    
                    # Check for match
                    is_match, matched_name, confidence_score = is_company_match(owner, company_info)
                    
                    # Write detailed results (matching expected format)
                    details_f.write(f"SEARCH RESULTS FOR: {owner}\n")
                    details_f.write("=" * 80 + "\n\n")
                    
                    # Company details section
                    details_f.write("COMPANY DETAILS\n")
                    details_f.write("-" * 80 + "\n")
                    
                    # Define the order of fields we want to display (matching original format)
                    field_order = [
                        'COMPANY_NAME', 'CORPORATION_NUMBER', 'REGISTRY_TYPE', 'STATUS',
                        'ADDRESS', 'BUSINESS_TYPE', 'INCORPORATION_DATE', 'AMALGAMATION_DATE'
                    ]
                    
                    # Write fields in the specified order
                    for field in field_order:
                        value = company_info.get(field)
                        if value:
                            display_name = field.replace('_', ' ')
                            details_f.write(f"{display_name}: {value}\n")
                    
                    # Write matching debug information if it's a match
                    if is_match:
                        details_f.write("\n" + "=" * 80 + "\n")
                        details_f.write("MATCHING DEBUG INFORMATION\n")
                        details_f.write("-" * 80 + "\n")
                        
                        # Generate normalized search and company name for debug info
                        normalized_search = ' '.join(re.findall(r'\w+', owner.lower()))
                        company_name = company_info.get('COMPANY_NAME', '').lower()
                        normalized_company = ' '.join(re.findall(r'\w+', company_name))
                        
                        # Generate search variations
                        search_terms = normalized_search.split()
                        variations = set()
                        if len(search_terms) >= 2:
                            variations.update([
                                ' '.join(search_terms),
                                ' '.join(reversed(search_terms)),
                                search_terms[0] + ' ' + search_terms[1][0] if len(search_terms) > 1 else search_terms[0],
                                search_terms[0][0] + search_terms[1][0] if len(search_terms) > 1 else search_terms[0][0]
                            ])
                        
                        # Write debug info
                        details_f.write(f"Original search: '{owner}'\n")
                        details_f.write(f"Original company: '{company_info.get('COMPANY_NAME', '')}'\n")
                        details_f.write(f"Normalized search: '{normalized_search}'\n")
                        details_f.write(f"Normalized company: '{normalized_company}'\n")
                        details_f.write(f"Search variations: {variations}\n")
                        
                        # Check for direct match
                        matching_variations = [v for v in variations if v in normalized_company]
                        if matching_variations:
                            details_f.write(f"✅ Direct match found with variations: {matching_variations}\n")
                        else:
                            details_f.write("❌ No direct match found in variations\n")
                        
                        details_f.write("-" * 80 + "\n")
                    
                    # Match status
                    details_f.write("\n" + "=" * 80 + "\n")
                    details_f.write(f"MATCH FOUND: {'YES' if is_match else 'NO'}\n")
                    if confidence_score > 0:
                        details_f.write(f"CONFIDENCE: {confidence_score:.0%}\n")
                    if is_match:
                        details_f.write(f"CLOSEST MATCH: {company_info.get('COMPANY_NAME', 'N/A')}\n")
                    details_f.write("=" * 80 + "\n")
                    
                    # Add detailed company information section if we have good data
                    if is_match and company_info.get('COMPANY_NAME'):
                        details_f.write("\n" + "=" * 80 + "\n")
                        details_f.write("DETAILED COMPANY INFORMATION (Result #1)\n")
                        details_f.write("=" * 80 + "\n\n")
                        
                        for field in field_order:
                            value = company_info.get(field)
                            if value and value.strip():
                                display_name = field.replace('_', ' ')
                                details_f.write(f"{display_name}: {value}\n")
                        
                        details_f.write("\n" + "=" * 80 + "\n")
                    
                    details_f.write("\n\n")  # Extra spacing between entries
                    
                    # Store results
                    results[owner] = {
                        'match': is_match,
                        'matched_name': matched_name,
                        'confidence_score': confidence_score,
                        'company_info': company_info,
                        'search_time': result.search_time,
                        'content_size': len(result.html_content)
                    }
                
                # Brief pause between batches
                if batch_end < total_owners:
                    print(f"✅ Batch {batch_num} completed. Brief pause before next batch...")
                    await asyncio.sleep(3)
    
    # Print summary
    successful_searches = sum(1 for r in results.values() if r.get('match', False))
    total_searches = len(results)
    
    print(f"\n🎉 Concurrent processing complete!")
    print(f"📊 Results: {successful_searches}/{total_searches} matches found")
    print(f"💾 Detailed report saved to: {os.path.abspath(details_file)}")
    
    return results

def main():
    # Path to your GeoJSON file
    geojson_path = '../Property_Ownership_Public_8585062059551015044.geojson'
    
    if not os.path.exists(geojson_path):
        print(f"Error: GeoJSON file not found at {geojson_path}")
        print("Please ensure the GeoJSON file is in the correct location.")
        return
    
    print(f"🗺️  Extracting owners from {geojson_path}...")
    owners = extract_owners_from_geojson(geojson_path, debug=True)
    
    if not owners:
        print("❌ No owners found in the GeoJSON file.")
        return
    
    print(f"✅ Found {len(owners)} unique private owners.")
    print("\n📋 Sample of owners to be processed:")
    for i, owner in enumerate(sorted(owners)[:10]):
        print(f"  {i+1:2}. {owner}")
    if len(owners) > 10:
        print(f"  ... and {len(owners) - 10} more")
    
    print(f"\n⚡ This will use concurrent processing with:")
    print(f"   • Batch size: {BATCH_SIZE} businesses per batch")
    print(f"   • Max concurrent: {MAX_CONCURRENT} browser contexts")
    print(f"   • Expected time: ~{(len(owners) * 7) / (BATCH_SIZE * MAX_CONCURRENT) / 60:.1f} minutes")
    
    # Ask for confirmation
    confirm = input(f"\n🚀 Proceed with concurrent lookup of {len(owners)} owners? (y/n): ")
    if confirm.lower() != 'y':
        print("❌ Operation cancelled.")
        return
    
    # Process the owners concurrently
    try:
        results = asyncio.run(process_owners_concurrent(owners))
        print(f"🎯 Processing completed successfully!")
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()