import os
import sys
import time
from datetime import datetime
from web_scraper import WebScraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import re
from typing import Dict, List, Optional, Tuple

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

def search_ontario_business(business_name: str) -> str:
    """Search for a business in the Ontario Business Registry."""
    # Run in non-headless mode to see what's happening
    scraper = WebScraper(headless=False)  # Set to True in production
    
    try:
        # Navigate to the search page - using the current Ontario Business Registry URL
        print(f"Searching for: {business_name}")
        search_url = "https://www.appmybizaccount.gov.on.ca/onbis/master/viewInstance/view.pub?id=3abd3bce3cc0ad2a5f4d3e3394f70a887b5d3629f9b7ec72&_timestamp=576646948208925"
        print(f"Accessing: {search_url}")
        scraper.get_page(search_url)
        
        # Wait for the page to load completely
        time.sleep(3)
        
        # Accept cookies if the banner appears
        try:
            cookie_button = scraper.driver.find_element(By.XPATH, "//button[contains(., 'Accept all')]")
            if cookie_button:
                cookie_button.click()
                print("Accepted cookies")
                time.sleep(1)  # Wait for any cookie acceptance to process
        except Exception as e:
            print(f"No cookie banner found or could not accept cookies: {e}")
        
        # Wait for the search box to be present
        try:
            wait = WebDriverWait(scraper.driver, 10)
            search_box = wait.until(
                EC.presence_of_element_located((By.ID, "QueryString"))
            )
            
            # Enter search term
            search_box.clear()
            search_box.send_keys(business_name)
            print("Search term entered")
            
            # Find and click search button using multiple possible selectors
            search_button_selectors = [
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "input[type='submit']"),
                (By.XPATH, "//button[contains(., 'Search') or contains(., 'SEARCH')]"),
                (By.XPATH, "//input[@value='Search' or @value='SEARCH']"),
                (By.ID, "nodeW20"),  # Keep the original as last resort
            ]
            
            search_button = None
            for selector in search_button_selectors:
                try:
                    search_button = wait.until(EC.element_to_be_clickable(selector))
                    search_button.click()
                    print(f"Search button clicked using {selector}")
                    break
                except Exception as e:
                    print(f"Tried selector {selector} but failed: {str(e)}")
            
            if not search_button:
                raise Exception("Could not find or click the search button")
            
            # Wait for results to load - give it more time
            print("Waiting for results...")
            time.sleep(10)  # Increased wait time for results to load
            
            # Save the page source for debugging
            page_source = scraper.driver.page_source
            if SAVE_DEBUG_FILES:
                debug_file = get_output_path('search_results_page.html')
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(page_source)
                print(f"Saved search results page for debugging: {debug_file}")
            else:
                print("Debug file saving disabled - skipping search_results_page.html")
            
            # Try to find results using multiple possible selectors
            result_selectors = [
                "div.registerItemSearch-results-page-line-ItemBox",  # Main results
                "div.search-results",
                "div.result-item",
                "div.search-result"
            ]
            
            for selector in result_selectors:
                results = scraper.driver.find_elements(By.CSS_SELECTOR, selector)
                if results:
                    print(f"Found {len(results)} results with selector: {selector}")
                    break
            else:
                print("Warning: No results found with any selector")
                # Check for "no results" message
                no_results = scraper.driver.find_elements(By.XPATH, "//*[contains(text(), 'No results found') or contains(text(), 'No matches found')]")
                if no_results:
                    print("No results found for the search term")
            
            # Return the page source regardless
            return page_source
            
        except TimeoutException as te:
            print(f"Timeout while waiting for elements: {te}")
            print("Current URL:", scraper.driver.current_url)
            print("Page title:", scraper.driver.title)
            print("Page source length:", len(scraper.driver.page_source))
            
            # Save the page source for debugging
            if SAVE_DEBUG_FILES:
                debug_file = get_output_path('debug_page.html')
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(scraper.driver.page_source)
                print(f"Debug page saved as {debug_file}")
            else:
                print("Debug file saving disabled - skipping debug_page.html")
            
            return ""
            
    except Exception as e:
        print(f"Unexpected error during search: {e}")
        import traceback
        traceback.print_exc()
        return ""
        
    finally:
        if hasattr(scraper, 'driver'):
            # Keep the browser open for 30 seconds for debugging
            # Remove this in production
            time.sleep(30)
            scraper.driver.quit()

