"""固定小型合成开发集，衡量字符错误；不代表真实单据表现。"""
import json
import re
import unicodedata
from datetime import datetime,timezone
from pathlib import Path
from .ocr import recognize

ROOT=Path(__file__).resolve().parents[1]


def normalize(text):
    return re.sub(r'\s+','',unicodedata.normalize('NFKC',text))


def distance(a,b):
    previous=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        current=[i]
        for j,y in enumerate(b,1):
            current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(x!=y)))
        previous=current
    return previous[-1]


def main():
    truth=json.loads((ROOT/'samples'/'ground-truth.json').read_text('utf-8'))
    expected=normalize('\n'.join(truth['texts']))
    cases=[]
    for condition in truth['conditions']:
        result=recognize((ROOT/'samples'/f'{condition}.png').read_bytes())
        predicted=normalize('\n'.join(line['original'] for line in result['lines']))
        target='' if condition=='blank' else expected
        edits=distance(target,predicted)
        cases.append({'condition':condition,'expected_chars':len(target),'edit_distance':edits,
            'cer':round(edits/len(target),4) if target else None,
            'line_count':len(result['lines']),'elapsed_ms':result['elapsed_ms'],
            'expected_text':target,'recognized_text':predicted,
            'empty_correct':not predicted if condition=='blank' else None})
    report={'created_at':datetime.now(timezone.utc).isoformat(),'engine':'RapidOCR 3.9.2 / CPU',
            'dataset':'5 positive synthetic development images + 1 blank, same text/font/layout, not real documents',
            'normalization':'NFKC and remove whitespace; punctuation retained; detector reading order retained',
            'character_error_rate':round(sum(x['edit_distance'] for x in cases if x['expected_chars'])/sum(x['expected_chars'] for x in cases),4),
            'cases':cases}
    (ROOT/'docs'/'benchmark.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='cases'},ensure_ascii=True,indent=2))


if __name__=='__main__':main()
