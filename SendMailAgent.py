from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.styles import getSampleStyleSheet
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import routers.Connection as Connection  # Database connection module
from reportlab.lib.pagesizes import landscape
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
import platform,sys
import math
from os.path import basename
import locale


# Register a font that supports Cyrillic
pdfmetrics.registerFont(TTFont("DejaVuSans", "DejaVuSans.ttf"))

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4,A3
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet


def Directories(m,g):
    if platform.system() == "Windows":
        sep="\\"
        configDIR="c:\\Anakonda\\PyInsurance"        
        inputDIR="C:\\Pregledi\\"+m+"_"+str(g)     
    else:
        sep="\\"
        configDIR="/opt/siglife-reporting/"        
        inputDIR="/opt/siglife-reporting/Pregledi/"+m+"_"+str(g)      
    return configDIR,inputDIR,sep

def Directories1(mesec, godina):
    configDIR = "/opt/siglife-reporting/Config"
    inputDIR = f"/opt/siglife-reporting/Pregledi/{godina}_{mesec}"
    return configDIR, inputDIR  


def generate_dynamic_pdf(output_path, mesec, godina, agent_name, agent_tim, agent_nivo, record):
    # Create a PDF document
    pdf = SimpleDocTemplate(output_path, pagesize=A4)
    background_image_path = "/opt/siglife-reporting/Image/UNIQA_MEMO1.png"


    # Define styles
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    title_style.fontName = "DejaVuSans"
    normal_style = styles["Normal"]
    normal_style.fontName = "DejaVuSans"
    bold_style = styles["Heading2"]
    bold_style.fontName = "DejaVuSans"
    wrap_style = styles["Normal"]
    wrap_style.wordWrap = 'CJK'  

    # Content for page 1
    page1_title = Paragraph(f"ПРЕСМЕТКОВЕН ПЕРИОД {mesec}/{godina}", title_style)
    page1_data = [
        ["Промотор:", "", agent_name],
        ["Позиција:", "", agent_nivo],
        ["Тим:", "", agent_tim],
    ]

    page1_table6 = [["Бодови во пресметковен период"]]
    page1_table1 = [
        ["", "Почеток на период", "Тековен месец", "Вкупно бодови"],
        ["Лична продукција", record[16], record[13], round(record[16] + record[13],2)],
        ["Тимска продукција", record[17], record[14], round(record[17] + record[14],2)],
        ["Вкупно бодови", record[18], record[15], round(record[18] + record[15],2)],
    ]
    page1_table2 = [["Бодови до следна позиција",  record[29]]]
    page1_table5 = [
        ["Инкасо бруто надомест", "Вкупно провизија"],
        ["Лична продукција", f"{record[42]} €"],
        ["Тимска продукција", f"{record[43]} €"],
        ["Вкупна провизија", f"{record[44]} €"],
    ]
 
    page1_table7 = [
        ["Пресметана провизија", "Вкупно провизија"],
        ["Лична продукција", f"{record[56]} €"],
        ["Тимска продукција", f"{record[57]} €"],
        ["Вкупна провизија", f"{round(record[56]+record[57],2)} €"],
    ]
 
    page1_table4 = [["Исплатена провизија"]]
    page1_table3 = [
        ["Вкупно бруто надомест", f"{record[51]} €", f"{record[52]} ден."],
        ["Персонален данок", f"{round(record[51] * 0.10,2)} €", f"{round(record[52] * 0.10)} ден."],
        ["Нетo надомест", f"{round(record[51] - round(record[51] * 0.10,2),2)} €", f"{round(record[52] - round(record[52] * 0.10))} ден."],
    ]

    # Content for page 2
    sql = f"""
           select polisa_broj,
            dogovoruvac_name,
             skadenca_datum_od,
            skadenca_datum_do,
             LF_UL,
            INN,
             ZD,
             TBS,
            VKUPNO_PREMIJA,
             datum_naplata,
             period_od,
            period_do,
             sum(prov_lf) prov_lf,
             sum(prov_in) prov_in,
            sum(prov_zd)prov_zd ,
            sum( prov_tbs)prov_tbs,
             sum(VKUPNO_PROVIZIJA) VKUPNO_PROVIZIJA,
            sum(br_bodovi)br_bodovi ,
            sum(bod) bod,
             sum(naplata) naplata,br_rati,koja_godina, rata,tip_provizija
   from (
   SELECT 
            polisa_broj,
            dogovoruvac_name,
            TO_CHAR(skadenca_datum_od, '%d/%m/%Y') AS skadenca_datum_od,
            TO_CHAR(skadenca_datum_do, '%d/%m/%Y') AS skadenca_datum_do,
            premija_zivot AS LF_UL,
            premija_nezgoda AS INN,
            premija_zdravstveno AS ZD,
            NVL(premija_tbs, 0) AS TBS,
            ROUND(premija_zivot + premija_nezgoda + premija_zdravstveno + NVL(premija_tbs,0), 2) AS VKUPNO_PREMIJA,
            TO_CHAR(dat_naplata, '%d/%m/%Y') AS datum_naplata,
            TO_CHAR(skadenca_datum_od, '%d/%m/%Y') AS period_od,
            TO_CHAR(skadenca_datum_do, '%d/%m/%Y') AS period_do,
            case when tip_knizi='Премија за осигурување на живот' then  iznos_provizija else 0 end  AS prov_lf,
            case when tip_knizi='Дополнително осигурување -незгода' then  iznos_provizija else 0 end AS prov_in,
            case when tip_knizi='Дополнително осигурување -здравствено' then  iznos_provizija  else 0 end AS prov_zd,
            case when tip_knizi='Дополнително осигурување -ТБС' then  iznos_provizija  else 0 end AS prov_tbs,
            iznos_provizija  AS VKUPNO_PROVIZIJA,
            br_bodovi,
            bod,
            naplata AS naplata,br_rati,koja_godina, rata,tip_provizija,tip_knizi
        FROM 
            agenti_provizija
        WHERE 
            mesec = {mesec}
            AND godina = {godina}
            AND par_agentid = {record[3]})a
            group by polisa_broj,
            dogovoruvac_name,
             skadenca_datum_od,
            skadenca_datum_do,
             LF_UL,
            INN,
             ZD,
             TBS,
            VKUPNO_PREMIJA,
             datum_naplata,
             period_od,
            period_do, br_rati,koja_godina, rata,tip_provizija
            order by polisa_broj
   
    """

    # --- Execute query ---
    results, OK = Connection.OSISinit()
    if not OK:
        print("❌ Грешка - нема врска со база")
        return

    results.execute(sql)
    analitika1 = []
    while True:
        row = results.fetchone()
        if not row:
            break
        analitika1.append(row)
    results.close()

    # --- PDF title ---
    page2_title = Paragraph("Детали за Продажба", bold_style)

    # --- Header rows (grouped like Excel) ---
    page2_table = [
        # Row 1 - group headers
        [
        Paragraph("", wrap_style),  # Tip provizija
        Paragraph("", wrap_style),  # Полиса
        Paragraph("", wrap_style),  # Договорувач
        Paragraph("Премија", bold_style), "", "", "", "","",  # group 5
        Paragraph("Период на уплата", bold_style), "",   # group 3
        "","","",Paragraph("Провизија", bold_style), "", "", "",  # group 5
        Paragraph("", wrap_style),  # Бодови
        Paragraph("", wrap_style),  # Вредност бод
        Paragraph("", wrap_style),  # Наплата
        ],
        # Row 2 - subheaders
        [
            Paragraph("Тип на провизија", wrap_style),
            Paragraph("Полиса", wrap_style),
            Paragraph("Договорувач", wrap_style),
            Paragraph("LF/UL", wrap_style),
            Paragraph("IN", wrap_style),
            Paragraph("ZD", wrap_style),
            Paragraph("TBS", wrap_style),
            Paragraph("Вкупно", wrap_style),
            Paragraph("Датум на наплата", wrap_style),
            Paragraph("Од", wrap_style),
            Paragraph("До", wrap_style),
            Paragraph("Број на рати", wrap_style),
            Paragraph("Година на уплата", wrap_style),
            Paragraph("Уплатена рата", wrap_style),
            Paragraph("LF/UL", wrap_style),
            Paragraph("IN", wrap_style),
            Paragraph("ZD", wrap_style),
            Paragraph("TBS", wrap_style),
            Paragraph("Вкупно", wrap_style),
            Paragraph("Бодови", wrap_style),
            Paragraph("Вредност бод", wrap_style),
            Paragraph("Наплата", wrap_style),
        ]
    ]

    # --- Add data rows ---
    for row in analitika1:
        page2_table.append([
            row[23], # Tip provizija
            row[0],  # Полиса
            row[1],  # Договорувач
            row[4],  # LF/UL
            row[5],  # IN
            row[6],  # ZD
            row[7],  # TBS
            row[8],  # Вкупно премија
            row[9],  # Датум на наплата
            row[10], # Од
            row[11], # До
            row[20], # Број на рати
            row[21], # Година на уплата
            row[22], # Уплатена рата
            row[12], # Prov LF
            row[13], # Prov IN
            row[14], # Prov ZD
            row[15], # Prov TBS
            row[16], # Вкупно провизија
            row[17], # Бодови
            row[18], # Вредност бод
            row[19], # Наплата
        ])

    # # --- Create PDF ---
    # landscape_pdf_path = "detali_prodazba.pdf"
    # landscape_pdf = SimpleDocTemplate(landscape_pdf_path, pagesize=landscape(A3))

    # col_widths = [60, 90, 40, 40, 40, 40, 50, 50, 50, 55, 45, 45, 45, 45, 55, 45, 50, 55]

    # table = Table(page2_table, colWidths=col_widths, repeatRows=2)

    # # --- Styling with merged headers ---
    # table_style = TableStyle([
    #     ('SPAN', (2,0), (6,0)),  # Премија
    #     ('SPAN', (7,0), (9,0)),  # Период на уплата
    #     ('SPAN', (10,0), (14,0)), # Провизија
    #     ('BACKGROUND', (0,0), (-1,1), colors.lightgrey),
    #     ('GRID', (0,0), (-1,-1), 0.5, colors.black),
    #     ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    #     ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    #     ('FONTNAME', (0,0), (-1,-1), 'DejaVuSans'),
    #     ('FONTSIZE', (0,0), (-1,-1), 7),
    #     ('BOTTOMPADDING', (0,0), (-1,0), 6),
    # ])
    # table.setStyle(table_style)

    # # --- Build PDF ---
    # elements = [page2_title, Spacer(1, 20), table]
    # landscape_pdf.build(elements)
    # print(f"✅ PDF 'detali_prodazba.pdf' successfully created.")


    # sql = f"""
    # SELECT 
    # polisa_broj,
    # dogovoruvac_name, 
    # TO_CHAR(skadenca_datum_od, '%d/%m/%Y') AS skadenca_datum_od,
    # TO_CHAR(skadenca_datum_do, '%d/%m/%Y') AS skadenca_datum_do,
    # premija_zivot,
    # premija_nezgoda,
    # premija_zdravstveno, 
    # NVL(premija_tbs, 0) AS premija_tbs, 
    # tip_knizi,
    # koja_godina,
    # br_rati,
    # rata, 
    # ROUND(iznos_provizija * vrati_kurs(TODAY, 'EUR')) AS provizija_mkd,
    # tip_provizija,
    # br_bodovi, 
    # bod, 
    # TO_CHAR(dat_naplata, '%d/%m/%Y') dat_naplata  
    # FROM 
    # agenti_provizija 
    # where mesec= {mesec}
    # and godina={godina}
    # and par_agentid={record[3]}
    # """

    # print(sql)
    # results, OK = Connection.OSISinit()
    # if not OK:
    #     print("Greska - nema vrska so baza")
    #     return OK, 0.0, "Greska - nema vrska so baza"

    # # Execute SQL query and fetch results
    # results.execute(sql)  
    # analitika = []
    
    # while True:
    #     row = results.fetchone()
    #     if not row:
    #         break
    #     analitika.append(row)
    
    # results.close()
    # # Page 2 Data
    # page2_title = Paragraph("Детали за Продажба", bold_style)
    # page2_table = [
    # [
    #     Paragraph("Полиса", wrap_style),
    #     Paragraph("Договорувач", wrap_style),
    #     Paragraph("Датум од скаденца", wrap_style),
    #     Paragraph("Датум до скаденца", wrap_style),
    #     Paragraph("Премија живот", wrap_style),
    #     Paragraph("Премија незгода", wrap_style),
    #     Paragraph("Премија здравство", wrap_style),
    #     Paragraph("Премија ТБС", wrap_style),
    #     Paragraph("Тип на осигурување", wrap_style),
    #     Paragraph("Година", wrap_style),
    #     Paragraph("Број на рати", wrap_style),
    #     Paragraph("Рата", wrap_style),
    #     Paragraph("МКД провизија", wrap_style),
    #     Paragraph("Тип на провизија", wrap_style),
    #     Paragraph("Бодови", wrap_style),
    #     Paragraph("Вредност бод", wrap_style),
    #     Paragraph("Датум на наплата", wrap_style),
    # ]
    # ]
    # for row in analitika1:
    #     page2_table.append(row)
    portrait_pdf_path = "portrait_temp.pdf"
    portrait_pdf = SimpleDocTemplate(portrait_pdf_path, pagesize=A4)
    portrait_elements = [
        page1_title,
        Spacer(1, 40),
        create_table(page1_data, col_widths=[200, 150, 150], alignments=['LEFT', 'CENTER', 'RIGHT'],border_color=colors.white),
        Spacer(1, 40),
        create_table(page1_table6, col_widths=[510], alignments=['LEFT'],background_colors=["gray"]),
        Spacer(1, 5),
        create_table(page1_table1, col_widths=[150, 120, 120, 120], alignments=['LEFT', 'RIGHT', 'RIGHT', 'RIGHT']),
        Spacer(1, 20),
        create_table(page1_table2, col_widths=[360, 150], alignments=['LEFT', 'RIGHT'],background_colors=["gray"]),
        Spacer(1, 20),
        create_table(page1_table5, col_widths=[360, 150], alignments=['LEFT', 'RIGHT']),
        Spacer(1, 20),
        create_table(page1_table7, col_widths=[360, 150], alignments=['LEFT', 'RIGHT']),
        Spacer(1, 20),
        create_table(page1_table4, col_widths=[510], alignments=['LEFT'],background_colors=["gray"]),
        Spacer(1, 5),
        create_table(page1_table3, col_widths=[210, 150, 150], alignments=['LEFT', 'RIGHT', 'RIGHT']),
    ]
    portrait_pdf.build(portrait_elements, onFirstPage=lambda canvas_obj, doc: draw_first_page(canvas_obj, doc, background_image_path))

    
    table1 = Table(page2_table, repeatRows=2, colWidths=[70,	70,	150,	40,	40,	40,	40,	40,	50,	50,	50,	40,	40,	40,	40,	40,	40,	40,	40,	40,	40,	40])

