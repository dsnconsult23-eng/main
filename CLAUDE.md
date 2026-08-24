# SigLife Reporting — Техничка Документација

## Преглед на проектот

Интерен систем за известување и управување за СИГАЛ Лајф (UNIQA Life Insurance), изграден со Python/FastAPI. Ги покрива: пресметка на провизии, резервни извештаи, регулаторна усогласеност (AML), генерирање PDF/Excel, закажани email/SMS известувања, синхронизација со core insurance DB и интеграција со надворешни системи (Mesh, Иуте).

**Tech stack:** Python 3.9+, FastAPI, Jinja2, APScheduler, jaydebeapi (Informix JDBC), openpyxl, xlsxwriter, reportlab, paramiko (SFTP), passlib/bcrypt, python-jose (JWT)

---

## Архитектура

```
app  (root FastAPI — само за scheduler и блокирање на /)
└── siglife_app  (sub-app, монтирана на /siglife-report)
    ├── SessionMiddleware  (Starlette, session-based auth)
    ├── Static files  → /static
    ├── Templates     → templates/  (Jinja2)
    └── Routers       → routers/
```

- Сите URL-ови имаат `/siglife-report` префикс.
- Scheduler-от (`APScheduler BackgroundScheduler`) се стартува при `app` startup (root app, не sub-app).
- Login/logout се дефинирани директно во `main.py`, не во посебен router.

---

## Покренување локално

```bash
pip install -r requrements.txt
uvicorn main:app --reload
# Апликацијата е достапна на http://localhost:8000/siglife-report
```

**Предуслов:** JDBC jar-ови мора да постојат пред стартување:
- Windows: `C:\SigLifeReporting_Informix\`
- Linux: `/opt/siglife-reporting/`

**Потребни jar-ови:** `jdbc-4.50.4.1.jar`, `bson-4.2.0.jar`
**UCanAccess jar-ови** (MS-Access): `ucanaccess-5.0.1.jar` + `lib/` директориум

---

## База на податоци

**IBM Informix** пристапена преку `jaydebeapi` (JDBC bridge).

| Параметар | Вредност |
|-----------|---------|
| Host | `192.168.100.120` |
| Port | `5864` |
| Database | `uniqa_live` |
| User | `appuser` |
| Reporting Host | `192.168.100.143:1400` |

### Конфигурација преку env vars

| Env Var | Default | Опис |
|---------|---------|------|
| `IFX_HOST` | `192.168.100.120` | DB host |
| `IFX_PORT` | `5864` | DB port |
| `IFX_DB` | `uniqa_live` | DB name |
| `IFX_USER` | `appuser` | DB user |
| `IFX_PASS` | *(внатрешна вредност)* | DB лозинка |
| `IFX_REPORTING_HOST` | `192.168.100.143` | Reporting server host |
| `IFX_REPORTING_PORT` | `1400` | Reporting server port |
| `SIGLIFE_SECRET_KEY` | `change_this_secret` | Session middleware secret |

### Connection helpers

**Препорачано** — `db_ifx.py` (context manager, auto-close):
```python
from db_ifx import informix_cursor

with informix_cursor() as cur:
    cur.execute("SELECT * FROM polisa WHERE br_polisa = ?", [polisa_id])
    rows = cur.fetchall()
