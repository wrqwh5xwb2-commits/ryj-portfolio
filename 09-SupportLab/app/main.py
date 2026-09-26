"""单机教学部署：只绑定 127.0.0.1。公开上线前需增加身份认证与访问控制。"""
from contextlib import asynccontextmanager
import json
import mimetypes
import os
from pathlib import Path
import sqlite3
from threading import RLock
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .dataset import TRAIN
from .engine import Retriever, Triage, analyze
from .evaluation import run_evaluation
from .storage import Store, now

ROOT = Path(__file__).resolve().parents[1]
# Windows 注册表可能把 .js 映射为 text/plain，nosniff 下浏览器会拒绝执行。
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")


class CleanModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class Question(CleanModel):
    text: str = Field(min_length=2, max_length=2000)
    mode: Literal["hybrid", "tfidf", "bm25"] = "hybrid"


class Document(CleanModel):
    title: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=2, max_length=30)
    content: str = Field(min_length=15, max_length=12000)


class Ticket(CleanModel):
    title: str = Field(min_length=2, max_length=120)
    content: str = Field(min_length=2, max_length=2000)
    category: str = Field(min_length=2, max_length=30)
    priority: Literal["普通", "高"] = "普通"


class UpdateTicket(CleanModel):
    status: Literal["待处理", "处理中", "已关闭"]
    note: str = Field(min_length=2, max_length=1000)


class Feedback(CleanModel):
    value: Literal["helpful", "unhelpful"]


