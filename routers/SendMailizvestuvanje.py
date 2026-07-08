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
    print("Starting sendMailIzvestuvanje...")
    sql = """
      SELECT  faktura, par_clientid, email
      FROM report_dolzna_premija 
      WHERE saldo<>0
      AND datum_izvest1=mdy(month(today),1,year(today))
      AND polisa_broj[1,2] <> '27'
      AND client_prav_fiz = 'F'
      AND tip_izvestuvanje = 1
      and par_tip_platiid=35
      and nvl(email,'.') like '%@%'
      and par_clientid  not  in (select par_clientid from send_mail_dolzna_premija 
      where month(datecreated)=month(today) and year(datecreated) =year(today) and usercreated='admin')
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
        tpar_clientid = str(par_clientid).strip()
        print(f"Processing: {email}, client: {par_clientid}, faktura: {faktura}")
        if not is_valid_email(email):
            print(f"Invalid email skipped: {email}")
            continue
        # Fetch client details
        sql_client = """
         SELECT client_name, client_adresa, client_post client_grad, polisa_broj polisa_number,datum_knizi due_date, 
               premija_tekovna premium_amount,naplata_tekovna  paid_premium, godina_tekovna godina,rata_tekovna  rata,period_tekoven period, 
               round(saldo_zaostanat_dolg,2) unpaid_premium, valuta,
               saldo_zaostanat_dolg+premija_tekovna - naplata_tekovna vk_premija
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
        client_name, client_adresa, client_grad, polisa_number, due_date, premium_amount, paid_premium, godina, rata, period, unpaid_premium,  valuta,vk_premija = client_row  
        print(f"Client details: {client_name}, {client_adresa}, {client_grad}, {polisa_number}, {due_date}, {premium_amount}, {paid_premium}, {godina}, {rata}, {period}, {unpaid_premium}, {valuta},{vk_premija}")
        balance =premium_amount - paid_premium
        # vk_premija = balance + unpaid_premium

        # PDF path pattern
        #pdf_path = f"/path/to/pdf/ProvizijaAgent_{par_clientid}_07_2025.pdf"

#         html_body = """
# <html>
#   <body style="font-family: Arial, sans-serif; line-height: 1.6; color:#000;">

#     <p>Почитувани,</p>

#     <!-- Section with image on the left -->
#     <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:20px 0;">
#       <tr>
#         <!-- Left column with image -->
#         <td width="120" valign="top" style="padding-right:15px;">
#           <img src="cid:uniqa_logo" alt="UNIQA" width="100" style="display:block;">
#         </td>

#         <!-- Right column with text -->
#         <td valign="top" style="font-family:Arial,sans-serif; font-size:14px; color:#000;">
#           <p style="margin:0 0 10px 0;">Во прилог Ви испраќаме известување за доспеана премија за осигурување на живот.</p>

#           <p style="margin:0 0 10px 0;">Сега можете брзо и лесно да ја платите Вашата премија 
#              <a href="https://plationline.sigal.com.mk/" style="color:#007bff; text-decoration:none;">онлајн</a>, без надоместок.
#           </p>

#           <p style="margin:0;"><strong>Ново!</strong> Премијата може да ја платите на рати преку кредитна картичка на 
#              Стопанска Банка АД Скопје со кликање на копчето
#           </p>
#         </td>
#       </tr>
#     </table>

#     <p><strong>На рати преку „Стопанска Банка“ А.Д. Скопје</strong></p>

#     <p>СИГАЛ ЛАЈФ АД Скопје ви овозможува креирање на 
#        <strong>траен налог</strong> за плаќање на премија за осигурување на живот со кликање на копчето</p>

#     <p>
#       <a href="https://plationline.sigal.com.mk/" 
#          style="display:inline-block; padding:12px 25px; background:#007bff; color:#fff; 
#                 text-decoration:none; border-radius:6px; font-weight:bold;">
#         Плати премија онлајн
#       </a>
#     </p>

#     <p>Потврда за извршеното плаќање ќе добиете на Вашиот е-мејл.</p>

#     <p>Подигнување на <a href="https://www.sigal.com.mk/подигнување-на-заем-по-полиса-за-осигу/" 
#            style="color:#007bff; text-decoration:none;"><strong>ЗАЕМ</strong></a> 
#        врз основ на Вашата полиса за осигурување на живот во рок од еден работен ден.</p>

#     <p>Сите информации околу условите и потребните документи за подигнување на заем, 
#        може да ги најдете на следниот линк: 
#        <a href="https://www.sigal.com.mk/подигнување-на-заем-по-полиса-за-осигу/" style="color:#007bff;">
#          Заем по полиса за осигурување на живот
#        </a>.
#     </p>

#     <p>За дополнителни прашања или информации, слободно обратете се на телефонскиот број: 
#        02/ 3 288 -820, E-mail: 
#        <a href="mailto:lifeinsurance@sigal.com.mk" style="color:#007bff;">lifeinsurance@sigal.com.mk</a>, 
#        Веб-страна: <a href="https://sigal.com.mk" style="color:#007bff;">www.sigal.com.mk</a>
#     </p>

#     <p style="font-size:12px; color:gray;">
#       Напомена: Оваа е-пошта и сите прилози содржат доверливи информации наменети само за употреба на лицето 
#       на кое таа се однесува... Ако сте ја примиле оваа е-пошта по грешка, Ве молиме веднаш да нè известите 
#       и потоа да ја избришете од Вашиот систем.
#     </p>

#     <p>Со почит,<br><strong>СИГАЛ ЛАЈФ АД Скопје</strong></p>
#     <hr>

