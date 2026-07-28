import copy
import json
import tempfile
import unittest
from pathlib import Path

from app.services.product_registry import (
    ProductRegistry,
    ProductRegistryError,
    ProfileNotReadyError,
    _default_product_config,
)


ROOT = Path(__file__).resolve().parents[3]
PRODUCT_CONFIG = ROOT / "config" / "product"


class ProductRegistryRuntimeTest(unittest.TestCase):
    def test_loads_shared_registry(self):
        registry = ProductRegistry.load(PRODUCT_CONFIG)
        self.assertEqual(
            [item.slug for item in registry.get_contests()],
            ["pfki", "fpg", "rosmolodezh", "first_grants"],
        )
        self.assertEqual(len(registry.get_modules()), 7)

    def test_ready_profile_resolves_all_pack_ids(self):
        profile = ProductRegistry.load(PRODUCT_CONFIG).require_ready_profile("salary", "pfki")
        self.assertEqual(profile.prompt_pack_id, "prompt.pfki.salary.v1")
        self.assertEqual(profile.profile_version, "1.0.0")

    def test_preparing_profile_is_not_runnable(self):
        with self.assertRaises(ProfileNotReadyError) as caught:
            ProductRegistry.load(PRODUCT_CONFIG).require_ready_profile("salary", "fpg")
        self.assertEqual(caught.exception.status, "preparing")

    def test_duplicate_profile_fails_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for source in PRODUCT_CONFIG.glob("*.json"):
                (target / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            profiles_path = target / "module-contest-profiles.json"
            profiles = json.loads(profiles_path.read_text(encoding="utf-8"))
            profiles.append(copy.deepcopy(profiles[0]))
            profiles_path.write_text(json.dumps(profiles, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(ProductRegistryError):
                ProductRegistry.load(target)

    def test_public_serializer_does_not_expose_private_runtime_data(self):
        registry = ProductRegistry.load(PRODUCT_CONFIG)
        payload = registry.public_profile("salary", "pfki")
        serialized = json.dumps(payload, ensure_ascii=False)
        for forbidden in ("system_prompt", "credentials", "provider", "filesystem_path"):
            self.assertNotIn(forbidden, serialized)

    def test_shallow_service_root_uses_packaged_registry_without_parent_indexing(self):
        with tempfile.TemporaryDirectory() as directory:
            service_root = Path(directory)
            packaged = service_root / "product-config"
            packaged.mkdir()
            self.assertEqual(_default_product_config(service_root), packaged)


if __name__ == "__main__":
    unittest.main()
