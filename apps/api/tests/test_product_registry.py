import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PRODUCT_CONFIG = REPO_ROOT / "config" / "product"


def load_json(name: str):
    with (PRODUCT_CONFIG / name).open(encoding="utf-8") as source:
        return json.load(source)


class ProductRegistryTest(unittest.TestCase):
    def test_contest_registry_contains_the_four_approved_contests(self):
        contests = load_json("contests.json")

        self.assertEqual(
            [contest["slug"] for contest in contests],
            ["pfki", "fpg", "rosmolodezh", "first_grants"],
        )
        self.assertEqual(len({contest["slug"] for contest in contests}), len(contests))
        self.assertTrue(all(contest["official_url"].startswith("https://") for contest in contests))
        self.assertTrue(all(contest["status"] in {"active", "preparing", "hidden"} for contest in contests))

    def test_module_registry_has_unique_slugs_and_no_contest_specific_prompt_content(self):
        modules = load_json("modules.json")

        self.assertEqual(len({module["slug"] for module in modules}), len(modules))
        self.assertEqual(
            [module["slug"] for module in modules],
            [
                "social-research",
                "legal-acts",
                "salary",
                "support-letter",
                "presentation",
                "scenario-plan",
                "check-application",
            ],
        )
        serialized = json.dumps(modules, ensure_ascii=False).lower()
        self.assertNotIn("system_prompt", serialized)
        self.assertNotIn("user_prompt", serialized)
        for module in modules:
            self.assertTrue(module["title"].strip())
            self.assertTrue(module["promise"].strip())
            self.assertTrue(module["output_formats"])
            self.assertIsInstance(module["feature_flags"], dict)

    def test_profile_matrix_references_known_modules_and_contests(self):
        contests = {contest["slug"] for contest in load_json("contests.json")}
        modules = {module["slug"] for module in load_json("modules.json")}
        profiles = load_json("module-contest-profiles.json")
        profile_keys = set()

        for profile in profiles:
            key = (profile["module_slug"], profile["contest_slug"])
            self.assertNotIn(key, profile_keys)
            profile_keys.add(key)
            self.assertIn(profile["module_slug"], modules)
            self.assertIn(profile["contest_slug"], contests)
            self.assertIn(profile["status"], {"ready", "preparing", "disabled"})
            self.assertIn(profile["card_visibility"], {"visible", "hidden"})

        self.assertEqual(len(profile_keys), len(modules) * len(contests))

    def test_ready_profiles_have_all_public_pack_references(self):
        profiles = load_json("module-contest-profiles.json")
        examples = {item["example_pack_id"] for item in load_json("examples-manifest.json")}
        faqs = {item["faq_pack_id"] for item in load_json("faq-manifest.json")}

        for profile in profiles:
            if profile["status"] != "ready":
                continue
            for field in (
                "form_schema_id",
                "prompt_pack_id",
                "result_schema_id",
                "template_id",
                "criteria_pack_id",
                "example_pack_id",
                "faq_pack_id",
                "source_policy_id",
                "profile_version",
            ):
                self.assertTrue(profile[field], f"{field} is required for {profile}")
            self.assertIn(profile["example_pack_id"], examples)
            self.assertIn(profile["faq_pack_id"], faqs)

    def test_public_manifests_reference_existing_profiles(self):
        profile_keys = {
            (profile["module_slug"], profile["contest_slug"])
            for profile in load_json("module-contest-profiles.json")
        }

        for manifest_name in ("examples-manifest.json", "faq-manifest.json"):
            manifest = load_json(manifest_name)
            ids = set()
            for item in manifest:
                item_id = item["example_pack_id"] if manifest_name.startswith("examples") else item["faq_pack_id"]
                self.assertNotIn(item_id, ids)
                ids.add(item_id)
                self.assertIn((item["module_slug"], item["contest_slug"]), profile_keys)
                self.assertTrue(item["version"])

    def test_feature_flags_match_phase_zero_decisions(self):
        flags = load_json("feature-flags.json")

        self.assertEqual(
            flags,
            {
                "UNIVERSAL_RUNS_ENABLED": True,
                "MODULE_SPECIFIC_RUNS_ENABLED": False,
                "SUBSCRIPTIONS_ENABLED": False,
                "SUBSCRIPTION_3_DAYS_ENABLED": False,
                "SUBSCRIPTION_7_DAYS_ENABLED": False,
                "SUBSCRIPTION_30_DAYS_ENABLED": False,
            },
        )

    def test_registry_schema_documents_exist(self):
        schemas = PRODUCT_CONFIG / "schemas"

        for name in (
            "contests.schema.json",
            "modules.schema.json",
            "module-contest-profiles.schema.json",
            "examples-manifest.schema.json",
            "faq-manifest.schema.json",
            "feature-flags.schema.json",
        ):
            schema = json.loads((schemas / name).read_text(encoding="utf-8"))
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertIn("$id", schema)
            self.assertIn("type", schema)


if __name__ == "__main__":
    unittest.main()