# Style the table
    table_style = TableStyle([
    # HEADER STYLING
    ('BACKGROUND', (0, 0), (-1, 1), colors.lightgrey),
    ('TEXTCOLOR', (0, 0), (-1, 1), colors.black),
    ('ALIGN', (0, 0), (-1, 1), 'CENTER'),
    ('VALIGN', (0, 0), (-1, 1), 'MIDDLE'),
    ('FONTNAME', (0, 0), (-1, 1), 'DejaVuSans'),
    ('FONTSIZE', (0, 0), (-1, 1), 8),
    ('BOTTOMPADDING', (0, 0), (-1, 1), 5),
    ('TOPPADDING', (0, 0), (-1, 1), 5),

    # --- MERGED HEADER CELLS ---
    ('SPAN', (3, 0), (7, 0)),   # Премија covers LF/UL–Вкупно
    ('SPAN', (9, 0), (10, 0)),   # Период на уплата covers Од–До
    ('SPAN', (14, 0), (18, 0)),  # Провизија covers LF/UL–Наплата

    # BODY STYLE
    ('BACKGROUND', (0, 2), (-1, -1), colors.white),
    ('ALIGN', (0, 2), (-1, -1), 'CENTER'),
    ('VALIGN', (0, 2), (-1, -1), 'MIDDLE'),
    ('FONTNAME', (0, 2), (-1, -1), 'DejaVuSans'),
    ('FONTSIZE', (0, 2), (-1, -1), 7),

    # GRID
    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ])



    table1.setStyle(table_style)
    landscape_pdf_path = "landscape_temp.pdf"
    landscape_pdf = SimpleDocTemplate(landscape_pdf_path, pagesize=landscape(A3))
    
    landscape_elements = [
        page2_title,
        Spacer(1, 20),
        table1,
    ]
    landscape_pdf.build(landscape_elements)

    # Merge portrait and landscape PDFs
    from PyPDF2 import PdfMerger
    merger = PdfMerger()
    merger.append(portrait_pdf_path)
    merger.append(landscape_pdf_path)
    merger.write(output_path)
    merger.close()

    # Clean up temporary files
    os.remove(portrait_pdf_path)
    os.remove(landscape_pdf_path)
  