```

**Legacy** — `routers/Connection.py` (се уште го користат постари рутери, треба миграција):
```python
db, ok = Connection.OSISinit()          # cursor + bool
conn, db, ok = Connection.OSISinitConn()  # conn + cursor + bool
conn, db, ok = Connection.OSISinitReporting()  # кон reporting сервер
```

> ⚠️ Рутерите кои уште користат `Connection.py`: `ASO.py`, `aso_router.py`, `aso_reports.py`, `izvestuvanja.py`, `SendMailBroker.py`, `SendMailLog.py`, `SendMailizvestuvanje.py`. Планирана миграција кон `informix_cursor()`.

---

## Автентикација и авторизација

### Session Auth (примарна)
- Имплементација: `auth/auth_repository.py`
- Складирање: табела `polisa_users` во Informix
- Состојба: `request.session["user"]` преку Starlette `SessionMiddleware`
- Лозинка: bcrypt hash преку passlib
- **Auto-миграција:** при логин со стара plaintext лозинка, системот автоматски ја надградува во bcrypt

### JWT Auth (секундарна / API рути)
- Имплементација: `auth/auth_utils.py`
- Алгоритам: HS256, TTL: 8 часа
- Складирање: httponly cookie

### SMTP Конфигурација
- `auth/smtp_config.py` — `load_smtp_config_once()` ги вчитува SMTP параметрите (lazy, singleton)

### Улоги
Дефинирани во `auth/role_utils.py`. Клучни helpers: `normalize_roles()`, `has_any_role()`.

| Улога | Пристап |
|-------|---------|
| `admin` | Сите модули |
| `users_create` | Управување со корисници |
| `aso_reports` | ASO извештаи |
| `provizia` | Модул за провизии |
| `ponuda` | Увоз на понуди |
| `matematicka_rezerva` | Математичка резерва |
| `reo` | REO извештаи |
| `report_udel` | Извештаи за удел |
| `finansii` | Финансиски извештаи |
| `finansiski_izvestai` | Финансиски известувања |
| `finance` | Финансии пакет |
| `izvestuvanja` | Модул за известувања |
| `aml` | AML усогласеност |
| `mesh` | Mesh API интеграција |
| `kolektivno_uu` | Колективно УУ - усогласување на уплати |
| `report_fakturi` | Преглед на фактури |
| `kontrola_polisi` | Контрола на полиси - откуп/капитализација/фактури |
| `promena_premija` | Промена на премија на фактура Колективно |

---

## Мапи на рутери / модули

| Модул | Фајл(ови) | Опис |
|-------|-----------|------|
| Понуди | `routers/ponudi_upload.py` | Excel увоз на понуди за осигурување во Informix |
| Математичка Резерва | `routers/MatematickaRezerva.py` | Пресметка на мат. резерва; извоз во Excel и SOAP XML |
| REO | `routers/REO.py` | Месечни REO извештаи |
| Провизија | `routers/provizija.py` | Провизии — dashboards, multilevel агрегација |
| ASO | `routers/ASO.py`, `routers/aso_router.py`, `routers/aso_reports.py` | Извештаи за осигурување, SI увоз, трансфер кон reporting сервер |
| AML | `routers/AML.py` | Anti-money laundering извоз |
| Финансии | `routers/finansii.py` | Финансиски извештаи и усогласување |
| Известувања | `routers/izvestuvanja.py`, `routers/GeneratePDFIzvestuvanje.py`, `routers/SendMailizvestuvanje.py` | Генерирање PDF известувања за неплатена премија, закажано испраќање |
| Опомени | `routers/GeneratePDFOpomeni.py` | Генерирање PDF опомени |
| Report Удел | `routers/report_udel.py` | Извештаи за удел/учество по датум/договарач |
| Инкасо | `routers/InkasoProvizijaAgent.py`, `InkasoProvizijaBroker.py` | Инкасо и провизии за брокери |
| Корисници | `routers/users_router.py` | Управување со корисници (create/list/update), привремени лозинки |
| SendMail | `routers/SendMail.py` | SMTP конфигурација и email helpers |
| SendMailBroker | `routers/SendMailBroker.py` | Email до брокери со шифриран Excel attachment |
| SendMailLog | `routers/SendMailLog.py` | Лог на испратени email-ови |
| SMS | `routers/SMS.py` | Роденденски SMS и SMS за промена на име |
| SchedulerBackUp | `routers/SchedulerBackUp.py` | Закажани backup jobs за Книжи ПО/КО |
| Mesh | `routers/mesh_router.py` | Интеграција со надворешен Mesh compliance API |
| Fund Update | `routers/update_fund_data_soap.py` | Синхронизација на фондови преку SOAP |
| Connection | `routers/Connection.py` | Legacy DB helpers (предност: `db_ifx.py`) |
| Колективно УУ | `routers/kolektivno_uu.py` | Усогласување на уплати и затворање на полиси со салдо нула |
| Преглед на фактури | `routers/report_fakturi.py` | Преглед на фактури по полиса/фактура/ред, извоз, затворање |
| Контрола на полиси | `routers/kontrola_polisi.py` | Валидациски проверки: салдо кај капитализирани полиси, недостасувачки фактури кај обновени/активни полиси, пренаплата |

---

## Закажани задачи (APScheduler)

Сите jobs се регистрираат во `main.py` при startup.

| Job ID | Распоред | Функција | Опис |
|--------|----------|----------|------|
| `birthday_sms` | Дневно 11:00 | `scheduled_prebSMSRodenden` | Роденденски SMS до клиенти |
| `scheduled_fund_update` | Дневно 18:35 | `scheduled_fund_update` | Синх. на фондови преку SOAP |
| `SendMailIzvestuvanje_morning` | Дневно 09:10 | `sendMailIzvestuvanje` | Утринско испраќање на известувања |
| `SendMailIzvestuvanje_afternoon` | Дневно 16:00 | `sendMailIzvestuvanje` | Попладневно испраќање на известувања |
| `scheduled_knizi_po` | Дневно 18:00 | `scheduled_knizi_PO` | Backup Книжи ПО |
| `scheduled_knizi_ko` | Дневно 20:30 | `scheduled_knizi_KO` | Backup Книжи КО |
| `sync_dolzna_premija` | Дневно 07:12 | `sync_dolzna_premija` | SFTP синх. на должна премија кон Server B |
| `iute_claim_notification` | На секои 10 мин *(планирано)* | `check_new_claims` | Email известување за нова штета од Иуте |
| `sms_dospeana_premija` | Дневно 10:00 (реален SMS само на 17-ти/најблиски работен ден) | `scheduled_prebSMSDospeanaPremija` | SMS за доспеана премија — Тип А |

---

## SMS известувања за доспеана премија

### Тип А — сите клиенти освен банка и Иуте (40/)

**Статус: имплементирано, во TEST РЕЖИМ** (`routers/SMS.py::prebSMSDospeanaPremija`, `main.py` job `sms_dospeana_premija`).

- **Кога:** job се пушта дневно во 10:00, но реално испраќа само кога денешниот датум е таргет-денот пресметан во `_dospeana_premija_target_day()` — 17-ти во месецот, или најблискиот понеделник ако 17-ти е сабота/недела. (Само weekend-shift, не и државни празници.)
- **Порака:** `Pocituvani, Ve izvestuvame deka premijata za polisa {polisa} vo iznos od {iznos} EUR e dospeana. Uplata moze da izvrsite I preku nasata web strana. Vi blagodarime`
- **Извор на податоци:** нов SQL во `prebSMSDospeanaPremija()` (CTE `base`/`naplata`, ист паттерн како `izvestuvanja.py`) — баланс `iznos - naplata` по `os_aneks_faktura`/`fin_stavka`/`os_polisa`/`os_ponuda`, групирано **по полиса** (една SMS по полиса, не збирно по клиент). Исклучува:
  - канал банка (`os_ponuda.par_prod_kanalid = 62`)
  - Иуте полиси (префикс `40/` на `polisa_broj_cel`)
  - само физички лица (`par_client.client_tip_pf = 'F'`) — **претпоставка**, конзистентно со останатите SMS функции
  - само EUR износи (шаблонот на пораката е EUR-специфичен) — **не е валидирано со база**
- **Dedup:** по `job_id = DPP_{polisa_broj}_{YYYYMM}` во `sms_audit_log` — една полиса добива најмногу 1 SMS месечно (не по телефон, бидејќи клиент може да има повеќе доспеани полиси истовремено).
- **Test режим:** `SMS_DOSPEANA_TEST_MODE` env var (default `true`) — реалната SMS се праќа до `SMS_DOSPEANA_TEST_PHONE` (env var), но во `sms_audit_log.recipient` се запишува РЕАЛНИОТ телефон на клиентот (за преглед на кој ЌЕ добие порака кога ќе се исклучи test режимот). За да се пушти во продукција: `SMS_DOSPEANA_TEST_MODE=false`.

### Тип Б — банкарски клиенти со долг ("Ризико кредит")

**Статус: во план, не е имплементирано.** Чека бизнис-потврда за точна дефиниција на "Ризико кредит" банкарска полиса (производ/канал/комбинација) — нема постоечка логика во кодот за овој конкретен производ (само генерички `banka_par_client`/канал=62).

- **Кога:** на самиот ден на доспевање, само ако клиентот има долг.
- **Порака:** `Pocituvani, Ve potsetuvame deka imate dospeani obvrski po polisa Riziko kredit, i potrebno e istite da gi podmirite vo tekot na denot. Vi blagodarime`

---

## Интеграции со надворешни системи

### Иуте — Пријави на штета
- Штетите пристигаат во табелата `polisa_claim` во Informix
- Клучни колони: `gacclaimid`, `policynumber`, `claimdate`, `ctype`, `claimdescription`, `beneficiary_*`, `date_insert`, `claim_status`
- **Планирано:** APScheduler job (`check_new_claims`) на секои 10 минути за детекција на нови записи и email известување до одговорните лица

### Mesh API
- `services/mesh_service.py` — `get_client_info()`, `customers()`
- Router: `routers/mesh_router.py`
- Улога: `mesh`

### SFTP Синхронизација (Server B)
- `services/sync_dolzna_premija.py` — paramiko SFTP
- Дневно 07:12 — пренос на датотека за должна премија

### SOAP (Фондови)
- `routers/update_fund_data_soap.py`
- Дневно 18:35 — синхронизација на податоци за фондови

---

## Контрола на полиси (`routers/kontrola_polisi.py`)

Валидациски проверки за откривање на несогласувања во полисите. Пристап преку улога `admin`/`kontrola_polisi`, страница `/kontrola-polisi` (форма со влезна година + 4 таба со резултати). Секоја проверка се извршува независно (грешка во една не ги рушат другите) и рутата е **синхрона** `def` (не `async def`) за FastAPI да ја пушти во threadpool — inline блокирачки JDBC повици во `async def` рута го замрзнуваат целиот event loop (цел сервер), не само тековното барање.

**Клучни поими:**
- Статус на полиса се зема секогаш од **последната понуда** — `o.ponuda_podbroj = maxpodbroj_datum(o.ponuda_broj, p.polisa_broj, o.os_produktid, TODAY)`. Наивен join преку `os_polisa.os_ponudaid` може да покаже застарен статус.
- `os_ponuda.par_statusid`: `17`/`18` = активна/склучена, `18` = капитализирана, `20`/`21` = откуп, `42` = раскината/сторнирана.
- Наплата по фактура се зема преку UDF `vrati_naplata(os_aneks_fakturaid)` (иста логика како `sql/zatvori_izvod.sql`) — **не** преку рачен join на `fin_stavka`, бидејќи тоа погрешно ја смета наплатата кај сторнирани/негативни фактури.
- Еднократна премија: `os_ponuda.os_produkt_uplataid → os_produkt_uplata.par_nacin_platiid = 75` (шифра `005` во `par_nacin_plati`). Не се join-ва директна колона на `os_ponuda`.
- Намерно НЕ се користат `vesna.report_fakturi` и `vw_pregled2` (тешки views) — предизвикувале 504 timeout; наместо тоа директни join-ови на `os_aneks_faktura`/`os_aneks`/`os_polisa`/`os_ponuda`.
- Informix `GROUP BY` не поддржува повторување на UDF израз (`vrati_godina(...)`) — се користат позициони броеви (`GROUP BY 1,2,3,4`).

**Проверки:**

| # | Наслов | Логика |
|---|--------|--------|
| 1 | Капитализирани — салдо ≠ 0 | За полиси чија максимална понуда (по `polisa_broj_cel`, не по конкретен `os_polisaid`) е `par_statusid=18`: `SUM(iznos) - SUM(vrati_naplata(...))` собрано преку **сите** `os_polisaid` записи со тој `polisa_broj_cel` (заради историски замени/капитализации), при што секоја фактура мора да има `fin_stavka` ред со `iznos_d IS NOT NULL` и `f_rs <> 'N'` (исто како во "Преглед на фактури") — треба да е `0` (заокружено на 2 децимали); инаку прекршување |
| 2 | Полиси — недостасуваат фактури | По анекс/година: `COUNT(fakturi generirani) < br_rati` (очекуван број рати); исклучени раскинати (`42`) и капитализирани (`18`), и исклучени полиси со префикс `19/` |
| 3 | Активни — недостасуваат фактури | Исто како #2, но само за `par_statusid IN (17,18)`, исклучени полиси со еднократна премија (`par_nacin_platiid=75`) и полиси со префикс `19/`. Не филтрира по `data_faktura < TODAY` — фактурите се генерираат однапред за целата година, па тој услов лажно ги прикажувал веќе-генерираните идни рати како "недостасуваат" |
| 4 | Наплата > износ | На ниво на **фактура** (aneks/година-рата), не по одделен `os_aneks_fakturaid` ред: `SUM(vrati_naplata(...)) > SUM(iznos)` групирано по фактура — истата фактура може да има повеќе `os_aneks_faktura` записи (оригинал + сторно/корекција), па per-ред споредбата лажно пријавувала нарушување |

---

## Utility модули

| Фајл | Клучни функции | Опис |
|------|----------------|------|
| `Utils/excel_formatter.py` | `format_provision_excel()`, `process_broker_excel()` | Excel форматирање |
| `services/pdf_service.py` | wraps `SendMailAgent.gen_pdf()` | Влезна точка за PDF генерирање |
| `services/SendMailAgent.py` | `gen_pdf()` | PDF генерирање, email со attachments |
| `services/sync_dolzna_premija.py` | `sync_dolzna_premija()` | SFTP синх. до remote сервер |
| `services/mesh_service.py` | `get_client_info()`, `customers()` | Mesh compliance API клиент |
| `auth/models_auth.py` | `UserLogin`, `UserCreate`, `UserOut`, `TokenData` | Pydantic auth модели |
| `auth/smtp_config.py` | `load_smtp_config_once()` | Lazy singleton за SMTP конфиг |

---

## PDF Генерирање

Два типа документи, секој во посебен модул:

| Тип | Фајл | Клучна функција | Date parsing |
|-----|------|-----------------|--------------|
| Известување | `routers/GeneratePDFIzvestuvanje.py` | `generate_pdf()` | `_parse_date()` — поддржува date object, string, повеќе формати |
| Опомена | `routers/GeneratePDFOpomeni.py` | `generate_pdf()` | `_parse_date()` — поддржува date object, string, повеќе формати |

**Font фајлови:** `routers/DejaVuSans.ttf`, `DejaVuSans-Bold.ttf`, `DejaVuSans-Oblique.ttf`
**Background image (Linux):** `/opt/siglife-reporting/Image/UNIQA_MEMO1.png`

---

## Клучни паттерни

**Route со заштита на улога:**
```python
from auth.role_utils import has_any_role

