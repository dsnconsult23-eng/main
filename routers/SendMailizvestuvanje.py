from routers    import Connection, SendMail, GeneratePDFIzvestuvanje
import re
import os
from datetime import datetime, timedelta
from routers.GeneratePDFIzvestuvanje import generate_pdf

def is_valid_email(email):
    """Basic regex-based email validator"""
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email) is not None

def sendMailIzvestuvanje():
    """Send email notification for insurance premium due with PDF attachment."""

    sql = """
    SELECT faktura, par_clientid, email
    FROM report_dolzna_premija 
    WHERE saldo<>0
      AND datum_izvest1=today-1 
      AND polisa_broj[1,2] <> '27'
      AND client_prav_fiz = 'F'
      AND tip_izvestuvanje = 1
      and nvl(email,'.') <>'.'
    """
    
    results, OK = Connection.OSISinit()
    if not OK:
        print("Database connection failed.")
        return
    
    results.execute(sql)
    while True:
        row = results.fetchone()
        if not row:
            break
        
        faktura, par_clientid, email = row
        print(f"Processing: {email}, client: {par_clientid}, faktura: {faktura}")
        if not is_valid_email(email):
            print(f"Invalid email skipped: {email}")
            continue
        # Fetch client details
        sql_client = """
         SELECT client_name, client_adresa, client_post client_grad, polisa_broj polisa_number,datum_knizi due_date, 
               premija_tekovna premium_amount,naplata_tekovna  paid_premium, godina_tekovna godina,rata_tekovna  rata,period_tekoven period, 
               saldo_zaostanat_dolg unpaid_premium, valuta
        FROM vesna.print_izvest
        where klient_faktura= ?
        """
        results_client, OK = Connection.OSISinit()
        if not OK:
            print("Database connection failed for client details.")
            return
        results_client.execute(sql_client, (f"{par_clientid}_{faktura}",))
        client_row = results_client.fetchone()
        if not client_row:
            print(f"No client details found for faktura: {faktura}")
            continue
        client_name, client_adresa, client_grad, polisa_number, due_date, premium_amount, paid_premium, godina, rata, period, unpaid_premium,  valuta = client_row  
        print(f"Client details: {client_name}, {client_adresa}, {client_grad}, {polisa_number}, {due_date}, {premium_amount}, {paid_premium}, {godina}, {rata}, {period}, {unpaid_premium}, {valuta}")
        balance =premium_amount - paid_premium
        vk_premija = balance + unpaid_premium

        # PDF path pattern
        #pdf_path = f"/path/to/pdf/ProvizijaAgent_{par_clientid}_07_2025.pdf"

        html_body = """
        <html><body>
        <p>Почитувани,</p>
        <p>Во прилог Ви испраќаме известување за доспеана премија за осигурување на живот.</p>

        <p>Сега можете брзо и лесно да ја платите Вашата премија <a href="https://plationline.uniqa.mk/">онлајн</a>, без надоменсток.</p>

        <p><strong>Ново!</strong> Премијата може да ја платите на рати преку кредитна картичка на Стопанска Банка АД Скопје со кликање на копчето</p>
        <p><strong>На рати преку „Стопанска Банка“ А.Д. Скопје</strong></p>
        <p>УНИКА ЛАЈФ АД Скопје ви овозможува креирање на <strong>траен налог</strong> за плаќање на премија за осигурување на живот со кликање на копчето</p>

        <p><a href="https://plationline.uniqa.mk/" style="padding:10px 20px;background:#007bff;color:white;text-decoration:none;border-radius:4px;">Плати премија онлајн</a></p>

        <p>Потврда за извршеното плаќање ќе добиете на Вашиот е-мејл.</p>

        <p>Подигнување на <strong><a href="https://www.uniqa.mk/подигнување-на-заем-по-полиса-за-осигу/">ЗАЕМ</a></strong> врз основ на Вашата полиса за осигурување на живот во рок од еден работен ден.</p>

        <p>Сите информации околу условите и потребните документи за подигнување на заем, може да ги најдете на следниот линк: <a href="https://www.uniqa.mk/подигнување-на-заем-по-полиса-за-осигу/">Заем по полиса за осигурување на живот</a>.</p>

        <p>За дополнителни прашања или информации, слободно обратете се на телефонскиот број: 02/ 3 288 -820, E-mail: <a href="mailto:uniqalifeinfo@uniqa.mk">uniqalifeinfo@uniqa.mk</a>, Веб-страна: <a href="https://www.uniqa.mk">www.uniqa.mk</a></p>

        <p style="font-size:small;color:gray;">
        Напомена: Оваа е-пошта и сите прилози содржат доверливи информации наменети само за употреба на лицето на кое таа се однесува... Ако сте ја примиле оваа е-пошта по грешка, Ве молиме веднаш да нè известите и потоа да ја избришете од Вашиот систем.
        </p>

        <p>Со почит,<br><strong>УНИКА ЛАЈФ АД Скопје</strong></p>
        <hr>
        <p style="font-size:small;">
        UNIQA Life a.d. Skopje<br>
        Bul. Ilinden br.1<br>
        Skopje, Macedonia<br>
        Tel.+389(0)23288820<br>
        Fax.+389(0)23215128<br>
        <a href="mailto:uniqalifeinfo@uniqa.mk">uniqalifeinfo@uniqa.mk</a><br>
        <a href="https://www.uniqa.mk">www.uniqa.mk</a>
        </p>
        </body></html>
        """
    # Send email with PDF attachment
    # Assuming generate_pdf is a function that creates the PDF and saves it to a known path
        save_folder = "C:/Reports/UNIQA"
        os.makedirs(save_folder, exist_ok=True)
        safe_faktura = faktura.replace("/", "-")

# Then use it
        file_name = f"Izvestuvanje za dospeana premija_{safe_faktura}.pdf"
        full_path = os.path.join(save_folder, file_name)
        generate_pdf(full_path, client_name,client_adresa, client_grad,polisa_number, due_date,
                      premium_amount, paid_premium, balance,godina, rata,period,unpaid_premium, vk_premija, valuta)
        SendMail.send_html_email_with_attachments(
        recipient_email="snakevska@gmail.com",
        subject="Известување за доспеана премија",
        html_body=html_body,
        pdf_paths=[full_path]
)