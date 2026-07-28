from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class StoredRun:
    run_id: str
    module_slug: str
    title: str
    status: str
    summary: str
    sections: list[dict[str, str]]
    downloads: dict[str, str]
    files: dict[str, str]
    contest_slug: str = "pfki"
    profile_version: str | None = None
    project_id: str | None = None
    error_code: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class RunStore:
    def __init__(self) -> None:
        self._runs: dict[str, StoredRun] = {}

    def save(self, run: StoredRun) -> StoredRun:
        self._runs[run.run_id] = run
        return run

    def get(self, run_id: str) -> StoredRun | None:
        return self._runs.get(run_id)

    def clear(self) -> None:
        self._runs.clear()


run_store = RunStore()
