import unittest

from app.services.field_quality_rules import analyze_field_quality


class PlaytestFieldAssistantTest(unittest.TestCase):
    def test_filled_region_is_covered_and_not_suggested_inside_problem(self):
        result = analyze_field_quality(
            "social-research",
            "problem",
            "Молодёжь мало знает современные форматы народного театра",
            {
                "region": "Свердловская область",
                "direction": "Театр",
                "target_group": "Подростки 12–17 лет",
            },
        )

        self.assertIn("region", result["covered_by_fields"])
        self.assertNotIn("add_region", [item["id"] for item in result["suggestions"]])
        self.assertNotIn("территор", result["message"].lower())

    def test_filled_age_is_not_suggested_again_for_target_group(self):
        result = analyze_field_quality(
            "social-research",
            "target_group",
            "Подростки и молодёжь 12–22 лет",
            {"region": "Свердловская область"},
        )

        self.assertNotIn("add_age", [item["id"] for item in result["suggestions"]])

    def test_suggestions_have_stable_ids_and_operations(self):
        result = analyze_field_quality(
            "social-research",
            "problem",
            "Молодёжь мало знает театральные форматы",
            {"region": "Свердловская область"},
        )

        self.assertTrue(result["suggestions"])
        for suggestion in result["suggestions"]:
            self.assertTrue(suggestion["id"])
            self.assertIn(suggestion["operation"], {"suggest_text", "dismiss"})

    def test_scenario_suggestions_do_not_leak_into_social_research(self):
        result = analyze_field_quality(
            "social-research",
            "problem",
            "Молодёжь мало знает театральные форматы",
            {"region": "Свердловская область"},
        )

        self.assertNotIn("add_schedule", [item["id"] for item in result["suggestions"]])


if __name__ == "__main__":
    unittest.main()
