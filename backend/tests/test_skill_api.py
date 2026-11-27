import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.config import settings
from app.main import app

class SkillApiTests(unittest.TestCase):
    def test_skills_are_seeded_managed_and_used_by_chat(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(settings, "database_path", str(Path(tmp) / "db.sqlite3")), patch.object(settings, "workspace_path", str(Path(tmp) / "workspace")):
                with TestClient(app) as client:
                    skills = client.get("/api/skills").json()
                    self.assertIn("coding", [skill["id"] for skill in skills])
                    with patch("app.main.run_agent", new_callable=AsyncMock, return_value="done") as run:
                        response = client.post("/api/chat", json={"message": "Help me debug this Python code", "agent": "developer"})
                        self.assertEqual(response.status_code, 200, response.text)
                        self.assertEqual(response.json()["skills"][0]["id"], "coding")
                        self.assertEqual(run.await_args.args[5][0]["id"], "coding")

    def test_custom_skill_crud_and_builtin_protection(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(settings, "database_path", str(Path(tmp) / "db.sqlite3")), patch.object(settings, "workspace_path", str(Path(tmp) / "workspace")):
                with TestClient(app) as client:
                    created = client.post("/api/skills", json={
                        "name": "SQL Helper",
                        "description": "Helps with SQL queries",
                        "instructions": "Explain SQL queries safely and clearly.",
                        "triggers": ["sql", "database"]
                    })
                    self.assertEqual(created.status_code, 200, created.text)
                    skill_id = created.json()["id"]
                    self.assertEqual(client.patch(f"/api/skills/{skill_id}", json={"enabled": False}).json()["enabled"], False)
                    self.assertEqual(client.delete(f"/api/skills/{skill_id}").status_code, 200)
                    protected = client.delete("/api/skills/coding")
                    self.assertEqual(protected.status_code, 403)

if __name__ == "__main__":
    unittest.main()
