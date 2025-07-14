from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
import os
import sys
from reportlab.lib.styles import getSampleStyleSheet

# Define font paths
base_path = os.path.dirname(__file__) if '__file__' in globals() else os.path.dirname(sys.argv[0])
font_path_regular = os.path.join(base_path, "DejaVuSans.ttf")
font_path_bold = os.path.join(base_path, "DejaVuSans-Bold.ttf")
font_path_oblique = os.path.join(base_path, "DejaVuSans-Oblique.ttf")

# Register fonts
pdfmetrics.registerFont(TTFont("DejaVu", font_path_regular))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", font_path_bold))
pdfmetrics.registerFont(TTFont("DejaVu-Oblique", font_path_oblique))


def generate_pdf(filename, client_name, client_adresa, client_grad, polisa_number, due_date, premium_amount,
                 paid_premium, balance, godina, rata, period, unpaid_premium, vk_premija, valuta):
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    styles = getSampleStyleSheet()

    # Header
    c.setFont("DejaVu-Bold", 16)
    c.drawString(20 * mm, height - 25 * mm, "UNIQA LIFE")

    c.setFont("DejaVu", 10)
    c.drawRightString(width - 20 * mm, height - 25 * mm, "Сектор Финансии")
    c.drawRightString(width - 20 * mm, height - 30 * mm, "Телефон: +389 2 3288 820")
    c.drawRightString(width - 20 * mm, height - 35 * mm, "Факс: +389 2 3215 128")
    c.drawRightString(width - 20 * mm, height - 40 * mm, "E-Mail: uniqalifefininfo@uniqa.mk")
    c.drawRightString(width - 20 * mm, height - 45 * mm, "Дата: 23/06/2025")

    # Recipient
    y = height - 60 * mm
    c.setFont("DejaVu-Bold", 10)
    c.drawString(20 * mm, y, "До")
    c.setFont("DejaVu", 10)
    c.drawString(20 * mm, y - 5 * mm, str(client_name))
    c.drawString(20 * mm, y - 10 * mm, str(client_adresa))
    c.drawString(20 * mm, y - 15 * mm, str(client_grad))

    # Subject
    y -= 25 * mm
    c.setFont("DejaVu-Bold", 10)
    c.drawString(20 * mm, y, "Предмет:")
    c.drawString(50 * mm, y, "Известување")

    # Body Text
    y -= 10 * mm
    text = c.beginText(20 * mm, y)
    text.setFont("DejaVu-Oblique", 9)
    message = (
        f"Почитувани,\n\n"
        f"Ве известуваме дека премијата за осигурување на живот по полиса бр. {polisa_number} \n"
        f"која ја плаќате месечно, доспева на {due_date}.\n\n"
        f"Согласно нашата евиденција состојбата на Вашата полиса бр. {polisa_number} на ден "
        f"23.06.2025 е следна:"
    )
    for line in message.split('\n'):
        text.textLine(line)
    c.drawText(text)

    # Table
    y -= 50 * mm
    draw_premium_table(
        c=c,
        width=width,
        y=y,
        rows=[[godina, rata, period, premium_amount, paid_premium, balance]],
        unpaid_premium=unpaid_premium,
        total_due=vk_premija,
        currency=valuta
    )

    # Payment Instructions
    draw_payment_instructions(c, width, start_y=y - 60 * mm, due_date="31.07.2025")

    # Footer
    c.setFont("DejaVu-Bold", 10)
    c.drawString(20 * mm, 30 * mm, "Со почит:")
    c.drawString(20 * mm, 25 * mm, "UNIQA Life a.d Скопје")

    c.save()


def draw_premium_table(c, width, y, rows, unpaid_premium, total_due, currency):
    data = [
        ["Година", "Број на рата", "Период", "Премија", "Уплатена премија", "Салдо"],
        ["Премија за тековен период", "", "", "", "", ""]
    ] + rows + [
        ["Неплатена премија за изминат период", "", "", "", "", f"{unpaid_premium:.2f}"],
        ["", "", "", "", "Вкупно за наплата:", f"{total_due:.2f} {currency}"]
    ]

    table = Table(data, colWidths=[25 * mm, 30 * mm, 50 * mm, 25 * mm, 35 * mm, 30 * mm])
    row_count = len(data)

    # Style
    table_style = []

    for row in range(row_count):
        table_style.append(("LINEABOVE", (0, row), (-1, row), 0.5, colors.black))
        table_style.append(("LINEBELOW", (0, row), (-1, row), 0.5, colors.black))

    table_style += [
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (-1, -1), "DejaVu-Oblique"),

        # Header
        ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),

        # Merged rows
        ("SPAN", (0, 1), (-1, 1)),
        ("FONTNAME", (0, 1), (-1, 1), "DejaVu-Bold"),
        ("ALIGN", (0, 1), (-1, 1), "LEFT"),

        ("SPAN", (0, len(rows)+2), (4, len(rows)+2)),
        ("FONTNAME", (0, len(rows)+2), (-1, len(rows)+2), "DejaVu-Bold"),
        ("ALIGN", (5, len(rows)+2), (5, len(rows)+2), "RIGHT"),

        ("SPAN", (0, len(rows)+3), (3, len(rows)+3)),
        ("FONTNAME", (0, len(rows)+3), (-1, len(rows)+3), "DejaVu-Bold"),
        ("ALIGN", (4, len(rows)+3), (4, len(rows)+3), "RIGHT"),
        ("ALIGN", (5, len(rows)+3), (5, len(rows)+3), "RIGHT"),
    ]

    table.setStyle(TableStyle(table_style))
    table.wrapOn(c, width, y)
    table.drawOn(c, 20 * mm, y - (row_count + 2) * 10)


def draw_payment_instructions(c, width, start_y, due_date):
    text2 = c.beginText(20 * mm, start_y)
    text2.setFont("DejaVu-Oblique", 9)
    instructions = f"""\

Ве молиме вкупната премија за наплата да се уплати најдоцна до {due_date} по денарска противвредност
по среден курс на НБРМ на денот на уплата на еден од следните жиро сметки:

Стопанска Банка: 200 0023430082 08 Комерцијална Банка: 300 00000300239 83 НЛБ Банка:  210 0671233901 38
Шпаркасе Банка:  250 1010001676 24 Силк Роуд Банка:    240 7016232997 75  Халк Банка: 270 0671233901 45

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
        save_folder = "C:/Reports/UNIQA"
        os.makedirs(save_folder, exist_ok=True)
        full_path = os.path.join(save_folder, "izvesuvanje.pdf")

        generate_pdf(
            filename=full_path,
            client_name="Ели Иванова",
            client_adresa="Ул.Христо Татарчев  123",
            client_grad="Скопје",
            polisa_number="20/12345678",
            due_date="31.07.2025",
            premium_amount=85.00,
            paid_premium=0.00,
            balance=85.00,
            godina="2025",
            rata="8",
            period="01/07/2025 – 01/08/2025",
            unpaid_premium=85.00,
            vk_premija=170.00,
            valuta="Евро"
        )

        print(f"✅ PDF saved to: {full_path}")
    except Exception as e:
        print(f"❌ Error generating PDF: {e}")


