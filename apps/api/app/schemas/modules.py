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
    supported_contests: list[dict] = Field(default_factory=list)


class ModulesResponse(BaseModel):
    items: list[ModuleItem]


class ModuleRunCreateRequest(BaseModel):
    module_slug: str = Field(..., min_length=2)
    inputs: dict[str, str | int | float | bool | list[str] | None] = Field(default_factory=dict)
    presentation_variant: str | None = Field(default=None, description="grant_defense or calendar_plan")


class ModuleValidationRequest(BaseModel):
    inputs: dict[str, str | int | float | bool | list[str] | None] = Field(default_factory=dict)


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


class PaymentWebhookRequest(BaseModel):
    payment_id: str = Field(..., min_length=2)
    provider_payment_id: str = Field(..., min_length=2)
    status: str = Field(..., pattern="^(created|pending|paid|failed|canceled|refunded)$")
    signature: str | None = None


class PaymentWebhookResponse(BaseModel):
    payment_id: str
    status: str
    runs_added: int
    message: str


class UsageModuleState(BaseModel):
    free_attempt_used: bool
    free_attempt_available: bool


class UsageResponse(BaseModel):
    anon_session_id: str
    mode: str
    paid_runs: int
    modules: dict[str, UsageModuleState]


class MagicLinkRequest(BaseModel):
    email: str = Field(..., min_length=5)


class MagicLinkRequestResponse(BaseModel):
    status: str
    message: str
    dev_token: str | None = None


class MagicLinkConsumeRequest(BaseModel):
    token: str = Field(..., min_length=10)


class MagicLinkConsumeResponse(BaseModel):
    status: str
    attached_works: int
    message: str


class AccountWorkItem(BaseModel):
    run_id: str
    date: str
    work: str
    competition: str
    project: str
    status: str
    file_format: str
    download_path: str
    actions: list[str]


class AccountWorksResponse(BaseModel):
    mode: str
    items: list[AccountWorkItem]


class DeleteWorkResponse(BaseModel):
    status: str
    run_id: str
    message: str


class ProjectCreateRequest(BaseModel):
    title: str = Field(..., min_length=2)
    competition: str = "ПФКИ"


class ProjectCreateResponse(BaseModel):
    project_id: str
    title: str
    competition: str


class ProjectItem(BaseModel):
    project_id: str
    title: str
    competition: str
    works_count: int


class ProjectsResponse(BaseModel):
    items: list[ProjectItem]


class ProjectAttachRequest(BaseModel):
    run_id: str = Field(..., min_length=2)


class ProjectAttachResponse(BaseModel):
    status: str
    project_id: str
    run_id: str
    project: str
