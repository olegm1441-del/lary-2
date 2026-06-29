import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from docx import Document

from app.services.support_letter import (
    SupportLetterValidationError,
    build_support_letter_document,
    normalize_cofinance,
    normalize_partner_name,
    normalize_project_title,
    sanitize_filename,
)


VALID_PAYLOAD = {
    "contest": "pfki",
    "project_title": "«Фестиваль \"Теплый дом\"»",
    "partner_name": "ООО \"Лютики\"",
    "partner_intro_block": "крупнейший региональный поставщик футболок.",
    "value_keywords": "дети 10–17 лет; Екатеринбург; творческое самовыражение; уверенность; общение со сверстниками; семейное участие",
    "support_types": ["Информационная поддержка", "Подарки / призы"],
    "support_details": "разместит 5 публикаций в социальных сетях и предоставит 100 футболок для победителей и участников финального мероприятия",
    "cofinance_block": "600000",
    "signatory": "Генеральный директор ООО \"Лютики\" Иванов Иван Иванович",
}


def docx_text(docx_bytes: bytes) -> str:
    document = Document(BytesIO(docx_bytes))
    parts = [paragraph.text for paragraph in document.paragraphs if paragraph.text]
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text:
                    parts.append(cell.text)
    return "\n".join(parts)


class SupportLetterServiceTest(unittest.TestCase):
    def test_normalization_examples_match_pfki_template_rules(self):
        self.assertEqual(normalize_partner_name('ООО "Лютики"'), "ООО «Лютики»")
        self.assertEqual(normalize_partner_name("ООО «Лютики»"), "ООО «Лютики»")
        self.assertEqual(normalize_partner_name('МБУК "Городской дом культуры"'), "МБУК «Городской дом культуры»")

        self.assertEqual(normalize_project_title('"Детство. Лагерь.Like"'), "Детство. Лагерь.Like")
        self.assertEqual(normalize_project_title("«Детство. Лагерь.Like»"), "Детство. Лагерь.Like")
        self.assertEqual(normalize_project_title('Семейный фестиваль "Теплый дом"'), "Семейный фестиваль „Теплый дом“")
        self.assertEqual(normalize_project_title("«Семейный фестиваль «Теплый дом»»"), "Семейный фестиваль „Теплый дом“")

        cofinance = normalize_cofinance("600000")
        self.assertEqual(cofinance.raw_digits, "600000")
        self.assertEqual(cofinance.formatted, "600 000")
        self.assertEqual(normalize_cofinance("600 000").formatted, "600 000")

        with self.assertRaises(SupportLetterValidationError):
            normalize_cofinance("600000 рублей")

        self.assertEqual(sanitize_filename("ООО «Лютики»"), "Письмо поддержки_ПФКИ_ООО «Лютики».docx")
        self.assertEqual(sanitize_filename('ООО "Лютики" / тест'), "Письмо поддержки_ПФКИ_ООО Лютики тест.docx")

    def test_support_letter_docx_uses_template_and_two_short_ai_json_blocks(self):
        ai_value = {
            "ai_value_block": "Видим необходимость проекта в следующем:\n1. Проект помогает детям безопасно проявлять себя творчески.\n2. Проект усиливает семейное участие и общение со сверстниками.\n3. Проект создает понятный культурный маршрут для участников.\nВидим особенным этот проект для нашей территории Екатеринбурга.",
        }
        ai_support = {
            "ai_support_block": "- Информационная поддержка: разместим 5 публикаций в социальных сетях проекта.\n- Подарки / призы: предоставим 100 футболок для победителей и участников финала.",
        }

        with patch("app.services.support_letter.generate_with_gigachat", side_effect=[json.dumps(ai_value, ensure_ascii=False), json.dumps(ai_support, ensure_ascii=False)]) as ai:
            result = build_support_letter_document(VALID_PAYLOAD)

        self.assertEqual(ai.call_count, 2)
        prompts = "\n\n".join(call.args[0] for call in ai.call_args_list)
        self.assertNotIn("{{AI_VALUE_BLOCK}}", prompts)
        self.assertNotIn("{{AI_SUPPORT_BLOCK}}", prompts)
        self.assertNotIn(VALID_PAYLOAD["signatory"], prompts)

        text = docx_text(result.docx_bytes)
        self.assertNotIn("{{", text)
        self.assertIn("Мы – ООО «Лютики» – крупнейший региональный поставщик футболок. Выражаем поддержку проекта «Фестиваль „Теплый дом“».", text)
        self.assertIn("Оцениваем наш вклад в 600 000 рублей", text)
        self.assertNotIn("600 000 рублей рублей", text)
        self.assertIn("Генеральный директор ООО «Лютики» Иванов Иван Иванович", text)
        self.assertEqual(result.filename, "Письмо поддержки_ПФКИ_ООО «Лютики».docx")


if __name__ == "__main__":
    unittest.main()