#     <p style="font-size:12px; color:#333; line-height:1.4;">
#       SIGAL Life a.d. Skopje<br>
#       Bul. Ilinden br.1<br>
#       Skopje, Macedonia<br>
#       Tel.+389(0)23288820<br>
#       Fax.+389(0)23215128<br>
#       <a href="mailto:lifeinsurance@sigal.com.mk" style="color:#007bff;">lifeinsurance@sigal.com.mk</a><br>
#       <a href="https://sigal.com.mk style="color:#007bff;">www.sigal.com.mk</a>
#     </p>

#   </body>
# </html>
# """
        polisa_number = str(polisa_number)  # осигурај се дека е string

        loan_section = ""
        if not polisa_number.startswith("28"):
          loan_section = """
    <p>Подигнување на <a href="https://www.sigal.com.mk/подигнување-на-заем-по-полиса-за-осигу/"
           style="color:#007bff; text-decoration:none;"><strong>ЗАЕМ</strong></a>
       врз основ на Вашата полиса за осигурување на живот во рок од еден работен ден.</p>

    <p>Сите информации околу условите и потребните документи за подигнување на заем,
       може да ги најдете на следниот линк:
       <a href="https://www.sigal.com.mk/подигнување-на-заем-по-полиса-за-осигу/" style="color:#007bff;">
         Заем по полиса за осигурување на живот
       </a>.
    </p>
    """

        html_body = f"""
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color:#000;">

    <p>Почитувани,</p>

    <!-- Section with image on the left -->
    <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:20px 0;">
      <tr>
        <!-- Left column with image -->
        <td width="120" valign="top" style="padding-right:15px;">
          <img src="cid:uniqa_logo" alt="UNIQA" width="100" style="display:block;">
        </td>

        <!-- Right column with text -->
        <td valign="top" style="font-family:Arial,sans-serif; font-size:14px; color:#000;">
          <p style="margin:0 0 10px 0;">Во прилог Ви испраќаме известување за доспеана премија за осигурување на живот.</p>

          <p style="margin:0 0 10px 0;">Сега можете брзо и лесно да ја платите Вашата премија
             <a href="https://plationline.sigal.com.mk/" style="color:#007bff; text-decoration:none;">онлајн</a>, без надоместок.
          </p>

          <p style="margin:0;"><strong>Ново!</strong> Премијата може да ја платите на рати преку кредитна картичка на
             Стопанска Банка АД Скопје со кликање на копчето
          </p>
        </td>
      </tr>
    </table>

    <p><strong>На рати преку „Стопанска Банка“ А.Д. Скопје</strong></p>

    <p>СИГАЛ ЛАЈФ АД Скопје ви овозможува креирање на
       <strong>траен налог</strong> за плаќање на премија за осигурување на живот со кликање на копчето</p>

    <p>
      <a href="https://plationline.sigal.com.mk/"
         style="display:inline-block; padding:12px 25px; background:#007bff; color:#fff;
                text-decoration:none; border-radius:6px; font-weight:bold;">
        Плати премија онлајн
      </a>
    </p>

    <p>Потврда за извршеното плаќање ќе добиете на Вашиот е-мејл.</p>

    {loan_section}

    <p>За дополнителни прашања или информации, слободно обратете се на телефонскиот број:
       02/ 3 288 -820, E-mail:
       <a href="mailto:lifeinsurance@sigal.com.mk" style="color:#007bff;">lifeinsurance@sigal.com.mk</a>,
       Веб-страна: <a href="https://sigal.com.mk" style="color:#007bff;">www.sigal.com.mk</a>
    </p>

    <p style="font-size:12px; color:gray;">
      Напомена: Оваа е-пошта и сите прилози содржат доверливи информации наменети само за употреба на лицето
      на кое таа се однесува... Ако сте ја примиле оваа е-пошта по грешка, Ве молиме веднаш да нè известите
      и потоа да ја избришете од Вашиот систем.
    </p>

    <p>Со почит,<br><strong>СИГАЛ ЛАЈФ АД Скопје</strong></p>
    <hr>

    <p style="font-size:12px; color:#333; line-height:1.4;">
      SIGAL Life a.d. Skopje<br>
      Bul. Ilinden br.1<br>
      Skopje, Macedonia<br>
      Tel.+389(0)23288820<br>
      Fax.+389(0)23215128<br>
      <a href="mailto:lifeinsurance@sigal.com.mk" style="color:#007bff;">lifeinsurance@sigal.com.mk</a><br>
      <a href="https://sigal.com.mk" style="color:#007bff;">www.sigal.com.mk</a>
    </p>

  </body>
</html>
"""

    # Send email with PDF attachment
    # Assuming generate_pdf is a function that creates the PDF and saves it to a known path
        save_folder = "/opt/siglife-reporting/UNIQA"
        today = datetime.today().strftime("%Y-%m-%d")

# Create full path with date
        full_save_path = os.path.join(save_folder, today)
        os.makedirs(full_save_path, exist_ok=True)

        print(full_save_path)
        safe_faktura = faktura.replace("/", "-")

# Then use it
        file_name = f"Izvestuvanje za dospeana premija_{safe_faktura}.pdf"
        full_path = os.path.join(full_save_path, file_name)
        generate_pdf(full_path, client_name,client_adresa, client_grad,polisa_number, due_date,
                      premium_amount, paid_premium, balance,godina, rata,period,unpaid_premium, vk_premija, valuta)
        SendMail.send_html_email_with_attachments_image(
        recipient_email=email,
        subject="Известување за доспеана премија",
        html_body=html_body,client_id=tpar_clientid,
        pdf_paths=[full_path]
      )