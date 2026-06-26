from __future__ import annotations

import hashlib
import json
import re
import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
from fastapi import Request, Response

from app.core.config import settings
from app.data.modules import get_modules
from app.services.run_store import StoredRun, run_store

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ANON_COOKIE = "anon_session_id"
ACCOUNT_COOKIE = "account_session_id"
WORK_TTL = timedelta(hours=24)
MAGIC_LINK_TTL = timedelta(minutes=30)

PROMO_SEEDS = {
    "LARY-START": {"runs": 3, "status": "active", "campaign": "start"},
    "LARY-OLD": {"runs": 0, "status": "expired", "campaign": "legacy"},
}
PAYMENT_PACKAGES = {
    "single": {"runs": 1, "amount_rub": 320},
    "six": {"runs": 6, "amount_rub": 320 * 6},
}


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
    ensure_account_schema()
    with _connect() as conn:
        for table in [
            "payment_events",
            "credit_ledger",
            "promo_redemptions",
            "payments",
            "free_attempts",
            "module_outputs",
            "module_inputs",
            "module_runs",
            "works",
            "projects",
            "account_sessions",
            "magic_links",
            "users",
            "devices",
            "anonymous_sessions",
        ]:
            _execute(conn, f"delete from {table}")
        conn.commit()
    _seed_promo_codes()


def simulate_account_store_restart_for_tests() -> None:
    """No-op hook: SQL is the source of truth, so clearing process memory is unnecessary."""
    ensure_account_schema()


def ensure_account_schema() -> dict:
    statements = [
        """
        create table if not exists schema_migrations (
            version text primary key,
            applied_at text not null
        )
        """,
        """
        create table if not exists users (
            id text primary key,
            email text not null unique,
            created_at text not null,
            updated_at text not null
        )
        """,
        """
        create table if not exists anonymous_sessions (
            id text primary key,
            created_at text not null,
            last_seen_at text not null
        )
        """,
        """
        create table if not exists devices (
            id text primary key,
            anon_session_id text not null,
            user_id text,
            first_seen_at text not null,
            last_seen_at text not null
        )
        """,
        """
        create table if not exists account_sessions (
            id text primary key,
            user_id text not null,
            created_at text not null,
            expires_at text
        )
        """,
        """
        create table if not exists magic_links (
            token_hash text primary key,
            email text not null,
            anon_session_id text,
            expires_at text not null,
            consumed_at text,
            created_at text not null
        )
        """,
        """
        create table if not exists projects (
            id text primary key,
            anon_session_id text,
            user_id text,
            title text not null,
            competition text not null,
            created_at text not null,
            updated_at text not null
        )
        """,
        """
        create table if not exists module_runs (
            run_id text primary key,
            module_slug text not null,
            title text not null,
            status text not null,
            summary text not null,
            downloads_json text not null,
            files_json text not null,
            created_at text not null,
            deleted_at text
        )
        """,
        """
        create table if not exists module_inputs (
            run_id text primary key,
            inputs_json text not null,
            created_at text not null
        )
        """,
        """
        create table if not exists module_outputs (
            run_id text primary key,
            sections_json text not null,
            created_at text not null
        )
        """,
        """
        create table if not exists works (
            run_id text primary key,
            anon_session_id text,
            user_id text,
            project_id text,
            module_slug text not null,
            title text not null,
            status text not null,
            file_format text not null,
            download_path text not null,
            created_at text not null,
            expires_at text,
            deleted_at text
        )
        """,
        """
        create table if not exists free_attempts (
            owner_key text not null,
            module_slug text not null,
            created_at text not null,
            primary key (owner_key, module_slug)
        )
        """,
        """
        create table if not exists payments (
            id text primary key,
            owner_key text,
            provider text not null,
            provider_payment_id text,
            package text not null,
            amount_rub integer not null,
            runs integer not null,
            status text not null,
            created_at text not null,
            paid_at text,
            provider_payload text
        )
        """,
        """
        create table if not exists payment_events (
            id text primary key,
            payment_id text,
            provider text not null,
            provider_payment_id text not null,
            status text not null,
            created_at text not null,
            unique(provider, provider_payment_id, status)
        )
        """,
        """
        create table if not exists credit_ledger (
            id text primary key,
            owner_key text not null,
            source text not null,
            delta integer not null,
            module_slug text,
            run_id text,
            payment_id text,
            promo_code text,
            created_at text not null
        )
        """,
        """
        create table if not exists promo_codes (
            code text primary key,
            runs integer not null,
            status text not null,
            expires_at text,
            total_limit integer,
            per_owner_limit integer,
            module_scope text,
            campaign text,
            created_at text not null
        )
        """,
        """
        create table if not exists promo_redemptions (
            id text primary key,
            owner_key text not null,
            code text not null,
            added_runs integer not null,
            created_at text not null,
            unique(owner_key, code)
        )
        """,
    ]

    with _connect() as conn:
        for statement in statements:
            _execute(conn, statement)
        _ensure_legacy_columns(conn)
        _execute(
            conn,
            "insert into schema_migrations(version, applied_at) values(?, ?) on conflict(version) do nothing",
            ("2026-06-26-p2-state-ledger", _now()),
        )
        conn.commit()
    _seed_promo_codes()
    return {"status": "ok", "backend": "postgresql" if settings.database_url else "sqlite"}


