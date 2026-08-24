-- ============================================================
-- presmetka_prov_promotori_polisa
-- Gi presmetuva bodovite i provizijata za EDNA specificna polisa.
-- Raboti za novi polisi (skadenca >= 01.02.2023) i stari (<01.02.2023).
-- Gi sledи istite formuli kako glavnata procedura.
--
-- Parametri:
--   tmesec       - mesec ('06')
--   tgodina      - godina ('2026')
--   tpolisa_broj - broj na polisa ('28/006028')
--   tuser_id     - korisnik ID
--
-- EXECUTE FUNCTION vesna.presmetka_prov_promotori_polisa('06','2026','28/006028',1);
-- ============================================================

DROP FUNCTION IF EXISTS vesna.presmetka_prov_promotori_polisa(CHAR(2), CHAR(4), VARCHAR(20), INT);

CREATE FUNCTION vesna.presmetka_prov_promotori_polisa(
    tmesec        CHAR(2),
    tgodina       CHAR(4),
    tpolisa_broj  VARCHAR(20),
    tuser_id      INT
)
RETURNING INT, LVARCHAR(2000);

DEFINE tod_odatum              DATE;
DEFINE tdo_datum               DATE;
DEFINE tpar_yearid             INT;
DEFINE tusername               VARCHAR(30);
DEFINE tporaka                 LVARCHAR(2000);

-- Polisa / ponuda
DEFINE tos_polisaid            INT;
DEFINE tos_ponudaid            INT;
DEFINE tos_produktid           INT;
DEFINE tos_aneksid             INT;
DEFINE tos_produkt_uplataid    INT;
DEFINE tos_aneks_fakturaid     INT;
DEFINE tskadenca               DATE;
DEFINE tdatum_ponuda           DATE;
DEFINE tperiod_osig            INT;
DEFINE tsifra_polisa           VARCHAR(2);
DEFINE tbr_osig_lica_ponuda    INT;
DEFINE tpar_valutaid           INT;
DEFINE tpar_nacin_platiid      INT;
DEFINE tpar_nacin_plati        CHAR(3);
DEFINE tppi_onetime            INT;
DEFINE tpar_tip_kniziid        INT;
DEFINE tposrednik_par_client   INT;
DEFINE tind_grupno             INT;
DEFINE tpar_tip_kniziid_faktura INT;

-- Agent
DEFINE tpar_agentid            INT;
DEFINE tpar_provizija_agentid  INT;
DEFINE tpar_provizijadefid     INT;
DEFINE tpar_provizijatipid     INT;
DEFINE tpar_provizijaispid     INT;
DEFINE tpar_status_aktiven     VARCHAR(1);
DEFINE tbodovi_defid           INT;

-- par_provizijadef
DEFINE tppd_valueval           DECIMAL(18,6);
DEFINE tppd_from               DECIMAL(18,4);
DEFINE tppd_to                 DECIMAL(18,4);
DEFINE tppd_nadredenid         INT;
DEFINE tppd_level              INT;
DEFINE tdenovi_lp              INT;
DEFINE tdenovi_tp              INT;
DEFINE tpar_client_agent       INT;
DEFINE tpoceten_datum          DATE;
DEFINE tdogovoruvac_par_client INT;
DEFINE tprva_licna_polisa      CHAR(1);
DEFINE tprva_druga_polisa      CHAR(1);

-- Premii
DEFINE tpremija_zivot          DECIMAL(18,4);
DEFINE tpremija_nezgoda        DECIMAL(18,4);
DEFINE tpremija_zdravstveno    DECIMAL(18,4);

-- Bodovi
DEFINE BB                      DECIMAL(18,6);
DEFINE BB_iznos                DECIMAL(18,4);
DEFINE dali_presm              INT;

