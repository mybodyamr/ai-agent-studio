import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.config import settings
from app.main import app

class ApiTests(unittest.TestCase):
    def test_memory_and_file_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(settings,"database_path",str(Path(tmp)/"db.sqlite3")), patch.object(settings,"workspace_path",str(Path(tmp)/"workspace")):
                with TestClient(app) as client:
                    created=client.post("/api/memory",json={"content":"remember local test"})
                    self.assertEqual(created.status_code,200)
                    self.assertEqual(client.get("/api/memory").json()[0]["content"],"remember local test")
                    rejected=client.post("/api/memory",json={"content":"   "})
                    self.assertEqual(rejected.status_code,422)
                    upload=client.post("/api/files",files={"file":("notes.txt",b"private file phrase","text/plain")})
                    self.assertEqual(upload.status_code,200,upload.text)
                    doc_id=upload.json()["id"]
                    found=client.get("/api/files/search",params={"q":"phrase"})
                    self.assertEqual(found.status_code,200)
                    self.assertEqual(found.json()[0]["document_id"],doc_id)
                    self.assertEqual(client.delete("/api/files/"+doc_id).status_code,200)
                    self.assertEqual(client.get("/api/files").json(),[])
                    self.assertEqual(client.delete("/api/memory/"+str(created.json()["id"])).status_code,200)

    def test_upload_rejects_fake_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(settings,"database_path",str(Path(tmp)/"db.sqlite3")), patch.object(settings,"workspace_path",str(Path(tmp)/"workspace")):
                with TestClient(app) as client:
                    response=client.post("/api/files",files={"file":("fake.pdf",b"not pdf","application/pdf")})
                    self.assertEqual(response.status_code,400)

    def test_chat_uses_relevant_local_file_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(settings,"database_path",str(Path(tmp)/"db.sqlite3")), patch.object(settings,"workspace_path",str(Path(tmp)/"workspace")):
                with TestClient(app) as client:
                    uploaded=client.post("/api/files",files={"file":("invoice.txt",b"The invoice total is 125 dollars.","text/plain")})
                    self.assertEqual(uploaded.status_code,200,uploaded.text)
                    with patch("app.main.run_agent",new_callable=AsyncMock,return_value="summary") as agent:
                        response=client.post("/api/chat",json={"message":"summarize invoice","agent":"analyst"})
                        self.assertEqual(response.status_code,200,response.text)
                        self.assertIn("invoice",agent.await_args.args[4].lower())
                        self.assertIn("125",agent.await_args.args[4])

if __name__ == "__main__":
    unittest.main()