def get_request_context(request: Request, response: Response) -> RequestContext:
    ensure_account_schema()
    anon_session_id = request.cookies.get(ANON_COOKIE) or str(uuid4())
    _set_cookie(response, ANON_COOKIE, anon_session_id, max_age=60 * 60 * 24 * 180)

    now = _now()
    with _connect() as conn:
        _execute(
            conn,
            """
            insert into anonymous_sessions(id, created_at, last_seen_at)
            values(?, ?, ?)
            on conflict(id) do update set last_seen_at = excluded.last_seen_at
            """,
            (anon_session_id, now, now),
        )
        _execute(
            conn,
            _device_upsert_sql(conn),
            _device_upsert_params(conn, anon_session_id, now),
        )
        account_session_id = request.cookies.get(ACCOUNT_COOKIE)
        user_id = None
        if account_session_id:
            row = _fetchone(conn, "select user_id, expires_at from account_sessions where id = ?", (account_session_id,))
            if row and (not row["expires_at"] or row["expires_at"] > now):
                user_id = row["user_id"]
        conn.commit()

    owner_key = _user_owner_key(user_id) if user_id else _anon_owner_key(anon_session_id)
    return RequestContext(anon_session_id, account_session_id if user_id else None, user_id, owner_key)


def get_usage(context: RequestContext) -> dict:
    active_modules = [item["slug"] for item in get_modules() if item["status"] == "active"]
    with _connect() as conn:
        used_rows = _fetchall(conn, "select module_slug from free_attempts where owner_key = ?", (context.owner_key,))
        used = {row["module_slug"] for row in used_rows}
        paid_runs = _ledger_balance(conn, context.owner_key)
    return {
        "anon_session_id": context.anon_session_id,
        "mode": "account" if context.user_id else "temporary",
        "paid_runs": paid_runs,
        "modules": {
            slug: {
                "free_attempt_used": slug in used,
                "free_attempt_available": slug not in used,
            }
            for slug in active_modules
        },
    }


def prepare_module_access(module_slug: str, context: RequestContext) -> ModuleAccessDecision:
    with _connect() as conn:
        used = _fetchone(conn, "select module_slug from free_attempts where owner_key = ? and module_slug = ?", (context.owner_key, module_slug))
        if not used:
            return ModuleAccessDecision(module_slug, "free", context.owner_key, context.anon_session_id, context.user_id)
        if _ledger_balance(conn, context.owner_key) > 0:
            return ModuleAccessDecision(module_slug, "paid", context.owner_key, context.anon_session_id, context.user_id)
    raise ModuleAccessError("Для повторного запуска необходимо купить запуск модуля или применить промокод.")


