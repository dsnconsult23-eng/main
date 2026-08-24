from decimal import Decimal, InvalidOperation
from datetime import datetime
import os
import sys

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.pdfbase.pdfmetrics import stringWidth


base_path = os.path.dirname(__file__) if "__file__" in globals() else os.path.dirname(sys.argv[0])
font_path_regular = os.path.join(base_path, "DejaVuSans.ttf")
font_path_bold = os.path.join(base_path, "DejaVuSans-Bold.ttf")
font_path_oblique = os.path.join(base_path, "DejaVuSans-Oblique.ttf")

pdfmetrics.registerFont(TTFont("DejaVu", font_path_regular))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", font_path_bold))
pdfmetrics.registerFont(TTFont("DejaVu-Oblique", font_path_oblique))


def _to_decimal(value):
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def _format_amount(value):
    return f"{_to_decimal(value):.2f}"


def _parse_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
        return datetime(value.year, value.month, value.day)

    value = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value[:10], fmt)
        except ValueError:
            continue
    return None


def _format_due_date(due_date, period=None):
    period_text = str(period or "").replace("–", "-").replace("—", "-")
    period_start = period_text.split("-", 1)[0].strip()
    parsed = _parse_date(period_start) or _parse_date(due_date)
    if parsed:
        return parsed.strftime("%d.%m.%Y")
    return str(due_date or "").strip()


def _draw_wrapped_text(c, text, x, y, max_width, font_name="DejaVu", font_size=9, leading=14):
    c.setFont(font_name, font_size)
    words = str(text or "").split()
    lines = []
    current = ""

    for word in words:
        candidate = word if not current else f"{current} {word}"
        if stringWidth(candidate, font_name, font_size) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    text_obj = c.beginText(x, y)
    text_obj.setFont(font_name, font_size)
    text_obj.setLeading(leading)
    for line in lines:
        text_obj.textLine(line)
    c.drawText(text_obj)
    return len(lines) * leading


def generate_pdf(
    filename,
    client_name,
    client_adresa,
    client_grad,
    polisa_number,
    due_date,
    premium_amount,
    paid_premium,
    balance,
    godina,
    rata,
    period,
    unpaid_premium,
    vk_premija,
    valuta,
    nacin_plakanje="месечно",
):
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    getSampleStyleSheet()

    client_name = str(client_name or "").strip()
    client_adresa = str(client_adresa or "").strip()
    client_grad = str(client_grad or "").strip()
    polisa_number = str(polisa_number or "").strip()
    nacin_plakanje = str(nacin_plakanje or "месечно").strip()

    background_image_path = "/opt/siglife-reporting/Image/UNIQA_MEMO1.png"
    if os.path.exists(background_image_path):
        bg_image = ImageReader(background_image_path)
        c.drawImage(bg_image, 0, 0, width=width, height=height)

    today_str = datetime.today().strftime("%d.%m.%Y")
    due_date_formatted = _format_due_date(due_date, period)

    c.setFont("DejaVu", 10)
    c.drawRightString(width - 20 * mm, height - 25 * mm, "Сектор Финансии")
    c.drawRightString(width - 20 * mm, height - 30 * mm, "Телефон: +389 2 3288 820")
    c.drawRightString(width - 20 * mm, height - 35 * mm, "Факс: +389 2 3215 128")
    c.drawRightString(width - 20 * mm, height - 40 * mm, "E-Mail: lifeinsurance@sigal.com.mk")
    c.drawRightString(width - 20 * mm, height - 45 * mm, f"Дата: {today_str}")

    y = height - 62 * mm
    c.setFont("DejaVu-Bold", 10)
    c.drawString(10 * mm, y, "До")
    c.setFont("DejaVu", 10)
    c.drawString(10 * mm, y - 5 * mm, client_name)
    c.drawString(10 * mm, y - 10 * mm, client_adresa)
    c.drawString(10 * mm, y - 15 * mm, client_grad)

    y -= 25 * mm
    c.setFont("DejaVu-Bold", 10)
    c.drawString(10 * mm, y, "Предмет:")
    c.drawString(32 * mm, y, "Известување")

    y -= 12 * mm
    c.setFont("DejaVu", 9)
    c.drawString(10 * mm, y, "Почитувани,")

    paragraph_1 = (
        f"Ве известуваме дека премијата за осигурување на живот по полиса бр. {polisa_number}, "
        f"која ја плаќате {nacin_plakanje}, доспева на {due_date_formatted}."
    )
    paragraph_2 = (
        f"Согласно нашата евиденција состојбата на Вашата полиса бр. {polisa_number} "
        f"на ден {today_str} е следна:"
    )

    used_height_1 = _draw_wrapped_text(
        c,
        paragraph_1,
        10 * mm,
        y - 14,
        max_width=170 * mm,
        font_name="DejaVu",
        font_size=9,
        leading=14,
    )
    used_height_2 = _draw_wrapped_text(
        c,
        paragraph_2,
        10 * mm,
        y - 14 - used_height_1 - 10,
        max_width=170 * mm,
        font_name="DejaVu",
        font_size=9,
        leading=14,
    )

    y -= (24 + used_height_1 + used_height_2)
    draw_premium_table(
        c=c,
        width=width,
        y=y,
        rows=[[godina, rata, period, premium_amount, paid_premium, balance]],
        unpaid_premium=unpaid_premium,
        total_due=vk_premija,
        currency=valuta,
    )

    draw_payment_instructions(c, width, start_y=y - 58 * mm, due_date=due_date_formatted)

    c.setFont("DejaVu-Bold", 10)
    c.drawString(10 * mm, 30 * mm, "Со почит:")
    c.drawString(10 * mm, 25 * mm, "SIGAL Life a.d Скопје")

    c.save()