def create_table(data, col_widths=None, alignments=None, background_colors=None, border_color=colors.black):
    """
    Create a styled table with dynamic column widths, alignments, background colors, and border color.

    Args:
        data (list): 2D list representing table data.
        col_widths (list): List of column widths.
        alignments (list): List of alignments for each column (e.g., 'CENTER', 'LEFT', 'RIGHT').
        background_colors (list): List of background colors for each row (or specific cells).
                                  Use None or an empty list for no background styling.
        border_color: Color for the table borders (default is black).

    Returns:
        Table: Styled Table object.
    """
    table = Table(data, colWidths=col_widths)

    # Default alignments if not provided
    if not alignments:
        alignments = ['CENTER'] * len(data[0])  # Default to center alignment for all columns

    # Build TableStyle dynamically
    style = [
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),  # Header text color
        ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),  # Use the registered font
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),        # Padding for header cells
        ('GRID', (0, 0), (-1, -1), 1, border_color),   # Add borders for all cells
    ]

    # Apply dynamic background colors if provided
    if background_colors:
        for row_idx, bg_color in enumerate(background_colors):
            if bg_color:  # Only apply if the color is not None
                style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), bg_color))

    # Apply alignments dynamically for each column
    for col_idx, alignment in enumerate(alignments):
        style.append(('ALIGN', (col_idx, 0), (col_idx, -1), alignment))

    table.setStyle(TableStyle(style))
    return table

    
