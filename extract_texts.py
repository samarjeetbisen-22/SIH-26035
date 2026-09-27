import json
from pathlib import Path
import PyPDF2

base = Path(r'd:/SAMARJEET/sih26035')
output = {}
for pdf_path in base.glob('*.pdf'):
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            pages_text = []
            for i, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ''
                pages_text.append(f"--- Page {i} ---\n{text}")
            full_text = "\n".join(pages_text)
            # Save to .txt file for manual inspection if needed
            txt_path = pdf_path.with_suffix('.txt')
            txt_path.write_text(full_text, encoding='utf-8')
            # Store first 2000 chars for summary
            output[pdf_path.name] = full_text[:2000]
    except Exception as e:
        output[pdf_path.name] = f"Error extracting: {e}"

print(json.dumps(output, ensure_ascii=False, indent=2))