def create_app(db_path=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.store = Store(db_path or os.environ.get("SUPPORTLAB_DB", str(ROOT / "data" / "supportlab.db")))
        app.state.triage = Triage()
        app.state.retriever = Retriever(app.state.store.documents())
        app.state.lock = RLock()
        report_path = ROOT / "data" / "evaluation.json"
        app.state.report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else None
        yield

    app = FastAPI(title="SupportLab · 知答", version="1.0.0", lifespan=lifespan, docs_url=None, redoc_url=None)

    @app.middleware("http")
    async def local_guard(request: Request, call_next):
        # 阻止其他网站向本地应用跨源写数据；本机 CLI 仍可无 Origin 调用。
        host = request.headers.get("host", "").split(":")[0]
        if host not in {"127.0.0.1", "localhost", "testserver"}:
            return JSONResponse({"detail": "仅支持本机访问"}, status_code=403)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin and origin != str(request.base_url).rstrip("/"):
                return JSONResponse({"detail": "不接受跨来源写入"}, status_code=403)
            try:
                length = int(request.headers.get("content-length", "0"))
            except ValueError:
                return JSONResponse({"detail": "请求长度无效"}, status_code=400)
            if length > 150000:
                return JSONResponse({"detail": "请求过大"}, status_code=413)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; frame-ancestors 'none'"
        return response

    @app.get("/api/health")
    def health():
        return {"app": "supportlab", "status": "ok", "mode": "local", "version": "1.0.0"}

    @app.get("/api/overview")
    def overview():
        with app.state.store.connect() as db:
            return {"documents": db.execute("SELECT COUNT(*) FROM documents").fetchone()[0],
                    "questions": db.execute("SELECT COUNT(*) FROM questions").fetchone()[0],
                    "open_tickets": db.execute("SELECT COUNT(*) FROM tickets WHERE status != '已关闭'").fetchone()[0],
                    "closed_tickets": db.execute("SELECT COUNT(*) FROM tickets WHERE status = '已关闭'").fetchone()[0],
                    "feedback": {r[0]: r[1] for r in db.execute("SELECT feedback, COUNT(*) FROM questions WHERE feedback IS NOT NULL GROUP BY feedback")},
                    "categories": list(TRAIN)}

    @app.get("/api/documents")
    def documents():
        return app.state.store.documents()

    @app.post("/api/documents", status_code=201)
    def add_document(doc: Document):
        if doc.category not in TRAIN:
            raise HTTPException(422, "请选择已有业务类别")
        # 上传内容只作为资料保存；从不执行其中的命令或 HTML。
        if not any(c.isalnum() for c in doc.content):
            raise HTTPException(422, "文档需要包含有效文字")
        ident = uuid4().hex[:12]
        with app.state.lock:
            try:
                with app.state.store.connect() as db:
                    if db.execute("SELECT COUNT(*) FROM documents").fetchone()[0] >= 300:
                        raise HTTPException(409, "教学版最多保存300篇规范")
                    db.execute("INSERT INTO documents VALUES (?,?,?,?,?,?)", (ident, doc.title, doc.category, doc.content, Store.fingerprint(doc.title, doc.content), now()))
                    # 先成功构建新索引，再提交。异常时数据库事务会回滚。
                    new_index = Retriever([dict(r) for r in db.execute("SELECT * FROM documents ORDER BY created_at, id")])
                app.state.retriever = new_index
            except sqlite3.IntegrityError:
                raise HTTPException(409, "相同标题和正文的文档已经存在")
        return {"id": ident, "message": "资料已保存，索引已更新"}

    @app.post("/api/questions")
    def question(body: Question):
        result = analyze(body.text, app.state.triage, app.state.retriever, body.mode)
        with app.state.store.connect() as db:
            cursor = db.execute("INSERT INTO questions (question,result,created_at) VALUES (?,?,?)", (body.text, json.dumps(result, ensure_ascii=False), now()))
            result["id"] = cursor.lastrowid
        return result

    @app.get("/api/questions")
    def history():
        with app.state.store.connect() as db:
            return [dict(r) for r in db.execute("SELECT id,question,feedback,created_at FROM questions ORDER BY id DESC LIMIT 15")]

    @app.post("/api/questions/{ident}/feedback")
    def feedback(ident: int, body: Feedback):
        with app.state.store.connect() as db:
            if db.execute("UPDATE questions SET feedback=? WHERE id=?", (body.value, ident)).rowcount == 0:
                raise HTTPException(404, "问题不存在")
        return {"message": "反馈已保存；用于后续人工分析，不会自动改变模型"}

    @app.post("/api/tickets", status_code=201)
    def create_ticket(body: Ticket):
        if body.category not in TRAIN:
            raise HTTPException(422, "请选择已有业务类别")
        with app.state.store.connect() as db:
            timestamp = now()
            cursor = db.execute("INSERT INTO tickets (title,content,category,priority,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?)", (body.title, body.content, body.category, body.priority, "待处理", timestamp, timestamp))
            ident = cursor.lastrowid
            db.execute("INSERT INTO ticket_events (ticket_id,action,note,created_at) VALUES (?,?,?,?)", (ident, "创建工单", "由用户确认分类后创建", timestamp))
        return {"id": ident}

    @app.get("/api/tickets")
    def tickets():
        with app.state.store.connect() as db:
            rows = [dict(r) for r in db.execute("SELECT * FROM tickets ORDER BY id DESC")]
            for row in rows:
                row["events"] = [dict(r) for r in db.execute("SELECT action,note,created_at FROM ticket_events WHERE ticket_id=? ORDER BY id", (row["id"],))]
            return rows

    @app.patch("/api/tickets/{ident}")
    def update_ticket(ident: int, body: UpdateTicket):
        with app.state.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT status FROM tickets WHERE id=?", (ident,)).fetchone()
            if not row:
                raise HTTPException(404, "工单不存在")
            allowed = {"待处理": {"处理中"}, "处理中": {"已关闭", "待处理"}, "已关闭": {"待处理"}}
            if body.status not in allowed[row["status"]]:
                raise HTTPException(409, "状态变化不合法：请先接单处理，再关闭；已关闭可重新打开")
            timestamp = now()
            db.execute("UPDATE tickets SET status=?,updated_at=? WHERE id=?", (body.status, timestamp, ident))
            db.execute("INSERT INTO ticket_events (ticket_id,action,note,created_at) VALUES (?,?,?,?)", (ident, f"{row['status']} → {body.status}", body.note, timestamp))
        return {"message": "工单状态已更新"}

    @app.get("/api/evaluation")
    def evaluation():
        return app.state.report

    @app.post("/api/evaluation")
    def evaluate():
        with app.state.lock:
            report = run_evaluation()
            app.state.report = report
        return report

    @app.get("/")
    def index():
        return FileResponse(ROOT / "static" / "index.html")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon():
        return Response(status_code=204)

    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
    return app


app = create_app()