def draw_first_page(canvas_obj, doc, image_path):
    """
    Draw the first page with a background image.
    """
    canvas_obj.saveState()  # Save the state before modifying the canvas
    if os.path.exists(image_path):
        canvas_obj.drawImage(image_path, x=0, y=0, width=A4[0], height=A4[1], mask='auto')
    else:
        print(f"Error: Image {image_path} not found.")
    canvas_obj.restoreState()  # Restore the state after drawing



def send_email_with_pdf(mesec, godina,par_teamid, par_regionuid,par_agentid):

    print(par_teamid)
    print(par_regionuid)
    print(par_agentid)

    sql = f"""
    select * from zbiren_prov_promotori_ex
    where mesec= {mesec}
    and godina={godina} 
    """
    if par_teamid:
        sql += f"""
        and par_agentid in (
        select par_agentid from par_agent_pripadnost a 
        where par_teamid={par_teamid})"""
    if par_regionuid:
        sql += f""" 
         and par_agentid in (
        select par_agentid from par_agent_pripadnost a , par_regionu_filijala b 
        where a.par_regionu_filijalaid=b.par_regionu_filijalaid
        and par_regionuid={par_regionuid}) """
    if par_agentid:
        sql += f" AND par_agentid = {par_agentid}"

    print(sql)
    results, OK = Connection.OSISinit()
    if not OK:
        print("Greska - nema vrska so baza")
        return OK, 0.0, "Greska - nema vrska so baza"

    # Execute SQL query and fetch results
    results.execute(sql)  
    podatoci = []
    
    while True:
        row = results.fetchone()
        if not row:
            break
        podatoci.append(row)
    
    results.close()
    
    # Main processing loop
    for record in podatoci:
        # Extract recipient email and other data from the record
        #recipient_email = record['agent_email']  # Replace 'email' with the correct column name
        #recipient_email = "snakevska@gmail.com"
        recipient_email = "aleksandra.shkembi@uniqa.mk"
        agent_name = record[4].strip() if record[4] else "Непознат Промотор"  # Default value if None
        agent_tim = record[7].strip() if record[7] else "Непознат Тим"       # Default value if None
        agent_nivo = record[5].strip() if record[5] else "Непозната Позиција"  # Default value if None

        sanitized_agent_name = sanitize_filename(agent_name)
        print (sanitized_agent_name)

        # Generate a unique PDF for each agent
        output_pdf_path = "ProvizijaAgent.pdf"
        #output_pdf_path = f"ProvizijaAgent_{sanitized_agent_name}.pdf"
        print (output_pdf_path) 
        generate_dynamic_pdf(output_pdf_path, mesec, godina,agent_name, agent_tim, agent_nivo, record  )  # Pass agent-specific data if needed

        # Email details
        subject = f"Провизија за месец {mesec}/{godina}"
        body = f"Во прилог е провизијата за месец {mesec}/{godina} за {agent_name}."

        # Send email
        send_email(recipient_email, subject, body, output_pdf_path)

    print("All emails sent successfully.")
    return "OK", "Email sent successfully!"
    
    
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