def record_module_run_success(run: StoredRun, decision: ModuleAccessDecision, inputs: dict | None = None) -> None:
    now = run.created_at.astimezone(timezone.utc).isoformat()
    file_format = _preferred_file_format(run)
    expires_at = (run.created_at + WORK_TTL).astimezone(timezone.utc).isoformat() if not decision.user_id else None
    with _connect() as conn:
        if decision.source == "free":
            _execute(
                conn,
                "insert into free_attempts(owner_key, module_slug, created_at) values(?, ?, ?) on conflict(owner_key, module_slug) do nothing",
                (decision.owner_key, decision.module_slug, _now()),
            )
        elif decision.source == "paid":
            _insert_ledger(conn, decision.owner_key, "module_spend", -1, module_slug=decision.module_slug, run_id=run.run_id)

        _execute(
            conn,
            """
            insert into module_runs(run_id, module_slug, title, status, summary, downloads_json, files_json, created_at, deleted_at)
            values(?, ?, ?, ?, ?, ?, ?, ?, null)
            on conflict(run_id) do update set
              module_slug = excluded.module_slug,
              title = excluded.title,
              status = excluded.status,
              summary = excluded.summary,
              downloads_json = excluded.downloads_json,
              files_json = excluded.files_json,
              deleted_at = null
            """,
            (run.run_id, run.module_slug, run.title, run.status, run.summary, _dumps(run.downloads), _dumps(run.files), now),
        )
        _execute(
            conn,
            """
            insert into module_inputs(run_id, inputs_json, created_at)
            values(?, ?, ?)
            on conflict(run_id) do update set inputs_json = excluded.inputs_json
            """,
            (run.run_id, _dumps(inputs or {}), now),
        )
        _execute(
            conn,
            """
            insert into module_outputs(run_id, sections_json, created_at)
            values(?, ?, ?)
            on conflict(run_id) do update set sections_json = excluded.sections_json
            """,
            (run.run_id, _dumps(run.sections), now),
        )
        _upsert_work(conn, run, decision, file_format, now, expires_at)
        conn.commit()


def _upsert_work(conn: Any, run: StoredRun, decision: ModuleAccessDecision, file_format: str, now: str, expires_at: str | None) -> None:
    params = (
        run.run_id,
        decision.anon_session_id,
        decision.user_id,
        run.module_slug,
        run.title,
        run.status,
        file_format,
        run.downloads[file_format],
        now,
        expires_at,
    )
    if _column_exists(conn, "works", "id"):
        _execute(
            conn,
            """
            insert into works(id, run_id, anon_session_id, user_id, project_id, module_slug, title, status, file_format, download_path, created_at, expires_at, deleted_at)
            values(?, ?, ?, ?, null, ?, ?, ?, ?, ?, ?, ?, null)
            on conflict(run_id) do update set
              anon_session_id = excluded.anon_session_id,
              user_id = excluded.user_id,
              module_slug = excluded.module_slug,
              title = excluded.title,
              status = excluded.status,
              file_format = excluded.file_format,
              download_path = excluded.download_path,
              expires_at = excluded.expires_at,
              deleted_at = null
            """,
            (str(uuid4()), *params),
        )
        return

    _execute(
        conn,
        """
        insert into works(run_id, anon_session_id, user_id, project_id, module_slug, title, status, file_format, download_path, created_at, expires_at, deleted_at)
        values(?, ?, ?, null, ?, ?, ?, ?, ?, ?, ?, null)
        on conflict(run_id) do update set
          anon_session_id = excluded.anon_session_id,
          user_id = excluded.user_id,
          module_slug = excluded.module_slug,
          title = excluded.title,
          status = excluded.status,
          file_format = excluded.file_format,
          download_path = excluded.download_path,
          expires_at = excluded.expires_at,
          deleted_at = null
        """,
        params,
    )


