from pathlib import Path
from io import BytesIO
import csv

from fastapi.testclient import TestClient
from PIL import Image
import pytest

from app.main import app
from app.ocr import decode,export_csv,recognize
from app.evaluate import distance,normalize

ROOT=Path(__file__).resolve().parents[1]


def test_real_engine_and_bounding_boxes():
    data=recognize((ROOT/'samples'/'clean.png').read_bytes())
    assert data['status']=='ready'
    assert '采购清单' in ''.join(row['text'] for row in data['lines'])
    w,h=data['working_size']
    for row in data['lines']:
        assert 0<=row['score']<=1
        assert len(row['box'])==4
        assert all(0<=x<=w and 0<=y<=h for x,y in row['box'])


def test_blank_does_not_invent_text():
    data=recognize((ROOT/'samples'/'blank.png').read_bytes())
    assert data['status']=='no_text' and data['lines']==[]


@pytest.mark.parametrize('raw',[b'',b'not-an-image',b'x'*(8*1024*1024+1)],ids=['empty','invalid','too_large'])
def test_invalid_input(raw):
    with pytest.raises(ValueError):decode(raw)


def test_exif_and_transparency():
    buf=BytesIO();im=Image.new('RGB',(80,160),'white');exif=im.getexif();exif[274]=6
    im.save(buf,format='JPEG',exif=exif)
    array,original=decode(buf.getvalue());assert original==[160,80] and array.shape[:2]==(80,160)
    buf=BytesIO();Image.new('RGBA',(80,80),(0,0,0,0)).save(buf,format='PNG')
    array,_=decode(buf.getvalue());assert array.min()==255


@pytest.mark.parametrize('value',['=1+1',' +1','@SUM(1)','-2','\t=1'])
def test_csv_formula_protection_preserves_review(value):
    rows=[{'id':1,'original':value,'text':'已核对,"含逗号"\n第二行','score':.9,'reviewed':True}]
    content=export_csv(rows)
    assert content.startswith(b'\xef\xbb\xbf')
    result=list(csv.reader(content.decode('utf-8-sig').splitlines(keepends=True)))
    assert result[1][1]=="'"+value and result[1][2]==rows[0]['text']
    assert result[1][-2:]==['True','True']


def test_character_error_metric():
    assert distance('abc','adc')==1
    assert distance('abc','abcd')==1
    assert distance('abc','')==3
    assert normalize('Ａ B\nＣ')=='ABC'


def test_api_upload_export_and_guards():
    with TestClient(app) as client:
        assert client.get('/api/health').json()['app']=='ocrdesk'
        response=client.post('/api/recognize',files={'file':('中文清单.png',(ROOT/'samples'/'clean.png').read_bytes(),'image/png')})
        assert response.status_code==200 and response.json()['status']=='ready'
        rows=response.json()['lines'];rows[0]['text']='修改后的中文';rows[0]['reviewed']=True
        response=client.post('/api/export/csv',json={'rows':rows})
        assert response.status_code==200 and '修改后的中文' in response.content.decode('utf-8-sig')
        assert client.post('/api/export/csv',json={'rows':[{'id':1,'original':'x','text':'x','score':2}]}).status_code==422
        assert client.post('/api/recognize',files={'file':('bad.png',b'bad','image/png')}).status_code==422
        assert client.post('/api/export/csv',json={'rows':[]},headers={'origin':'https://other.example'}).status_code==403
        assert client.get('/',headers={'host':'other.example'}).status_code==403
        assert client.get('/static/app.js').headers['content-type'].startswith('text/javascript')