def draw_premium_table(c, width, y, rows, unpaid_premium, total_due, currency):
    currency = str(currency or "").strip()
    formatted_total_due = f"{_format_amount(total_due)}{' ' + currency if currency else ''}"

    formatted_rows = []
    for godina, rata, period, premium_amount, paid_premium, balance in rows:
        formatted_rows.append(
            [
                str(godina or "").strip(),
                str(rata or "").strip(),
                str(period or "").strip(),
                _format_amount(premium_amount),
                _format_amount(paid_premium),
                _format_amount(balance),
            ]
        )

    data = [
        ["Година", "Број на рата", "Период", "Премија", "Уплатена премија", "Салдо"],
        ["Премија за тековен период", "", "", "", "", ""],
    ] + formatted_rows + [
        ["Неплатена премија за изминат период", "", "", "", "", _format_amount(unpaid_premium)],
        ["", "", "", "", "Вкупно за наплата:", formatted_total_due],
    ]

    table = Table(data, colWidths=[25 * mm, 30 * mm, 50 * mm, 25 * mm, 35 * mm, 30 * mm])
    row_count = len(data)

    table_style = []
    for row in range(row_count):
        table_style.append(("LINEABOVE", (0, row), (-1, row), 0.5, colors.black))
        table_style.append(("LINEBELOW", (0, row), (-1, row), 0.5, colors.black))

    table_style += [
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (-1, -1), "DejaVu-Oblique"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("SPAN", (0, 1), (-1, 1)),
        ("FONTNAME", (0, 1), (-1, 1), "DejaVu-Bold"),
        ("ALIGN", (0, 1), (-1, 1), "LEFT"),
        ("ALIGN", (3, 2), (5, -1), "RIGHT"),
        ("SPAN", (0, len(formatted_rows) + 2), (4, len(formatted_rows) + 2)),
        ("FONTNAME", (0, len(formatted_rows) + 2), (-1, len(formatted_rows) + 2), "DejaVu-Bold"),
        ("ALIGN", (5, len(formatted_rows) + 2), (5, len(formatted_rows) + 2), "RIGHT"),
        ("SPAN", (0, len(formatted_rows) + 3), (3, len(formatted_rows) + 3)),
        ("FONTNAME", (0, len(formatted_rows) + 3), (-1, len(formatted_rows) + 3), "DejaVu-Bold"),
        ("ALIGN", (4, len(formatted_rows) + 3), (4, len(formatted_rows) + 3), "RIGHT"),
        ("ALIGN", (5, len(formatted_rows) + 3), (5, len(formatted_rows) + 3), "RIGHT"),
    ]

    table.setStyle(TableStyle(table_style))
    table.wrapOn(c, width, y)
    table.drawOn(c, 10 * mm, y - 42 * mm)


def draw_payment_instructions(c, width, start_y, due_date):
    text2 = c.beginText(10 * mm, start_y)
    text2.setFont("DejaVu-Oblique", 9)
    text2.setLeading(13)
    instructions = f"""\

Ве молиме вкупната премија за наплата да се уплати најдоцна до {due_date} по денарска противвредност
по среден курс на НБРМ на денот на уплата на еден од следните жиро сметки:

Стопанска Банка: 200 0023430088 02   Комерцијална Банка: 300 0000033029 83   НЛБ Банка: 210 0671233901 38
Шпаркасе Банка: 250 1010001762 24   Силк Роуд Банка: 280 1001048952 79   Халк Банка: 270 0671233901 45

Врз основа на Законот за ДДВ (Сл. весник бр. 44/99, 58/99, 11/2008, 8/2001 и 21/2003) член 23 став 1 точка 6
премијата на осигурување е ослободена од ДДВ.

*Доколку на денот на прием на известувањето премијата е уплатена, Ве молиме истото
да не го земете во предвид.
"""
    for line in instructions.split("\n"):
        text2.textLine(line)

    c.drawText(text2)


def scheduled_generate_pdf():
    try:
        save_folder = "/opt/siglife/reports/UNIQA"
        os.makedirs(save_folder, exist_ok=True)
        full_path = os.path.join(save_folder, "izvesuvanje.pdf")

        generate_pdf(
            filename=full_path,
            client_name="Ели Иванова",
            client_adresa="Ул. Христо Татарчев 123",
            client_grad="Скопје",
            polisa_number="20/12345678",
            due_date="2025-07-31",
            premium_amount=85.00,
            paid_premium=0.00,
            balance=85.00,
            godina="2025",
            rata="8",
            period="01/07/2025-01/08/2025",
            unpaid_premium=85.00,
            vk_premija=170.00,
            valuta="Евро",
        )

        print(f"PDF saved to: {full_path}")
    except Exception as e:
        print(f"Error generating PDF: {e}")
