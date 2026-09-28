"""Adapted from RapidAI/RapidOCR README Usage (Apache-2.0).

Copyright (c) 2021 RapidOCR Authors. All rights reserved.
Upstream commit: 095232a4c94f7f0e6600ba5bba1177010ad696d4 (v3.9.2).
Changes: accept a local image argument; serialize an execution summary instead
of printing the full object; omit vis() to avoid an additional font download.
The engine construction and OCR call follow the original quickstart.
"""
import json
import sys
from pathlib import Path
from rapidocr import RapidOCR


def main():
    engine = RapidOCR()
    image = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[1] / 'samples' / 'clean.png')
    result = engine(image)
    summary = {'source': 'RapidOCR README Usage', 'input': Path(image).name,
               'texts': list(result.txts or []), 'scores': [float(x) for x in (result.scores or [])]}
    output = Path(__file__).resolve().parents[1] / 'docs' / 'upstream-run.json'
    output.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
