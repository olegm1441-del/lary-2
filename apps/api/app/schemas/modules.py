from pydantic import BaseModel, Field


class ModuleItem(BaseModel):
    slug: str
    status: str
    title: str
    task_title: str
    duration: str
    competition: str
    output_formats: list[str]
    fields: list[str]


class ModulesResponse(BaseModel):
    items: list[ModuleItem]


class ModuleRunCreateRequest(BaseModel):
    module_slug: str = Field(..., min_length=2)
    inputs: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    presentation_variant: str | None = Field(default=None, description="grant_defense or calendar_plan")


class ModuleValidationRequest(BaseModel):
    inputs: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class ModuleValidationHint(BaseModel):
    field_key: str
    message: str
    tone: str = "attention"


class ModuleValidationResponse(BaseModel):
    module_slug: str
    status: str
    hints: list[ModuleValidationHint]


class ModuleRunCreateResponse(BaseModel):
    run_id: str
    status: str
    module_slug: str
    title: str
    message: str
    downloads: dict[str, str]


class ModuleRunResultResponse(BaseModel):
    run_id: str
    status: str
    module_slug: str
    title: str
    summary: str
    sections: list[dict[str, str]]
    downloads: dict[str, str]


class EmailFileRequest(BaseModel):
    email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=6)


class EmailFileResponse(BaseModel):
    status: str
    email: str
    file_format: str
    message: str


class ImproveRequest(BaseModel):
    instruction: str = Field(default="Сделать текст понятнее и официальнее")


class PromoApplyRequest(BaseModel):
    code: str = Field(..., min_length=2)


class PromoApplyResponse(BaseModel):
    status: str
    added_runs: int
    remaining_runs: int
    message: str


class PaymentCreateRequest(BaseModel):
    package: str = Field(default="single", pattern="^(single|six)$")


class PaymentCreateResponse(BaseModel):
    payment_id: str
    status: str
    amount_rub: int
    runs: int
    payment_url: str
    message: str


class PaymentStatusResponse(BaseModel):
    payment_id: str
    status: str
    message: str
