import json
from pathlib import Path
from pdfminer.high_level import extract_text

base = Path(r'd:/SAMARJEET/sih26035')
output = {}
for pdf_path in base.glob('*.pdf'):
    try:
        text = extract_text(str(pdf_path))
        txt_path = pdf_path.with_suffix('.txt')
        txt_path.write_text(text, encoding='utf-8')
        # Store first 3000 chars for summary
        output[pdf_path.name] = text[:3000]
    except Exception as e:
        output[pdf_path.name] = f"Error extracting: {e}"
print(json.dumps(output, ensure_ascii=False, indent=2))
