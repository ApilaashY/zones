from bs4 import BeautifulSoup, Tag
import os
import re
from typing import List, Dict, Optional

def extract_previous_names(block) -> List[str]:
    """
    Extract previous company names from the result block.
    
    Args:
        block: BeautifulSoup element containing company information
        
    Returns:
        List of previous company names
    """
    previous_names = []
    
    # Try multiple possible selectors for previous names section
    prev_name_selectors = [
        'div.previousNameSearchResult',
        'div.previous-names',
        'div.previousNamesBox',
        'div.appMinimalBox:has(> span.appMinimalLabel:contains("Previously known as"))'
    ]
    
    prev_names_section = None
    for selector in prev_name_selectors:
        prev_names_section = block.select_one(selector)
        if prev_names_section:
            break
    
    if not prev_names_section:
        return previous_names
    
    # Find all name entries in the previous names section
    name_entries = prev_names_section.find_all(['div', 'span'], class_=re.compile('Name|appMinimalValue'))
    
    for entry in name_entries:
        # Skip if this is a label
        if 'appMinimalLabel' in entry.get('class', []):
            continue
            
        # Get the text and clean it up
        name = entry.get_text(strip=True)
        if name and name.lower() not in ['previously known as', 'name']:
            # Clean up any extra whitespace or special characters
            name = ' '.join(name.split())
            if name not in previous_names:
                previous_names.append(name)
    
    # If no names found, try alternative approach
    if not previous_names:
        for item in prev_names_section.find_all(text=True):
            text = item.strip()
            if text and len(text) > 3 and 'previously' not in text.lower():
                previous_names.append(text)
    
    return previous_names

