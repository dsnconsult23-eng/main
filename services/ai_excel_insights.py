"""
AI-генерирани коментари/анализи за Excel извештаи преку Claude API.

Употреба:
    from services.ai_excel_insights import generate_commentary, append_commentary_sheet

    text = generate_commentary(rows, context="Месечен извештај за провизии на брокери")
    append_commentary_sheet(excel_io, text)  # или append_commentary_sheet(file_path, text)
"""

import io
import os

import anthropic

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        # Чита ANTHROPIC_API_KEY од environment (или `ant auth login` профил).
        _client = anthropic.Anthropic()
    return _client


def generate_commentary(rows: list[dict], context: str, max_rows: int = 500) -> str:
    """
    Генерира краток коментар/анализа на македонски за дадени табеларни податоци.

    rows: листа од dict-ови (на пр. резултат од cur.fetchall() конвертиран во dict-ови)
    context: краток опис на извештајот (за системскиот промпт)
    """
    if not rows:
        return "Нема податоци за анализа."

    sample = rows[:max_rows]

    client = _get_client()
    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        system=(
            "Ти си финансиски аналитичар за осигурителна компанија. "
            "Добиваш табеларни податоци од извештај и треба да дадеш кратка, "
            "јасна анализа на македонски јазик: клучни бројки, трендови и аномалии. "
            "Максимум 5-6 реченици, без markdown форматирање."
        ),
        messages=[
            {
                "role": "user",
                "content": f"Контекст на извештајот: {context}\n\nПодатоци (JSON):\n{sample}",
            }
        ],
    )

    return next((b.text for b in response.content if b.type == "text"), "").strip()


def append_commentary_sheet(excel_source, commentary: str, sheet_name: str = "AI Анализа"):
    """
    Додава нов лист со AI коментар во Excel workbook.

    excel_source: патека (str) или io.BytesIO
    Враќа io.BytesIO ако е даден BytesIO, инаку зачувува на истата патека.
    """
    from openpyxl import load_workbook
    from openpyxl.styles import Font, Alignment

    is_memory = isinstance(excel_source, io.BytesIO)
    if is_memory:
        excel_source.seek(0)
        wb = load_workbook(excel_source)
    else:
        wb = load_workbook(excel_source)

    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    ws = wb.create_sheet(sheet_name)

    ws["A1"] = "AI Анализа"
    ws["A1"].font = Font(bold=True, size=14)

    ws["A3"] = commentary
    ws["A3"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 100
    ws.row_dimensions[3].height = 150

    if is_memory:
        out_io = io.BytesIO()
        wb.save(out_io)
        out_io.seek(0)
        return out_io
    else:
        wb.save(excel_source)
        return excel_source
