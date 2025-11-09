#!/usr/bin/env python3
"""
Setup script for the Playwright-based business lookup pipeline.
This script installs the required dependencies and sets up Playwright browsers.
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a shell command and handle errors."""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        print(f"Error: {e.stderr}")
        return False

def main():
    """Main setup function."""
    print("=" * 60)
    print("PLAYWRIGHT BUSINESS LOOKUP PIPELINE SETUP")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists('requirements.txt'):
        print("❌ Error: requirements.txt not found. Please run this script from the playwright_version directory.")
        return False
    
    # Install Python requirements
    if not run_command("pip install -r requirements.txt", "Installing Python requirements"):
        return False
    
    # Install Playwright browsers
    if not run_command("python -m playwright install", "Installing Playwright browsers"):
        return False
    
    # Install Playwright system dependencies (Linux/WSL only)
    if sys.platform.startswith('linux'):
        run_command("python -m playwright install-deps", "Installing Playwright system dependencies")
    
    print("\n" + "=" * 60)
    print("✅ SETUP COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print("\nYou can now run the business lookup pipeline:")
    print("1. For a single business lookup:")
    print("   python business_lookup_playwright.py 'Business Name'")
    print("\n2. For processing GeoJSON owners:")
    print("   python process_geojson_owners_playwright.py")
    print("\n3. Make sure your GeoJSON file is in the same directory")
    print("   (default: Property_Ownership_Public_8585062059551015044.geojson)")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)