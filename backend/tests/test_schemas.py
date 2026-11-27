import unittest
from pydantic import ValidationError
from app.schemas import ChatRequest, MemoryRequest, ResearchRequest, TaskRequest

class SchemaValidationTests(unittest.TestCase):
    def test_rejects_blank_required_fields(self):
        for factory in (
            lambda: ChatRequest(message="   "),
            lambda: MemoryRequest(content="   "),
            lambda: ResearchRequest(query="  "),
            lambda: TaskRequest(title="   "),
        ):
            with self.assertRaises(ValidationError):
                factory()

    def test_trims_user_text(self):
        self.assertEqual(ChatRequest(message="  hello  ").message,"hello")
        self.assertEqual(TaskRequest(title="  task  ").title,"task")
        self.assertEqual(ResearchRequest(query="  ai  ").query,"ai")

if __name__ == "__main__":
    unittest.main()
