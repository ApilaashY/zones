from clean_html import clean_search_results

# Read the HTML file
with open('business_lookup_output/search_results_UNION_CO-OP.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

# Clean it
result = clean_search_results(html_content)

# Look for key structures
print("Length of cleaned result:", len(result))
print("\nLooking for RESULT structures...")

lines = result.split('\n')
for i, line in enumerate(lines):
    line = line.strip()
    if 'RESULT' in line.upper() or 'UNION' in line.upper():
        print(f'Line {i}: {line}')
        
print("\nFirst 20 lines of cleaned output:")
for i, line in enumerate(lines[:20]):
    print(f"{i:2}: {line.strip()}")