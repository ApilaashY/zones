import json
import os
from typing import List, Dict, Set, Optional
from business_lookup_playwright import search_ontario_business_playwright, extract_company_info, is_company_match, save_results
from tqdm import tqdm
import time

# Configuration - Set these to control file output behavior
SAVE_DEBUG_FILES = True  # Set to False to disable saving HTML and debug files
OUTPUT_FOLDER = 'business_lookup_output'  # Folder name for organizing output files

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
        return False  # Skip invalid entries
    
    owner_upper = owner_name.upper().strip()
    
    # Skip empty or very short names
    if len(owner_upper) < 3:
        return False
    
    # Check for "LTD" or "LIMITED" in the name (case-insensitive)
    if 'LTD' in owner_upper or 'LIMITED' in owner_upper:
        return False  # Skip corporate owners
    
    # Split into words for more precise matching
    words = owner_upper.split()
    if not words:
        return False
    
    # Only exclude 'LTD' and 'LIMITED' as corporate indicators
    corporate_indicators = {
        'LTD', 'LIMITED'
    }
    # Check if any word in the name matches a corporate indicator
    if any(word in corporate_indicators for word in words):
        return False
    
    # Check for numbers in the name (often indicates a business)
    if any(word.isdigit() for word in words):
        # But allow if it's a year (e.g., "John Smith 2020 Trust")
        numbers = [int(word) for word in words if word.isdigit()]
        if not any(1900 <= num <= 2100 for num in numbers):
            return False
    
    # Check for common business patterns like "123 MAIN ST" or "ABC 123"
    if len(words) >= 2:
        # Pattern like "123 MAIN"
        if words[0].isdigit() and len(words[0]) <= 4 and len(words[1]) > 2:
            return False
        # Pattern like "ABC 123"
        if words[-1].isdigit() and len(words[-1]) <= 4 and len(words[-2]) > 2:
            return False
    
    # Common indicators of private ownership
    private_indicators = {
        'PRIVATE', 
        # 'INDIVIDUAL', 'PERSONAL', 'ESTATE', 'EST', 'OF',
        # 'DECEASED', 'TRUST', 'FAMILY', 'MR', 'MRS', 'MS', 'DR',
        # 'AND', '&', 'TRUSTEES', 'TRUSTEE', 'EXECUTOR', 'EXECUTRIX'
    }
    
    # If it has private indicators, definitely process it
    if any(word in private_indicators for word in words):
        return True
    
    # Check for name patterns like "Last, First" or "First Last"
    if 2 <= len(words) <= 4:  # Likely a person's name if 2-4 words
        # Check if first character of each word is uppercase (common in names)
        if all(word[0].isupper() if word else False for word in words):
            # Check if it looks like a name (contains at least one vowel in each word)
            vowels = {'A', 'E', 'I', 'O', 'U'}
            if all(any(c in vowels for c in word) for word in words if len(word) > 2):
                return True
    
    # Default to skipping if we're not sure
    return False