-- Presmetka
DEFINE tdat_naplata            DATE;
DEFINE tnaplata                DECIMAL(18,4);
DEFINE tnaplata_den            DECIMAL(18,4);
DEFINE tcela_naplata           DECIMAL(18,4);
DEFINE tiznos_d                DECIMAL(18,4);
DEFINE tiznos_bod              DECIMAL(18,4);
DEFINE tproc_prov              DECIMAL(10,4);
DEFINE tprovizija              DECIMAL(18,4);
DEFINE tpersonalec             DECIMAL(10,4);
DEFINE tkoja_god               INT;
DEFINE tbr_rati                INT;
DEFINE trata                   INT;
DEFINE tpar_yearid1            INT;
DEFINE tgodina_polisa          VARCHAR(4);
DEFINE tkolku                  INT;
DEFINE tiznt_eur               DECIMAL(18,4);
DEFINE tprocent_provizija      DECIMAL(10,4);

-- Nadreden
DEFINE tnadreden_agentid       INT;
DEFINE tnadreden_pag_id        INT;
DEFINE tnadreden_defid         INT;
DEFINE tnadreden_tipid         INT;
DEFINE tnadreden_ispid         INT;
DEFINE tppd_nadredenid_current INT;
DEFINE tnadreden_pps_val       DECIMAL(18,6);
DEFINE tiznos_bod_tip2         DECIMAL(18,4);
DEFINE tprovizija_nadreden     DECIMAL(18,4);
DEFINE tkolku_nadreden         INT;

-- Statistika
DEFINE tbodovi_vmeteni         INT;
DEFINE tpresmetki_vmeteni      INT;
DEFINE tnadreden_vmeteni       INT;

-- Greska handling
DEFINE terror_code             INT;
DEFINE terror_isam             INT;
DEFINE tStep                   LVARCHAR(80);

ON EXCEPTION SET terror_code, terror_isam
    RETURN -1, 'GRESKA kod=' || terror_code || ' isam=' || terror_isam || ' step=' || tStep;
END EXCEPTION;

set isolation to dirty read;
LET tStep = 'init';

LET tod_odatum         = MDY(tmesec::INT, 1, tgodina::INT);
LET tdo_datum          = LAST_DAY(tod_odatum);
LET tpersonalec        = 0.10;
LET tbodovi_vmeteni    = 0;
LET tpresmetki_vmeteni = 0;
LET tnadreden_vmeteni  = 0;
LET tporaka            = '';

LET tStep = 'par_year'; SELECT par_yearid INTO tpar_yearid FROM par_year WHERE par_year = tgodina;
LET tStep = 'adm_user'; SELECT username   INTO tusername   FROM adm_user   WHERE userid  = tuser_id;

-- Pronajdi ja polisata
LET tStep = 'os_polisa';
SELECT FIRST 1 p.os_polisaid, p.os_ponudaid
INTO   tos_polisaid, tos_ponudaid
FROM   os_polisa p
WHERE  TRIM(p.polisa_broj_cel) = TRIM(tpolisa_broj);

IF tos_polisaid IS NULL THEN
    RETURN -1, 'Polisata ' || tpolisa_broj || ' ne postoi.';
END IF;

LET tStep = 'os_ponuda';
SELECT o.os_produktid, o.skadenca_datum_od, o.period_osig,
       o.os_produkt_uplataid, nvl(o.par_valutaid, 0),
       o.par_agentid, nvl(o.promotor_par_agent, 0),
       o.datum_ponuda, nvl(o.br_osig_lica, 1),
       o.dogovoruvac_par_client
INTO   tos_produktid, tskadenca, tperiod_osig,
       tos_produkt_uplataid, tpar_valutaid,
       tpar_agentid, tposrednik_par_client,
       tdatum_ponuda, tbr_osig_lica_ponuda,
       tdogovoruvac_par_client
FROM   os_ponuda o
WHERE  o.os_ponudaid = tos_ponudaid;

IF tpar_valutaid = 0 THEN
    LET tStep = 'os_produkt_val';
    SELECT par_valutaid INTO tpar_valutaid
    FROM   os_produkt WHERE os_produktid = tos_produktid;
END IF;

LET tStep = 'os_produkt_sif';
SELECT sifra_polisa INTO tsifra_polisa
FROM   os_produkt WHERE os_produktid = tos_produktid;

