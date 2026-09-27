import pathlib, csv, re, sys

# Ensure pdfplumber is available; install if missing
try:
    import pdfplumber
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pdfplumber', '-q'])
    import pdfplumber

pdf_path = pathlib.Path('oiml r76.pdf')
if not pdf_path.exists():
    print('PDF not found:', pdf_path)
    sys.exit(1)

# Regex to capture rows like "0‑5   0.001   0.0015"
row_pattern = re.compile(r"(?P<range>\d+\s*[\-–]\s*\d+|[≥≤]?\s*\d+)\s+(?P<classI>\d*\.\d+)\s+(?P<classII>\d*\.\d+)")

rows = []
with pdfplumber.open(pdf_path) as pdf:
    for page_number, page in enumerate(pdf.pages, start=1):
        text = page.extract_text() or ''
        # Look for the specific heading to narrow search (optional)
        if 'Maximum permissible errors' in text:
            print(f'Found heading on page {page_number}')
        for line in text.split('\n'):
            m = row_pattern.search(line.replace('‑', '-'))
            if m:
                rows.append((page_number, m.group('range'), float(m.group('classI')), float(m.group('classII'))))

if not rows:
    print('No table rows found.')
    sys.exit(0)

# Write CSV
csv_path = pathlib.Path('oiml_limits.csv')
with csv_path.open('w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['page', 'range', 'class_I_error', 'class_II_error'])
    for r in rows:
        writer.writerow(r)

# Write simplified text for parser
txt_path = pathlib.Path('oiml_limits.txt')
with txt_path.open('w') as f:
    for _, range_part, ci, ci2 in rows:
        f.write(f"{range_part} {ci} {ci2}\n")

print(f'Extracted {len(rows)} rows to {csv_path} and {txt_path}')
