drop FUNCTION appuser.fin_uu_kolektivno;
CREATE FUNCTION appuser.fin_uu_kolektivno(
    p_session_key  CHAR(20),
    p_datum        DATE,
    p_user_id      INT
) RETURNING INTEGER, CHAR(200), INT;

DEFINE v_os_aneksid          INT8;
DEFINE v_os_fakturaid        INT8;
DEFINE v_iznos               DECIMAL(20,2);
DEFINE v_iznos_den           DECIMAL(20,2);
DEFINE v_naplata_item        DECIMAL(20,2);
DEFINE v_par_clientid        INT;
DEFINE v_os_ponudaid         INT;
DEFINE v_par_valutaid        INT;
DEFINE v_vk_iznos            DECIMAL(20,2);
DEFINE v_vk_naplata          DECIMAL(20,2);
DEFINE v_vk_saldo            DECIMAL(20,2);
DEFINE v_br_stavki           INT;
DEFINE v_dali_postoi         INT;
DEFINE v_next_seq            INT;
DEFINE v_godina              CHAR(4);
DEFINE v_FIN_IZVOD_HID       INT;
DEFINE v_rbr                 INT;
DEFINE v_par_tip_dokumentid  INT;
DEFINE v_par_vid_izvodid     INT;
DEFINE v_polisa_broj         VARCHAR(20);
DEFINE tvaluta               VARCHAR(3);
DEFINE tos_produktid         INT;
DEFINE v_broj_izvod          VARCHAR(40);
DEFINE esql, eisam ,tsifra_zatvaranje          INT;
DEFINE esql_msg              VARCHAR(200);
DEFINE v_par_tip_kniziid     INT;
define tfin_izvod_iid,sid int8;
define tusername char(30);

ON EXCEPTION SET esql, eisam, esql_msg
    RETURN -1, 'SQL грешка [' || esql || ']: ' || NVL(esql_msg, '(без порака)'), 0;
END EXCEPTION;

--SET DEBUG FILE TO 'err_fin_uu_kolektivno.log';
--TRACE ON;

-- ── 0. Провери дали постои worklist за овој session ───────────────
SELECT COUNT(*) INTO v_br_stavki
FROM   fin_uu_worklist
WHERE  session_key = p_session_key;

IF v_br_stavki = 0 THEN
    RETURN -1, 'Нема избрани ставки за session: ' || p_session_key, 0;
END IF;

-- ── 1. УУ тип во par_vid_izvod ────────────────────────────────────
SELECT par_vid_izvodid INTO v_par_vid_izvodid
FROM   par_vid_izvod
WHERE  UPPER(TRIM(par_vid_izvod)) = 'УУ'
    OR UPPER(TRIM(par_vid_izvod)) = 'UU';

IF v_par_vid_izvodid IS NULL THEN
    RETURN -1, 'Не е пронајден   тип УУ во par_vid_izvod', 0;
END IF;

select username into tusername from adm_user
where userid=p_user_id;

-- ── 2. Полиса број ────────────────────────────────────────────────
SELECT FIRST 1 pol.polisa_broj_cel INTO v_polisa_broj
FROM   fin_uu_worklist       wl,
       viki.os_aneks_faktura f,
       viki.os_aneks         a,
       viki.os_polisa        pol
WHERE  wl.session_key        = p_session_key
  AND  f.os_aneks_fakturaid  = wl.os_aneks_fakturaid
  AND  a.os_aneksid          = f.os_aneksid
  AND  pol.os_polisaid       = a.os_polisaid;

-- ── 3. Верификација: SUM(iznos) и SUM(naplata) одделно ───────────
SELECT COUNT(*), SUM(NVL(f.iznos, 0))
INTO   v_br_stavki, v_vk_iznos
FROM   fin_uu_worklist       wl,
       viki.os_aneks_faktura f
WHERE  wl.session_key       = p_session_key
  AND  f.os_aneks_fakturaid = wl.os_aneks_fakturaid
  AND  NVL(f.f_rs, 'R')   <> 'N';

SELECT NVL(SUM(NVL(fs.iznos_p, 0)), 0) INTO v_vk_naplata
FROM   fin_uu_worklist wl,
       fin_stavka      fs
