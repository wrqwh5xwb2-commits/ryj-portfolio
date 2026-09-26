import json
import mimetypes
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from .vision import decode, process

ROOT = Path(__file__).resolve().parents[1]
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")
app = FastAPI(title="ScanLab", version="1.0.0", docs_url=None, redoc_url=None)


@app.middleware("http")
async def local_only(request: Request, call_next):
    host = request.headers.get("host", "").split(":")[0]
    if host not in {"127.0.0.1", "localhost", "testserver"}:
        return JSONResponse({"detail":"仅供本机使用"},403)
    if request.method == "POST":
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            return JSONResponse({"detail":"不接受其他网站发起的处理请求"},403)
        try:
            length = int(request.headers.get("content-length", "0"))
        except ValueError:
            return JSONResponse({"detail":"无效长度"},400)
        if length > 13 * 1024 * 1024:
            return JSONResponse({"detail":"文件超过12MB限制"},413)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data: blob:; script-src 'self'; style-src 'self'; frame-ancestors 'none'"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/health")
def health():
    return {"app":"scanlab", "status":"ok"}


@app.post("/api/process")
async def scan(file: UploadFile = File(...), corners: str = Form(""), aspect: Literal["auto","a4","a4-landscape"] = Form("auto"), block_size: int = Form(35), c: int = Form(12)):
    try:
        raw = await file.read(12 * 1024 * 1024 + 1)
        if len(raw) > 12 * 1024 * 1024:
            raise HTTPException(413, "文件不能超过12MB")
        def work():
            image, original = decode(raw)
            points = json.loads(corners) if corners else None
            result = process(image, points, aspect, block_size, c)
            result["original_size"] = original
            return result
        return await run_in_threadpool(work)
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc
    finally:
        await file.close()


@app.get("/api/evaluation")
def evaluation():
    path = ROOT / "docs" / "benchmark.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
app.mount("/samples", StaticFiles(directory=ROOT / "samples"), name="samples")