def extract_owners_from_geojson(geojson_path: str, debug: bool = False) -> Set[str]:
    """Extract unique owner names from a GeoJSON file, excluding corporate names.
    
    Args:
        geojson_path: Path to the GeoJSON file
        debug: If True, save filtered and excluded owners to files
        
    Returns:
        Set of unique private owner names
    """
    try:
        with open(geojson_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        owners = set()
        corporate_owners = set()
        private_owners = set()
        
        # Handle both FeatureCollection and single Feature
        features = data.get('features', [])
        if not features and isinstance(data, dict) and 'type' in data and data['type'] == 'Feature':
            features = [data]
        
        for feature in features:
            if not isinstance(feature, dict) or 'properties' not in feature:
                continue
                
            props = feature.get('properties', {})
            owner = props.get('OWNERNAME', '').strip()  # Changed from 'OWNER' to 'OWNERNAME'
            
            if not owner:
                continue
                
            if is_private_owner(owner):
                private_owners.add(owner)
            else:
                corporate_owners.add(owner)
        
        # Debug: Save filtered and excluded owners to files
        if debug:
            # Save private owners (to be processed)
            with open('filtered_owners.txt', 'w', encoding='utf-8') as f:
                f.write("=== PRIVATE OWNERS (TO BE PROCESSED) ===\n\n")
                for i, owner in enumerate(sorted(private_owners), 1):
                    f.write(f"{i:4}. {owner}\n")
            
            # Save excluded corporate owners
            with open('excluded_owners.txt', 'w', encoding='utf-8') as f:
                f.write("=== EXCLUDED CORPORATE OWNERS ===\n\n")
                f.write("This file contains owners that were excluded from processing\n")
                f.write(f"Total excluded: {len(corporate_owners)}\n\n")
                
                # Only group by 'LTD/LIMITED' exclusion reason
                exclusion_reasons = {
                    'LTD/LIMITED': [o for o in corporate_owners 
                                   if 'LTD' in o.upper() or 'LIMITED' in o.upper()]
                }
                # Write each category
                for reason, owners_list in exclusion_reasons.items():
                    if owners_list:
                        f.write(f"\n=== {reason} ({len(owners_list)}) ===\n\n")
                        for i, owner in enumerate(sorted(owners_list), 1):
                            f.write(f"{i:4}. {owner}\n")
            
            print("\nDebug files created:")
            print(f"- filtered_owners.txt: {len(private_owners)} owners to be processed")
            print(f"- excluded_owners.txt: {len(corporate_owners)} excluded owners")
        
        return private_owners
        
    except Exception as e:
        print(f"Error processing GeoJSON file: {e}")
        return set()

def process_owners(owners: Set[str], output_dir: str = 'owner_lookups_playwright') -> Dict[str, Dict]:
    """Process a list of owners and perform business lookups using Playwright."""
    # Use the configured output folder if saving debug files is enabled
    if SAVE_DEBUG_FILES:
        ensure_output_folder()
        output_dir = os.path.join(OUTPUT_FOLDER, 'owner_lookups_playwright')
    
    os.makedirs(output_dir, exist_ok=True)
    results = {}
    
    # Create a comprehensive details file with all business lookups
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    details_file = os.path.join(output_dir, f'business_lookup_details_playwright_{timestamp}.txt')
    
    with open(details_file, 'w', encoding='utf-8') as details_f:
        # Write header
        details_f.write("=" * 80 + "\n")
        details_f.write("BUSINESS LOOKUP DETAILS - COMPREHENSIVE REPORT (PLAYWRIGHT VERSION)\n")
        details_f.write("=" * 80 + "\n")
        details_f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        details_f.write(f"Total owners to process: {len(owners)}\n")
        details_f.write("=" * 80 + "\n\n")
        
        for i, owner in enumerate(tqdm(sorted(owners), desc="Processing owners with Playwright"), 1):
            try:
                # Skip empty or very short names
                if not owner or len(owner) < 3:
                    continue
                
                print(f"\nProcessing: {owner}")
                
                # Write section header for this owner
                details_f.write("\n" + "=" * 80 + "\n")
                details_f.write(f"BUSINESS LOOKUP #{i}: {owner}\n")
                details_f.write("=" * 80 + "\n\n")
                
                # Perform the search and extract company info using Playwright
                html_content = search_ontario_business_playwright(owner)
                
                if not html_content:
                    print(f"No results for: {owner}")
                    details_f.write(f"SEARCH RESULTS FOR: {owner}\n")
                    details_f.write("-" * 80 + "\n")
                    details_f.write("STATUS: No results found\n")
                    details_f.write("REASON: Unable to retrieve search results from Ontario Business Registry\n")
                    details_f.write("-" * 80 + "\n\n")
                    continue
                
                company_info = extract_company_info(html_content)
                
                if not company_info or 'COMPANY NAME' not in company_info:
                    print(f"Could not extract company info for: {owner}")
                    details_f.write(f"SEARCH RESULTS FOR: {owner}\n")
                    details_f.write("-" * 80 + "\n")
                    details_f.write("STATUS: No company information extracted\n")
                    details_f.write("REASON: Search completed but could not parse company details\n")
                    details_f.write("-" * 80 + "\n\n")
                    continue
                
                # Check for a match
                is_match, matched_name, confidence_score = is_company_match(owner, company_info)
                
                # Extract detailed information from the cleaned HTML file if available
                detailed_info = {}
                try:
                    # Import the functions we need from business_lookup
                    from business_lookup_playwright import extract_detailed_info_from_cleaned_file
                    
                    # Check if we have a cleaned file from the search
                    if os.path.exists('last_search_results_cleaned.txt'):
                        detailed_info = extract_detailed_info_from_cleaned_file('last_search_results_cleaned.txt')
                        if detailed_info:
                            company_info['_detailed_info'] = detailed_info
                except Exception as e:
                    print(f"Warning: Could not extract detailed info: {e}")
                
                # Write the complete detailed information (similar to business_lookup_results.txt)
                details_f.write(f"SEARCH RESULTS FOR: {owner}\n")
                details_f.write("=" * 80 + "\n\n")
                
                # Company details section
                details_f.write("COMPANY DETAILS\n")
                details_f.write("-" * 80 + "\n")
                
                # Extract additional details from HTML if available
                raw_html = company_info.get('_raw_html', '')
                if raw_html:
                    from business_lookup_playwright import extract_company_details
                    details = extract_company_details(raw_html)
                    company_info.update(details)
                
                # Define the order of fields we want to display
                field_order = [
                    'COMPANY NAME', 'CORPORATION NUMBER', 'REGISTRY TYPE', 'STATUS',
                    'ADDRESS', 'BUSINESS TYPE', 'INCORPORATION DATE', 'AMALGAMATION DATE'
                ]
                
                # Write fields in the specified order
                for field in field_order:
                    value = company_info.get(field.replace(' ', '_').upper())
                    if value:
                        details_f.write(f"{field}: {value}\n")
                
                # Write debug information if it's a match
                if is_match and '_raw_html' in company_info:
                    details_f.write("\n" + "=" * 80 + "\n")
                    details_f.write("MATCHING DEBUG INFORMATION\n")
                    details_f.write("-" * 80 + "\n")
                    
                    # Generate normalized search and company name for debug info
                    import re
                    normalized_search = ' '.join(re.findall(r'\w+', owner.lower()))
                    company_name = company_info.get('COMPANY NAME', '').lower()
                    normalized_company = ' '.join(re.findall(r'\w+', company_name))
                    
                    # Generate search variations
                    search_terms = normalized_search.split()
                    variations = set()
                    if len(search_terms) >= 2:
                        variations.update([
                            ' '.join(search_terms),
                            ' '.join(reversed(search_terms)),
                            search_terms[0] + ' ' + search_terms[1][0],
                            search_terms[0][0] + search_terms[1][0]
                        ])
                    
                    # Write debug info
                    details_f.write(f"Original search: '{owner}'\n")
                    details_f.write(f"Original company: '{company_name.upper()}'\n")
                    details_f.write(f"Normalized search: '{normalized_search}'\n")
                    details_f.write(f"Normalized company: '{normalized_company}'\n")
                    details_f.write(f"Search variations: {variations}\n")
                    
                    # Check for direct match
                    if any(variation in normalized_company for variation in variations):
                        details_f.write(f"✅ Direct match found with variations: {[v for v in variations if v in normalized_company]}\n")
                    else:
                        details_f.write("❌ No direct match found in variations\n")
                    
                    details_f.write("-" * 80 + "\n")
                
                # Write match status
                details_f.write("\n" + "=" * 80 + "\n")
                details_f.write(f"MATCH FOUND: {'YES' if is_match else 'NO'}\n")
                if confidence_score > 0:
                    details_f.write(f"CONFIDENCE: {confidence_score:.0%}\n")
                if is_match:
                    details_f.write(f"CLOSEST MATCH: {company_info.get('COMPANY NAME', 'N/A')}\n")
                details_f.write("=" * 80 + "\n")
                
                # If we have detailed information from the cleaned file, append it
                detailed_info = company_info.get('_detailed_info')
                if detailed_info:
                    details_f.write("\n" + "=" * 80 + "\n")
                    details_f.write("DETAILED COMPANY INFORMATION (Result #1)\n")
                    details_f.write("=" * 80 + "\n\n")
                    
                    for key, value in detailed_info.items():
                        if value and value.strip():
                            details_f.write(f"{key}: {value}\n")
                    
                    details_f.write("\n" + "=" * 80 + "\n")
                
                details_f.write("\n\n")  # Extra spacing between entries
                
                # Add to results
                results[owner] = {
                    'match': is_match,
                    'matched_name': matched_name,
                    'confidence_score': confidence_score,
                    'company_info': company_info
                }
                
                # Be nice to the server
                time.sleep(2)
                
            except Exception as e:
                print(f"Error processing owner '{owner}': {e}")
                details_f.write(f"\nERROR PROCESSING: {owner}\n")
                details_f.write("-" * 80 + "\n")
                details_f.write(f"Error: {str(e)}\n")
                details_f.write("-" * 80 + "\n\n")
    
    print(f"\nProcessing complete! Detailed report saved to: {os.path.abspath(details_file)}")
    return results

def main():
    # Path to your GeoJSON file
    geojson_path = 'Property_Ownership_Public_8585062059551015044.geojson'
    
    if not os.path.exists(geojson_path):
        print(f"Error: GeoJSON file not found at {geojson_path}")
        return
    
    print(f"Extracting owners from {geojson_path}...")
    owners = extract_owners_from_geojson(geojson_path, debug=True)
    
    if not owners:
        print("No owners found in the GeoJSON file.")
        return
    
    print(f"Found {len(owners)} unique non-private owners.")
    print("\nSample of owners to be processed:")
    for i, owner in enumerate(sorted(owners)[:5]):
        print(f"  {i+1}. {owner}")
    if len(owners) > 5:
        print(f"  ... and {len(owners) - 5} more")
    
    # Ask for confirmation before proceeding
    confirm = input("\nDo you want to proceed with the Playwright-based lookups? (y/n): ")
    if confirm.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Process the owners using Playwright
    process_owners(owners)

if __name__ == "__main__":
    main()