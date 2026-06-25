from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timezone
from uuid import uuid4

import psycopg

from app.core.config import settings
from app.services.run_store import StoredRun

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_memory_users: dict[str, dict] = {}
_memory_user_runs: list[dict] = []
_memory_email_deliveries: list[dict] = []
_memory_payments: dict[str, dict] = {}


def ensure_account_schema() -> dict:
    if not settings.database_url:
        return {"status": "skipped", "reason": "DATABASE_URL is not set"}

    statements = [
        """
        create table if not exists users (
            id uuid primary key,
            email text not null unique,
            password_hash text not null,
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
        create table if not exists user_runs (
            id uuid primary key,
            user_id uuid not null references users(id) on delete cascade,
            run_id text not null,
            module_slug text not null,
            title text not null,
            file_format text not null,
            download_path text not null,
            created_at timestamptz not null default now(),
            unique(user_id, run_id, file_format)
        );
        """,
        """
        create table if not exists email_deliveries (
            id uuid primary key,
            user_id uuid not null references users(id) on delete cascade,
            run_id text not null,
            email text not null,
            file_format text not null,
            status text not null,
            provider_message_id text,
            error_message text,
            created_at timestamptz not null default now(),
            sent_at timestamptz
        );
        """,
        """
        create table if not exists payments (
            id text primary key,
            user_id uuid references users(id) on delete set null,
            provider text not null default 'placeholder',
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
        create table if not exists credit_ledger (
            id uuid primary key,
            user_id uuid references users(id) on delete set null,
            source text not null,
            delta integer not null,
            balance_after integer,
            module_slug text,
            run_id text,
            payment_id text references payments(id) on delete set null,
            created_at timestamptz not null default now()
        );
        """,
    ]

    with psycopg.connect(settings.database_url, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            for statement in statements:
                cur.execute(statement)
        conn.commit()

    return {"status": "ok"}


def save_result_for_email(run: StoredRun, email: str, password: str) -> dict:
    normalized_email = _normalize_email(email)
    if not EMAIL_RE.match(normalized_email):
        raise ValueError("Введите корректный email.")
    if len(password) < 6:
        raise ValueError("Пароль должен быть не короче 6 символов.")

    file_format = _preferred_file_format(run)
    download_path = run.downloads[file_format]
    password_hash = _hash_password(password)
    now = datetime.now(timezone.utc)

    if not settings.database_url:
        user = _memory_users.setdefault(normalized_email, {"id": str(uuid4()), "email": normalized_email, "created_at": now})
        user["password_hash"] = password_hash
        user["updated_at"] = now
        _memory_user_runs.append(
            {
                "user_id": user["id"],
                "run_id": run.run_id,
                "module_slug": run.module_slug,
                "title": run.title,
                "file_format": file_format,
                "download_path": download_path,
                "created_at": now,
            }
        )
        _memory_email_deliveries.append(
            {
                "user_id": user["id"],
                "run_id": run.run_id,
                "email": normalized_email,
                "file_format": file_format,
                "status": "queued",
                "created_at": now,
            }
        )
        return _email_file_response(normalized_email, file_format)

    ensure_account_schema()
    user_id = str(uuid4())

    with psycopg.connect(settings.database_url, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into users (id, email, password_hash)
                values (%s, %s, %s)
                on conflict (email) do update
                    set password_hash = excluded.password_hash,
                        updated_at = now()
                returning id;
                """,
                (user_id, normalized_email, password_hash),
            )
            user_id = cur.fetchone()[0]
            cur.execute(
                """
                insert into user_runs (id, user_id, run_id, module_slug, title, file_format, download_path)
                values (%s, %s, %s, %s, %s, %s, %s)
                on conflict (user_id, run_id, file_format) do update
                    set download_path = excluded.download_path,
                        title = excluded.title;
                """,
                (str(uuid4()), user_id, run.run_id, run.module_slug, run.title, file_format, download_path),
            )
            cur.execute(
                """
                insert into email_deliveries (id, user_id, run_id, email, file_format, status)
                values (%s, %s, %s, %s, %s, %s);
                """,
                (str(uuid4()), user_id, run.run_id, normalized_email, file_format, "queued"),
            )
        conn.commit()

    return _email_file_response(normalized_email, file_format)


def record_payment_created(payment_id: str, package: str, amount_rub: int, runs: int) -> None:
    payload = {
        "payment_id": payment_id,
        "package": package,
        "amount_rub": amount_rub,
        "runs": runs,
        "status": "created",
        "created_at": datetime.now(timezone.utc),
    }
    if not settings.database_url:
        _memory_payments[payment_id] = payload
        return

    ensure_account_schema()
    with psycopg.connect(settings.database_url, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into payments (id, package, amount_rub, runs, status)
                values (%s, %s, %s, %s, %s)
                on conflict (id) do nothing;
                """,
                (payment_id, package, amount_rub, runs, "created"),
            )
        conn.commit()


def _preferred_file_format(run: StoredRun) -> str:
    for file_format in ("docx", "pptx"):
        if file_format in run.downloads:
            return file_format
    if run.downloads:
        return next(iter(run.downloads))
    raise ValueError("У этой работы пока нет файла для отправки.")


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    iterations = 120_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def _email_file_response(email: str, file_format: str) -> dict:
    return {
        "status": "saved",
        "email": email,
        "file_format": file_format,
        "message": "Файл сохранен в аккаунт. Отправка письма поставлена в очередь; SMTP-провайдера подключим перед боевыми письмами.",
    }
