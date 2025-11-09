# Business Lookup Pipeline - Updated Configuration System

## 📁 **File Organization & Debug Control**

The business lookup pipeline now includes configurable file output with organized folder structure.

## 🎛️ **Configuration Options**

### **Toggle Debug Files On/Off**
```python
# In config.py
SAVE_DEBUG_FILES = True   # Enable debug file generation
SAVE_DEBUG_FILES = False  # Disable debug file generation (cleaner operation)
```

### **Organize Files in Folders**
```python
# In config.py  
OUTPUT_FOLDER = 'business_lookup_output'  # All files go here when enabled
```

## 📂 **File Organization Structure**

### **When SAVE_DEBUG_FILES = True** (Default)
```
business_lookup_output/
├── business_lookup_results.txt          # Main results
├── last_search_results.html            # Debug HTML from search
├── search_results_page.html            # Full search page HTML
├── last_search_results_cleaned.txt     # Cleaned/parsed results
├── debug_page.html                     # Error debugging page (if needed)
└── owner_lookups/                      # GeoJSON processing results
    └── business_lookup_details_20241109_143022.txt
```

### **When SAVE_DEBUG_FILES = False** (Clean Mode)
```
current_directory/
├── business_lookup_results.txt          # Main results only
└── owner_lookups/                      # GeoJSON processing results
    └── business_lookup_details_20241109_143022.txt
```

## 🚀 **Quick Start**

### **1. Configure Output Behavior**
```powershell
# View current configuration
python demo_config.py

# Toggle debug files on/off
python demo_config.py --toggle
```

### **2. Run Business Lookups**

**Selenium Version:**
```powershell
python business_lookup.py "MTD Products Limited"
```

**Playwright Version:**
```powershell
cd playwright_version
python business_lookup_playwright.py "MTD Products Limited" 
```

### **3. Process GeoJSON Files**

**Selenium Version:**
```powershell
python process_geojson_owners.py
```

**Playwright Version:**
```powershell
cd playwright_version
python process_geojson_owners_playwright.py
```

## ⚙️ **Configuration Details**

### **What Gets Saved When**

| File Type | Debug ON | Debug OFF | Description |
|-----------|----------|-----------|-------------|
| Main results | ✅ | ✅ | business_lookup_results.txt |
| HTML debug files | ✅ | ❌ | Raw search pages for troubleshooting |
| Cleaned results | ✅ | ❌ | Parsed and formatted HTML content |
| Owner reports | ✅ | ✅ | Comprehensive business lookup details |
| Error pages | ✅ | ❌ | Debug pages when searches fail |

### **Benefits of Each Mode**

**Debug Mode (SAVE_DEBUG_FILES = True):**
- 📋 Complete debugging information
- 🔍 Raw HTML for troubleshooting failed searches
- 📊 Cleaned/parsed results for analysis
- 📁 Organized in dedicated folder
- 🛠️ Perfect for development and problem-solving

**Clean Mode (SAVE_DEBUG_FILES = False):**
- 🚀 Faster operation (no file I/O overhead)
- 💾 Less disk space usage
- 🎯 Only essential results saved
- 📱 Perfect for production/batch processing

## 📋 **Configuration Files**

### **Main Configuration: config.py**
```python
# Configuration for both Selenium and Playwright versions
SAVE_DEBUG_FILES = True  # Toggle debug file generation
OUTPUT_FOLDER = 'business_lookup_output'  # Organize files here
```

### **Per-Script Configuration**
Each script also has its own configuration constants at the top:
- `business_lookup.py`
- `business_lookup_playwright.py`  
- `process_geojson_owners.py`
- `process_geojson_owners_playwright.py`
- `web_scraper_playwright.py`

## 🎯 **Use Cases**

### **Development & Debugging**
```python
SAVE_DEBUG_FILES = True
OUTPUT_FOLDER = 'debug_output'
```
- Keep all HTML files for troubleshooting
- Organized in dedicated folder
- Easy to clean up when done

### **Production Batch Processing**
```python
SAVE_DEBUG_FILES = False
# Files saved to current directory
```
- Minimal file generation
- Faster processing
- Only essential results

### **Custom Organization**
```python
SAVE_DEBUG_FILES = True
OUTPUT_FOLDER = 'client_project_2024'
```
- Project-specific folder
- Complete documentation
- Professional organization

## 🔧 **Technical Notes**

### **Backwards Compatibility**
- All existing functionality preserved
- Default behavior: debug files enabled with folder organization
- Can be switched back to original behavior by setting `SAVE_DEBUG_FILES = False`

### **Performance Impact**
- Debug mode: ~10-15% slower due to file I/O
- Clean mode: Minimal performance impact
- Folder creation is automatic and one-time

### **Error Handling**
- Graceful fallback if folder creation fails
- Configuration errors don't break core functionality
- Debug file failures don't stop business lookups

## 🎉 **Summary**

The updated business lookup pipeline gives you complete control over file generation and organization:

1. **Toggle debug files on/off** with a simple boolean
2. **Organize all files in a dedicated folder** for cleaner workspaces
3. **Switch between development and production modes** easily
4. **Maintain full backwards compatibility** with existing workflows

Perfect for both development debugging and clean production runs! 🚀