LET tStep = 'os_produkt_uplata';
SELECT par_nacin_platiid INTO tpar_nacin_platiid
FROM   os_produkt_uplata WHERE os_produkt_uplataid = tos_produkt_uplataid;
LET tStep = 'par_nacin_plati';
SELECT par_nacin_plati INTO tpar_nacin_plati
FROM   par_nacin_plati WHERE par_nacin_platiid = tpar_nacin_platiid;
IF tpar_nacin_plati = '005' THEN LET tppi_onetime = 1; ELSE LET tppi_onetime = 2; END IF;

-- br_osig_lica (od produkt, ne od ponuda)
LET tStep = 'os_produkt_brol';
SELECT nvl(br_osig_lica, 1) INTO tind_grupno
FROM   os_produkt WHERE os_produktid = tos_produktid;
IF tind_grupno > 1 THEN LET tind_grupno = 2; ELSE LET tind_grupno = 1; END IF;

-- Najdi go agentot i negoviot provizija_agent zapis
LET tStep = 'prov_agent';
SELECT FIRST 1
       pa.par_agentid,
       pa.par_provizija_agentid,
       pa.par_provizijadefid,
       pa.par_provizijatipid,
       pa.par_provizijaispid
INTO   tpar_agentid,
       tpar_provizija_agentid,
       tpar_provizijadefid,
       tpar_provizijatipid,
       tpar_provizijaispid
FROM   provizija_agent pa
JOIN   par_provizijadef pd ON pd.par_provizijadefid = pa.par_provizijadefid
JOIN   par_provizijatip pt ON pt.par_provizijatipid = pd.par_provizijatipid
WHERE  pa.par_agentid = tpar_agentid
  AND  pt.tip_provizija = 'P'
  AND  ((tdatum_ponuda BETWEEN pa.pag_datumod AND pa.pag_datumdo)
        OR (tdatum_ponuda >= pa.pag_datumod AND pa.pag_datumdo IS NULL));

IF tpar_provizija_agentid IS NULL THEN
    RETURN -1, 'Agent ' || tpar_agentid || ' nema aktiven provizija_agent zapis za datum_ponuda=' || tdatum_ponuda;
END IF;

LET tStep = 'par_agent_stat';
SELECT nvl(par_status_aktiven, 'A') INTO tpar_status_aktiven
FROM   par_agent WHERE par_agentid = tpar_agentid;
IF tpar_status_aktiven = 'Z' THEN
    RETURN -1, 'Agent ' || tpar_agentid || ' e zatvoren (status=Z). Ponatamosna provizija ne se presmetuva.';
END IF;

-- Par provizijadef podatoci
LET tStep = 'par_provizijadef';
SELECT ppd_from, ppd_to, ppd_level, nvl(ppd_nadredenid,0),
       nvl(denovi_lp,0), nvl(denovi_tp,0), ppd_valueval
INTO   tppd_from, tppd_to, tppd_level, tppd_nadredenid,
       tdenovi_lp, tdenovi_tp, tppd_valueval
FROM   par_provizijadef
WHERE  par_provizijadefid = tpar_provizijadefid;

LET tStep = 'par_agent_client';
SELECT par_client_id, poceten_datum INTO tpar_client_agent, tpoceten_datum
FROM   par_agent WHERE par_agentid = tpar_agentid;

