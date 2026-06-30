from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


SalarySourceStatus = Literal["ok", "no_data", "unavailable", "blocked", "parse_error", "not_implemented"]
SalaryType = Literal["mean", "median", "mode", "vacancy_sample_median", "official_region_mean", "manual"]


class SalarySourceResult(BaseModel):
    source: str
    status: SalarySourceStatus
    query_role: str
    matched_role: str | None = None
    region: str
    region_id: str | None = None
    year: int | None = None
    salary_value: int | None = None
    salary_type: SalaryType | None = None
    sample_size: int | None = None
    source_url: str | None = None
    notes: str | None = None


class SalaryProbeResponse(BaseModel):
    role: str
    region: str
    year: int
    results: list[SalarySourceResult]
    recommended: SalarySourceResult | None
    warnings: list[str] = Field(default_factory=list)


class SalaryProbeRequest(BaseModel):
    role: str
    region: str
    year: int