def load_persisted_run(run_id: str) -> StoredRun | None:
    with _connect() as conn:
        row = _fetchone(
            conn,
            """
            select run_id, module_slug, title, status, summary, downloads_json, files_json, created_at
            from module_runs
            where run_id = ? and deleted_at is null
            """,
            (run_id,),
        )
        if not row:
            return None
        output = _fetchone(conn, "select sections_json from module_outputs where run_id = ?", (run_id,))

    run = StoredRun(
        run_id=row["run_id"],
        module_slug=row["module_slug"],
        title=row["title"],
        status=row["status"],
        summary=row["summary"],
        sections=json.loads(output["sections_json"]) if output else [],
        downloads=json.loads(row["downloads_json"]),
        files=json.loads(row["files_json"]),
        created_at=_parse_dt(row["created_at"]),
    )
    return run_store.save(run)


def apply_promo_code(code: str, context: RequestContext) -> dict:
    normalized = code.strip().upper()
    now = _now()
    with _connect() as conn:
        promo = _fetchone(conn, "select * from promo_codes where code = ?", (normalized,))
        if not promo:
            raise KeyError("Такой промокод не найден.")
        if promo["status"] == "expired" or (promo["expires_at"] and promo["expires_at"] < now):
            raise TimeoutError("Срок действия промокода закончился.")
        if _fetchone(conn, "select id from promo_redemptions where owner_key = ? and code = ?", (context.owner_key, normalized)):
            raise FileExistsError("Промокод уже применен.")
        if promo["total_limit"] is not None:
            used_total = _fetchone(conn, "select count(*) as count from promo_redemptions where code = ?", (normalized,))["count"]
            if int(used_total) >= int(promo["total_limit"]):
                raise TimeoutError("Срок действия промокода закончился.")

        added_runs = int(promo["runs"])
        _execute(
            conn,
            "insert into promo_redemptions(id, owner_key, code, added_runs, created_at) values(?, ?, ?, ?, ?)",
            (str(uuid4()), context.owner_key, normalized, added_runs, now),
        )
        _insert_ledger(conn, context.owner_key, "promo_add", added_runs, promo_code=normalized)
        remaining = _ledger_balance(conn, context.owner_key)
        conn.commit()
    return {
        "status": "applied",
        "added_runs": added_runs,
        "remaining_runs": remaining,
        "message": f"Промокод применен. Добавлено запусков: {added_runs}.",
    }


def record_payment_created(payment_id: str, package: str, amount_rub: int, runs: int, context: RequestContext | None = None) -> None:
    with _connect() as conn:
        _execute(
            conn,
            """
            insert into payments(id, owner_key, provider, provider_payment_id, package, amount_rub, runs, status, created_at, paid_at, provider_payload)
            values(?, ?, ?, null, ?, ?, ?, ?, ?, null, null)
            on conflict(id) do update set status = excluded.status
            """,
            (payment_id, context.owner_key if context else None, "placeholder", package, amount_rub, runs, "created", _now()),
        )
        conn.commit()


def get_payment(payment_id: str) -> dict | None:
    with _connect() as conn:
        row = _fetchone(conn, "select * from payments where id = ?", (payment_id,))
    if not row:
        return None
    return dict(row, payment_id=row["id"])


def handle_payment_webhook(provider: str, payload: dict) -> dict:
    payment_id = str(payload.get("payment_id") or "")
    provider_payment_id = str(payload.get("provider_payment_id") or "")
    status = str(payload.get("status") or "")
    signature = str(payload.get("signature") or "")
    if not payment_id or not provider_payment_id:
        raise ValueError("Не удалось подтвердить платеж.")
    if settings.payment_webhook_secret and signature != _payment_signature(provider, payment_id, provider_payment_id, status):
        raise ValueError("Не удалось подтвердить платеж.")
    if status not in {"created", "pending", "paid", "failed", "canceled", "refunded"}:
        raise ValueError("Не удалось подтвердить платеж.")

    with _connect() as conn:
        payment = _fetchone(conn, "select * from payments where id = ?", (payment_id,))
        if not payment:
            raise KeyError("Платеж не найден.")
        if _fetchone(conn, "select id from payment_events where provider = ? and provider_payment_id = ? and status = ?", (provider, provider_payment_id, status)):
            return {"payment_id": payment_id, "status": payment["status"], "runs_added": 0, "message": "Событие платежа уже обработано."}

        _execute(
            conn,
            "insert into payment_events(id, payment_id, provider, provider_payment_id, status, created_at) values(?, ?, ?, ?, ?, ?)",
            (str(uuid4()), payment_id, provider, provider_payment_id, status, _now()),
        )
        _execute(
            conn,
            "update payments set provider = ?, provider_payment_id = ?, status = ?, paid_at = case when ? = 'paid' then ? else paid_at end, provider_payload = ? where id = ?",
            (provider, provider_payment_id, status, status, _now(), _dumps(payload), payment_id),
        )
        runs_added = 0
        if status == "paid" and payment["owner_key"]:
            already_credited = _fetchone(conn, "select id from credit_ledger where payment_id = ? and source = 'purchase_add'", (payment_id,))
            if not already_credited:
                runs_added = int(payment["runs"])
                _insert_ledger(conn, payment["owner_key"], "purchase_add", runs_added, payment_id=payment_id)
        conn.commit()
    return {"payment_id": payment_id, "status": status, "runs_added": runs_added, "message": "Платеж обработан."}