def extract_company_info(block) -> Dict[str, str]:
    """
    Extract comprehensive company information from a result block.
    
    Args:
        block: BeautifulSoup element containing company information
        
    Returns:
        Dictionary containing extracted company information
    """
    info = {}
    
    # 1. Extract basic company information
    # Company name from the main anchor tag
    company_link = block.find('a', class_=re.compile('viewMenu|registerItemSearch-results-page-line-ItemBox-resultLeft-viewMenu'))
    if company_link:
        company_name = company_link.get_text(strip=True)
        if company_name:
            # Clean up the company name (remove extra spaces, newlines, etc.)
            company_name = ' '.join(company_name.split())
            info['COMPANY NAME'] = company_name
            
            # Try to extract corporation number if present in the name (e.g., "COMPANY NAME (1234567)")
            corp_num_match = re.search(r'\(\s*(\d+)\s*\)\s*$', company_name)
            if corp_num_match:
                info['CORPORATION NUMBER'] = corp_num_match.group(1)
    
    # 2. Extract registry type (Corporation, Business Name, etc.)
    registry_elem = block.find('div', class_=re.compile('registerItemSearch-results-page-line-item1|registryInfo'))
    if registry_elem and registry_elem.get_text(strip=True):
        info['REGISTRY TYPE'] = registry_elem.get_text(strip=True)
    
    # 3. Extract status information
    status_elem = block.find('div', class_=re.compile('Status|status|statusSearchResult'))
    if status_elem:
        status_value = status_elem.find(class_=re.compile('appMinimalValue|value'))
        if status_value:
            info['STATUS'] = status_value.get_text(strip=True)
    
    # 4. Extract address information
    address_elems = block.find_all('div', class_=re.compile('ItemAddress|address|addressSearchResultBox'))
    for address_elem in address_elems:
        # Skip if this is just a container
        if 'addressSearchResultBox' in address_elem.get('class', []) and not address_elem.find('div', class_='appAttrValue'):
            continue
            
        addr_text = ' '.join(address_elem.get_text(' ', strip=True).split())
        if addr_text and ('ADDRESS' not in info or len(addr_text) > len(info.get('ADDRESS', ''))):
            info['ADDRESS'] = addr_text
    
    # 5. Extract previous names if available
    previous_names = extract_previous_names(block)
    if previous_names:
        info['PREVIOUS NAMES'] = '; '.join(previous_names)
    
    # 6. Extract all label-value pairs from the entire block
    for row in block.find_all('div', class_=re.compile('row|appMinimalAttr|field-row|appMinimalBox')):
        # Skip if this is a container without direct label-value pairs
        if 'appMinimalBox' in row.get('class', []) and not row.find(class_=re.compile('appMinimalLabel|label')):
            continue
            
        # Try to find label and value elements
        label_elem = row.find(class_=re.compile('appMinimalLabel|label|field-label'))
        value_elem = row.find(class_=re.compile('appMinimalValue|value|field-value|appAttrValue'))
        
        if not (label_elem and value_elem):
            # Try alternative approach for finding label-value pairs
            label_elems = row.find_all(['span', 'div'], class_=True)
            if len(label_elems) >= 2:
                # Find first element that looks like a label
                for i, elem in enumerate(label_elems):
                    if 'label' in elem.get('class', []) or 'Label' in elem.get('class', []):
                        label_elem = elem
                        # Next element is likely the value
                        if i + 1 < len(label_elems):
                            value_elem = label_elems[i + 1]
                        break
        
        if label_elem and value_elem:
            label = label_elem.get_text(strip=True).strip(':').upper()
            value = ' '.join(value_elem.get_text(' ', strip=True).split())
            
            # Special handling for specific fields
            if 'date' in label.lower() and value:
                value = value.replace(',', '')  # Standardize date format
            
            if label and value and label not in info:
                info[label] = value
    
    # 7. Extract specific important fields that might have been missed
    # Business Type
    business_type_elem = block.find('div', class_=re.compile('EntitySubTypeCode|business-type'))
    if business_type_elem and 'BUSINESS TYPE' not in info:
        value_elem = business_type_elem.find(class_=re.compile('appMinimalValue|value'))
        if value_elem:
            info['BUSINESS TYPE'] = value_elem.get_text(strip=True)
    
    # Incorporation/Registration Date
    date_elem = block.find('div', class_=re.compile('RegistrationDate|incorporation-date'))
    if date_elem and 'INCORPORATION DATE' not in info:
        value_elem = date_elem.find('span', class_=re.compile('appMinimalValue|value'))
        if value_elem:
            date_text = value_elem.get_text(strip=True)
            if date_text and not date_text.startswith('Incorporation'):
                info['INCORPORATION DATE'] = date_text
    
    # 8. Extract any remaining values that might have been missed
    for div in block.find_all(['div', 'span'], class_=re.compile('appMinimalValue|value|appAttrValue')):
        if 'appMinimalLabel' not in div.get('class', []) and 'label' not in div.get('class', []):
            text = ' '.join(div.get_text(' ', strip=True).split())
            if text and text not in info.values() and len(text) > 2:
                # Skip common text that's not useful
                if text.lower() in ['active', 'inactive', 'dissolved']:
                    continue
                    
                # Try to find a corresponding label
                label = div.find_previous(class_=re.compile('appMinimalLabel|label'))
                if label and label.get_text(strip=True):
                    label_text = label.get_text(strip=True).strip(':').upper()
                    if label_text and label_text not in info:
                        info[label_text] = text
    
    # 9. Clean up and standardize field names
    field_mapping = {
        'INCORPORATION/AMALGAMATION DATE': 'INCORPORATION DATE',
        'INCORPORATIONDATE': 'INCORPORATION DATE',
        'BUSINESS TYPE': 'BUSINESS TYPE',
        'BUSINESS-TYPE': 'BUSINESS TYPE',
        'REGISTRYTYPE': 'REGISTRY TYPE',
        'REGISTRY-TYPE': 'REGISTRY TYPE',
        'COMPANYNAME': 'COMPANY NAME',
        'COMPANY-NAME': 'COMPANY NAME',
        'PREVIOUSLYKNOWNAS': 'PREVIOUS NAMES',
        'PREVIOUSLY-KNOWN-AS': 'PREVIOUS NAMES'
    }
    
    # Apply field name standardization
    for old_key, new_key in field_mapping.items():
        if old_key in info and new_key not in info:
            info[new_key] = info.pop(old_key)
    
    # 10. Clean up the company name if we found one
    if 'COMPANY NAME' in info:
        info['COMPANY NAME'] = re.sub(r'\s+', ' ', info['COMPANY NAME']).strip()
        # Remove any corporation number from the name if it's a separate field
        if 'CORPORATION NUMBER' in info:
            info['COMPANY NAME'] = re.sub(r'\s*\(' + re.escape(info['CORPORATION NUMBER']) + r'\)\s*$', 
                                        '', info['COMPANY NAME']).strip()
    
    return info