WHERE  wl.session_key        = p_session_key
  AND  fs.os_aneks_fakturaid = wl.os_aneks_fakturaid
  AND  fs.sifra_zatvaranje  IS NOT NULL
  AND  fs.f_rs              <> 'N';

LET v_vk_saldo = NVL(v_vk_iznos, 0) - NVL(v_vk_naplata, 0);

IF v_br_stavki < 2 THEN
    RETURN -1, 'Нема доволно ставки: ' || v_br_stavki, 0;
END IF;

IF ABS(v_vk_saldo) > 0.01 THEN
    RETURN -1, 'Салдото не е нула. Вкупно: ' || v_vk_saldo, 0;
END IF;

-- ── 4. Следен сериски број за годината (УУ-YYYY-NNNNN) ──────────
LET v_godina = TO_CHAR(p_datum, '%Y');

SELECT max(broj_izvod) INTO v_next_seq
FROM   fin_izvod_h
WHERE  par_vid_izvodid = v_par_vid_izvodid
  AND  datum >= MDY(1, 1, YEAR(p_datum))
  AND  datum <  MDY(1, 1, YEAR(p_datum) + 1);

LET v_next_seq = v_next_seq + 1;

let v_broj_izvod=v_next_seq;

-- ── 5. Тип документ ──────────────────────────────────────────────
SELECT par_tip_dokumentid INTO v_par_tip_dokumentid
FROM   par_tip_dokument
WHERE  par_tip_dokument = 'PREM';

-- ── 6. fin_izvod_h — најди постоечки со <200 ставки или создај нов ─
LET v_FIN_IZVOD_HID = 0;

FOREACH SELECT fin_izvod_hid
    INTO v_FIN_IZVOD_HID
    FROM fin_izvod_h
    WHERE par_vid_izvodid = v_par_vid_izvodid
      AND datum           = p_datum
    ORDER BY fin_izvod_hid DESC

    SELECT COUNT(1) INTO v_br_stavki
    FROM fin_izvod_i
    WHERE fin_izvod_hid = v_FIN_IZVOD_HID;

    IF v_br_stavki < 200 THEN
        EXIT FOREACH;
    END IF;

    LET v_FIN_IZVOD_HID = 0;
END FOREACH;

IF v_FIN_IZVOD_HID = 0 THEN
    LET v_FIN_IZVOD_HID = sq_fin_izvod_h.nextval;
    INSERT INTO fin_izvod_h (
        fin_izvod_hid, datecreated, usercreated, version,
        par_vid_izvodid, broj_izvod, datum, par_statusid
    ) VALUES (
        v_FIN_IZVOD_HID, TODAY, p_user_id, 0,
        v_par_vid_izvodid, v_broj_izvod, p_datum, 1
    );
END IF;

-- ── 7. fin_izvod_i — еден ред по faktura ─────────────────────────
--    os_aneksid = os_aneks_rataid (PK на os_aneks_faktura, per view)
--    iznos_naplata = iznos - naplata (отворено салдо)
-- ─────────────────────────────────────────────────────────────────
SELECT NVL(MAX(rbr), 0) INTO v_rbr
FROM fin_izvod_i
WHERE fin_izvod_hid = v_FIN_IZVOD_HID;

