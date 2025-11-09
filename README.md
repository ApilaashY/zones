# Business Lookup Pipeline

## Overview

This pipeline automatically processes property ownership data from GeoJSON files and performs comprehensive business registry lookups for corporate entities in the Ontario Business Registry. It extracts owner information, filters out private individuals, and generates detailed business reports for corporate entities.

## What It Does

### 1. **Owner Extraction & Filtering**
- Reads property ownership data from GeoJSON files
- Extracts unique owner names from the `OWNERNAME` property
- **Filters out private individuals** and keeps only corporate entities
- **Corporate filtering criteria**: Only excludes owners with 'LTD' or 'LIMITED' in their names
- Allows other corporate entities (INC, CORP, etc.) to be processed
- Generates debug files showing filtered vs excluded owners

### 2. **Automated Business Registry Lookup**
- Performs automated web scraping of the Ontario Business Registry
- Searches for each corporate owner using Selenium WebDriver
- Extracts comprehensive company information from search results
- Uses fuzzy matching algorithms to determine if search results match the original owner name

### 3. **Intelligent Matching System**
- **Confidence Scoring**: Assigns confidence scores (70-95%) based on match quality:
  - 95% for direct name matches
  - 85% for exact term matches
  - 80% for acronym matches
  - 70% for partial/substring matches
- **Flexible Name Matching**: Handles variations in company names, abbreviations, and corporate suffixes
- **Debug Information**: Provides detailed matching analysis for each lookup

### 4. **Comprehensive Reporting**
- Generates a single comprehensive text file with detailed information for all business lookups
- Each business entry includes:
  - **Search Results**: Original search term and match status
  - **Company Details**: Status, address, and basic information
  - **Matching Debug Information**: Detailed analysis of the matching process
  - **Confidence Score**: Percentage confidence in the match
  - **Detailed Company Information**: Complete registry details including:
    - Company name and corporation number
    - Registry type and status
    - Full address information
    - Incorporation/amalgamation dates
    - Business type (Ontario Business Corporation, Not-for-Profit, etc.)
    - Previous names (if applicable)

## File Structure

```
├── business_lookup.py          # Main business registry search engine
├── clean_html.py              # HTML processing and cleaning utilities
├── process_geojson_owners.py   # GeoJSON processing and owner extraction
├── web_scraper.py             # Selenium WebDriver utilities
├── Property_Ownership_Public_*.geojson  # Input GeoJSON files
├── filtered_owners.txt        # Debug: Owners selected for processing
├── excluded_owners.txt        # Debug: Owners excluded (LTD/LIMITED only)
└── owner_lookups/
    └── business_lookup_details_*.txt  # Comprehensive business reports
```

## Key Features

### **Smart Corporate Filtering**
- **Updated filtering logic**: Only excludes 'LTD' and 'LIMITED' entities
- Processes other corporate types: INC, CORP, HOLDINGS, etc.
- Maintains debug visibility into filtering decisions

### **Web Scraping & Data Extraction**
- Automated Chrome browser control via Selenium
- Handles dynamic web content and form submissions
- Robust error handling and retry logic
- Extracts both basic and detailed company information

### **Fuzzy Matching Algorithm**
- Normalizes company names for comparison
- Generates multiple name variations and abbreviations
- Handles common business suffixes and abbreviations
- Provides confidence scores for match quality assessment

### **Comprehensive Output Format**
Each business lookup generates a detailed section including:

```
================================================================================
BUSINESS LOOKUP #X: [OWNER NAME]
================================================================================

SEARCH RESULTS FOR: [OWNER NAME]
================================================================================

COMPANY DETAILS
--------------------------------------------------------------------------------
STATUS: Active
ADDRESS: City, Ontario, Canada

================================================================================
MATCHING DEBUG INFORMATION
--------------------------------------------------------------------------------
Original search: '[SEARCH TERM]'
Original company: '[FOUND COMPANY NAME]'
Normalized search: '[NORMALIZED SEARCH]'
Normalized company: '[NORMALIZED COMPANY]'
Search variations: {variations}
✅ Direct match found with variations: [matching_variations]
--------------------------------------------------------------------------------

================================================================================
MATCH FOUND: YES
CONFIDENCE: 95%
CLOSEST MATCH: [MATCHED COMPANY NAME]
================================================================================

================================================================================
DETAILED COMPANY INFORMATION (Result #1)
================================================================================

COMPANY NAME: [FULL COMPANY NAME]
CORPORATION NUMBER: [NUMBER]
REGISTRY TYPE: Corporations
STATUS: Active
ADDRESS: [FULL ADDRESS]
INCORPORATION DATE: [DATE]
BUSINESS TYPE: Ontario Business Corporation

================================================================================
```

## Usage

### **Basic Usage**
```bash
# Run the full pipeline
python process_geojson_owners.py

# Run individual business lookup
python business_lookup.py "Company Name" output_file.txt
```

### **Configuration Options**
- **Debug mode**: Set `debug=True` in `extract_owners_from_geojson()` to generate filtering debug files
- **Headless mode**: Toggle `headless=True/False` in `WebScraper()` for visible/invisible browser operation
- **Output directory**: Customize output directory in `process_owners()` function

## Output Files

### **Main Output**
- `business_lookup_details_[timestamp].txt`: Comprehensive report with all business lookups

### **Debug Files** (when debug=True)
- `filtered_owners.txt`: List of owners selected for processing
- `excluded_owners.txt`: List of owners excluded (LTD/LIMITED only)

### **Processing Files** (temporary)
- `last_search_results.html`: Raw HTML from last search
- `last_search_results_cleaned.txt`: Cleaned and parsed search results
- `search_results_page.html`: Debug page source

## System Requirements

- **Python 3.7+**
- **Chrome Browser** (for Selenium WebDriver)
- **Required Libraries**:
  - selenium
  - beautifulsoup4
  - tqdm (progress bars)
  - json (built-in)
  - re (built-in)
  - time (built-in)

## Data Flow

1. **Input**: GeoJSON file with property ownership data
2. **Extraction**: Parse owner names from `OWNERNAME` property
3. **Filtering**: Remove private individuals, keep corporate entities (excludes only LTD/LIMITED)
4. **Web Scraping**: Search Ontario Business Registry for each corporate owner
5. **Matching**: Use fuzzy matching to determine if results match the search
6. **Scoring**: Assign confidence scores based on match quality
7. **Reporting**: Generate comprehensive business lookup report

## Performance Notes

- **Processing Time**: ~75 seconds per business lookup (includes server-friendly delays)
- **Rate Limiting**: 2-second delays between requests to avoid overloading the registry
- **Progress Tracking**: Real-time progress bars show processing status
- **Error Handling**: Continues processing even if individual lookups fail

## Sample Statistics

From a typical run processing 1,105 corporate owners:
- **Total Processed**: 1,105 business entities
- **Successful Matches**: ~95% with high confidence scores
- **Processing Time**: ~20 hours for full dataset
- **Output Size**: Comprehensive report with 44,000+ lines of detailed information