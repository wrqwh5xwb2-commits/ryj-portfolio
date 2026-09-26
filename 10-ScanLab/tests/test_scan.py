from io import BytesIO
import cv2
import numpy as np
from PIL import Image
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.synthetic import scene
from app.vision import decode, detect, enhance, ordered, process, rectify, validate


def encoded(image):return cv2.imencode('.png',image)[1].tobytes()


def test_known_corners_located():
    image,truth=scene(42)
    found,_,_=detect(image)
    assert found is not None
    assert np.linalg.norm(found-truth,axis=1).mean()<10


def test_rectification_maps_four_corners_to_canvas():
    image,points=scene(42)
    warped,matrix=rectify(image,points)
    transformed=cv2.perspectiveTransform(points[None],matrix)[0]
    h,w=warped.shape[:2]
    assert np.allclose(transformed,[[0,0],[w-1,0],[w-1,h-1],[0,h-1]],atol=.01)


def test_ordering_is_stable():
    points=np.float32([[60,10],[100,60],[50,110],[10,50]])
    expected=ordered(points)
    for shuffled in [points[[2,0,3,1]],points[::-1]]:assert np.array_equal(ordered(shuffled),expected)


@pytest.mark.parametrize("points",[[[0,0],[1,1],[0,1],[1,0]],[[0,0],[0,0],[1,1],[0,1]],[[0,0],[1,0],[1,float('nan')],[0,1]],[[0,0],[2,0],[1,1],[0,1]]])
def test_invalid_manual_geometry(points):
    image,_=scene(1)
    with pytest.raises(ValueError):process(image,points)


def test_blank_requires_explicit_manual_selection():
    image=np.full((300,400,3),255,np.uint8)
    assert process(image)["status"]=="needs_manual"
    result=process(image,[[.1,.1],[.9,.1],[.9,.9],[.1,.9]])
    assert result["status"]=="ready" and result["method"]=="manual"


def test_binary_is_binary_and_a4_ratio():
    image,truth=scene(2)
    warped,_=rectify(image,truth,"a4")
    assert abs(warped.shape[1]/warped.shape[0]-1/np.sqrt(2))<.005
    _,binary=enhance(warped)
    assert set(np.unique(binary))=={0,255}


def test_exif_orientation_and_resize():
    im=Image.new('RGB',(120,240),'white');exif=im.getexif();exif[274]=6
    buf=BytesIO();im.save(buf,format='JPEG',exif=exif)
    decoded,size=decode(buf.getvalue())
    assert size==[240,120] and decoded.shape[:2]==(120,240)
    buf=BytesIO();Image.new('RGB',(2400,1900),'white').save(buf,format='PNG')
    decoded,size=decode(buf.getvalue());assert max(decoded.shape[:2])==1800


def test_transparency_is_white():
    buf=BytesIO();Image.new('RGBA',(100,100),(0,0,0,0)).save(buf,format='PNG')
    image,_=decode(buf.getvalue());assert image.min()==255


def test_api_process_and_health():
    with TestClient(app) as client:
        image,_=scene(42)
        response=client.post('/api/process',files={'file':('中文.png',encoded(image),'image/png')})
        assert response.status_code==200
        data=response.json();assert data['status']=='ready'
        assert set(data['outputs'])=={'color','enhanced','binary'}
        assert client.get('/api/health').json()['app']=='scanlab'


@pytest.mark.parametrize('body',[b'',b'not a picture'])
def test_bad_file_rejected(body):
    with TestClient(app) as client:assert client.post('/api/process',files={'file':('bad.png',body,'image/png')}).status_code==422


def test_parameter_validation_and_host_guard():
    with TestClient(app) as client:
        image,_=scene(42);file={'file':('demo.png',encoded(image),'image/png')}
        assert client.post('/api/process',files=file,data={'block_size':4}).status_code==422
        assert client.post('/api/process',files=file,data={'corners':'[1,2]'}).status_code==422
        assert client.post('/api/process',files=file,headers={'Origin':'https://other.example'}).status_code==403
        assert client.get('/',headers={'Host':'other.example'}).status_code==403
        assert client.get('/static/app.js').headers['content-type'].startswith('text/javascript')
