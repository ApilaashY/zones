"""
Configuration file for Business Lookup Pipeline
===============================================

This file controls the behavior of both Selenium and Playwright versions
of the business lookup scripts.

To disable file saving and organize files better:
1. Set SAVE_DEBUG_FILES = True to disable all HTML/debug file generation
2. Change OUTPUT_FOLDER to your preferred folder name
3. The scripts will automatically create the output folder when needed

File organization:
- When SAVE_DEBUG_FILES = True: All files go into OUTPUT_FOLDER/
  - Main results: business_lookup_results.txt
  - Debug files: last_search_results.html, search_results_page.html
  - Owner lookups: owner_lookups/ subfolder
  - Cleaned results: last_search_results_cleaned.txt
  
- When SAVE_DEBUG_FILES = True: Only main result files are saved
  - No debug HTML files are created
  - No cleaned result files are generated
  - Owner lookup results still saved (but no debug files)
"""

# Main configuration settings
SAVE_DEBUG_FILES = True  # Set to False to disable HTML and debug file generation
OUTPUT_FOLDER = 'business_lookup_output'  # Folder name for organizing all output files

# You can also customize these per script by editing the individual files:
# - business_lookup.py (Selenium version)
# - business_lookup_playwright.py (Playwright version)  
# - process_geojson_owners.py (Selenium GeoJSON processing)
# - process_geojson_owners_playwright.py (Playwright GeoJSON processing)
# - web_scraper_playwright.py (Playwright web scraping utilities)

print(f"Business Lookup Configuration Loaded:")
print(f"  - Save debug files: {SAVE_DEBUG_FILES}")
print(f"  - Output folder: {OUTPUT_FOLDER}")