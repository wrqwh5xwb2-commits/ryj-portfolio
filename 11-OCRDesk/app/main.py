import json
import mimetypes
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from .ocr import recognize,export_csv

ROOT=Path(__file__).resolve().parents[1]
mimetypes.add_type('text/javascript','.js')
mimetypes.add_type('text/css','.css')
app=FastAPI(title='OCRDesk',docs_url=None,redoc_url=None)


@app.middleware('http')
async def local_only(request:Request,call_next):
    if request.headers.get('host','').split(':')[0] not in {'127.0.0.1','localhost','testserver'}:
        return JSONResponse({'detail':'只支持本机访问'},status_code=403)
    if request.method=='POST':
        origin=request.headers.get('origin')
        if origin and origin!=str(request.base_url).rstrip('/'):
            return JSONResponse({'detail':'不接受跨站请求'},status_code=403)
        try:length=int(request.headers.get('content-length','0'))
        except ValueError:return JSONResponse({'detail':'无效请求长度'},status_code=400)
        if length>9*1024*1024:return JSONResponse({'detail':'请求过大'},status_code=413)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Cache-Control']='no-store'
    response.headers['Content-Security-Policy']="default-src 'self'; img-src 'self' data: blob:; style-src 'self'; script-src 'self'; frame-ancestors 'none'"
    return response


@app.get('/api/health')
def health():return {'app':'ocrdesk','status':'ok'}


@app.post('/api/recognize')
async def recognize_file(file:UploadFile=File(...)):
    try:
        raw=await file.read(8*1024*1024+1)
        return await run_in_threadpool(recognize,raw)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    finally:await file.close()


class Row(BaseModel):
    id:int=Field(ge=1)
    original:str=Field(max_length=10000)
    text:str=Field(max_length=10000)
    score:float=Field(ge=0,le=1,allow_inf_nan=False)
    reviewed:bool=False


class Export(BaseModel):
    rows:list[Row]=Field(max_length=1000)


@app.post('/api/export/csv')
def csv_file(body:Export):
    return Response(export_csv([r.model_dump() for r in body.rows]),media_type='text/csv',
                    headers={'Content-Disposition':'attachment; filename="ocrdesk-reviewed.csv"'})


@app.get('/api/benchmark')
def benchmark():
    path=ROOT/'docs'/'benchmark.json'
    return json.loads(path.read_text('utf-8')) if path.exists() else None


@app.get('/')
def index():return FileResponse(ROOT/'static'/'index.html')


@app.get('/favicon.ico')
def favicon():return Response(status_code=204)


app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')
app.mount('/samples',StaticFiles(directory=ROOT/'samples'),name='samples')