def send_email_with_pdf_odg_lice(mesec, godina, par_teamid, par_regionuid, par_agentid):
    print(par_teamid)
    print(par_regionuid)
    print(par_agentid)

    # SQL query preparation
    sql = f"""
    SELECT * FROM zbiren_prov_promotori_ex
    WHERE mesec = {mesec} AND godina = {godina}
    """
    if par_teamid:
        sql += f"""
        AND par_agentid IN (
            SELECT par_agentid FROM par_agent_pripadnost a 
            WHERE par_teamid = {par_teamid}
        )
        """
    if par_regionuid:
        sql += f"""
        AND par_agentid IN (
            SELECT a.par_agentid FROM par_agent_pripadnost a, par_regionu_filijala b 
            WHERE a.par_regionu_filijalaid = b.par_regionu_filijalaid
            AND par_regionuid = {par_regionuid}
        )
        """
    if par_agentid:
        sql += f" AND par_agentid = {par_agentid}"

    print(sql)

    # Connect to the database
    results, OK = Connection.OSISinit()
    if not OK:
        print("Грешка - нема врска со база")
        return OK, 0.0, "Грешка - нема врска со база"

    # Execute SQL query and fetch results
    results.execute(sql)
    podatoci = []

    while True:
        row = results.fetchone()
        if not row:
            break
        podatoci.append(row)

    results.close()

    # Collect PDF paths for attachment
    pdf_paths = []
    for record in podatoci:
        agent_name = record[4].strip() if record[4] else "Непознат Промотор"
        agent_tim = record[7].strip() if record[7] else "Непознат Тим"
        agent_nivo = record[5].strip() if record[5] else "Непозната Позиција"

        sanitized_agent_name = transliterate_macedonian(sanitize_filename(agent_name))
        print(sanitized_agent_name)

        par_teamid_str = str(par_teamid) if par_teamid else "unknown_team"
        configDIR, inputDIR, sep = Directories(str(mesec), str(godina))

        output_pdf_filename = f"ProvizijaAgent_{sanitized_agent_name}_{mesec}_{godina}.pdf"
        directory = os.path.join(inputDIR, par_teamid_str)

        if not os.path.exists(directory):
            os.makedirs(directory)

        output_pdf_path = os.path.join(directory, output_pdf_filename)
        print(f"Output PDF Path: {output_pdf_path}")

        try:
            generate_dynamic_pdf(output_pdf_path, mesec, godina, agent_name, agent_tim, agent_nivo, record)
            pdf_paths.append(output_pdf_path)  # Add generated PDF to list
        except PermissionError as e:
            print(f"Error: {e}. Ensure the file is not open and you have write permissions.")

    # Send a single email with all PDFs attached
    #recipient_email = "aleksandra.shkembi@uniqa.mk"
    recipient_email = "snakevska@gmail.com"
    subject = f"Провизија за месец {mesec}/{godina}"
    body = f"Во прилог е провизијата за месец {mesec}/{godina}."

    send_email_with_attachments(recipient_email, subject, body, pdf_paths)

    print("All emails sent successfully.")
    return "OK", "Email sent successfully!"


