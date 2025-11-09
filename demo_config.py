#!/usr/bin/env python3
"""
Demo script to show the configurable file output behavior.
This script demonstrates how to toggle debug file generation on and off.
"""

import os
import sys

def demo_configuration():
    """Demonstrate the configuration options."""
    print("=" * 60)
    print("BUSINESS LOOKUP PIPELINE - CONFIGURATION DEMO")
    print("=" * 60)
    
    print("\n1. CURRENT CONFIGURATION:")
    
    # Import the current configuration
    try:
        from config import SAVE_DEBUG_FILES, OUTPUT_FOLDER
        print(f"   - Save debug files: {SAVE_DEBUG_FILES}")
        print(f"   - Output folder: {OUTPUT_FOLDER}")
    except ImportError:
        print("   - Configuration file not found, using defaults")
        SAVE_DEBUG_FILES = True
        OUTPUT_FOLDER = 'business_lookup_output'
    
    print(f"\n2. FILE ORGANIZATION:")
    if SAVE_DEBUG_FILES:
        print(f"   ✅ Files will be organized in: {OUTPUT_FOLDER}/")
        print(f"   ✅ Debug HTML files will be saved")
        print(f"   ✅ Cleaned result files will be generated")
        print(f"   ✅ Owner lookup results in: {OUTPUT_FOLDER}/owner_lookups/")
    else:
        print(f"   ❌ Debug files disabled - only main results saved")
        print(f"   ❌ No HTML debug files")
        print(f"   ❌ No cleaned result files")
        print(f"   ✅ Owner lookup results still saved (no debug files)")
    
    print(f"\n3. TO CHANGE CONFIGURATION:")
    print(f"   Edit config.py and change:")
    print(f"   - SAVE_DEBUG_FILES = True/False")
    print(f"   - OUTPUT_FOLDER = 'your_folder_name'")
    
    print(f"\n4. EXAMPLE USAGE:")
    print(f"   Selenium version:")
    print(f"     python business_lookup.py 'MTD Products Limited'")
    print(f"   Playwright version:")
    print(f"     cd playwright_version")
    print(f"     python business_lookup_playwright.py 'MTD Products Limited'")
    
    print(f"\n5. OUTPUT FILES:")
    if SAVE_DEBUG_FILES:
        print(f"   Main results: {OUTPUT_FOLDER}/business_lookup_results.txt")
        print(f"   Debug HTML: {OUTPUT_FOLDER}/last_search_results.html")
        print(f"   Search page: {OUTPUT_FOLDER}/search_results_page.html")
        print(f"   Owner reports: {OUTPUT_FOLDER}/owner_lookups/business_lookup_details_*.txt")
    else:
        print(f"   Main results: business_lookup_results.txt (current directory)")
        print(f"   Owner reports: owner_lookups/business_lookup_details_*.txt")
    
    print("=" * 60)

def toggle_debug_files():
    """Toggle debug file generation on/off."""
    print("\n" + "=" * 40)
    print("TOGGLE DEBUG FILES")
    print("=" * 40)
    
    # Read current config
    config_file = 'config.py'
    if not os.path.exists(config_file):
        print(f"Config file {config_file} not found!")
        return
    
    with open(config_file, 'r') as f:
        content = f.read()
    
    # Toggle the setting
    if 'SAVE_DEBUG_FILES = True' in content:
        new_content = content.replace('SAVE_DEBUG_FILES = True', 'SAVE_DEBUG_FILES = False')
        new_state = "DISABLED"
    elif 'SAVE_DEBUG_FILES = False' in content:
        new_content = content.replace('SAVE_DEBUG_FILES = False', 'SAVE_DEBUG_FILES = True')
        new_state = "ENABLED"
    else:
        print("Could not find SAVE_DEBUG_FILES setting in config.py")
        return
    
    # Write updated config
    with open(config_file, 'w') as f:
        f.write(new_content)
    
    print(f"✅ Debug file generation is now {new_state}")
    print("Run this demo again to see the updated configuration.")

def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == '--toggle':
        toggle_debug_files()
    else:
        demo_configuration()
        print(f"\nTip: Run 'python demo_config.py --toggle' to toggle debug files on/off")

if __name__ == "__main__":
    main()