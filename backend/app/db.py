import sqlite3
from pathlib import Path
from .config import settings

def connect():
    path = Path(settings.database_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
          id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS messages (
          id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
          role TEXT NOT NULL CHECK(role IN ('user','assistant','system')), content TEXT NOT NULL,
          agent TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, id);
        CREATE TABLE IF NOT EXISTS memories (
          id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT NOT NULL DEFAULT 'default',
          content TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(content, content='memories', content_rowid='id');
        CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
          INSERT INTO memories_fts(rowid, content) VALUES (new.id, new.content);
        END;
        CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
          INSERT INTO memories_fts(memories_fts, rowid, content) VALUES('delete', old.id, old.content);
        END;
        CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
          INSERT INTO memories_fts(memories_fts, rowid, content) VALUES('delete', old.id, old.content);
          INSERT INTO memories_fts(rowid, content) VALUES (new.id, new.content);
        END;
        CREATE TABLE IF NOT EXISTS tasks (
          id TEXT PRIMARY KEY, title TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'queued',
          detail TEXT, result TEXT, error TEXT, agent TEXT NOT NULL DEFAULT 'manager',
          created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS documents (
          id TEXT PRIMARY KEY, original_name TEXT NOT NULL, stored_name TEXT NOT NULL UNIQUE,
          characters INTEGER NOT NULL DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(document_id UNINDEXED, original_name, content);
        CREATE TABLE IF NOT EXISTS audit_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL, entity_id TEXT,
          detail TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS skills (
          id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL,
          instructions TEXT NOT NULL, triggers TEXT NOT NULL DEFAULT '[]',
          enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1)),
          builtin INTEGER NOT NULL DEFAULT 0 CHECK(builtin IN (0,1)),
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)
        # Forward-compatible migration for databases created by earlier builds.
        task_columns = {r["name"] for r in db.execute("PRAGMA table_info(tasks)")}
        for name, declaration in (("result", "TEXT"), ("error", "TEXT"), ("agent", "TEXT NOT NULL DEFAULT 'manager'")):
            if name not in task_columns:
                db.execute(f"ALTER TABLE tasks ADD COLUMN {name} {declaration}")
        from .skills import seed_default_skills
        seed_default_skills(db)
