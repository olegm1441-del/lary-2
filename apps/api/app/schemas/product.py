from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PublicProductModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Contest(PublicProductModel):
    slug: str
    name: str
    short_name: str
    status: Literal["active", "preparing", "hidden"]
    official_url: str
    docs_version: str | None = None
    updated_at: str


class ProductModule(PublicProductModel):
    slug: str
    status: Literal["active", "preparing", "hidden"]
    category: str
    title: str
    promise: str
    duration: str
    output_formats: list[str]
    feature_flags: dict[str, bool] = Field(default_factory=dict)


class ModuleContestProfile(PublicProductModel):
    module_slug: str
    contest_slug: str
    status: Literal["ready", "preparing", "disabled"]
    card_visibility: Literal["visible", "hidden"]
    form_schema_id: str | None = None
    prompt_pack_id: str | None = None
    result_schema_id: str | None = None
    template_id: str | None = None
    criteria_pack_id: str | None = None
    example_pack_id: str | None = None
    faq_pack_id: str | None = None
    source_policy_id: str | None = None
    profile_version: str | None = None


class ExampleAsset(PublicProductModel):
    format: str
    filename: str
    path: str
    size: int


class ExampleManifestItem(PublicProductModel):
    example_pack_id: str
    module_slug: str
    contest_slug: str
    version: str
    input_summary: str
    preview_sections: list[str]
    assets: list[ExampleAsset]
    notes_for_user: str
    migration_status: str
    updated_at: str


class FaqEntry(PublicProductModel):
    question: str
    answer: str
    category: str


class FaqManifestItem(PublicProductModel):
    faq_pack_id: str
    module_slug: str
    contest_slug: str
    version: str
    categories: list[str]
    entries: list[FaqEntry]
    migration_status: str
    updated_at: str


class FeatureFlags(PublicProductModel):
    UNIVERSAL_RUNS_ENABLED: bool
    MODULE_SPECIFIC_RUNS_ENABLED: bool
    SUBSCRIPTIONS_ENABLED: bool
    SUBSCRIPTION_3_DAYS_ENABLED: bool
    SUBSCRIPTION_7_DAYS_ENABLED: bool
    SUBSCRIPTION_30_DAYS_ENABLED: bool