def clean_search_results(html_file_path: str) -> str:
    """
    Extract search results from HTML and save to a flat text file.
    
    Args:
        html_file_path: Path to the HTML file containing search results
        
    Returns:
        Path to the cleaned text file
    """
    # Read the HTML file
    with open(html_file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')
    
    # Create output filename
    base_name = os.path.splitext(html_file_path)[0]
    output_path = f"{base_name}_cleaned.txt"
    
    # Find all result items (each company's block)
    result_blocks = soup.find_all('div', class_=re.compile('registerItemSearch-results-page-line'))
    
    # Process and write to file directly
    with open(output_path, 'w', encoding='utf-8') as file:
        file.write(f"Search Results from: {os.path.basename(html_file_path)}\n")
        file.write("=" * 80 + "\n\n")
        
        valid_results = 0
        
        for i, block in enumerate(result_blocks, 1):
            info = extract_company_info(block)
            
            # Skip if we don't have enough information
            if len(info) < 2:  # At least company name and one other field
                continue
                
            valid_results += 1
            
            file.write(f"RESULT #{valid_results}\n")
            file.write("-" * 80 + "\n")
            
            # Write company info in a clean format
            for key, value in info.items():
                if value and str(value).strip() and str(value).strip() != 'N/A':
                    file.write(f"{key}: {value}\n")
            
            file.write("\n" + ("-" * 80) + "\n\n")
    
    return output_path

def check_company_match(txt_file_path: str, search_name: str) -> bool:
    """
    Check if the given company name matches the first result in the cleaned text file.
    
    Args:
        txt_file_path: Path to the cleaned text file
        search_name: The company name to check
        
    Returns:
        bool: True if there's a match, False otherwise
    """
    try:
        with open(txt_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Find the first result section
        result_sections = content.split('RESULT #1')[1].split('RESULT #2')[0]
        
        # Extract the company name line
        company_line = next((line for line in result_sections.split('\n') 
                           if line.startswith('COMPANY NAME:')), '')
        
        if not company_line:
            return False
            
        # Get just the company name part (remove 'COMPANY NAME: ' and any trailing details in parentheses)
        full_company_name = company_line.split('COMPANY NAME: ')[1].strip()
        company_name = re.sub(r'\s*\([^)]*\)$', '', full_company_name).strip()
        
        def normalize_name(name):
            """Normalize company name for comparison by removing common suffixes and special chars."""
            # Remove common suffixes and business identifiers
            suffixes = ['inc', 'llc', 'ltd', 'llp', 'co', 'corp', 'corporation', 'cooperative', 'co-op', 'coop']
            name = name.lower()
            
            # Remove anything in parentheses and special characters
            name = re.sub(r'\([^)]*\)', '', name)  # Remove anything in parentheses
            name = re.sub(r'[^a-z0-9\s]', ' ', name)  # Replace special chars with space
            
            # Remove common suffixes
            words = [word for word in name.split() if word not in suffixes]
            return ' '.join(words).strip()
            
        def get_abbreviation(full_name):
            """Get abbreviation from a full name (e.g., 'United Nations' -> 'UN')."""
            return ''.join(word[0].upper() for word in full_name.split() if len(word) > 1)
        
        # Normalize both names
        norm_search = normalize_name(search_name)
        norm_company = normalize_name(company_name)
        
        # Get abbreviations
        search_abbr = get_abbreviation(norm_search)
        company_abbr = get_abbreviation(norm_company)
        
        # Check for various match conditions
        search_words = set(norm_search.split())
        company_words = set(norm_company.split())
        
        # Check for direct word matches or abbreviations
        return (search_words.issubset(company_words) or
                company_words.issubset(search_words) or
                search_abbr in company_abbr or
                company_abbr in search_abbr or
                any(word in norm_company for word in norm_search.split()) or
                any(word in norm_search for word in norm_company.split()))
                
    except Exception as e:
        print(f"Error checking company match: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python clean_html.py <path_to_html_file> [company_name]")
        print("If company_name is provided, will check if it matches the first result.")
        sys.exit(1)
        
    html_file = sys.argv[1]
    output_file = clean_search_results(html_file)
    
    # If a company name was provided, check for a match
    if len(sys.argv) >= 3:
        company_name = ' '.join(sys.argv[2:])
        is_match = check_company_match(output_file, company_name)
        print(f"\nChecking if '{company_name}' matches the first result...")
        print(f"Match found: {'YES' if is_match else 'NO'}")
        if is_match:
            with open(output_file, 'r', encoding='utf-8') as f:
                print("\nFirst result details:")
                print(f.read().split('RESULT #2')[0].strip())
    print(f"Cleaned HTML saved to: {os.path.abspath(output_file)}")