@router.get("/some-page")
async def some_page(request: Request):
    if not has_any_role(request, ["admin", "provizia"]):
        raise HTTPException(status_code=403)
```

**DB query (препорачано):**
```python
from db_ifx import informix_cursor

with informix_cursor() as cur:
    cur.execute("SELECT * FROM polisa WHERE br_polisa = ?", [polisa_id])
    rows = cur.fetchall()
```

**Scheduler job (interval):**
```python
scheduler.add_job(
    my_function,
    trigger='interval',
    minutes=10,
    id='my_job_id',
    max_instances=1,
    coalesce=True
)
```

---

## Структура на фајлови

```
siglife-reporting/
├── main.py                        # App влез, scheduler, login/logout рути
├── db_ifx.py                      # Informix JDBC конекција (informix_cursor, Informixdriver)
├── auth/
│   ├── auth_repository.py         # DB CRUD за корисници (polisa_users)
│   ├── auth_utils.py              # JWT, bcrypt hash/verify
│   ├── role_utils.py              # normalize_roles(), has_any_role()
│   ├── smtp_config.py             # Lazy SMTP конфигурација
│   └── models_auth.py             # Pydantic модели: UserLogin, UserCreate, UserOut
├── routers/
│   ├── Connection.py              # Legacy DB helpers
│   ├── izvestuvanja.py            # Известувања за неплатена премија (главен рuter)
│   ├── GeneratePDFIzvestuvanje.py # PDF генерирање — известувања
│   ├── GeneratePDFOpomeni.py      # PDF генерирање — опомени
│   ├── SendMailizvestuvanje.py    # Закажано испраќање на известувања
│   ├── SendMailBroker.py          # Email до брокери
│   ├── SendMailLog.py             # Лог на email
│   ├── SendMail.py                # SMTP helpers
│   ├── SMS.py                     # SMS (роденден, промена на име)
│   ├── ASO.py                     # ASO извештаи
│   ├── aso_router.py              # ASO router (трансфер, SI)
│   ├── aso_reports.py             # ASO stat извештаи
│   ├── MatematickaRezerva.py      # Математичка резерва
│   ├── REO.py                     # REO извештаи
│   ├── AML.py                     # AML compliance
│   ├── finansii.py                # Финансиски извештаи
│   ├── provizija.py               # Провизии
│   ├── report_udel.py             # Извештаи за удел
│   ├── ponudi_upload.py           # Excel увоз на понуди
│   ├── InkasoProvizijaAgent.py    # Инкасо агент провизии
│   ├── users_router.py            # Управување со корисници
│   ├── mesh_router.py             # Mesh API
│   ├── SchedulerBackUp.py         # Backup jobs
│   ├── update_fund_data_soap.py   # SOAP фонд синх.
│   ├── kolektivno_uu.py           # Усогласување на уплати / затворање со салдо нула
│   ├── report_fakturi.py          # Преглед на фактури
│   └── kontrola_polisi.py         # Контрола на полиси (капитализација/откуп/фактури)
├── services/
│   ├── pdf_service.py             # PDF генерирање (wrapper)
│   ├── SendMailAgent.py           # Email со PDF attachment
│   ├── sync_dolzna_premija.py     # SFTP синх.
│   └── mesh_service.py            # Mesh API клиент
├── Utils/
│   └── excel_formatter.py         # Excel форматирање helpers
├── templates/                     # Jinja2 HTML шаблони
├── static/                        # CSS, JS, слики
├── Image/                         # Брендирање (логоа, memo слики)
├── data/                          # JSON конфиг за финансиски шаблони
├── uploads/                       # Прикачени фајлови (runtime)
└── requrements.txt                # Python зависности (typo во името — намерно)
```

---

## Безбедност — применети поправки

| # | Проблем | Решение | Фајл |
|---|---------|---------|------|
| 1 | Plaintext лозинки при логин | bcrypt верификација + auto-миграција | `main.py` |
| 2 | Hardcoded credentials | env vars (`IFX_PASS`, `IFX_HOST`...) | `Connection.py`, `db_ifx.py` |
| 3 | DB connection leak во auth | Мигрирано на `informix_cursor()` context manager | `auth/auth_repository.py` |
| 4 | DEBUG prints при секоја DB конекција | Отстранети | `db_ifx.py` |
| 5 | Scheduler crossproduct (4 jobs наместо 2) | Два одделни `add_job()` | `main.py` |
| 6 | PDF crash со Informix date object | `_parse_date()` helper | `GeneratePDFOpomeni.py` |