-- ============================================================
-- FAZA 1: BODOVI
-- ============================================================
IF tsifra_polisa <> '19' THEN

    -- Za stari polisi bara provizijadefid od toa vreme
    IF tskadenca < DATE('01.02.2023') THEN
        SELECT nvl(MAX(pa2.par_provizijadefid), tpar_provizijadefid)
        INTO   tbodovi_defid
        FROM   provizija_agent pa2
        JOIN   par_provizijadef pd2 ON pd2.par_provizijadefid = pa2.par_provizijadefid
        JOIN   par_provizijatip pt2 ON pt2.par_provizijatipid = pd2.par_provizijatipid
        WHERE  pa2.par_agentid = tpar_agentid
          AND  pt2.tip_provizija = 'P'
          AND  ((tdatum_ponuda BETWEEN pa2.pag_datumod AND pa2.pag_datumdo)
                OR (tdatum_ponuda >= pa2.pag_datumod AND pa2.pag_datumdo IS NULL));
    ELSE
        LET tbodovi_defid = tpar_provizijadefid;
    END IF;

    -- Proverka dali veche ima bodovi
    LET tStep = 'F1_count_bodovi';
    SELECT COUNT(*) INTO dali_presm
    FROM   provizija_promotori_bodovi
    WHERE  vrati_polisa(os_polisaid) = vrati_polisa(tos_polisaid)
      AND  par_agentid = tpar_agentid
      AND  par_tip_kniziid IS NOT NULL;

    IF dali_presm = 0 THEN

        -- pps_valueval
        LET tStep = 'F1_pps_valueval';
        SELECT FIRST 1 nvl(pps_valueval, 0) INTO tppd_valueval
        FROM   par_provizijadef_St
        WHERE  par_provizijadefid = tbodovi_defid
          AND  nvl(pps_valueden, 1) = tind_grupno
          AND  ((tdatum_ponuda BETWEEN pps_datumod AND pps_datumdo)
                OR (tdatum_ponuda >= pps_datumod AND pps_datumdo IS NULL));

        IF tppd_valueval > 0 THEN

            -- prva_licna / prva_druga
            LET tprva_licna_polisa = '0';
            LET tprva_druga_polisa = '0';
            IF tppd_level = 1 THEN
                IF tdenovi_lp <> 0 THEN
                    IF tdogovoruvac_par_client = tpar_client_agent
                       AND tdatum_ponuda BETWEEN tpoceten_datum AND tpoceten_datum + tdenovi_lp THEN
                        LET tprva_licna_polisa = '1';
                    END IF;
                END IF;
                IF tdenovi_tp <> 0 THEN
                    IF tdogovoruvac_par_client <> tpar_client_agent
                       AND tdatum_ponuda BETWEEN tpoceten_datum AND tpoceten_datum + tdenovi_tp THEN
                        LET tprva_druga_polisa = '1';
                    END IF;
                END IF;
            END IF;

            -- BB formula po tip_kniziid
            -- Premijata se vika VNATRE vo FOREACH koga tpar_tip_kniziid e poznat
            FOREACH
                SELECT UNIQUE f.par_tip_kniziid
                INTO   tpar_tip_kniziid
                FROM   fin_stavka f
                JOIN   os_polisa p ON p.os_polisaid = f.os_polisaid
                WHERE  p.os_polisaid = tos_polisaid
                  AND  f.par_tip_kniziid IN (285, 1128, 1567)
                  AND  f.iznos_p IS NOT NULL

                LET BB       = 0;
                LET BB_iznos = 0;

                IF tpar_tip_kniziid = 285 THEN
                    LET tStep = 'F1_zivot_exec';
                    EXECUTE FUNCTION vrati_premija_zivot(tos_ponudaid, tos_produktid)
                        INTO tpremija_zivot;
                    IF tpar_nacin_plati = '005' THEN
                        LET BB = (tpremija_zivot * tbr_osig_lica_ponuda) / 520;
                    ELSE
                        LET BB = (tperiod_osig * tpremija_zivot * tbr_osig_lica_ponuda) / 520;
                    END IF;
                END IF;
                IF tpar_tip_kniziid = 1128 THEN
                    LET tStep = 'F1_nezgoda_exec';
                    EXECUTE FUNCTION vrati_premija_nezgoda(tos_ponudaid, tos_produktid)
                        INTO tpremija_nezgoda;
                    LET BB = (tpremija_nezgoda * tbr_osig_lica_ponuda) / 333;
                END IF;
                IF tpar_tip_kniziid = 1567 THEN
                    LET tStep = 'F1_zdravstveno_exec';
                    EXECUTE FUNCTION vrati_premija_zdravstveno(tos_ponudaid, tos_produktid)
                        INTO tpremija_zdravstveno;
                    LET BB = (tpremija_zdravstveno * tbr_osig_lica_ponuda) / 333;
                END IF;

                LET BB_iznos = tppd_valueval * BB;

                INSERT INTO provizija_promotori_bodovi (
                    provizija_promotori_bodoviid,
                    datecreated, usercreated, version,
                    mesec, par_yearid,
                    par_agentid, os_polisaid,
                    br_bodovi, par_statusid,
                    iznos_bod, tip_produkcija,
                    datum_presmetka, promotor_par_agentid,
                    prva_licna_polisa, prva_druga_polisa,
                    bod, duplirani_bodovi, storno_bodovi,
                    par_tip_kniziid
                ) VALUES (
                    sq_provizija_promotori_bodovi.nextval,
                    CURRENT, tusername, 0,
                    tmesec, tpar_yearid,
                    tpar_agentid, tos_polisaid,
                    BB, 1,
                    BB_iznos, '1',
                    tod_odatum, tpar_agentid,
                    tprva_licna_polisa, tprva_druga_polisa,
                    tppd_valueval, 0, 0,
                    tpar_tip_kniziid
                );

                LET tbodovi_vmeteni = tbodovi_vmeteni + 1;

            END FOREACH;

        ELSE
            LET tporaka = tporaka || '[WARN] pps_valueval=0 za datum_ponuda=' || tdatum_ponuda || ' defid=' || tbodovi_defid || ' ';
        END IF; -- tppd_valueval > 0

    ELSE
        LET tporaka = tporaka || '[INFO] Bodovi veche postojat. ';
    END IF; -- dali_presm = 0

