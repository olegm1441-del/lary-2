from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import psycopg
from fastapi import Request, Response

from app.core.config import settings
from app.data.modules import get_modules
from app.services.run_store import StoredRun

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ANON_COOKIE = "anon_session_id"
ACCOUNT_COOKIE = "account_session_id"
WORK_TTL = timedelta(hours=24)
MAGIC_LINK_TTL = timedelta(minutes=30)

PROMO_CODES = {
    "LARY-START": {"runs": 3, "status": "active"},
    "LARY-OLD": {"runs": 0, "status": "expired"},
}
PAYMENT_PACKAGES = {
    "single": {"runs": 1, "amount_rub": 320},
    "six": {"runs": 6, "amount_rub": 320 * 6},
}

_memory_users: dict[str, dict] = {}
_memory_account_sessions: dict[str, dict] = {}
_memory_magic_links: dict[str, dict] = {}
_memory_paid_balances: dict[str, int] = {}
_memory_free_attempts: dict[str, set[str]] = {}
_memory_works: dict[str, dict] = {}
_memory_projects: dict[str, dict] = {}
_memory_payments: dict[str, dict] = {}
_memory_payment_events: set[str] = set()
_memory_promo_redemptions: set[tuple[str, str]] = set()


@dataclass
class RequestContext:
    anon_session_id: str
    account_session_id: str | None
    user_id: str | None
    owner_key: str


@dataclass
class ModuleAccessDecision:
    module_slug: str
    source: str
    owner_key: str
    anon_session_id: str
    user_id: str | None


class ModuleAccessError(ValueError):
    pass


def clear_account_store_for_tests() -> None:
    _memory_users.clear()
    _memory_account_sessions.clear()
    _memory_magic_links.clear()
    _memory_paid_balances.clear()
    _memory_free_attempts.clear()
    _memory_works.clear()
    _memory_projects.clear()
    _memory_payments.clear()
    _memory_payment_events.clear()
    _memory_promo_redemptions.clear()