def send_email_with_attachments(recipient_email, subject, body, pdf_paths):
     # Get SMTP settings from database
    settings = get_smtp_settings()
    print(settings.get("smtp.fromaddress")) 
    sender_email = settings.get("smtp.fromaddress")
    sender_username = settings.get("smtp.username")
    sender_password = settings.get("smtp.password")
    smtp_host = settings.get("smtp.host")
    smtp_port = int(settings.get("smtp.port", 25))
    smtp_port=587
    smtp_auth = settings.get("smtp.auth", "").lower() == "true"  # Convert to boolean

    if not sender_email or not smtp_host:
        print("Missing SMTP settings. Please check the database.")
        return
    
    # Create email message
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg["Subject"] = subject

    
    msg.attach(MIMEText(body, 'plain'))

    # Attach all PDFs
    for pdf_path in pdf_paths:
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={os.path.basename(pdf_path)}",
                )
                msg.attach(part)
        else:
            print(f"Warning: PDF {pdf_path} not found.")

    # Send the email
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()  # Identify with the server
            if smtp_port == 587:
                server.starttls()  # Only for STARTTLS (port 587)
            if smtp_auth:
                server.login(sender_username, sender_password,)
            server.sendmail(sender_email, recipient_email, msg.as_string())
            print(f"Email sent successfully to {recipient_email}")
    except Exception as e:
        print(f"Failed to send email to {recipient_email}: {e}")
        

