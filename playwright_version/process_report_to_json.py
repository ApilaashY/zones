import re
import json
import os

def parse_report_to_json(file_path):
    """
    Parses the non-profit search report, deduplicates entries, and saves to JSON.
    """
    print(f"Reading file: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex to find all result blocks
    # Looks for "--- Result #<number> ---" followed by the block content until the next empty line or end of file
    # We capture the content *after* the header
    result_blocks = re.split(r'--- Result #\d+ ---', content)
    
    # The first split is usually the header/preamble, so we skip it
    raw_blocks = result_blocks[1:]
    
    print(f"Found {len(raw_blocks)} raw result blocks.")

    # Clean and collect blocks
    cleaned_blocks = []
    for block in raw_blocks:
        # Strip whitespace
        block = block.strip()
        if not block:
            continue
        
        # We only want blocks that look like data (have "Business Name:")
        if "Business Name:" in block:
            cleaned_blocks.append(block)

    # Deduplicate using set
    unique_blocks = list(set(cleaned_blocks))
    print(f"Unique blocks after deduplication: {len(unique_blocks)}")

    # Parse into dictionaries
    data_list = []
    for block in unique_blocks:
        entry = {}
        lines = block.split('\n')
        for line in lines:
            line = line.strip()
            if ": " in line:
                key, value = line.split(": ", 1)
                entry[key] = value
        
        if entry:
            data_list.append(entry)

    # Sort by Business Name for consistency
    data_list.sort(key=lambda x: x.get("Business Name", ""))

    # Output to JSON
    output_path = os.path.join(os.path.dirname(file_path), 'non_profit_data2.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data_list, f, indent=4, ensure_ascii=False)

    print(f"Successfully saved {len(data_list)} unique records to: {output_path}")
    return output_path

if __name__ == "__main__":
    # Find the latest report file automatically
    output_dir = r'c:\Users\senth\Downloads\zones\business_lookup_output\non_profit_lookups'
    
    try:
        files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.startswith('non_profit_search_report') and f.endswith('.txt')]
        if not files:
            print("No report files found!")
        else:
            # Get the most recent file
            latest_file = max(files, key=os.path.getmtime)
            parse_report_to_json(latest_file)
    except Exception as e:
        print(f"Error: {e}")
