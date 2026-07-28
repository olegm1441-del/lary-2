from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter, ValidationError

from app.core.config import settings
from app.schemas.product import (
    Contest,
    ExampleManifestItem,
    FaqManifestItem,
    FeatureFlags,
    ModuleContestProfile,
    ProductModule,
)


READY_PROFILE_IDS = (
    "form_schema_id",
    "prompt_pack_id",
    "result_schema_id",
    "template_id",
    "criteria_pack_id",
    "example_pack_id",
    "faq_pack_id",
    "source_policy_id",
    "profile_version",
)
FORBIDDEN_PUBLIC_KEYS = {
    "system_prompt",
    "prompt_text",
    "credentials",
    "provider_settings",
    "secret",
    "template_path",
    "filesystem_path",
}


class ProductRegistryError(RuntimeError):
    pass


class UnknownModuleError(ProductRegistryError):
    pass


class UnknownContestError(ProductRegistryError):
    pass


class ProfileNotReadyError(ProductRegistryError):
    def __init__(self, status: str):
        self.status = status
        super().__init__(status)


class ProductRegistry:
    def __init__(
        self,
        *,
        contests: list[Contest],
        modules: list[ProductModule],
        profiles: list[ModuleContestProfile],
        examples: list[ExampleManifestItem],
        faqs: list[FaqManifestItem],
        feature_flags: FeatureFlags,
    ) -> None:
        self.contests = contests
        self.modules = modules
        self.profiles = profiles
        self.examples = examples
        self.faqs = faqs
        self.feature_flags = feature_flags
        self.contests_by_slug = {item.slug: item for item in contests}
        self.modules_by_slug = {item.slug: item for item in modules}
        self.profiles_by_key = {(item.module_slug, item.contest_slug): item for item in profiles}

    @classmethod
    def load(cls, config_dir: Path) -> "ProductRegistry":
        try:
            raw = {
                "contests": _read_json(config_dir / "contests.json"),
                "modules": _read_json(config_dir / "modules.json"),
                "profiles": _read_json(config_dir / "module-contest-profiles.json"),
                "examples": _read_json(config_dir / "examples-manifest.json"),
                "faqs": _read_json(config_dir / "faq-manifest.json"),
                "feature_flags": _read_json(config_dir / "feature-flags.json"),
            }
            _validate_public_payload(raw)
            registry = cls(
                contests=TypeAdapter(list[Contest]).validate_python(raw["contests"]),
                modules=TypeAdapter(list[ProductModule]).validate_python(raw["modules"]),
                profiles=TypeAdapter(list[ModuleContestProfile]).validate_python(raw["profiles"]),
                examples=TypeAdapter(list[ExampleManifestItem]).validate_python(raw["examples"]),
                faqs=TypeAdapter(list[FaqManifestItem]).validate_python(raw["faqs"]),
                feature_flags=FeatureFlags.model_validate(raw["feature_flags"]),
            )
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise ProductRegistryError(f"Invalid product registry: {exc}") from exc
        registry.validate_references()
        return registry

    def validate_references(self) -> None:
        _require_unique([item.slug for item in self.contests], "contest slug")
        _require_unique([item.slug for item in self.modules], "module slug")
        pairs = [(item.module_slug, item.contest_slug) for item in self.profiles]
        _require_unique(pairs, "module-contest profile")
        expected = {(module.slug, contest.slug) for module in self.modules for contest in self.contests}
        if set(pairs) != expected:
            raise ProductRegistryError("Profile matrix must contain exactly one item for every module and contest.")
        example_ids = {item.example_pack_id for item in self.examples}
        faq_ids = {item.faq_pack_id for item in self.faqs}
        for profile in self.profiles:
            if profile.module_slug not in self.modules_by_slug:
                raise ProductRegistryError(f"Unknown module reference: {profile.module_slug}")
            if profile.contest_slug not in self.contests_by_slug:
                raise ProductRegistryError(f"Unknown contest reference: {profile.contest_slug}")
            if profile.status == "ready":
                missing = [name for name in READY_PROFILE_IDS if not getattr(profile, name)]
                if missing:
                    raise ProductRegistryError(f"Ready profile is incomplete: {profile.module_slug}/{profile.contest_slug}")
                if profile.example_pack_id not in example_ids or profile.faq_pack_id not in faq_ids:
                    raise ProductRegistryError(f"Manifest reference is missing: {profile.module_slug}/{profile.contest_slug}")

    def get_contests(self) -> list[Contest]:
        return list(self.contests)

    def get_modules(self) -> list[ProductModule]:
        return list(self.modules)

    def get_profile(self, module_slug: str, contest_slug: str) -> ModuleContestProfile | None:
        if module_slug not in self.modules_by_slug:
            raise UnknownModuleError(module_slug)
        if contest_slug not in self.contests_by_slug:
            raise UnknownContestError(contest_slug)
        return self.profiles_by_key.get((module_slug, contest_slug))

    def require_ready_profile(self, module_slug: str, contest_slug: str) -> ModuleContestProfile:
        profile = self.get_profile(module_slug, contest_slug)
        if profile is None:
            raise ProductRegistryError("Unknown module-contest profile")
        if profile.status != "ready":
            raise ProfileNotReadyError(profile.status)
        return profile

    def get_supported_contests(self, module_slug: str) -> list[Contest]:
        if module_slug not in self.modules_by_slug:
            raise UnknownModuleError(module_slug)
        return [
            contest
            for contest in self.contests
            if self.profiles_by_key[(module_slug, contest.slug)].card_visibility == "visible"
        ]

    def public_profile(self, module_slug: str, contest_slug: str) -> dict[str, Any]:
        profile = self.get_profile(module_slug, contest_slug)
        if profile is None:
            raise ProductRegistryError("Unknown module-contest profile")
        # Public IDs are deliberate opaque identifiers; prompt/template contents never leave backend.
        return profile.model_dump()

    def public_module(self, module: ProductModule) -> dict[str, Any]:
        payload = module.model_dump()
        payload["supported_contests"] = [
            contest.model_dump() for contest in self.get_supported_contests(module.slug)
        ]
        return payload


def product_config_dir() -> Path:
    if settings.product_config_dir:
        return Path(settings.product_config_dir).expanduser().resolve()
    repository_config = Path(__file__).resolve().parents[4] / "config" / "product"
    if repository_config.is_dir():
        return repository_config
    return Path(__file__).resolve().parents[2] / "product-config"


@lru_cache(maxsize=4)
def _load_cached(config_dir: str) -> ProductRegistry:
    return ProductRegistry.load(Path(config_dir))


def get_product_registry() -> ProductRegistry:
    return _load_cached(str(product_config_dir()))


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_unique(values: list[Any], label: str) -> None:
    if len(values) != len(set(values)):
        raise ProductRegistryError(f"Duplicate {label}.")


def _validate_public_payload(value: Any, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key.lower() in FORBIDDEN_PUBLIC_KEYS:
                raise ProductRegistryError(f"Private key in public registry: {'.'.join((*path, key))}")
            _validate_public_payload(nested, (*path, key))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _validate_public_payload(nested, (*path, str(index)))