def extract_detailed_info_from_cleaned_file(cleaned_file_path: str) -> dict:
    """
    Extract detailed company information from the cleaned search results file.
    
    Args:
        cleaned_file_path: Path to the cleaned text file
        
    Returns:
        Dictionary containing detailed company information from Result #1
    """
    try:
        with open(cleaned_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find Result #1 section
        if 'RESULT #1' not in content:
            return {}
        
        # Extract the Result #1 section
        result_start = content.find('RESULT #1')
        result_end = content.find('RESULT #2')
        
        if result_end == -1:
            # If there's no Result #2, go to the end
            result_section = content[result_start:]
        else:
            result_section = content[result_start:result_end]
        
        # Parse the result section to extract key-value pairs
        detailed_info = {}
        lines = result_section.split('\n')
        
        for line in lines:
            # Look for lines with format "KEY: VALUE"
            if ':' in line and not line.startswith('-') and not line.startswith('RESULT #'):
                parts = line.split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip().upper()
                    value = parts[1].strip()
                    if key and value:
                        detailed_info[key] = value
        
        return detailed_info
        
    except Exception as e:
        print(f"Error extracting detailed info from cleaned file: {e}")
        return {}

def append_detailed_info_to_results(output_file: str, detailed_info: dict) -> None:
    """
    Append detailed information from the cleaned search results to the business lookup results file.
    
    Args:
        output_file: Path to the business lookup results file
        detailed_info: Dictionary containing detailed company information
    """
    try:
        if not detailed_info:
            return
        
        # Read the existing content
        with open(output_file, 'r', encoding='utf-8') as f:
            existing_content = f.read()
        
        # Check if detailed info is already present
        if 'DETAILED COMPANY INFORMATION (Result #1)' in existing_content:
            print("Detailed information already present in results file")
            return
        
        # Find the location to insert the detailed information
        # Look for the last line of the match section
        match_section_end = existing_content.rfind('================================================================================')
        
        if match_section_end == -1:
            # If no match section found, append to the end
            detailed_section = f"\n\n{'='*80}\nDETAILED COMPANY INFORMATION (Result #1)\n{'='*80}\n\n"
        else:
            # Insert after the match section
            detailed_section = f"\n\n{'='*80}\nDETAILED COMPANY INFORMATION (Result #1)\n{'='*80}\n\n"
        
        # Build the detailed information section
        for key, value in detailed_info.items():
            if value and value.strip():
                detailed_section += f"{key}: {value}\n"
        
        detailed_section += f"\n{'='*80}\n"
        
        # Insert the detailed section
        if match_section_end == -1:
            # Append to the end
            updated_content = existing_content + detailed_section
        else:
            # Find the end of the current match section line
            next_newline = existing_content.find('\n', match_section_end)
            if next_newline == -1:
                updated_content = existing_content + detailed_section
            else:
                updated_content = existing_content[:next_newline + 1] + detailed_section
        
        # Write the updated content back to the file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        print(f"Detailed information appended to: {output_file}")
        
    except Exception as e:
        print(f"Error appending detailed info: {e}")

def extract_company_info(html_content: str) -> Dict[str, str]:
    """Extract company information from HTML content with improved parsing."""
    try:
        # Save the HTML content for debugging
        if SAVE_DEBUG_FILES:
            html_file = get_output_path('last_search_results.html')
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
        else:
            html_file = None  # Set to None when not saving files
        
        # Clean the HTML file using clean_html.py (only if file was saved)
        if SAVE_DEBUG_FILES and html_file:
            from clean_html import clean_search_results
            try:
                cleaned_file = clean_search_results(html_file)
                print(f"\nCleaned results saved to: {cleaned_file}")
                
                # Extract detailed info from the cleaned file and store it for later use
                detailed_info = extract_detailed_info_from_cleaned_file(cleaned_file)
                if detailed_info:
                    info['_detailed_info'] = detailed_info
            except Exception as e:
                print(f"\nError cleaning HTML file: {e}")
        else:
            info = {}  # Initialize info dict when not saving files
        
        soup = BeautifulSoup(html_content, 'html.parser')
        info = {}
        
        # Try multiple selectors to find the main result container
        result_block = None
        result_selectors = [
            'div.registerItemSearch-results-page-line',
            'div.search-result',
            'div.result-item',
            'div[class*="result"]',
            'div[class*="item"]'
        ]
        
        for selector in result_selectors:
            result_blocks = soup.select(selector)
            if result_blocks:
                result_block = result_blocks[0]
                break
        
        if not result_block:
            print("No result blocks found in the HTML")
            return {}
            
        # Extract corporation type
        corp_type_elem = result_block.select_one('.registerItemSearch-results-page-line-item1.registryInfo')
        if corp_type_elem:
            info['CORPORATION TYPE'] = corp_type_elem.get_text(strip=True)
        else:
            info['CORPORATION TYPE'] = 'Not specified'
        
        # 1. Extract company name with multiple fallback strategies
        name_candidates = []
        
        # Try different patterns to find the company name
        name_patterns = [
            # Common patterns in the Ontario Business Registry
            'a[class*="viewMenu"]',
            'div[class*="name"]',
            'h3', 'h2', 'h1',
            'span[class*="title"]',
            'div[class*="title"]',
            'a[href*="view"]',
            'strong', 'b',
            'div:first-child',
            'a:first-child'
        ]
        
        for pattern in name_patterns:
            elements = result_block.select(pattern)
            for el in elements:
                text = el.get_text(strip=True)
                if text and len(text) > 2 and text.lower() not in ['view', 'details', 'more']:
                    name_candidates.append(text)
        
        # Remove duplicates while preserving order
        seen = set()
        name_candidates = [x for x in name_candidates if not (x in seen or seen.add(x))]
        
        # Select the most likely candidate (longest text that's not too long)
        if name_candidates:
            # Filter out very long candidates (likely not names)
            filtered = [n for n in name_candidates if 3 <= len(n) <= 100]
            if filtered:
                # Prefer longer names as they're more likely to be complete
                info['COMPANY NAME'] = max(filtered, key=len)
        
        # 2. Extract other details using a more robust approach
        # Look for label-value pairs in various formats
        label_value_patterns = [
            # Standard label: value pattern
            (r'^(.*?)[:：]\s*(.*)$', lambda m: (m.group(1).strip().upper(), m.group(2).strip())),
            # Bold label followed by text
            (r'<b>(.*?)</b>\s*(.*?)(?=<br|<p|$)', 
             lambda m: (m.group(1).strip().upper(), m.group(2).strip()))
        ]
        
        # Try different selectors for potential data rows
        row_selectors = [
            'div[class*="row"]', 'tr', 'div[class*="item"]', 
            'div[class*="field"]', 'div[class*="detail"]',
            'p', 'div > div'
        ]
        
        for selector in row_selectors:
            for row in result_block.select(selector):
                row_text = str(row)
                
                # Skip rows that are too short or too long to be data rows
                if len(row_text) < 10 or len(row_text) > 1000:
                    continue
                    
                # Try different patterns to extract label-value pairs
                for pattern, processor in label_value_patterns:
                    match = re.search(pattern, row_text, re.DOTALL | re.IGNORECASE)
                    if match:
                        try:
                            label, value = processor(match)
                            if label and value and len(label) < 50 and len(value) < 200:
                                info[label] = value
                        except (IndexError, AttributeError):
                            continue
        
        # 3. If we still don't have a company name, try extracting from the first link with text
        if 'COMPANY NAME' not in info:
            for link in result_block.find_all('a', href=True, string=True):
                text = link.get_text(strip=True)
                if len(text) > 2 and not text.lower().startswith(('http', 'www', 'mailto:')):
                    info['COMPANY NAME'] = text
                    break
        
        # 4. Add raw HTML for debugging (limited to first 2000 chars)
        info['_raw_html'] = str(result_block)[:2000] + ('...' if len(str(result_block)) > 2000 else '')
        
        # Clean up the company name if we found one
        if 'COMPANY NAME' in info:
            # Remove any HTML tags that might have been included
            info['COMPANY NAME'] = re.sub(r'<[^>]+>', '', info['COMPANY NAME']).strip()
            print(f"Extracted company info: {info['COMPANY NAME']}")
        else:
            print("Warning: Could not extract company name from the results")
            
        return info
        
    except Exception as e:
        print(f"Error extracting company info: {e}")
        import traceback
        traceback.print_exc()
        return {'ERROR': str(e), '_raw_html': str(html_content)[:1000] + '...'}

def is_company_match(search_name: str, company_info: dict) -> Tuple[bool, str, float]:
    """
    Check if the search name matches the company info using flexible matching.
    Returns a tuple of (is_match, matched_company_name, confidence_score).
    """
    if not company_info or 'COMPANY NAME' not in company_info:
        print("No company info or company name found in the results")
        return False, ""
    
    company_name = company_info['COMPANY NAME']
    
    def normalize_company_name(name):
        """Normalize company name for comparison with extensive cleaning."""
        if not name or not isinstance(name, str):
            return ""
            
        # Convert to lowercase and strip whitespace
        name = name.lower().strip()
        
        # Remove anything in parentheses and brackets (like registration numbers, legal status)
        name = re.sub(r'\s*[\(\[].*?[\]\)]', ' ', name)
        
        # Common business entity suffixes and their variations
        entity_suffixes = [
            # Standard suffixes
            'inc', 'llc', 'ltd', 'llp', 'corp', 'corporation', 'limited', 'incorporated',
            'llc.', 'ltd.', 'inc.', 'corp.', 'limited.', 'incorporated.',
            # International variations
            'gmbh', 'ag', 'sarl', 'srl', 'pte', 'ltee', 'bv', 'nv', 'oyj', 'ab', 'as',
            # Other common terms
            'company', 'co', 'lp', 'plc', 'llp', 'lllp', 'lc', 'p c', 'pc', 'pa',
            'professional corporation', 'professional association',
            # French variations
            'societe', 'société', 'societe en nom collectif', 'société en nom collectif',
            'societe en commandite', 'société en commandite', 'societe anonyme', 'société anonyme'
        ]
        
        # Remove common business suffixes
        suffix_pattern = r'\b(' + '|'.join(re.escape(suffix) for suffix in entity_suffixes) + r')\b'
        name = re.sub(suffix_pattern, '', name)
        
        # Handle co-op variations
        name = re.sub(r'\b(co[\s-]?op(?:erative)?|coop(?:erative)?)\b', 'co-op', name)
        
        # Replace common abbreviations and special characters
        replacements = {
            '&': 'and',
            '+': 'and',
            '@': 'at',
            'w/': 'with',
            'w /': 'with',
            'w.o.': 'without',
            'vs.': 'versus',
            # Remove punctuation except hyphens between words
            "'s": '',
            "'": '',
            '"': '',
            ',': ' ',
            '.': ' ',
            ';': ' ',
            ':': ' ',
            '  ': ' '
        }
        
        for old, new in replacements.items():
            name = name.replace(old, new)
        
        # Remove any remaining special characters except spaces and hyphens
        name = re.sub(r'[^a-z0-9\s-]', ' ', name)
        
        # Clean up spaces and hyphens
        name = re.sub(r'\s+-\s+', '-', name)  # Normalize spaces around hyphens
        name = re.sub(r'-+', '-', name)  # Replace multiple hyphens with one
        name = re.sub(r'\s+', ' ', name)  # Replace multiple spaces with one
        
        return name.strip(' -')
    
    def get_name_variations(name):
        """Generate multiple variations of the name for flexible matching."""
        if not name:
            return set()
            
        name = normalize_company_name(name)
        if not name:
            return set()
            
        variations = {name}
        
        # Add the full name
        variations.add(name)
        
        # Add version without hyphens
        variations.add(name.replace('-', ' '))
        
        # Add version with spaces instead of hyphens
        variations.add(name.replace('-', ' '))
        
        # Add acronym version (e.g., "MTD Products" -> "MTD")
        words = [word for word in name.split() if len(word) > 1]  # Only consider words with 2+ chars
        if words:
            acronym = ''.join(word[0].lower() for word in words)
            if len(acronym) > 1:  # Only add if we have at least 2 letters
                variations.add(acronym)
            
            # Add first letters of first two words (e.g., "MTD Products" -> "mt")
            if len(words) > 1:
                variations.add((words[0][0] + words[1][0]).lower())
        
        # Add first word (for cases like "MTD Products" matching "MTD")
        first_word = words[0] if words else ""
        if first_word and len(first_word) > 1:
            variations.add(first_word)
        
        # Add first two words (for cases like "MTD Products Limited" matching "MTD Products")
        if len(words) > 1:
            variations.add(' '.join(words[:2]))
        
        # Add versions with common words removed
        common_words = {'the', 'and', 'of', 'for', 'in', 'at', 'on', 'by', 'to', 'with', 'a', 'an'}
        filtered_words = [w for w in words if w.lower() not in common_words]
        if filtered_words and len(filtered_words) < len(words):
            variations.add(' '.join(filtered_words))
        
        # Add variations with common word order changes
        if len(words) == 2:
            variations.add(' '.join(reversed(words)))
        
        return variations
    
    # Generate all variations of both names
    search_variations = get_name_variations(search_name)
    company_variations = get_name_variations(company_name)
    
    # Debug output - show what we're comparing
    print("\n--- Matching Debug ---")
    print(f"Original search: '{search_name}'")
    print(f"Original company: '{company_name}'")
    print(f"Normalized search: '{normalize_company_name(search_name)}'")
    print(f"Normalized company: '{normalize_company_name(company_name)}'")
    print(f"Search variations: {search_variations}")
    
    # Check for direct matches first (most reliable)
    direct_matches = search_variations.intersection(company_variations)
    if direct_matches:
        print(f"✅ Direct match found with variations: {direct_matches}")
        print("--- End Debug ---\n")
        return True, company_name, 0.95  # High confidence for direct matches
    
    # If no direct match, check for partial matches
    search_terms = set()
    for var in search_variations:
        search_terms.update(var.split())
    
    company_terms = set()
    for var in company_variations:
        company_terms.update(var.split())
    
    # Remove very short terms (1-2 chars) as they're not reliable for matching
    search_terms = {t for t in search_terms if len(t) > 2}
    company_terms = {t for t in company_terms if len(t) > 2}
    
    # Check for any term that appears in both sets
    common_terms = search_terms.intersection(company_terms)
    
    # For the match to be valid, we need at least one significant term in common
    # or one term from search contained in company name or vice versa
    significant_match = False
    
    if common_terms:
        print(f"Common terms found: {common_terms}")
        significant_match = True
    else:
        # Check if any search term is a substring of any company term or vice versa
        for st in search_terms:
            for ct in company_terms:
                if st in ct or ct in st:
                    print(f"Partial match: '{st}' in '{ct}' or vice versa")
                    significant_match = True
                    break
            if significant_match:
                break
    
    # Special handling for co-op variations
    has_coop = any('coop' in term or 'co-op' in term for term in search_terms.union(company_terms))
    if has_coop and any(t in ['coop', 'co-op'] for t in search_terms.union(company_terms)):
        print("Co-op variation detected, considering as potential match")
        significant_match = True
    
    # Special handling for acronyms (e.g., MTD Products Limited matching MTD)
    search_acronyms = {v for v in search_variations if len(v) <= 4 and v.isalpha()}
    company_acronyms = {v for v in company_variations if len(v) <= 4 and v.isalpha()}
    
    if search_acronyms.intersection(company_acronyms):
        print(f"Matching acronyms found: {search_acronyms.intersection(company_acronyms)}")
        significant_match = True
    
    print(f"Match: {'✅' if significant_match else '❌'}")
    print("--- End Debug ---\n")
    
    # Calculate confidence score based on match quality
    confidence_score = 0.0
    if significant_match:
        if common_terms:
            # Higher confidence if we have exact term matches
            confidence_score = 0.85
        elif search_acronyms.intersection(company_acronyms):
            # Medium-high confidence for acronym matches
            confidence_score = 0.80
        else:
            # Lower confidence for partial/substring matches
            confidence_score = 0.70
    
    return significant_match, company_name, confidence_score

def clean_company_info(info: dict) -> dict:
    """Clean and format company information for better readability."""
    cleaned = {}
    for key, value in info.items():
        # Skip internal fields
        if key.startswith('_') or not value:
            continue
            
        # Clean up the key
        key = key.strip().upper()
        if key == 'COMPANY NAME':
            key = 'COMPANY NAME'
        
        # Clean up the value
        if isinstance(value, str):
            # Remove extra whitespace and newlines
            value = ' '.join(value.split())
            # Remove HTML tags if any
            value = re.sub(r'<[^>]+>', '', value)
            # Clean up common formatting issues
            value = re.sub(r'[\r\n\t]+', ' ', value).strip()
        
        cleaned[key] = value
    
    return cleaned

def format_company_info(info: dict) -> str:
    """Format company information into a readable string."""
    # Define the order of fields for consistent output
    field_order = [
        'COMPANY NAME', 'STATUS', 'REGISTRY', 'ADDRESS', 'CITY', 'PROVINCE', 'POSTAL CODE',
        'INCORPORATION DATE', 'BUSINESS NUMBER', 'CORPORATION NUMBER', 'JURISDICTION',
        'BUSINESS TYPE', 'INDUSTRY', 'WEBSITE', 'EMAIL', 'PHONE', 'FAX', 'CATEGORY',
        'SUBCATEGORY', 'PREVIOUSLY KNOWN AS', 'ADDITIONAL NAME', 'NOTES'
    ]
    
    # Get all fields not in our predefined order
    other_fields = [f for f in info.keys() if f not in field_order and not f.startswith('_')]
    
    # Combine fields in order, then any remaining fields
    all_fields = field_order + sorted(other_fields)
    
    # Build the output
    lines = []
    for field in all_fields:
        if field in info:
            value = info[field]
            if value:  # Only include non-empty values
                # Format the field name to be more readable
                formatted_field = field.title().replace('_', ' ')
                lines.append(f"{formatted_field}: {value}")
    
    return '\n'.join(lines)

def extract_company_details(html_content: str) -> dict:
    """Extract detailed company information from the HTML content."""
    details = {}
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract company name - get only the text within the span inside the view menu
        name_elem = soup.select_one('div.registerItemSearch-results-page-line-ItemBox-resultLeft-viewMenu span:not(.left):not(.right)')
        if name_elem:
            # Clean up the company name
            company_name = name_elem.get_text(strip=True)
            # Remove any numbers in parentheses at the end (corporation number)
            company_name = re.sub(r'\s*\(\d+\)\s*$', '', company_name)
            details['COMPANY NAME'] = company_name.strip()
        
        # Extract corporation number
        corp_num_match = re.search(r'\((\d+)\)', html_content)
        if corp_num_match:
            details['CORPORATION NUMBER'] = corp_num_match.group(1)
        
        # Extract registry type
        registry_elem = soup.select_one('.registerItemSearch-results-page-line-item1.registryInfo')
        if registry_elem:
            details['REGISTRY TYPE'] = registry_elem.get_text(strip=True)
        
        # Extract status - look for the status value specifically
        status_elem = soup.select_one('.appMinimalAttr.Status .appMinimalValue')
        if status_elem:
            details['STATUS'] = status_elem.get_text(strip=True)
        
        # Extract address - look for the address value specifically
        address_elem = soup.select_one('.appMinimalBox.addressSearchResultBox .appAttrValue')
        if address_elem:
            details['ADDRESS'] = address_elem.get_text(strip=True)
        
        # Extract dates (amalgamation and incorporation)
        # Look for dates in a more specific context to avoid false positives
        date_elems = soup.select('.appMinimalAttr')
        for elem in date_elems:
            text = elem.get_text()
            date_match = re.search(r'(Incorporation|Amalgamation).*?(\w+\s+\d{1,2},?\s+\d{4})', text, re.IGNORECASE)
            if date_match:
                date_type = date_match.group(1).upper()
                date_value = date_match.group(2)
                if 'INCORPORATION' in date_type:
                    details['INCORPORATION DATE'] = date_value
                elif 'AMALGAMATION' in date_type:
                    details['AMALGAMATION DATE'] = date_value
        
        # Extract business type
        type_elem = soup.select_one('.appMinimalBox.statusSearchResult')
        if type_elem and 'Business Corporation' in type_elem.get_text():
            details['BUSINESS TYPE'] = 'Ontario Business Corporation'
            
    except Exception as e:
        print(f"Error extracting company details: {e}")
    
    return details

def save_results(search_term: str, is_match: bool, company_info: dict, output_file: str, confidence_score: float = 0.0) -> str:
    """
    Save the search results to a well-formatted text file with detailed company information.
    
    Args:
        search_term: The original search term
        is_match: Whether an exact match was found
        company_info: Dictionary containing company information
        output_file: Path to save the output file
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write("=" * 80 + "\n")
            f.write(f"SEARCH RESULTS FOR: {search_term}\n")
            f.write("=" * 80 + "\n\n")
            
            if not company_info:
                f.write("No company information found.\n")
                return output_file
            
            # Extract additional details from HTML if available
            raw_html = company_info.get('_raw_html', '')
            if raw_html:
                details = extract_company_details(raw_html)
                # Update company_info with extracted details
                company_info.update(details)
            
            # Write company information section
            f.write("COMPANY DETAILS\n")
            f.write("-" * 80 + "\n")
            
            # Define the order of fields we want to display
            field_order = [
                'COMPANY NAME', 'CORPORATION NUMBER', 'REGISTRY TYPE', 'STATUS',
                'ADDRESS', 'BUSINESS TYPE', 'INCORPORATION DATE', 'AMALGAMATION DATE'
            ]
            
            # Write fields in the specified order
            for field in field_order:
                value = company_info.get(field.replace(' ', '_').upper())
                if value:
                    f.write(f"{field}: {value}\n")
            
            # Write debug information
            if is_match and '_raw_html' in company_info:
                f.write("\n" + "=" * 80 + "\n")
                f.write("MATCHING DEBUG INFORMATION\n")
                f.write("-" * 80 + "\n")
                
                # Generate normalized search and company name for debug info
                normalized_search = ' '.join(re.findall(r'\w+', search_term.lower()))
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
                f.write(f"Original search: '{search_term}'\n")
                f.write(f"Original company: '{company_name.upper()}'\n")
                f.write(f"Normalized search: '{normalized_search}'\n")
                f.write(f"Normalized company: '{normalized_company}'\n")
                f.write(f"Search variations: {variations}\n")
                
                # Check for direct match
                if any(variation in normalized_company for variation in variations):
                    f.write(f"✅ Direct match found with variations: {[v for v in variations if v in normalized_company]}\n")
                else:
                    f.write("❌ No direct match found in variations\n")
                
                f.write("-" * 80 + "\n")
            
            # Write match status
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"MATCH FOUND: {'YES' if is_match else 'NO'}\n")
            if confidence_score > 0:
                f.write(f"CONFIDENCE: {confidence_score:.0%}\n")
            if is_match:
                f.write(f"CLOSEST MATCH: {company_info.get('COMPANY NAME', 'N/A')}\n")
            f.write("=" * 80 + "\n")
            
        # If we have detailed information from the cleaned file, append it
        detailed_info = company_info.get('_detailed_info')
        if detailed_info:
            append_detailed_info_to_results(output_file, detailed_info)
        
    except Exception as e:
        print(f"Error saving results: {e}")
            
    # Save raw HTML for debugging (only if enabled)
    if SAVE_DEBUG_FILES and company_info and '_raw_html' in company_info:
        html_file = output_file.replace('.txt', '.html')
        with open(html_file, 'w', encoding='utf-8') as html_f:
            html_f.write(company_info['_raw_html'])
        print(f"Debug HTML saved to: {os.path.abspath(html_file)}")
    
    print(f"Results saved to: {os.path.abspath(output_file)}")
    return output_file

def main():
    if len(sys.argv) < 2:
        print("Usage: python business_lookup.py 'Business Name' [output_file.txt]")
        sys.exit(1)
    
    search_term = sys.argv[1]
    default_output = get_output_path('business_lookup_results.txt') if SAVE_DEBUG_FILES else 'business_lookup_results.txt'
    output_file = sys.argv[2] if len(sys.argv) > 2 else default_output
    
    print(f"Starting search for: {search_term}")
    
    # Step 1: Search the Ontario Business Registry
    html_content = search_ontario_business(search_term)
    
    if not html_content:
        print("Error: Could not retrieve search results.")
        sys.exit(1)
    
    # Step 2: Extract company info
    company_info = extract_company_info(html_content)
    
    # Step 3: Check for a match
    is_match, matched_name, confidence_score = is_company_match(search_term, company_info)
    
    # Step 4: Save results
    save_results(search_term, is_match, company_info, output_file, confidence_score)
    
    print(f"\nSearch complete! Results saved to: {os.path.abspath(output_file)}")
    print(f"Match found: {'✅ YES' if is_match else '❌ NO'}")
    if company_info:
        print(f"Closest match: {company_info.get('COMPANY NAME', 'N/A')}")

if __name__ == "__main__":
    main()
