import json, sys
from pathlib import Path
import PyPDF2

base = Path(r'd:/SAMARJEET/sih26035')
pdf_files = [p for p in base.iterdir() if p.suffix.lower() == '.pdf']
result = {}
for pdf in pdf_files:
    try:
        with open(pdf, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = []
            for page_num, page in enumerate(reader.pages, start=1):
                try:
                    page_text = page.extract_text() or ''
                except Exception as e:
                    page_text = ''
                text.append(f"--- Page {page_num} ---\n{page_text}")
            full_text = "\n".join(text)
            # keep only first 5000 chars to avoid huge output
            result[pdf.name] = full_text[:5000]
    except Exception as e:
        result[pdf.name] = f"Error extracting: {e}"
print(json.dumps(result, ensure_ascii=False))
