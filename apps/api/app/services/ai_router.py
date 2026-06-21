from gigachat import GigaChat

from app.core.config import settings


class AiRouterError(Exception):
    pass


def build_pfki_test_prompt(user_text: str) -> str:
    return f"""
Ты — эксперт по заявкам Президентского фонда культурных инициатив.

Пользователь описал идею проекта:
{user_text}

Сделай короткий тестовый ответ:
1. Что это за проект простыми словами.
2. Какие 5 данных нужно уточнить для заявки ПФКИ.
3. Какие 3 риска есть в формулировке.
4. Какие разделы заявки вероятно будут самыми сложными.
Не выдумывай источники и факты.
"""


def generate_with_gigachat(prompt: str) -> str:
    if not settings.gigachat_credentials:
        raise AiRouterError(
            "GIGACHAT_CREDENTIALS is not set. Put GigaChat Authorization Key into Railway Variables."
        )

    with GigaChat(
        credentials=settings.gigachat_credentials,
        scope=settings.gigachat_scope,
        model=settings.gigachat_model,
        verify_ssl_certs=settings.gigachat_verify_ssl_certs,
        timeout=settings.gigachat_timeout,
        max_retries=settings.gigachat_max_retries,
    ) as client:
        response = client.chat.create(prompt)

    return response.messages[0].content[0].text


def run_ai_test(user_text: str) -> str:
    prompt = build_pfki_test_prompt(user_text)
    return generate_with_gigachat(prompt)
