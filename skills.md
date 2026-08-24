# SigLife Reporting — Skills

## Project purpose
FastAPI-based интерен reporting/известување систем за СИГАЛ Лајф (UNIQA Life). Целосна техничка документација е во `CLAUDE.md` — овој фајл е кус потсетник за конвенции при работа.

## Main architecture
- Entry point: `main.py` (root app + scheduler; sub-app `/siglife-report` со сите рути)
- Routes: `routers/`
- Templates: `templates/` (Jinja2, `base.html` е layout со sidebar)
- Static files: `static/`
- Auth: `auth/` (session-based, `has_any_role()` за заштита на рути)
- DB access: `db_ifx.py` (`informix_cursor()`, препорачано) / `routers/Connection.py` (legacy, `OSISinit()` / `OSISinitConn()`)
- Utilities: `Utils/`, `services/`

## Working conventions
- Секој нов router: заштита преку `_require_role()` / `has_any_role()`, ист паттерн како постоечките (`report_fakturi.py`, `kolektivno_uu.py`, `kontrola_polisi.py`).
- Нов router → регистрирај во `main.py` (import + `include_router`) и додај линк во `templates/base.html` sidebar-от, гејтирано со соодветна улога.
- Пиши бизнис/финансиски пресметки (наплата, салдо) преку `vesna.vrati_naplata()` UDF, **не** преку рачен `fin_stavka` join — рачниот join погрешно ја смета наплатата кај сторнирани/негативни фактури.
- Кога агрегираш "по полиса", земи предвид дека иста `polisa_broj_cel` може да има повеќе `os_polisaid` записи (историски замени/капитализации) — собирај преку сите, не само преку тековниот.
- Секоја фактура во финансиски пресметки мора да има поврзан `fin_stavka` ред со `iznos_d IS NOT NULL` и `f_rs <> 'N'` за да се смета за важечка (исто како во `report_fakturi.py` `_BASE_FROM`).
- Датумски string-парametri кон Informix: `DBDATE=MDY` (mm/dd/yyyy) — види `db_ifx.py` коментари / претходни memory белешки.
- Informix `GROUP BY` не поддржува повторување на UDF израз — користи позициони броеви (`GROUP BY 1, 3` итн.).
- Секоја рута што прави блокирачки JDBC повици мора да е синхрона `def` (не `async def`), за FastAPI да ја пушти во threadpool.

## Common development workflow
1. `pip install -r requrements.txt` (намерен typo во името).
2. `uvicorn main:app --reload` од root на проектот.
3. Провери дека JDBC jar-овите постојат (`C:\SigLifeReporting_Informix\` на Windows).
4. Тестирај ја погодената рута/страница во браузер.
5. `python -m py_compile <фајл>` пред commit, за брза синтаксна проверка.

## Helpful reminders
- Не пишувај коментари што го објаснуваат ШТО прави кодот — само зошто (non-obvious constraint/workaround).
- Финансиски UPDATE-и (пример: `routers/promena_premija.py`) — секогаш со лог во текстуален фајл за audit trail (пример `promena_premija_log.txt`).
- Пред да менуваш проверка во `kontrola_polisi.py`, спореди со истата логика во `report_fakturi.py` — двете мора да се согласуваат за истите бизнис-концепти (наплата, салдо).
- Следи ја структурата на постоечки слични рутери/темплејти наместо да воведуваш нов паттерн.
