"""
Configuration file for Playwright Business Lookup Pipeline
=========================================================

This file controls the behavior of the Playwright-based business lookup scripts.

To disable file saving and organize files better:
1. Set SAVE_DEBUG_FILES = False to disable all HTML/debug file generation
2. Change OUTPUT_FOLDER to your preferred folder name
3. The scripts will automatically create the output folder when needed

File organization:
- When SAVE_DEBUG_FILES = True: All files go into OUTPUT_FOLDER/
  - Main results: business_lookup_results_playwright.txt
  - Debug files: last_search_results.html, search_results_page.html
  - Owner lookups: owner_lookups_playwright/ subfolder
  - Cleaned results: last_search_results_cleaned.txt
  
- When SAVE_DEBUG_FILES = False: Only main result files are saved
  - No debug HTML files are created
  - No cleaned result files are generated
  - Owner lookup results still saved (but no debug files)
"""

# Main configuration settings
SAVE_DEBUG_FILES = True  # Set to False to disable HTML and debug file generation
OUTPUT_FOLDER = 'business_lookup_output'  # Folder name for organizing all output files

# You can also customize these per script by editing the individual files:
# - business_lookup_playwright.py (Main lookup script)
# - process_geojson_owners_playwright.py (GeoJSON processing)
# - web_scraper_playwright.py (Web scraping utilities)

print(f"Playwright Business Lookup Configuration Loaded:")
print(f"  - Save debug files: {SAVE_DEBUG_FILES}")
print(f"  - Output folder: {OUTPUT_FOLDER}")