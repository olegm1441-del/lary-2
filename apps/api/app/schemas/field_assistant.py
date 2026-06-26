from pydantic import BaseModel, Field


class FieldAssistantRequest(BaseModel):
    module_slug: str = Field(..., min_length=2)
    field_key: str = Field(..., min_length=1)
    field_label: str = ""
    value: str | int | float | bool | None = ""
    form_context: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class FieldAssistantResponse(BaseModel):
    status: str = Field(..., pattern="^(info|warning|error|success)$")
    should_block: bool
    message: str = Field(default="", max_length=140)
    chips: list[str] = Field(default_factory=list, max_length=3)
    rewrite_suggestion: str | None = None
