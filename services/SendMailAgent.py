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
        configDIR="c:\\Anakonda\\PyInsurance"        
        inputDIR="C:\\Pregledi\\"+m+"_"+str(g)      
    return configDIR,inputDIR,sep

def Directories1(mesec, godina):
    configDIR = "C:\\ConfigPath"
    inputDIR = f"C:\\Pregledi\\{godina}_{mesec}"
    return configDIR, inputDIR  


def generate_dynamic_pdf(output_path, mesec, godina, agent_name, agent_tim, agent_nivo, record):
    # Create a PDF document
    pdf = SimpleDocTemplate(output_path, pagesize=A4)
    background_image_path = "C:\\Anakonda\\PyInsurance\\Image\\UNIQA_MEMO1.png"


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
    sql = f"""
    SELECT 
    polisa_broj,
    dogovoruvac_name, 
    TO_CHAR(skadenca_datum_od, '%d/%m/%Y') AS skadenca_datum_od,
    TO_CHAR(skadenca_datum_do, '%d/%m/%Y') AS skadenca_datum_do,
    premija_zivot,
    premija_nezgoda,
    premija_zdravstveno, 
    NVL(premija_tbs, 0) AS premija_tbs, 
    tip_knizi,
    koja_godina,
    br_rati,
    rata, 
    ROUND(iznos_provizija * vrati_kurs(TODAY, 'EUR')) AS provizija_mkd,
    tip_provizija,
    br_bodovi, 
    bod, 
    TO_CHAR(dat_naplata, '%d/%m/%Y') dat_naplata  
    FROM 
    agenti_provizija 
    where mesec= {mesec}
    and godina={godina}
    and par_agentid={record[3]}
    """

    print(sql)
    results, OK = Connection.OSISinit()
    if not OK:
        print("Greska - nema vrska so baza")
        return OK, 0.0, "Greska - nema vrska so baza"

    # Execute SQL query and fetch results
    results.execute(sql)  
    analitika = []
    
    while True:
        row = results.fetchone()
        if not row:
            break
        analitika.append(row)
    
    results.close()
    # Page 2 Data
    page2_title = Paragraph("Детали за Продажба", bold_style)
    page2_table = [
    [
        Paragraph("Полиса", wrap_style),
        Paragraph("Договорувач", wrap_style),
        Paragraph("Датум од скаденца", wrap_style),
        Paragraph("Датум до скаденца", wrap_style),
        Paragraph("Премија живот", wrap_style),
        Paragraph("Премија незгода", wrap_style),
        Paragraph("Премија здравство", wrap_style),
        Paragraph("Премија ТБС", wrap_style),
        Paragraph("Тип на осигурување", wrap_style),
        Paragraph("Година", wrap_style),
        Paragraph("Број на рати", wrap_style),
        Paragraph("Рата", wrap_style),
        Paragraph("МКД провизија", wrap_style),
        Paragraph("Тип на провизија", wrap_style),
        Paragraph("Бодови", wrap_style),
        Paragraph("Вредност бод", wrap_style),
        Paragraph("Датум на наплата", wrap_style),
    ]
    ]
    for row in analitika:
        page2_table.append(row)
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

    # Generate page 2 (Landscape)
    table = Table(page2_table, repeatRows=1, colWidths=[50, 150, 60, 60, 60, 60, 65, 60, 160, 55, 50, 40, 60, 50, 50, 60, 70])
    
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.white),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),              # Center-align headers
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),               # Left-align data rows
        ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
    ])
    table.setStyle(table_style)

    landscape_pdf_path = "landscape_temp.pdf"
    landscape_pdf = SimpleDocTemplate(landscape_pdf_path, pagesize=landscape(A3))
    
    landscape_elements = [
        page2_title,
        Spacer(1, 20),
        table,
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
    recipient_email = "aleksandra.shkembi@uniqa.mk"
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
    #smtp_port=int(587);
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
        use_starttls = (smtp_host or "").strip().lower() == "smtp.office365.com"

        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.ehlo()

            if use_starttls:
                server.starttls()
                server.ehlo()

            if smtp_auth:
                server.login(sender_username, sender_password)

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
        use_starttls = (smtp_host or "").strip().lower() == "smtp.office365.com"

        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.ehlo()

            if use_starttls:
                server.starttls()
                server.ehlo()

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
        recipient_email = "aleksandra.shkembi@uniqa.mk"
        agent_name = record[4].strip() if record[4] else "Непознат Промотор"  # Default value if None
        agent_tim = record[7].strip() if record[7] else "Непознат Тим"       # Default value if None
        agent_nivo = record[5].strip() if record[5] else "Непозната Позиција"  # Default value if None

        sanitized_agent_name = sanitize_filename(agent_name)
        print (sanitized_agent_name)

        # Generate a unique PDF for each agent
        configDIR, inputDIR, sep = Directories(str(mesec), str(godina))
        output_pdf_path = "ProvizijaAgent.pdf"
        output_pdf_path = f"ProvizijaAgent_{sanitized_agent_name}_{mesec}_{godina}.pdf"
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