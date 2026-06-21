import psycopg

from app.core.config import settings


def check_database() -> dict:
    if not settings.database_url:
        return {
            "status": "skipped",
            "reason": "DATABASE_URL is not set",
        }

    with psycopg.connect(settings.database_url, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute("select 1;")
            value = cur.fetchone()[0]

    return {
        "status": "ok",
        "result": value,
    }
