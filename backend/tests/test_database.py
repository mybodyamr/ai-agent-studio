import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app.config import settings
from app.db import connect, init_db

class DatabaseTests(unittest.TestCase):
    def test_schema_and_memory_fts(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(settings, "database_path", str(Path(tmp) / "test.sqlite3")):
                init_db()
                with connect() as db:
                    db.execute("INSERT INTO memories(project,content) VALUES(?,?)",("demo","local memory test"))
                    row=db.execute("SELECT content FROM memories_fts WHERE memories_fts MATCH ?",("local",)).fetchone()
                    self.assertIsNotNone(row)
                    db.execute("INSERT INTO conversations(id,title) VALUES(?,?)",("c1","test"))
                    db.execute("INSERT INTO messages(conversation_id,role,content) VALUES(?,?,?)",("c1","user","hello"))
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM messages WHERE conversation_id='c1'").fetchone()[0],1)

if __name__ == "__main__":
    unittest.main()
