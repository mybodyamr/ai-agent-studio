import unittest
from unittest.mock import AsyncMock, patch
from app.orchestrator import run_agent

class OrchestratorTests(unittest.IsolatedAsyncioTestCase):
    async def test_manager_delegates_then_reviews(self):
        with patch("app.orchestrator.generate", new_callable=AsyncMock) as generate:
            generate.side_effect = ["SPECIALIST: developer\nTASK: inspect the code", "draft answer", "reviewed answer"]
            result = await run_agent("manager", "review code", [], ["local note"])
            self.assertEqual(result, "reviewed answer")
            self.assertEqual(generate.await_count, 3)
            specialist_call = generate.await_args_list[1]
            self.assertIn("Developer", specialist_call.args[1])
            self.assertIn("local note", specialist_call.args[1])

    async def test_selected_specialist_runs_once(self):
        with patch("app.orchestrator.generate", new_callable=AsyncMock) as generate:
            generate.return_value = "analysis"
            result = await run_agent("analyst", "compare options", [], [])
            self.assertEqual(result, "analysis")
            self.assertEqual(generate.await_count, 1)

if __name__ == "__main__":
    unittest.main()