FOREACH
    SELECT f.os_aneks_rataid,
           f.os_aneks_fakturaid,
           a.par_clientid,
           NVL(f.iznos, 0),
           op.os_ponudaid
    INTO   v_os_aneksid,
           v_os_fakturaid,
           v_par_clientid,
           v_iznos,
           v_os_ponudaid
    FROM   fin_uu_worklist       wl,
           viki.os_aneks_faktura f,
           viki.os_aneks         a,
           viki.os_polisa        pol,
           viki.os_ponuda        op
    WHERE  wl.session_key       = p_session_key
      AND  f.os_aneks_fakturaid = wl.os_aneks_fakturaid
      AND  NVL(f.f_rs, 'R')   <> 'N'
      AND  a.os_aneksid         = f.os_aneksid
      AND  pol.os_polisaid      = a.os_polisaid
      AND  op.os_ponudaid       = pol.os_ponudaid
    ORDER  BY f.data_faktura, f.os_aneks_fakturaid

    -- Нaplata за оваа специфична faktura
    SELECT NVL(SUM(NVL(iznos_p, 0)), 0) INTO v_naplata_item
    FROM   fin_stavka
    WHERE  os_aneks_fakturaid = v_os_fakturaid
      AND  sifra_zatvaranje  IS NOT NULL
      AND  f_rs              <> 'N';


  LET v_par_tip_kniziid = NULL;
    SELECT FIRST 1 par_tip_kniziid INTO v_par_tip_kniziid
    FROM   fin_stavka
    WHERE  os_aneks_fakturaid = v_os_fakturaid
      
      AND  f_rs              <> 'N';
    LET v_iznos = v_iznos - NVL(v_naplata_item, 0);

    -- Пропусти ставки со нулто отворено салдо
    IF ABS(v_iznos) <= 0.005 THEN
        CONTINUE FOREACH;
    END IF;

    -- Валута
    SELECT NVL(par_valutaid, 0), os_produktid
    INTO   v_par_valutaid, tos_produktid
    FROM   os_ponuda
    WHERE  os_ponudaid = v_os_ponudaid;

    IF v_par_valutaid = 0 THEN
        SELECT NVL(par_valutaid, 0) INTO v_par_valutaid
        FROM   os_produkt
        WHERE  os_produktid = tos_produktid;
    END IF;

    SELECT valuta INTO tvaluta
    FROM   par_valuta
    WHERE  par_valutaid = v_par_valutaid;

    EXECUTE PROCEDURE konverzija(p_datum, v_iznos, tvaluta, 'MKD')
    INTO v_iznos_den;

    LET v_rbr = v_rbr + 1;
    LET tfin_izvod_iid=sq_fin_izvod_iid.nextval;
    INSERT INTO fin_izvod_i (
        fin_izvod_iid, datecreated, usercreated, version,
        fin_izvod_hid, rbr, pat_tip_dokumentid,par_tip_kniziid,
        par_clientid, iznos_naplata, iznos_naplata_den,
        par_statusid, par_valutaid, os_aneksid,desc
    ) VALUES (
        tfin_izvod_iid, TODAY, p_user_id, 0,
        v_FIN_IZVOD_HID, v_rbr, v_par_tip_dokumentid,v_par_tip_kniziid,
        v_par_clientid, v_iznos, v_iznos_den,
        1, v_par_valutaid, v_os_aneksid,'UU'
    );
    update izvod_broevi set broj=broj+1;
    select broj into tsifra_zatvaranje from izvod_broevi;
    let sid=sq_fin_stavka.nextval;	

insert into fin_stavka (fin_stavkaid, datecreated, usercreated, version, par_filijalaid,
    par_tip_dokumentid, par_tip_kniziid, par_clientid, os_aneks_fakturaid,
    par_yearid, datum, datum_stavka,datum_fakt_valuta, par_valutaid,
    par_kursid, os_polisaid,par_agent_id, fin_izvod_iid, pat_tip_platiid,
    sifra_zatvaranje, grupa_fin_stavkaid, f_rs,
    iznos_p,   iznos_p_den,  par_statusid)
  select sid,current, tusername,0, par_filijalaid,
   par_tip_dokumentid, par_tip_kniziid, par_clientid, os_aneks_fakturaid,
   par_yearid,p_datum, p_datum,p_datum,par_valutaid,
   par_kursid,os_polisaid, par_agent_id,tfin_izvod_iid,pat_tip_platiid,
   tsifra_zatvaranje ,fin_stavkaid, 'R',v_iznos, v_iznos_den, 1
   from fin_stavka 
   where os_aneks_fakturaid=v_os_fakturaid and iznos_d is not null;

END FOREACH;

-- ── 8. Проверка ───────────────────────────────────────────────────
IF v_rbr = 0 THEN
    DELETE FROM fin_izvod_h WHERE fin_izvod_hid = v_FIN_IZVOD_HID;
    RETURN -1, 'Нема ставки за вметнување', 0;
END IF;

RETURN 1,
       'УУ документот е креиран: ' || v_broj_izvod
       || ' (' || v_rbr || ' ставки)',
       v_FIN_IZVOD_HID;

END FUNCTION;