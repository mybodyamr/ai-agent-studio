import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app.config import settings
from app.db import connect, init_db

class DatabaseTests(unittest.TestCase):
    def test_schema_memory_document_indexes_and_task_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(settings, "database_path", str(Path(tmp) / "test.sqlite3")):
                init_db()
                with connect() as db:
                    db.execute("INSERT INTO memories(project,content) VALUES(?,?)",("demo","local memory test"))
                    row=db.execute("SELECT content FROM memories_fts WHERE memories_fts MATCH ?",("local",)).fetchone()
                    self.assertIsNotNone(row)
                    db.execute("DELETE FROM memories WHERE project='demo'")
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM memories_fts WHERE memories_fts MATCH ?",("local",)).fetchone()[0],0)
                    db.execute("INSERT INTO documents(id,original_name,stored_name,characters) VALUES(?,?,?,?)",("d1","notes.txt","abc.txt",12))
                    db.execute("INSERT INTO documents_fts(document_id,original_name,content) VALUES(?,?,?)",("d1","notes.txt","private local document"))
                    found=db.execute("SELECT document_id FROM documents_fts WHERE documents_fts MATCH ?",("private",)).fetchone()
                    self.assertEqual(found["document_id"],"d1")
                    columns={r["name"] for r in db.execute("PRAGMA table_info(tasks)")}
                    self.assertTrue({"result","error","agent"}.issubset(columns))
                    db.execute("INSERT INTO conversations(id,title) VALUES(?,?)",("c1","test"))
                    db.execute("INSERT INTO messages(conversation_id,role,content) VALUES(?,?,?)",("c1","user","hello"))
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM messages WHERE conversation_id='c1'").fetchone()[0],1)

    def test_init_db_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(settings, "database_path", str(Path(tmp) / "test.sqlite3")):
                init_db()
                init_db()

if __name__ == "__main__":
    unittest.main()