def request_magic_link(email: str, context: RequestContext) -> dict:
    normalized_email = _normalize_email(email)
    if not EMAIL_RE.match(normalized_email):
        raise ValueError("Введите корректный email.")
    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    with _connect() as conn:
        _execute(
            conn,
            "insert into magic_links(token_hash, email, anon_session_id, expires_at, consumed_at, created_at) values(?, ?, ?, ?, null, ?)",
            (token_hash, normalized_email, context.anon_session_id, (datetime.now(timezone.utc) + MAGIC_LINK_TTL).isoformat(), _now()),
        )
        conn.commit()
    result = {"status": "sent", "message": "Если email указан верно, ссылка для входа отправлена."}
    if settings.app_env != "production":
        result["dev_token"] = token
    return result


def consume_magic_link(token: str, response: Response) -> dict:
    token_hash = _hash_token(token)
    now = _now()
    with _connect() as conn:
        link = _fetchone(conn, "select * from magic_links where token_hash = ?", (token_hash,))
        if not link or link["consumed_at"] or link["expires_at"] < now:
            raise ValueError("Ссылка для входа устарела. Запросите новую.")

        user_id = _ensure_user(conn, link["email"])
        account_session_id = str(uuid4())
        _execute(
            conn,
            "insert into account_sessions(id, user_id, created_at, expires_at) values(?, ?, ?, ?)",
            (account_session_id, user_id, now, (datetime.now(timezone.utc) + timedelta(days=180)).isoformat()),
        )
        _execute(conn, "update magic_links set consumed_at = ? where token_hash = ?", (now, token_hash))

        old_owner = _anon_owner_key(link["anon_session_id"])
        new_owner = _user_owner_key(user_id)
        _transfer_owner_state(conn, old_owner, new_owner, link["anon_session_id"], user_id)
        attached = _fetchone(conn, "select count(*) as count from works where user_id = ? and deleted_at is null", (user_id,))["count"]
        conn.commit()

    _set_cookie(response, ACCOUNT_COOKIE, account_session_id, max_age=60 * 60 * 24 * 180)
    return {"status": "authenticated", "attached_works": int(attached), "message": "Вход выполнен. Временные работы перенесены в кабинет."}


def get_account_works(context: RequestContext) -> dict:
    now = _now()
    with _connect() as conn:
        if context.user_id:
            rows = _fetchall(
                conn,
                """
                select works.*, projects.title as project_title
                from works left join projects on projects.id = works.project_id
                where works.user_id = ? and works.deleted_at is null
                order by works.created_at desc
                """,
                (context.user_id,),
            )
        else:
            rows = _fetchall(
                conn,
                """
                select works.*, projects.title as project_title
                from works left join projects on projects.id = works.project_id
                where works.anon_session_id = ? and works.deleted_at is null and (works.expires_at is null or works.expires_at > ?)
                order by works.created_at desc
                """,
                (context.anon_session_id, now),
            )
    items = [
        {
            "run_id": str(row["run_id"]),
            "date": str(row["created_at"])[:10],
            "work": _display_work_title(row["module_slug"], row["title"]),
            "competition": "ПФКИ",
            "project": row["project_title"] or "Без проекта",
            "status": "Готово" if row["status"] == "completed" else "Черновик",
            "file_format": row["file_format"],
            "download_path": row["download_path"],
            "actions": ["Открыть", "Скачать", "Улучшить", "Прикрепить к проекту", "Удалить"],
        }
        for row in rows
    ]
    return {"mode": "account" if context.user_id else "temporary", "items": items}


