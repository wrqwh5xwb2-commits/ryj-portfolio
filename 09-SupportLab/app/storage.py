from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import sqlite3
from pathlib import Path

from .dataset import DOCUMENTS


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, title TEXT NOT NULL, category TEXT NOT NULL, content TEXT NOT NULL, fingerprint TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS questions (id INTEGER PRIMARY KEY, question TEXT NOT NULL, result TEXT NOT NULL, feedback TEXT, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS tickets (id INTEGER PRIMARY KEY, title TEXT NOT NULL, content TEXT NOT NULL, category TEXT NOT NULL, priority TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS ticket_events (id INTEGER PRIMARY KEY, ticket_id INTEGER NOT NULL, action TEXT NOT NULL, note TEXT NOT NULL, created_at TEXT NOT NULL);
            ''')
            for ident, title, category, content in DOCUMENTS:
                db.execute("INSERT OR IGNORE INTO documents VALUES (?,?,?,?,?,?)", (ident, title, category, content, self.fingerprint(title, content), now()))

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def fingerprint(title, content):
        return hashlib.sha256((title.strip() + "\n" + content.strip()).encode()).hexdigest()

    def documents(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT * FROM documents ORDER BY created_at, id")]