END IF; -- sifra <> 19


-- ============================================================
-- FAZA 2: PRESMETKA po faktura
-- ============================================================
FOREACH
    SELECT f.os_aneks_fakturaid,
           f.datum,
           f.par_tip_kniziid,
           SUM(f.iznos_p),
           SUM(f.iznos_p_den)
    INTO   tos_aneks_fakturaid,
           tdat_naplata,
           tpar_tip_kniziid,
           tnaplata,
           tnaplata_den
    FROM   fin_stavka f
    WHERE  f.os_polisaid = tos_polisaid
      AND  f.iznos_p IS NOT NULL
      AND  f.datum BETWEEN DATE('01.01.2017') AND tdo_datum
      AND  f.par_tip_kniziid IN (285, 1128, 1567, 2974)
      AND  f.os_aneks_fakturaid NOT IN (
               SELECT ppp.os_aneks_fakturaid
               FROM   provizija_promotori_presmetka ppp
               WHERE  ppp.provizija_agentid = tpar_provizija_agentid
           )
    GROUP BY 1, 2, 3
    HAVING SUM(f.iznos_p_den) <> 0
    ORDER BY 2 DESC

    -- Celoso naplatena faktura?
    LET tStep = 'F2_cela_naplata';
    SELECT nvl(SUM(iznos_p), 0) INTO tcela_naplata
    FROM   fin_stavka
    WHERE  os_aneks_fakturaid = tos_aneks_fakturaid
      AND  datum <= tdo_datum
      AND  iznos_p IS NOT NULL
      AND  par_tip_kniziid IN (285, 1128, 1567, 2974);

    LET tStep = 'F2_iznos_d';
    SELECT nvl(SUM(iznos_d), 0) INTO tiznos_d
    FROM   fin_stavka
    WHERE  os_aneks_fakturaid = tos_aneks_fakturaid
      AND  iznos_d IS NOT NULL;

    IF tcela_naplata <> tiznos_d THEN CONTINUE FOREACH; END IF;

    LET tStep = 'F2_os_aneksid';
    SELECT FIRST 1 os_aneksid INTO tos_aneksid
    FROM   os_aneks_faktura WHERE os_aneks_fakturaid = tos_aneks_fakturaid;

    LET tStep = 'F2_tip_kniziid_fak';
    SELECT FIRST 1 par_tip_kniziid INTO tpar_tip_kniziid_faktura
    FROM   os_aneks_faktura WHERE os_aneks_fakturaid = tos_aneks_fakturaid;

    LET tStep = 'F2_rata';
    SELECT FIRST 1 rata INTO trata
    FROM   os_aneks_faktura WHERE os_aneks_fakturaid = tos_aneks_fakturaid;

    LET tStep = 'F2_os_aneks';
    SELECT par_yearid, br_rati INTO tpar_yearid1, tbr_rati
    FROM   os_aneks WHERE os_aneksid = tos_aneksid;

    LET tStep = 'F2_par_year';
    SELECT par_year INTO tgodina_polisa
    FROM   par_year WHERE par_yearid = tpar_yearid1;

    LET tkoja_god = tgodina_polisa::INT - YEAR(tskadenca) + 1;

    LET tStep = 'F2_par_provizijaisp';
    SELECT FIRST 1 nvl(ppi_valueproc, 0), par_provizijaispid
    INTO   tproc_prov, tpar_provizijaispid
    FROM   par_provizijaisp
    WHERE  ppi_fromday        = tkoja_god
      AND  par_provizijatipid = tpar_provizijatipid
      AND  ppi_onetime        = tppi_onetime;

    IF tproc_prov = 0 THEN CONTINUE FOREACH; END IF;

    -- tiznos_bod
    IF tsifra_polisa <> '19' THEN
        LET tStep = 'F2_iznos_bod';
        SELECT nvl(SUM(iznos_bod), 0) INTO tiznos_bod
        FROM   provizija_promotori_bodovi
        WHERE  vrati_polisa(os_polisaid) = vrati_polisa(tos_polisaid)
          AND  par_agentid     = tpar_agentid
          AND  par_tip_kniziid = tpar_tip_kniziid_faktura
          AND  par_tip_kniziid IS NOT NULL
          AND  tip_produkcija  = '1';

        LET tStep = 'F2_prva_licna';
        SELECT FIRST 1 nvl(prva_licna_polisa, '0') INTO tprva_licna_polisa
        FROM   provizija_promotori_bodovi
        WHERE  vrati_polisa(os_polisaid) = vrati_polisa(tos_polisaid)
          AND  par_agentid     = tpar_agentid
          AND  par_tip_kniziid = tpar_tip_kniziid_faktura
          AND  par_tip_kniziid IS NOT NULL
          AND  tip_produkcija  = '1';
    END IF;

    -- Formula za provizija
    LET tprovizija = 0;
    IF tsifra_polisa <> '19' THEN
        IF tpar_tip_kniziid_faktura = 285 THEN
            IF tiznos_bod = 0 THEN CONTINUE FOREACH; END IF;
            LET tprovizija = (tiznos_bod * tproc_prov * 0.01) / tbr_rati;
        ELSE
            IF tkoja_god < 5 THEN
                LET tprovizija = tiznos_bod / tbr_rati + 0.1 * tnaplata;
            END IF;
        END IF;
        IF tprva_licna_polisa = '1' THEN LET tprovizija = tprovizija * 2; END IF;
    END IF;

    IF tsifra_polisa = '19' THEN
        IF tpar_valutaid = 363 THEN
            EXECUTE PROCEDURE konverzija(tdo_datum, tnaplata, 'MKD', 'EUR') INTO tiznt_eur;
            LET tprovizija = tiznt_eur * tproc_prov * 0.01;
        ELSE
            LET tprovizija = tnaplata * tproc_prov * 0.01;
        END IF;
    END IF;

    IF tprovizija = 0 THEN CONTINUE FOREACH; END IF;

    SELECT COUNT(*) INTO tkolku
    FROM   provizija_promotori_presmetka
    WHERE  os_aneks_fakturaid = tos_aneks_fakturaid
      AND  provizija_agentid  = tpar_provizija_agentid;

    IF tkolku > 0 THEN CONTINUE FOREACH; END IF;

    INSERT INTO provizija_promotori_presmetka (
        provizija_promotori_presmetkaid,
        datecreated, usercreated, version,
        provizija_agentid, os_aneks_fakturaid,
        par_yearid, iznos_provizija, iznos_peronalen,
        par_statusid, pap_datumod, pap_datumdo,
        par_provizijaispid, dat_naplata, proc_prov,
        naplata, naplata_den, koja_godina,
        br_rati, rata, prov_rata, mesec
    ) VALUES (
        sq_provizija_promotori_presmetka.nextval,
        CURRENT, tusername, 0,
        tpar_provizija_agentid, tos_aneks_fakturaid,
        tpar_yearid, tprovizija, tpersonalec,
        1, tod_odatum, tdo_datum,
        tpar_provizijaispid, tdat_naplata, tproc_prov,
        tnaplata, tnaplata_den, tkoja_god,
        tbr_rati, trata, tprovizija / tbr_rati, tmesec
    );

    LET tpresmetki_vmeteni = tpresmetki_vmeteni + 1;