def create_project(title: str, competition: str, context: RequestContext) -> dict:
    clean_title = title.strip()
    if len(clean_title) < 2:
        raise ValueError("Введите название проекта.")
    project_id = str(uuid4())
    with _connect() as conn:
        _execute(
            conn,
            "insert into projects(id, anon_session_id, user_id, title, competition, created_at, updated_at) values(?, ?, ?, ?, ?, ?, ?)",
            (project_id, context.anon_session_id, context.user_id, clean_title, competition.strip() or "ПФКИ", _now(), _now()),
        )
        conn.commit()
    return {"project_id": project_id, "title": clean_title, "competition": competition.strip() or "ПФКИ"}


def get_projects(context: RequestContext) -> dict:
    with _connect() as conn:
        if context.user_id:
            rows = _fetchall(
                conn,
                """
                select projects.id, projects.title, projects.competition, count(works.run_id) as works_count
                from projects left join works on works.project_id = projects.id and works.deleted_at is null
                where projects.user_id = ?
                group by projects.id, projects.title, projects.competition
                order by projects.updated_at desc
                """,
                (context.user_id,),
            )
        else:
            rows = _fetchall(
                conn,
                """
                select projects.id, projects.title, projects.competition, count(works.run_id) as works_count
                from projects left join works on works.project_id = projects.id and works.deleted_at is null
                where projects.anon_session_id = ?
                group by projects.id, projects.title, projects.competition
                order by projects.updated_at desc
                """,
                (context.anon_session_id,),
            )
    return {
        "items": [
            {
                "project_id": str(row["id"]),
                "title": row["title"],
                "competition": row["competition"],
                "works_count": int(row["works_count"] or 0),
            }
            for row in rows
        ]
    }


def attach_work_to_project(project_id: str, run_id: str, context: RequestContext) -> dict:
    with _connect() as conn:
        project = _fetchone(conn, "select * from projects where id = ?", (project_id,))
        work = _fetchone(conn, "select * from works where run_id = ? and deleted_at is null", (run_id,))
        if not project:
            raise KeyError("Проект не найден.")
        if not work:
            raise KeyError("Работа не найдена.")
        if context.user_id:
            allowed = project["user_id"] == context.user_id and work["user_id"] == context.user_id
        else:
            allowed = project["anon_session_id"] == context.anon_session_id and work["anon_session_id"] == context.anon_session_id
        if not allowed:
            raise PermissionError("Нет доступа к этой работе или проекту.")
        _execute(conn, "update works set project_id = ? where run_id = ?", (project_id, run_id))
        _execute(conn, "update projects set updated_at = ? where id = ?", (_now(), project_id))
        conn.commit()
    return {"status": "attached", "project_id": project_id, "run_id": run_id, "project": project["title"]}


def delete_work(run_id: str, context: RequestContext) -> dict:
    with _connect() as conn:
        work = _fetchone(conn, "select * from works where run_id = ? and deleted_at is null", (run_id,))
        if not work:
            raise KeyError("Работа не найдена.")
        if context.user_id:
            allowed = work["user_id"] == context.user_id
        else:
            allowed = work["anon_session_id"] == context.anon_session_id
        if not allowed:
            raise PermissionError("Нет доступа к этой работе.")
        now = _now()
        _execute(conn, "update works set deleted_at = ? where run_id = ?", (now, run_id))
        _execute(conn, "update module_runs set deleted_at = ? where run_id = ?", (now, run_id))
        conn.commit()
    run_store._runs.pop(run_id, None)
    return {"status": "deleted", "run_id": run_id, "message": "Работа удалена."}