# Function to send email
def send_email_gmail(recipient_email, subject, body, pdf_path):
    sender_email = "svconsult40@gmail.com"
    sender_password = "agao yavr gphd puvs"

    # Create email message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject

    # Attach the email body
    msg.attach(MIMEText(body, 'plain'))

    # Attach the PDF file
    with open(pdf_path, 'rb') as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(pdf_path)}')
    msg.attach(part)

    # Send the email
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            print(f"Email sent successfully to {recipient_email}")
    except Exception as e:
        print(f"Failed to send email to {recipient_email}: {e}")
 

def get_smtp_settings():
    """Fetch SMTP settings from the database using Connection.OSISinit()"""
    sql = "SELECT key, value FROM adm_appsettings WHERE key LIKE 'smtp.%'"

    results, OK = Connection.OSISinit()
    if not OK:
        print("Error - no connection to the database")
        return {}

    results.execute(sql)

    settings = {}
    while True:
        row = results.fetchone()
        if not row:
            break
        settings[row[0]] = row[1]  # Storing key-value pairs using tuple indices

    results.close()
    return settings


def send_email(recipient_email, subject, body, pdf_path):
    """Send an email with an attachment using SMTP settings from the database"""

    # Get SMTP settings from database
    settings = get_smtp_settings()
    print(settings.get("smtp.fromaddress")) 
    sender_email = settings.get("smtp.fromaddress")
    sender_username = settings.get("smtp.username")
    sender_password = settings.get("smtp.password")
    smtp_host = settings.get("smtp.host")
    smtp_port = int(settings.get("smtp.port", 25))
    #smtp_port=int(587);
    smtp_auth = settings.get("smtp.auth", "").lower() == "true"  # Convert to boolean

    smtp_host = "smtp.office365.com"
    smtp_port = 587
    smtp_auth= True


    if not sender_email or not smtp_host:
        print("Missing SMTP settings. Please check the database.")
        return
    
    # Create email message
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg["Subject"] = subject

    # Attach the email body
    msg.attach(MIMEText(body, "plain"))

    # Attach the PDF file if provided
    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(pdf_path)}")
        msg.attach(part)

    # Send the email
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()  # Identify with the server
            if smtp_port == 587:
                server.starttls()  # Only for STARTTLS (port 587)
            if smtp_auth:
                server.login(sender_username, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
            print(f"Email sent successfully to {recipient_email}")
    except Exception as e:
        print(f"Failed to send email to {recipient_email}: {e}")

        
def sanitize_filename(filename):
    # Remove or replace invalid characters
    filename = filename.strip()  # Remove leading/trailing spaces
    filename = filename.replace(" ", "_")  # Replace spaces with underscores
    filename = ''.join(c for c in filename if c.isalnum() or c in "._-")  # Allow only alphanumeric, dots, underscores, and hyphens
    return filename
    
    

def gen_pdf(mesec, godina,par_teamid, par_regionuid,par_agentid):
    print(par_teamid)
    print(par_regionuid)
    print(par_agentid)

    sql = f"""
    select * from zbiren_prov_promotori_ex
    where mesec= {mesec}
    and godina={godina}
    """
    if par_teamid:
        sql += f"""
        and par_agentid in (
        select par_agentid from par_agent_pripadnost a 
        where par_teamid={par_teamid})"""
    if par_regionuid:
        sql += f""" 
         and par_agentid in (
        select par_agentid from par_agent_pripadnost a , par_regionu_filijala b 
        where a.par_regionu_filijalaid=b.par_regionu_filijalaid
        and par_regionuid={par_regionuid}) """
    if par_agentid:
        sql += f" AND par_agentid = {par_agentid}"

   

    print(f"Generated SQL: {sql}")
    results, OK = Connection.OSISinit()
    if not OK:
        print("Greska - nema vrska so baza")
        return OK, 0.0, "Greska - nema vrska so baza"

    # Execute SQL query and fetch results
    results.execute(sql)  
    podatoci = []
    
    while True:
        row = results.fetchone()
        if not row:
            break
        podatoci.append(row)
    
    results.close()
    
    # Main processing loop
    for record in podatoci:
        # Extract recipient email and other data from the record
        #recipient_email = record['agent_email']  # Replace 'email' with the correct column name
        #recipient_email = "aleksandra.shkembi@uniqa.mk"
        recipient_email = "snakevska@gmail.com"
        agent_name = record[4].strip() if record[4] else "Непознат Промотор"  # Default value if None
        agent_tim = record[7].strip() if record[7] else "Непознат Тим"       # Default value if None
        agent_nivo = record[5].strip() if record[5] else "Непозната Позиција"  # Default value if None

        sanitized_agent_name = sanitize_filename(agent_name)
        print (sanitized_agent_name)

        # Generate a unique PDF for each agent
        month_str = str(mesec).zfill(2) 
        configDIR, inputDIR, sep = Directories(str(month_str), str(godina))
        output_pdf_path = "ProvizijaAgent.pdf"
        output_pdf_path = f"ProvizijaAgent_{sanitized_agent_name}_{month_str}_{godina}.pdf"
        output_pdf_path=os.path.join(inputDIR, output_pdf_path)
        print (output_pdf_path) 
        directory = os.path.dirname(output_pdf_path)
    
        # Check if the directory exists, if not, create it
        if not os.path.exists(directory):
            os.makedirs(directory)
        generate_dynamic_pdf(output_pdf_path, mesec, godina,agent_name, agent_tim, agent_nivo, record  )  # Pass agent-specific data if needed

    return "OK", "Изгенерирани се фајловите!"
 
def transliterate_macedonian(text):
    translit_map = {
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D',
        'Ѓ': 'Gj', 'Е': 'E', 'Ж': 'Zh', 'З': 'Z', 'И': 'I',
        'Ј': 'J', 'К': 'K', 'Л': 'L', 'Љ': 'Lj', 'М': 'M',
        'Н': 'N', 'Њ': 'Nj', 'О': 'O', 'П': 'P', 'Р': 'R',
        'С': 'S', 'Т': 'T', 'Ќ': 'Kj', 'У': 'U', 'Ф': 'F',
        'Х': 'H', 'Ц': 'C', 'Ч': 'Ch', 'Џ': 'Dzh', 'Ш': 'Sh',
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
        'ѓ': 'gj', 'е': 'e', 'ж': 'zh', 'з': 'z', 'и': 'i',
        'ј': 'j', 'к': 'k', 'л': 'l', 'љ': 'lj', 'м': 'm',
        'н': 'n', 'њ': 'nj', 'о': 'o', 'п': 'p', 'р': 'r',
        'с': 's', 'т': 't', 'ќ': 'kj', 'у': 'u', 'ф': 'f',
        'х': 'h', 'ц': 'c', 'ч': 'ch', 'џ': 'dzh', 'ш': 'sh'
    }
    return ''.join(translit_map.get(char, char) for char in text)