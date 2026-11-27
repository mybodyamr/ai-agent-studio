import unittest
from app.skills import DEFAULT_SKILLS, select_skills

class SkillSelectionTests(unittest.TestCase):
    def test_selects_programming_skill(self):
        selected = select_skills("ساعدني أصلح bug في كود Python", DEFAULT_SKILLS)
        self.assertEqual([item["id"] for item in selected], ["coding"])

    def test_selects_multiple_relevant_skills_with_limit(self):
        selected = select_skills("اشرح تحليل بيانات Excel واكتب ملخصًا", DEFAULT_SKILLS)
        self.assertLessEqual(len(selected), 2)
        self.assertIn("data-analysis", [item["id"] for item in selected])

    def test_ignores_unmatched_requests(self):
        self.assertEqual(select_skills("مرحبا، كيف حالك؟", DEFAULT_SKILLS), [])

if __name__ == "__main__":
    unittest.main()