def save_result_for_email(run: StoredRun, email: str) -> dict:
    normalized_email = _normalize_email(email)
    if not EMAIL_RE.match(normalized_email):
        raise ValueError("Введите корректный email.")
    with _connect() as conn:
        user_id = _ensure_user(conn, normalized_email)
        _execute(conn, "update works set user_id = ?, expires_at = null where run_id = ?", (user_id, run.run_id))
        conn.commit()
    return _email_file_response(normalized_email, _preferred_file_format(run))


def package_config(package: str) -> dict:
    if package not in PAYMENT_PACKAGES:
        raise ValueError("Такой пакет запусков недоступен.")
    return PAYMENT_PACKAGES[package]


def _seed_promo_codes() -> None:
    with _connect() as conn:
        for code, data in PROMO_SEEDS.items():
            _execute(
                conn,
                """
                insert into promo_codes(code, runs, status, expires_at, total_limit, per_owner_limit, module_scope, campaign, created_at)
                values(?, ?, ?, null, null, 1, null, ?, ?)
                on conflict(code) do nothing
                """,
                (code, data["runs"], data["status"], data["campaign"], _now()),
            )
        conn.commit()


def _ensure_legacy_columns(conn: Any) -> None:
    additions = {
        "devices": {
            "anon_session_id": "text",
            "user_id": "text",
            "first_seen_at": "text",
            "last_seen_at": "text",
        },
        "works": {
            "deleted_at": "text",
            "project_id": "text",
            "file_format": "text",
            "download_path": "text",
            "expires_at": "text",
        },
        "projects": {
            "updated_at": "text",
        },
        "payments": {
            "owner_key": "text",
            "provider": "text",
            "provider_payment_id": "text",
            "paid_at": "text",
            "provider_payload": "text",
        },
        "payment_events": {
            "payment_id": "text",
            "provider": "text",
            "provider_payment_id": "text",
            "status": "text",
            "created_at": "text",
        },
        "credit_ledger": {
            "owner_key": "text",
            "source": "text",
            "delta": "integer",
            "module_slug": "text",
            "run_id": "text",
            "payment_id": "text",
            "promo_code": "text",
            "created_at": "text",
        },
        "promo_codes": {
            "runs": "integer",
            "status": "text",
            "expires_at": "text",
            "total_limit": "integer",
            "per_owner_limit": "integer",
            "module_scope": "text",
            "campaign": "text",
            "created_at": "text",
        },
        "promo_redemptions": {
            "owner_key": "text",
            "code": "text",
            "added_runs": "integer",
            "created_at": "text",
        },
    }
    for table, columns in additions.items():
        for column, definition in columns.items():
            if not _column_exists(conn, table, column):
                _execute(conn, f"alter table {table} add column {column} {definition}")


def _device_upsert_sql(conn: Any) -> str:
    if _column_exists(conn, "devices", "fingerprint"):
        return """
            insert into devices(id, anon_session_id, user_id, fingerprint, first_seen_at, last_seen_at)
            values(?, ?, null, ?, ?, ?)
            on conflict(id) do update set
              anon_session_id = excluded.anon_session_id,
              last_seen_at = excluded.last_seen_at
            """
    return """
        insert into devices(id, anon_session_id, user_id, first_seen_at, last_seen_at)
        values(?, ?, null, ?, ?)
        on conflict(id) do update set last_seen_at = excluded.last_seen_at
        """


def _device_upsert_params(conn: Any, anon_session_id: str, now: str) -> tuple[Any, ...]:
    if _column_exists(conn, "devices", "fingerprint"):
        return (anon_session_id, anon_session_id, anon_session_id, now, now)
    return (anon_session_id, anon_session_id, now, now)


