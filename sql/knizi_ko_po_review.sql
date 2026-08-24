-- Reviewed copy of vesna.knizi_ko_po supplied on 2026-08-10.
-- This file is NOT executed against the database.
--
-- Review findings:
-- 1. fin_stavka.f_ko_po is set before pom_knizi_izvod is called.
-- 2. terr1/terr2/terr3/terr4 returned by pom_knizi_izvod are not checked.
-- 3. COMMIT and a success message are issued regardless of those return values.
-- 4. This function defines tip_knizenje 0 as KO and 1 as PO; callers must match it.
-- 5. Date validation uses AND instead of OR and does not validate tdatum_nalog.
-- 6. A header can be committed when no detail rows were selected (trb = 0).
-- 7. Verify whether the fin_izvod_i column is intentionally named pat_tip_dokumentid.

CREATE FUNCTION vesna.knizi_ko_po(
    vfin_stavkaid CHAR(1000),
    tod_datum CHAR(10),
    tdo_datum CHAR(10),
    tdatum_nalog CHAR(10),
    tip_knizenje CHAR(1),
    tuser_id INT
)
RETURNING INTEGER, CHAR(100);

DEFINE _f_nalog, _klasa_nalvid CHAR(2);
DEFINE tiznos_naplata_den, tiznos_naplata, tiznos_ko, tiznos_popust DECIMAL;
DEFINE _os_ponudaid, tos_aneks_fakturaid, tfin_izvod_hid, i INTEGER;
DEFINE tpar_vid_izvod, terr2 CHAR(4);
DEFINE v_datum DATE;
DEFINE v_premija DECIMAL;
DEFINE v_kolku, kolku_nalog, haha INTEGER;
DEFINE _err_msg, terr4 CHAR(100);
DEFINE _godina, tgodina, _nal_vid, tnal_vid CHAR(4);
DEFINE _dolzina, trb, m, tfin_stavkaid, toperator,
       _par_tip_kniziid, _par_valutaid, tbroj_izvod INT;
DEFINE tsfin_stavkaid CHAR(10);
DEFINE tpar_vid_izvodid, tpar_clientid, tpar_tip_kniziid,
       tpar_tip_dokumentid INT;
DEFINE tusername, tfaktura_broj CHAR(30);
DEFINE _edinica, _edinicamg CHAR(2);
DEFINE tos_aneksid INT8;
DEFINE terr1 CHAR(2);
DEFINE terr3 INTEGER;

ON EXCEPTION
    ROLLBACK WORK;
    RETURN -1, 'GRE[KA';
END EXCEPTION;

BEGIN WORK;

IF tod_datum IS NULL AND tdo_datum IS NULL THEN
    RETURN 1, 'NEKOJ VLEZEN PARAMETAR E NULL';
END IF;

BEGIN
    ON EXCEPTION IN (-206)
        CREATE TEMP TABLE tmp_knizi_polisa (
            fin_stavkaid INT,
            oznaka CHAR(1)
        );
        CREATE UNIQUE INDEX uix_tmp_knizi
            ON tmp_knizi_polisa(fin_stavkaid);
    END EXCEPTION

    DELETE FROM tmp_knizi_polisa;
END

LET _dolzina = LENGTH(TRIM(vfin_stavkaid));
LET i = 1;

WHILE i <= _dolzina
    EXECUTE FUNCTION locate(vfin_stavkaid, ';') INTO m;

    IF m = 0 THEN
        LET tsfin_stavkaid = SUBSTRING(vfin_stavkaid FROM 1 FOR _dolzina);
    ELSE
        LET tsfin_stavkaid = SUBSTRING(vfin_stavkaid FROM 1 FOR m - 1);
    END IF;

    SELECT (tsfin_stavkaid::NUMERIC)
      INTO tfin_stavkaid
      FROM sysdual;

    INSERT INTO tmp_knizi_polisa VALUES (tfin_stavkaid, '1');
    LET vfin_stavkaid = SUBSTRING(vfin_stavkaid FROM m + 1 FOR _dolzina);

    IF m = 0 THEN
        LET i = _dolzina + 1;
    ELSE
        LET i = i + m - 1;
    END IF;