END FOREACH; -- FAZA 2


-- ============================================================
-- FAZA 3: NADREDEN
-- Nadredeniot se proveruva spored TEKOVNIOT period (tdo_datum),
-- ne spored datumot na polisata (tdatum_ponuda).
-- ============================================================
LET tStep = 'F3_current_nadredenid';
LET tppd_nadredenid_current = 0;
SELECT FIRST 1 nvl(pd.ppd_nadredenid, 0)
INTO   tppd_nadredenid_current
FROM   provizija_agent pa
JOIN   par_provizijadef pd ON pd.par_provizijadefid = pa.par_provizijadefid
JOIN   par_provizijatip pt ON pt.par_provizijatipid = pd.par_provizijatipid
WHERE  pa.par_agentid = tpar_agentid
  AND  pt.tip_provizija = 'P'
  AND  ((tdo_datum BETWEEN pa.pag_datumod AND pa.pag_datumdo)
        OR (tdo_datum >= pa.pag_datumod AND pa.pag_datumdo IS NULL));

IF tppd_nadredenid_current <> 0 THEN

    SELECT FIRST 1
           pa.par_agentid,
           pa.par_provizija_agentid,
           pa.par_provizijadefid,
           pa.par_provizijatipid,
           pa.par_provizijaispid
    INTO   tnadreden_agentid,
           tnadreden_pag_id,
           tnadreden_defid,
           tnadreden_tipid,
           tnadreden_ispid
    FROM   provizija_agent pa
    JOIN   par_provizijadef pd ON pd.par_provizijadefid = pa.par_provizijadefid
    WHERE  pd.par_provizijadefid = tppd_nadredenid_current
      AND  ((tdo_datum BETWEEN pa.pag_datumod AND pa.pag_datumdo)
            OR (tdo_datum >= pa.pag_datumod AND pa.pag_datumdo IS NULL));

    IF tnadreden_agentid IS NOT NULL THEN

        SELECT FIRST 1 nvl(pps_valueval, 0) INTO tnadreden_pps_val
        FROM   par_provizijadef_St
        WHERE  par_provizijadefid = tnadreden_defid
          AND  nvl(pps_valueden, 1) = tind_grupno
          AND  ((tdatum_ponuda BETWEEN pps_datumod AND pps_datumdo)
                OR (tdatum_ponuda >= pps_datumod AND pps_datumdo IS NULL));

        -- tiznos_bod tip=2 za nadredeniot
        SELECT nvl(SUM(iznos_bod), 0) INTO tiznos_bod_tip2
        FROM   provizija_promotori_bodovi
        WHERE  vrati_polisa(os_polisaid) = vrati_polisa(tos_polisaid)
          AND  par_agentid   = tnadreden_agentid
          AND  tip_produkcija = '2';

        -- Ako nema tip=2 bodovi, generiraj gi od tip=1 bodovite
        IF tiznos_bod_tip2 = 0 THEN
            SELECT nvl(SUM(iznos_bod), 0) INTO tiznos_bod
            FROM   provizija_promotori_bodovi
            WHERE  vrati_polisa(os_polisaid) = vrati_polisa(tos_polisaid)
              AND  tip_produkcija  = '1'
              AND  par_tip_kniziid IS NOT NULL;

            IF tiznos_bod > 0 AND tnadreden_pps_val > 0 THEN
                LET BB_iznos = tnadreden_pps_val * (tiznos_bod / tppd_valueval);

                SELECT FIRST 1 par_tip_kniziid INTO tpar_tip_kniziid
                FROM   provizija_promotori_bodovi
                WHERE  vrati_polisa(os_polisaid) = vrati_polisa(tos_polisaid)
                  AND  tip_produkcija  = '1'
                  AND  par_tip_kniziid IS NOT NULL;

                INSERT INTO provizija_promotori_bodovi (
                    provizija_promotori_bodoviid,
                    datecreated, usercreated, version,
                    mesec, par_yearid,
                    par_agentid, os_polisaid,
                    br_bodovi, par_statusid,
                    iznos_bod, tip_produkcija,
                    datum_presmetka, promotor_par_agentid,
                    prva_licna_polisa, prva_druga_polisa,
                    bod, duplirani_bodovi, storno_bodovi,
                    par_tip_kniziid
                ) VALUES (
                    sq_provizija_promotori_bodovi.nextval,
                    CURRENT, tusername, 0,
                    tmesec, tpar_yearid,
                    tnadreden_agentid, tos_polisaid,
                    tiznos_bod / tppd_valueval, 1,
                    BB_iznos, '2',
                    tod_odatum, tpar_agentid,
                    '0', '0',
                    tnadreden_pps_val, 0, 0,
                    tpar_tip_kniziid
                );

                LET tiznos_bod_tip2 = BB_iznos;
                LET tbodovi_vmeteni = tbodovi_vmeteni + 1;
            END IF;
        END IF;

        -- Presmetka za nadredeniot
        FOREACH
            SELECT ppp.os_aneks_fakturaid,
                   ppp.dat_naplata,
                   ppp.naplata,
                   ppp.naplata_den,
                   ppp.koja_godina,
                   ppp.br_rati,
                   ppp.rata
            INTO   tos_aneks_fakturaid,
                   tdat_naplata,
                   tnaplata,
                   tnaplata_den,
                   tkoja_god,
                   tbr_rati,
                   trata
            FROM   provizija_promotori_presmetka ppp
            WHERE  ppp.provizija_agentid = tpar_provizija_agentid
              AND  ppp.pap_datumod = tod_odatum
              AND  ppp.os_aneks_fakturaid NOT IN (
                       SELECT ppp2.os_aneks_fakturaid
                       FROM   provizija_promotori_presmetka ppp2
                       WHERE  ppp2.provizija_agentid = tnadreden_pag_id
                   )

            SELECT FIRST 1 nvl(ppi_valueproc, 0), par_provizijaispid
            INTO   tproc_prov, tnadreden_ispid
            FROM   par_provizijaisp
            WHERE  ppi_fromday        = tkoja_god
              AND  par_provizijatipid = tnadreden_tipid
              AND  ppi_onetime        = tppi_onetime;

            IF tproc_prov = 0 THEN CONTINUE FOREACH; END IF;

            LET tprovizija_nadreden = (tiznos_bod_tip2 * tproc_prov * 0.01) / tbr_rati;
            IF tprovizija_nadreden = 0 THEN CONTINUE FOREACH; END IF;

            SELECT COUNT(*) INTO tkolku_nadreden
            FROM   provizija_promotori_presmetka
            WHERE  os_aneks_fakturaid = tos_aneks_fakturaid
              AND  provizija_agentid  = tnadreden_pag_id;

            IF tkolku_nadreden > 0 THEN CONTINUE FOREACH; END IF;

            INSERT INTO provizija_promotori_presmetka (
                provizija_promotori_presmetkaid,
                datecreated, usercreated, version,
                provizija_agentid, os_aneks_fakturaid,
                par_yearid, iznos_provizija, iznos_peronalen,
                par_statusid, pap_datumod, pap_datumdo,
                par_provizijaispid, dat_naplata, proc_prov,
                naplata, naplata_den, koja_godina,
                br_rati, rata, prov_rata, mesec
            ) VALUES (
                sq_provizija_promotori_presmetka.nextval,
                CURRENT, tusername, 0,
                tnadreden_pag_id, tos_aneks_fakturaid,
                tpar_yearid, tprovizija_nadreden, tpersonalec,
                1, tod_odatum, tdo_datum,
                tnadreden_ispid, tdat_naplata, tproc_prov,
                tnaplata, tnaplata_den, tkoja_god,
                tbr_rati, trata, tprovizija_nadreden / tbr_rati, tmesec
            );

            LET tnadreden_vmeteni = tnadreden_vmeteni + 1;

        END FOREACH;

    END IF; -- tnadreden_agentid IS NOT NULL

END IF; -- tppd_nadredenid <> 0


LET tporaka = tporaka
    || 'bodovi=' || tbodovi_vmeteni
    || '  presmetki=' || tpresmetki_vmeteni
    || '  nadreden=' || tnadreden_vmeteni;

RETURN 1, tporaka;

END FUNCTION;