def _transfer_owner_state(conn: Any, old_owner: str, new_owner: str, anon_session_id: str, user_id: str) -> None:
    for row in _fetchall(conn, "select module_slug, created_at from free_attempts where owner_key = ?", (old_owner,)):
        _execute(
            conn,
            "insert into free_attempts(owner_key, module_slug, created_at) values(?, ?, ?) on conflict(owner_key, module_slug) do nothing",
            (new_owner, row["module_slug"], row["created_at"]),
        )
    _execute(conn, "delete from free_attempts where owner_key = ?", (old_owner,))

    for row in _fetchall(conn, "select code, added_runs, created_at from promo_redemptions where owner_key = ?", (old_owner,)):
        _execute(
            conn,
            "insert into promo_redemptions(id, owner_key, code, added_runs, created_at) values(?, ?, ?, ?, ?) on conflict(owner_key, code) do nothing",
            (str(uuid4()), new_owner, row["code"], row["added_runs"], row["created_at"]),
        )
    _execute(conn, "delete from promo_redemptions where owner_key = ?", (old_owner,))

    _execute(conn, "update credit_ledger set owner_key = ? where owner_key = ?", (new_owner, old_owner))
    _execute(conn, "update payments set owner_key = ? where owner_key = ?", (new_owner, old_owner))
    _execute(conn, "update works set user_id = ?, expires_at = null where anon_session_id = ? and user_id is null", (user_id, anon_session_id))
    _execute(conn, "update projects set user_id = ? where anon_session_id = ? and user_id is null", (user_id, anon_session_id))
    _execute(conn, "update devices set user_id = ? where anon_session_id = ?", (user_id, anon_session_id))


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


def _ensure_user(conn: Any, email: str) -> str:
    row = _fetchone(conn, "select id from users where email = ?", (email,))
    if row:
        _execute(conn, "update users set updated_at = ? where email = ?", (_now(), email))
        return row["id"]
    user_id = str(uuid4())
    _execute(conn, "insert into users(id, email, created_at, updated_at) values(?, ?, ?, ?)", (user_id, email, _now(), _now()))
    return user_id


def _ledger_balance(conn: Any, owner_key: str) -> int:
    row = _fetchone(conn, "select coalesce(sum(delta), 0) as balance from credit_ledger where owner_key = ?", (owner_key,))
    return int(row["balance"] or 0)


def _insert_ledger(
    conn: Any,
    owner_key: str,
    source: str,
    delta: int,
    module_slug: str | None = None,
    run_id: str | None = None,
    payment_id: str | None = None,
    promo_code: str | None = None,
) -> None:
    _execute(
        conn,
        "insert into credit_ledger(id, owner_key, source, delta, module_slug, run_id, payment_id, promo_code, created_at) values(?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (str(uuid4()), owner_key, source, delta, module_slug, run_id, payment_id, promo_code, _now()),
    )


@contextmanager
def _connect() -> Iterator[Any]:
    if settings.database_url:
        with psycopg.connect(settings.database_url, connect_timeout=5, row_factory=dict_row) as conn:
            yield conn
        return

    path = Path(settings.state_sqlite_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _execute(conn: Any, sql: str, params: tuple[Any, ...] = ()) -> Any:
    return conn.execute(_sql(sql), params)


def _fetchone(conn: Any, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    cur = _execute(conn, sql, params)
    row = cur.fetchone()
    return _row_to_dict(row) if row is not None else None


def _fetchall(conn: Any, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    cur = _execute(conn, sql, params)
    return [_row_to_dict(row) for row in cur.fetchall()]


def _column_exists(conn: Any, table: str, column: str) -> bool:
    if settings.database_url:
        row = _fetchone(
            conn,
            """
            select column_name
            from information_schema.columns
            where table_schema = current_schema() and table_name = ? and column_name = ?
            """,
            (table, column),
        )
        return row is not None

    cur = conn.execute(f"pragma table_info({table})")
    return any(row["name"] == column for row in cur.fetchall())


def _row_to_dict(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return row
    if hasattr(row, "keys"):
        return {key: row[key] for key in row.keys()}
    return dict(row)


def _sql(sql: str) -> str:
    return sql.replace("?", "%s") if settings.database_url else sql


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


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
        "message": "Работа сохранена в личном кабинете. Ссылка для входа отправлена на email; пароль не нужен.",
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