END WHILE;

SELECT COUNT(*) INTO haha FROM tmp_knizi_polisa;

LET toperator = tuser_id;
SELECT username
  INTO tusername
  FROM adm_user
 WHERE userid = tuser_id;

LET _err_msg = '';

IF tip_knizenje = 0 THEN
    LET tpar_vid_izvod = 'КО';
ELSE
    LET tpar_vid_izvod = 'ПО';
END IF;

SELECT kn_edinica, NVL(kn_edinica_mg, kn_edinica)
  INTO _edinica, _edinicamg
  FROM org_company;

IF YEAR(tdatum_nalog) = YEAR(TODAY) THEN
    LET _edinica = _edinica;
ELSE
    LET _edinica = _edinicamg;
END IF;

SELECT par_vid_izvodid
  INTO tpar_vid_izvodid
  FROM par_vid_izvod
 WHERE par_vid_izvod = tpar_vid_izvod;

SELECT MAX(broj_izvod) + 1
  INTO tbroj_izvod
  FROM fin_izvod_h
 WHERE par_vid_izvodid = tpar_vid_izvodid
   AND YEAR(datum) = YEAR(tdatum_nalog);

IF tbroj_izvod IS NULL THEN
    LET tbroj_izvod = 1;
END IF;

LET tfin_izvod_hid = sq_fin_izvod_h.nextval;

INSERT INTO 'viki'.fin_izvod_h (
    fin_izvod_hid, datecreated, usercreated, version,
    par_vid_izvodid, broj_izvod, datum, par_statusid
) VALUES (
    tfin_izvod_hid, CURRENT, tusername, 0,
    tpar_vid_izvodid, tbroj_izvod, tdatum_nalog, 1
);

LET trb = 0;

FOREACH
    SELECT q.par_clientid, f.fin_stavkaid, faktura_broj,
           par_tip_kniziid, par_tip_dokumentid, iznos_ko, iznos_popust
      INTO tpar_clientid, tfin_stavkaid, tfaktura_broj,
           tpar_tip_kniziid, tpar_tip_dokumentid, tiznos_ko, tiznos_popust
      FROM knizenje_po f, tmp_knizi_polisa t, fin_stavka q
     WHERE f.fin_stavkaid = t.fin_stavkaid
       AND q.fin_stavkaid = t.fin_stavkaid

    SELECT FIRST 1 os_aneksid
      INTO tos_aneksid
      FROM izvod_aneks
     WHERE os_aneks = TRIM(tfaktura_broj);

    IF tip_knizenje = 0 THEN
        LET tiznos_naplata = tiznos_ko;
    ELSE
        LET tiznos_naplata = tiznos_popust;
    END IF;

    LET tiznos_naplata_den =
        konverzija(tdatum_nalog, tiznos_naplata, 'EUR', 'MKD');
    LET trb = trb + 1;

    INSERT INTO fin_izvod_i (
        fin_izvod_iid, datecreated, usercreated, version,
        fin_izvod_hid, rbr, par_clientid, os_aneksid,
        iznos_naplata, iznos_naplata_den, par_statusid, par_valutaid,
        par_tip_kniziid, pat_tip_dokumentid
    ) VALUES (
        sq_fin_izvod_iid.nextval, CURRENT, tusername, 0,
        tfin_izvod_hid, trb, tpar_clientid, tos_aneksid,
        tiznos_naplata, tiznos_naplata_den, 1, 1,
        tpar_tip_kniziid, tpar_tip_dokumentid
    );

    UPDATE fin_stavka
       SET f_ko_po = '1'
     WHERE fin_stavkaid = tfin_stavkaid;
END FOREACH;

EXECUTE FUNCTION pom_knizi_izvod(tfin_izvod_hid, tuser_id)
    INTO terr1, terr2, terr3, terr4;

COMMIT WORK;

RETURN trb,
       'KNI@EWETO E ZAVR[ENO USPE[NO' || tpar_vid_izvod || '/' || tbroj_izvod;
END FUNCTION;