def ensure_account_schema() -> dict:
    if not settings.database_url:
        return {"status": "skipped", "reason": "DATABASE_URL is not set"}

    statements = [
        """
        create table if not exists users (
            id uuid primary key,
            email text not null unique,
            created_at timestamptz not null default now(),
            updated_at timestamptz not null default now()
        );
        """,
        """
        create table if not exists devices (
            id uuid primary key,
            user_id uuid references users(id) on delete set null,
            fingerprint text not null unique,
            first_seen_at timestamptz not null default now(),
            last_seen_at timestamptz not null default now()
        );
        """,
        """
        create table if not exists works (
            id uuid primary key,
            run_id text not null unique,
            anon_session_id text,
            user_id uuid references users(id) on delete set null,
            project_id uuid,
            module_slug text not null,
            title text not null,
            status text not null,
            file_format text not null,
            download_path text not null,
            created_at timestamptz not null default now(),
            expires_at timestamptz
        );
        """,
        """
        create table if not exists projects (
            id uuid primary key,
            anon_session_id text,
            user_id uuid references users(id) on delete set null,
            title text not null,
            competition text not null default 'ПФКИ',
            created_at timestamptz not null default now(),
            updated_at timestamptz not null default now()
        );
        """,
        """
        create table if not exists magic_links (
            token_hash text primary key,
            email text not null,
            anon_session_id text,
            expires_at timestamptz not null,
            consumed_at timestamptz,
            created_at timestamptz not null default now()
        );
        """,
        """
        create table if not exists account_sessions (
            id text primary key,
            user_id uuid not null references users(id) on delete cascade,
            created_at timestamptz not null default now(),
            expires_at timestamptz
        );
        """,
        """
        create table if not exists payments (
            id text primary key,
            owner_key text,
            provider text not null default 'placeholder',
            provider_payment_id text unique,
            package text not null,
            amount_rub integer not null,
            runs integer not null,
            status text not null,
            created_at timestamptz not null default now(),
            paid_at timestamptz,
            provider_payload jsonb
        );
        """,
        """
        create table if not exists payment_events (
            id uuid primary key,
            payment_id text references payments(id) on delete set null,
            provider text not null,
            provider_payment_id text not null,
            status text not null,
            created_at timestamptz not null default now(),
            unique(provider, provider_payment_id, status)
        );
        """,
        """
        create table if not exists credit_ledger (
            id uuid primary key,
            owner_key text,
            source text not null,
            delta integer not null,
            balance_after integer,
            module_slug text,
            run_id text,
            payment_id text references payments(id) on delete set null,
            created_at timestamptz not null default now()
        );
        """,
        """
        create table if not exists promo_redemptions (
            id uuid primary key,
            owner_key text not null,
            code text not null,
            added_runs integer not null,
            created_at timestamptz not null default now(),
            unique(owner_key, code)
        );
        """,
    ]

    with psycopg.connect(settings.database_url, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            for statement in statements:
                cur.execute(statement)
        conn.commit()

    return {"status": "ok"}


def get_request_context(request: Request, response: Response) -> RequestContext:
    anon_session_id = request.cookies.get(ANON_COOKIE) or str(uuid4())
    _set_cookie(response, ANON_COOKIE, anon_session_id, max_age=60 * 60 * 24 * 180)

    account_session_id = request.cookies.get(ACCOUNT_COOKIE)
    user_id = None
    if account_session_id and account_session_id in _memory_account_sessions:
        user_id = _memory_account_sessions[account_session_id]["user_id"]

    owner_key = _user_owner_key(user_id) if user_id else _anon_owner_key(anon_session_id)
    return RequestContext(
        anon_session_id=anon_session_id,
        account_session_id=account_session_id if user_id else None,
        user_id=user_id,
        owner_key=owner_key,
    )


def get_usage(context: RequestContext) -> dict:
    active_modules = [item["slug"] for item in get_modules() if item["status"] == "active"]
    used = _memory_free_attempts.setdefault(context.owner_key, set())
    return {
        "anon_session_id": context.anon_session_id,
        "mode": "account" if context.user_id else "temporary",
        "paid_runs": _memory_paid_balances.get(context.owner_key, 0),
        "modules": {
            slug: {
                "free_attempt_used": slug in used,
                "free_attempt_available": slug not in used,
            }
            for slug in active_modules
        },
    }


def prepare_module_access(module_slug: str, context: RequestContext) -> ModuleAccessDecision:
    used = _memory_free_attempts.setdefault(context.owner_key, set())
    if module_slug not in used:
        return ModuleAccessDecision(module_slug, "free", context.owner_key, context.anon_session_id, context.user_id)
    if _memory_paid_balances.get(context.owner_key, 0) > 0:
        return ModuleAccessDecision(module_slug, "paid", context.owner_key, context.anon_session_id, context.user_id)
    raise ModuleAccessError("Для повторного запуска необходимо купить запуск модуля или применить промокод.")


def record_module_run_success(run: StoredRun, decision: ModuleAccessDecision) -> None:
    if decision.source == "free":
        _memory_free_attempts.setdefault(decision.owner_key, set()).add(decision.module_slug)
    elif decision.source == "paid":
        _memory_paid_balances[decision.owner_key] = max(0, _memory_paid_balances.get(decision.owner_key, 0) - 1)

    file_format = _preferred_file_format(run)
    _memory_works[run.run_id] = {
        "run_id": run.run_id,
        "anon_session_id": decision.anon_session_id,
        "user_id": decision.user_id,
        "project_id": None,
        "module_slug": run.module_slug,
        "title": run.title,
        "status": run.status,
        "file_format": file_format,
        "download_path": run.downloads[file_format],
        "created_at": run.created_at,
        "expires_at": run.created_at + WORK_TTL if not decision.user_id else None,
    }


def apply_promo_code(code: str, context: RequestContext) -> dict:
    normalized = code.strip().upper()
    promo = PROMO_CODES.get(normalized)
    if not promo:
        raise KeyError("Такой промокод не найден. Проверьте буквы и цифры.")
    if promo["status"] == "expired":
        raise TimeoutError("Срок действия промокода закончился.")

    redemption_key = (context.owner_key, normalized)
    if redemption_key in _memory_promo_redemptions:
        raise FileExistsError("Этот промокод уже был применен.")

    added_runs = int(promo["runs"])
    _memory_promo_redemptions.add(redemption_key)
    _memory_paid_balances[context.owner_key] = _memory_paid_balances.get(context.owner_key, 0) + added_runs
    return {
        "status": "applied",
        "added_runs": added_runs,
        "remaining_runs": _memory_paid_balances[context.owner_key],
        "message": f"Промокод применен. Добавлено запусков: {added_runs}.",
    }


def record_payment_created(payment_id: str, package: str, amount_rub: int, runs: int, context: RequestContext | None = None) -> None:
    owner_key = context.owner_key if context else None
    _memory_payments[payment_id] = {
        "payment_id": payment_id,
        "owner_key": owner_key,
        "package": package,
        "amount_rub": amount_rub,
        "runs": runs,
        "status": "created",
        "provider": "placeholder",
        "created_at": datetime.now(timezone.utc),
        "provider_payment_id": None,
    }


def get_payment(payment_id: str) -> dict | None:
    return _memory_payments.get(payment_id)


def handle_payment_webhook(provider: str, payload: dict) -> dict:
    payment_id = str(payload.get("payment_id") or "")
    provider_payment_id = str(payload.get("provider_payment_id") or "")
    status = str(payload.get("status") or "")
    signature = str(payload.get("signature") or "")
    if not payment_id or not provider_payment_id:
        raise ValueError("Не удалось подтвердить платеж.")
    if settings.payment_webhook_secret and signature != _payment_signature(provider, payment_id, provider_payment_id, status):
        raise ValueError("Не удалось подтвердить платеж.")
    payment = _memory_payments.get(payment_id)
    if not payment:
        raise KeyError("Платеж не найден.")
    if status not in {"created", "pending", "paid", "failed", "canceled", "refunded"}:
        raise ValueError("Не удалось подтвердить платеж.")

    event_key = f"{provider}:{provider_payment_id}:{status}"
    if event_key in _memory_payment_events:
        return {
            "payment_id": payment_id,
            "status": payment["status"],
            "runs_added": 0,
            "message": "Событие платежа уже обработано.",
        }

    _memory_payment_events.add(event_key)
    payment["provider"] = provider
    payment["provider_payment_id"] = provider_payment_id
    payment["status"] = status
    runs_added = 0
    if status == "paid" and not payment.get("credited_at"):
        owner_key = payment.get("owner_key")
        if owner_key:
            runs_added = int(payment["runs"])
            _memory_paid_balances[owner_key] = _memory_paid_balances.get(owner_key, 0) + runs_added
        payment["credited_at"] = datetime.now(timezone.utc)
        payment["paid_at"] = datetime.now(timezone.utc)
    return {
        "payment_id": payment_id,
        "status": payment["status"],
        "runs_added": runs_added,
        "message": "Платеж обработан.",
    }


def request_magic_link(email: str, context: RequestContext) -> dict:
    normalized_email = _normalize_email(email)
    if not EMAIL_RE.match(normalized_email):
        raise ValueError("Введите корректный email.")
    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    _memory_magic_links[token_hash] = {
        "email": normalized_email,
        "anon_session_id": context.anon_session_id,
        "expires_at": datetime.now(timezone.utc) + MAGIC_LINK_TTL,
        "consumed_at": None,
    }
    result = {
        "status": "sent",
        "message": "Если email указан верно, ссылка для входа отправлена.",
    }
    if settings.app_env != "production":
        result["dev_token"] = token
    return result


def consume_magic_link(token: str, response: Response) -> dict:
    token_hash = _hash_token(token)
    link = _memory_magic_links.get(token_hash)
    if not link or link["consumed_at"] or link["expires_at"] < datetime.now(timezone.utc):
        raise ValueError("Ссылка для входа устарела. Запросите новую.")

    user = _memory_users.setdefault(link["email"], {"id": str(uuid4()), "email": link["email"], "created_at": datetime.now(timezone.utc)})
    user_id = user["id"]
    account_session_id = str(uuid4())
    _memory_account_sessions[account_session_id] = {"user_id": user_id, "created_at": datetime.now(timezone.utc)}
    link["consumed_at"] = datetime.now(timezone.utc)

    old_owner = _anon_owner_key(link["anon_session_id"])
    new_owner = _user_owner_key(user_id)
    _transfer_owner_state(old_owner, new_owner)
    attached_works = 0
    for work in _memory_works.values():
        if work.get("anon_session_id") == link["anon_session_id"] and not work.get("user_id"):
            work["user_id"] = user_id
            work["expires_at"] = None
            attached_works += 1

    _set_cookie(response, ACCOUNT_COOKIE, account_session_id, max_age=60 * 60 * 24 * 180)
    return {
        "status": "authenticated",
        "attached_works": attached_works,
        "message": "Вход выполнен. Временные работы перенесены в кабинет.",
    }


def get_account_works(context: RequestContext) -> dict:
    now = datetime.now(timezone.utc)
    items = []
    for work in _memory_works.values():
        if context.user_id:
            matches = work.get("user_id") == context.user_id
        else:
            expires_at = work.get("expires_at")
            matches = work.get("anon_session_id") == context.anon_session_id and (not expires_at or expires_at > now)
        if not matches:
            continue
        project_title = "Без проекта"
        project_id = work.get("project_id")
        if project_id and project_id in _memory_projects:
            project_title = _memory_projects[project_id]["title"]
        items.append(
            {
                "run_id": work["run_id"],
                "date": work["created_at"].date().isoformat(),
                "work": _display_work_title(work["module_slug"], work["title"]),
                "competition": "ПФКИ",
                "project": project_title,
                "status": "Готово" if work["status"] == "completed" else "Черновик",
                "file_format": work["file_format"],
                "download_path": work["download_path"],
                "actions": ["Открыть", f"Скачать {work['file_format'].upper()}", "Улучшить", "Удалить"],
            }
        )
    items.sort(key=lambda item: item["date"], reverse=True)
    return {"mode": "account" if context.user_id else "temporary", "items": items}


def create_project(title: str, competition: str, context: RequestContext) -> dict:
    clean_title = title.strip()
    if len(clean_title) < 2:
        raise ValueError("Введите название проекта.")
    project_id = str(uuid4())
    _memory_projects[project_id] = {
        "project_id": project_id,
        "title": clean_title,
        "competition": competition.strip() or "ПФКИ",
        "anon_session_id": context.anon_session_id,
        "user_id": context.user_id,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    return {"project_id": project_id, "title": clean_title, "competition": _memory_projects[project_id]["competition"]}


def attach_work_to_project(project_id: str, run_id: str, context: RequestContext) -> dict:
    project = _memory_projects.get(project_id)
    work = _memory_works.get(run_id)
    if not project:
        raise KeyError("Проект не найден.")
    if not work:
        raise KeyError("Работа не найдена.")
    if context.user_id:
        allowed = project.get("user_id") == context.user_id and work.get("user_id") == context.user_id
    else:
        allowed = project.get("anon_session_id") == context.anon_session_id and work.get("anon_session_id") == context.anon_session_id
    if not allowed:
        raise PermissionError("Нет доступа к этой работе или проекту.")
    work["project_id"] = project_id
    project["updated_at"] = datetime.now(timezone.utc)
    return {"status": "attached", "project_id": project_id, "run_id": run_id, "project": project["title"]}


def save_result_for_email(run: StoredRun, email: str) -> dict:
    normalized_email = _normalize_email(email)
    if not EMAIL_RE.match(normalized_email):
        raise ValueError("Введите корректный email.")

    user = _memory_users.setdefault(normalized_email, {"id": str(uuid4()), "email": normalized_email, "created_at": datetime.now(timezone.utc)})
    user["updated_at"] = datetime.now(timezone.utc)

    if run.run_id in _memory_works:
        _memory_works[run.run_id]["user_id"] = user["id"]
        _memory_works[run.run_id]["expires_at"] = None
    else:
        file_format = _preferred_file_format(run)
        _memory_works[run.run_id] = {
            "run_id": run.run_id,
            "anon_session_id": None,
            "user_id": user["id"],
            "project_id": None,
            "module_slug": run.module_slug,
            "title": run.title,
            "status": run.status,
            "file_format": file_format,
            "download_path": run.downloads[file_format],
            "created_at": run.created_at,
            "expires_at": None,
        }
    return _email_file_response(normalized_email, _preferred_file_format(run))


def package_config(package: str) -> dict:
    if package not in PAYMENT_PACKAGES:
        raise ValueError("Такой пакет запусков недоступен.")
    return PAYMENT_PACKAGES[package]


def _transfer_owner_state(old_owner: str, new_owner: str) -> None:
    _memory_paid_balances[new_owner] = _memory_paid_balances.get(new_owner, 0) + _memory_paid_balances.pop(old_owner, 0)
    old_attempts = _memory_free_attempts.pop(old_owner, set())
    _memory_free_attempts.setdefault(new_owner, set()).update(old_attempts)
    for owner_key, code in list(_memory_promo_redemptions):
        if owner_key == old_owner:
            _memory_promo_redemptions.remove((owner_key, code))
            _memory_promo_redemptions.add((new_owner, code))


def _display_work_title(module_slug: str, title: str) -> str:
    if module_slug == "social-research":
        return "Доказательства актуальности"
    return title.split(":", 1)[0]


def _preferred_file_format(run: StoredRun) -> str:
    for file_format in ("docx", "pptx", "pdf"):
        if file_format in run.downloads:
            return file_format
    if run.downloads:
        return next(iter(run.downloads))
    raise ValueError("У этой работы пока нет файла для отправки.")


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _payment_signature(provider: str, payment_id: str, provider_payment_id: str, status: str) -> str:
    raw = f"{settings.payment_webhook_secret}:{provider}:{payment_id}:{provider_payment_id}:{status}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _email_file_response(email: str, file_format: str) -> dict:
    return {
        "status": "saved",
        "email": email,
        "file_format": file_format,
        "message": "Файл сохранен в аккаунт. Отправка письма поставлена в очередь; SMTP-провайдера подключим перед боевыми письмами.",
    }


def _anon_owner_key(anon_session_id: str) -> str:
    return f"anon:{anon_session_id}"


def _user_owner_key(user_id: str | None) -> str:
    return f"user:{user_id}"


def _set_cookie(response: Response, name: str, value: str, max_age: int) -> None:
    response.set_cookie(
        key=name,
        value=value,
        max_age=max_age,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
    )
