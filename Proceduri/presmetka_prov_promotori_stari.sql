-- ============================================================
-- presmetka_prov_promotori_stari
-- Retroaktivna presmetka na propusteni provizii za stari polisi
-- (skadenca_datum_od < 01.02.2023) vo dve fazi:
--
-- FAZA 1: INSERT vo provizija_promotori_bodovi (tip_produkcija='1')
--   BB formula (ista kako glavnata procedura):
--   BB = (period_osig * premija_zivot * br_osig_lica) / 520  -- za 285
--   BB = (premija_nezgoda * br_osig_lica) / 333              -- za 1128
--   BB = (premija_zdravstveno * br_osig_lica) / 333          -- za 1567
--   pps_valueval se bara po datum_ponuda so defid od toa vreme
--
-- FAZA 2: INSERT vo provizija_promotori_presmetka
--   Formula (ista kako glavnata procedura linii 919/924):
--   za 285:          tprovizija = (tiznos_bod * tproc_prov * 0.01) / tbr_rati
--   za 1128/1567:    tprovizija = tiznos_bod/tbr_rati + 0.1*tnaplata  (ako koja_god<5)
--
-- Parametri:
--   tpar_agentid - agentid (0 = site agenti so tip P)
--   tmesec       - mesec ('06')
--   tgodina      - godina ('2026')
--   tuser_id     - korisnik ID
--
-- EXECUTE FUNCTION vesna.presmetka_prov_promotori_stari(1809, '06', '2026', 1);
-- ============================================================

DROP FUNCTION IF EXISTS vesna.presmetka_prov_promotori_stari(INT, CHAR(2), CHAR(4), INT);

CREATE FUNCTION vesna.presmetka_prov_promotori_stari(
    tpar_agentid  INT,
    tmesec        CHAR(2),
    tgodina       CHAR(4),
    tuser_id      INT
)
RETURNING INT, VARCHAR(200);

DEFINE tod_odatum              DATE;
DEFINE tdo_datum               DATE;
DEFINE tpar_yearid             INT;
DEFINE tusername               VARCHAR(30);

-- Agent (od nadvoreshna FOREACH)
DEFINE tcur_agentid            INT;
DEFINE tcur_pag_id             INT;
DEFINE tcur_defid              INT;
DEFINE tcur_provtipid          INT;
DEFINE tcur_provizijaispid     INT;
DEFINE tpar_status_aktiven     VARCHAR(1);

-- Bodovi lookup
DEFINE tbodovi_defid           INT;
DEFINE tppd_valueval           DECIMAL(18,6);
DEFINE tind_grupno             INT;

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
DEFINE tpolisa_broj            VARCHAR(50);

-- Premii
DEFINE tpremija_zivot          DECIMAL(18,4);
DEFINE tpremija_nezgoda        DECIMAL(18,4);
DEFINE tpremija_zdravstveno    DECIMAL(18,4);

-- Bodovi presmetka
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
DEFINE tprva_licna_polisa      CHAR(1);

-- Statistika
DEFINE tbodovi_vmeteni         INT;
DEFINE tpresmetki_vmeteni      INT;
DEFINE tpreskokni              INT;

ON EXCEPTION
    RETURN -1, 'NASTANATA E GRESKA';
END EXCEPTION;

set isolation to dirty read;

LET tod_odatum         = MDY(tmesec::INT, 1, tgodina::INT);
LET tdo_datum          = LAST_DAY(tod_odatum);
LET tpersonalec        = 0.10;
LET tbodovi_vmeteni    = 0;
LET tpresmetki_vmeteni = 0;
LET tpreskokni         = 0;

SELECT par_yearid INTO tpar_yearid FROM par_year WHERE par_year = tgodina;
SELECT username   INTO tusername   FROM adm_user   WHERE userid  = tuser_id;


-- ============================================================
-- Iteracija po agenti so tip P aktivni za mesecot
-- ============================================================
FOREACH
    SELECT pa.par_agentid,
           pa.par_provizija_agentid,
           pa.par_provizijadefid,
           pa.par_provizijatipid,
           pa.par_provizijaispid
    INTO   tcur_agentid,
           tcur_pag_id,
           tcur_defid,
           tcur_provtipid,
           tcur_provizijaispid
    FROM   provizija_agent pa
    JOIN   par_provizijadef pd ON pd.par_provizijadefid = pa.par_provizijadefid
    JOIN   par_provizijatip pt ON pt.par_provizijatipid = pd.par_provizijatipid
    WHERE  pt.tip_provizija = 'P'
      AND  ((tdo_datum BETWEEN pa.pag_datumod AND pa.pag_datumdo)
            OR (tdo_datum >= pa.pag_datumod AND pa.pag_datumdo IS NULL))
      AND  (tpar_agentid = 0 OR pa.par_agentid = tpar_agentid)
    ORDER BY pa.par_agentid

    SELECT nvl(par_status_aktiven, 'A') INTO tpar_status_aktiven
    FROM   par_agent WHERE par_agentid = tcur_agentid;
    IF tpar_status_aktiven = 'Z' THEN CONTINUE FOREACH; END IF;


    -- ==========================================================
    -- FAZA 1: Generiranje na BODOVI za stari polisi
    -- ==========================================================
    FOREACH
        SELECT f.os_aneks_fakturaid,
               p.os_polisaid,
               o.period_osig,
               o.os_produktid,
               o.os_produkt_uplataid,
               vrati_premija_zivot(o.os_ponudaid, o.os_produktid),
               nvl(o.br_osig_lica, 1),
               o.datum_ponuda,
               f.par_tip_kniziid,
               o.os_ponudaid,
               p.polisa_broj,
               nvl(o.promotor_par_agent, 0),
               SUM(f.iznos_p),
               SUM(f.iznos_p_den)
        INTO   tos_aneks_fakturaid,
               tos_polisaid,
               tperiod_osig,
               tos_produktid,
               tos_produkt_uplataid,
               tpremija_zivot,
               tbr_osig_lica_ponuda,
               tdatum_ponuda,
               tpar_tip_kniziid,
               tos_ponudaid,
               tpolisa_broj,
               tposrednik_par_client,
               tnaplata,
               tnaplata_den
        FROM   fin_stavka f
        JOIN   os_polisa p ON p.os_polisaid = f.os_polisaid
        JOIN   os_ponuda o ON o.os_ponudaid = p.os_ponudaid
        WHERE  f.iznos_p IS NOT NULL
          AND  (o.par_agentid = tcur_agentid OR o.promotor_par_agent = tcur_agentid)
          AND  o.skadenca_datum_od < DATE('01.02.2023')
          AND  f.par_tip_kniziid IN (285, 1128, 1567)
          AND  f.datum BETWEEN DATE('01.01.2017') AND tdo_datum
          AND  p.datum_polisa <= tdo_datum + 15 UNITS DAY
          AND  vrati_polisa(p.os_polisaid) NOT IN (
                   SELECT vrati_polisa(os_polisaid)
                   FROM   provizija_promotori_bodovi
                   WHERE  tip_produkcija = '1'
                     AND  par_agentid    = tcur_agentid
                     AND  par_tip_kniziid IS NOT NULL
               )
        GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
        HAVING SUM(f.iznos_p_den) <> 0
        ORDER BY o.datum_ponuda, p.polisa_broj, f.par_tip_kniziid

        -- Preskokni ako agent e posrednik (ne sopstvena polisa)
        IF nvl(tposrednik_par_client, 0) <> 0 THEN
            IF tposrednik_par_client <> tcur_agentid THEN
                LET tpreskokni = tpreskokni + 1;
                CONTINUE FOREACH;
            END IF;
        END IF;

        SELECT sifra_polisa INTO tsifra_polisa
        FROM   os_produkt WHERE os_produktid = tos_produktid;

        -- Sifra 19 nema bodovi (kako vo glavnata procedura)
        IF tsifra_polisa = '19' THEN CONTINUE FOREACH; END IF;

        -- br_osig_lica za grupno/individualno
        SELECT nvl(br_osig_lica, 1) INTO tind_grupno
        FROM   os_produkt WHERE os_produktid = tos_produktid;
        IF tind_grupno > 1 THEN
            LET tind_grupno = 2;
        ELSE
            LET tind_grupno = 1;
        END IF;

        -- Premii za tip 1128/1567
        IF tpar_tip_kniziid = 1128 THEN
            EXECUTE FUNCTION vrati_premija_nezgoda(tos_ponudaid, tos_produktid)
                INTO tpremija_nezgoda;
        END IF;
        IF tpar_tip_kniziid = 1567 THEN
            EXECUTE FUNCTION vrati_premija_zdravstveno(tos_ponudaid, tos_produktid)
                INTO tpremija_zdravstveno;
        END IF;

        -- provizijadefid od TOGO vreme (datum_ponuda), ne od denes
        -- Vazno za agenti koi promenile nivo (npr. 1809: 274->286 na 01.06.2022)
        SELECT nvl(MAX(pa2.par_provizijadefid), tcur_defid)
        INTO   tbodovi_defid
        FROM   provizija_agent pa2
        JOIN   par_provizijadef pd2 ON pd2.par_provizijadefid = pa2.par_provizijadefid
        JOIN   par_provizijatip pt2 ON pt2.par_provizijatipid = pd2.par_provizijatipid
        WHERE  pa2.par_agentid = tcur_agentid
          AND  pt2.tip_provizija = 'P'
          AND  ((tdatum_ponuda BETWEEN pa2.pag_datumod AND pa2.pag_datumdo)
                OR (tdatum_ponuda >= pa2.pag_datumod AND pa2.pag_datumdo IS NULL));

        -- pps_valueval od par_provizijadef_St za datum_ponuda
        SELECT nvl(pps_valueval, 0) INTO tppd_valueval
        FROM   par_provizijadef_St
        WHERE  par_provizijadefid = tbodovi_defid
          AND  nvl(pps_valueden, 1) = tind_grupno
          AND  ((tdatum_ponuda BETWEEN pps_datumod AND pps_datumdo)
                OR (tdatum_ponuda >= pps_datumod AND pps_datumdo IS NULL));

        IF tppd_valueval = 0 THEN
            LET tpreskokni = tpreskokni + 1;
            CONTINUE FOREACH;
        END IF;

        -- Proverka: dali veche ima NOVI bodovi za ovaa polisa + tip
        -- (stari zapisi so NULL par_tip_kniziid se ignoriraat)
        SELECT COUNT(*) INTO dali_presm
        FROM   provizija_promotori_bodovi
        WHERE  vrati_polisa(os_polisaid) = vrati_polisa(tos_polisaid)
          AND  par_tip_kniziid    = tpar_tip_kniziid
          AND  par_tip_kniziid IS NOT NULL;

        IF dali_presm > 0 THEN CONTINUE FOREACH; END IF;

        -- Nacin na plakanje (za ednoratna presmetka na BB)
        SELECT par_nacin_platiid INTO tpar_nacin_platiid
        FROM   os_produkt_uplata WHERE os_produkt_uplataid = tos_produkt_uplataid;
        SELECT par_nacin_plati INTO tpar_nacin_plati
        FROM   par_nacin_plati WHERE par_nacin_platiid = tpar_nacin_platiid;

        -- BB formula (linii 322-336 vo glavnata procedura)
        IF tpar_tip_kniziid = 285 THEN
            IF tpar_nacin_plati = '005' THEN
                LET BB = (tpremija_zivot * tbr_osig_lica_ponuda) / 520;
            ELSE
                LET BB = (tperiod_osig * tpremija_zivot * tbr_osig_lica_ponuda) / 520;
            END IF;
        END IF;
        IF tpar_tip_kniziid = 1128 THEN
            LET BB = (tpremija_nezgoda * tbr_osig_lica_ponuda) / 333;
        END IF;
        IF tpar_tip_kniziid = 1567 THEN
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
            tcur_agentid, tos_polisaid,
            BB, 1,
            BB_iznos, '1',
            tod_odatum, tcur_agentid,
            '0', '0',
            tppd_valueval, 0, 0,
            tpar_tip_kniziid
        );

        LET tbodovi_vmeteni = tbodovi_vmeteni + 1;

    END FOREACH; -- FAZA 1 bodovi


    -- ==========================================================
    -- FAZA 2: Presmetka od bodovite
    -- ==========================================================
    FOREACH
        SELECT f.os_aneks_fakturaid,
               f.os_polisaid,
               f.datum,
               o.datum_ponuda,
               SUM(f.iznos_p),
               SUM(f.iznos_p_den)
        INTO   tos_aneks_fakturaid,
               tos_polisaid,
               tdat_naplata,
               tdatum_ponuda,
               tnaplata,
               tnaplata_den
        FROM   fin_stavka f
        JOIN   os_polisa p ON p.os_polisaid = f.os_polisaid
        JOIN   os_ponuda o ON o.os_ponudaid = p.os_ponudaid
        WHERE  f.iznos_p IS NOT NULL
          AND  (o.par_agentid = tcur_agentid OR o.promotor_par_agent = tcur_agentid)
          AND  o.skadenca_datum_od < DATE('01.02.2023')
          AND  f.datum BETWEEN DATE('01.01.2017') AND tdo_datum
          AND  f.par_tip_kniziid IN (285, 1128, 1567, 2974)
          AND  f.os_aneks_fakturaid NOT IN (
                   SELECT ppp.os_aneks_fakturaid
                   FROM   provizija_promotori_presmetka ppp
                   JOIN   provizija_agent pag2
                          ON pag2.par_provizija_agentid = ppp.provizija_agentid
                   WHERE  pag2.par_agentid = tcur_agentid
               )
        GROUP BY 1, 2, 3, 4
        HAVING SUM(f.iznos_p_den) <> 0
        ORDER BY 2, 3 DESC

        -- Proverka za celosen naplatena faktura (po faktura, ne po polisa)
        SELECT nvl(SUM(iznos_p), 0) INTO tcela_naplata
        FROM   fin_stavka
        WHERE  os_aneks_fakturaid = tos_aneks_fakturaid
          AND  datum <= tdo_datum
          AND  iznos_p IS NOT NULL
          AND  par_tip_kniziid IN (285, 1128, 1567, 2974);

        SELECT nvl(SUM(iznos_d), 0) INTO tiznos_d
        FROM   fin_stavka
        WHERE  os_aneks_fakturaid = tos_aneks_fakturaid
          AND  iznos_d IS NOT NULL;

        IF tcela_naplata <> tiznos_d THEN
            LET tpreskokni = tpreskokni + 1;
            CONTINUE FOREACH;
        END IF;

        -- Podatoci za polisata
        SELECT os_ponudaid INTO tos_ponudaid
        FROM   os_polisa WHERE os_polisaid = tos_polisaid;

        SELECT os_produktid, skadenca_datum_od, period_osig,
               os_produkt_uplataid, nvl(par_valutaid, 0)
        INTO   tos_produktid, tskadenca, tperiod_osig,
               tos_produkt_uplataid, tpar_valutaid
        FROM   os_ponuda WHERE os_ponudaid = tos_ponudaid;

        IF tpar_valutaid = 0 THEN
            SELECT par_valutaid INTO tpar_valutaid
            FROM   os_produkt WHERE os_produktid = tos_produktid;
        END IF;

        SELECT sifra_polisa INTO tsifra_polisa
        FROM   os_produkt WHERE os_produktid = tos_produktid;

        SELECT par_nacin_platiid INTO tpar_nacin_platiid
        FROM   os_produkt_uplata WHERE os_produkt_uplataid = tos_produkt_uplataid;
        SELECT par_nacin_plati INTO tpar_nacin_plati
        FROM   par_nacin_plati WHERE par_nacin_platiid = tpar_nacin_platiid;
        IF tpar_nacin_plati = '005' THEN
            LET tppi_onetime = 1;
        ELSE
            LET tppi_onetime = 2;
        END IF;

        SELECT UNIQUE os_aneksid INTO tos_aneksid
        FROM   os_aneks_faktura WHERE os_aneks_fakturaid = tos_aneks_fakturaid;

        SELECT UNIQUE par_tip_kniziid, rata INTO tpar_tip_kniziid, trata
        FROM   os_aneks_faktura WHERE os_aneks_fakturaid = tos_aneks_fakturaid;

        SELECT par_yearid, br_rati INTO tpar_yearid1, tbr_rati
        FROM   os_aneks WHERE os_aneksid = tos_aneksid;

        SELECT par_year INTO tgodina_polisa
        FROM   par_year WHERE par_yearid = tpar_yearid1;

        LET tkoja_god = tgodina_polisa::INT - YEAR(tskadenca) + 1;

        -- Procent od par_provizijaisp za taa godina
        SELECT nvl(ppi_valueproc, 0), par_provizijaispid
        INTO   tproc_prov, tcur_provizijaispid
        FROM   par_provizijaisp
        WHERE  ppi_fromday        = tkoja_god
          AND  par_provizijatipid = tcur_provtipid
          AND  ppi_onetime        = tppi_onetime;

        IF tproc_prov = 0 THEN
            LET tpreskokni = tpreskokni + 1;
            CONTINUE FOREACH;
        END IF;

        -- tiznos_bod od novite bodovi (par_tip_kniziid IS NOT NULL)
        SELECT nvl(SUM(iznos_bod), 0) INTO tiznos_bod
        FROM   provizija_promotori_bodovi
        WHERE  vrati_polisa(os_polisaid) = vrati_polisa(tos_polisaid)
          AND  par_agentid       = tcur_agentid
          AND  par_tip_kniziid   = tpar_tip_kniziid
          AND  par_tip_kniziid   IS NOT NULL
          AND  tip_produkcija    = '1';

        IF tiznos_bod = 0 THEN
            LET tpreskokni = tpreskokni + 1;
            CONTINUE FOREACH;
        END IF;

        -- prva_licna_polisa flag (vlijae na dvojna provizija)
        SELECT nvl(prva_licna_polisa, '0') INTO tprva_licna_polisa
        FROM   provizija_promotori_bodovi
        WHERE  vrati_polisa(os_polisaid) = vrati_polisa(tos_polisaid)
          AND  par_agentid       = tcur_agentid
          AND  par_tip_kniziid   = tpar_tip_kniziid
          AND  par_tip_kniziid   IS NOT NULL
          AND  tip_produkcija    = '1'
          LIMIT 1;

        -- Presmetka na provizija (linii 918-928 vo glavnata procedura)
        IF tsifra_polisa <> '19' THEN
            IF tpar_tip_kniziid = 285 THEN
                LET tprovizija = (tiznos_bod * tproc_prov * 0.01) / tbr_rati;
            ELSE
                IF tkoja_god < 5 THEN
                    LET tprovizija = tiznos_bod / tbr_rati + 0.1 * tnaplata;
                ELSE
                    LET tprovizija = 0;
                END IF;
            END IF;
        END IF;

        IF tprva_licna_polisa = '1' THEN
            LET tprovizija = tprovizija * 2;
        END IF;

        IF tprovizija = 0 THEN
            LET tpreskokni = tpreskokni + 1;
            CONTINUE FOREACH;
        END IF;

        -- Proverka dali veche postoi
        SELECT COUNT(*) INTO tkolku
        FROM   provizija_promotori_presmetka
        WHERE  os_aneks_fakturaid = tos_aneks_fakturaid
          AND  provizija_agentid  = tcur_pag_id;

        IF tkolku > 0 THEN
            LET tpreskokni = tpreskokni + 1;
            CONTINUE FOREACH;
        END IF;

        INSERT INTO provizija_promotori_presmetka (
            provizija_promotori_presmetkaid,
            datecreated, usercreated, version,
            provizija_agentid,
            os_aneks_fakturaid,
            par_yearid,
            iznos_provizija,
            iznos_peronalen,
            par_statusid,
            pap_datumod, pap_datumdo,
            par_provizijaispid,
            dat_naplata,
            proc_prov,
            naplata, naplata_den,
            koja_godina,
            br_rati, rata,
            prov_rata,
            mesec
        ) VALUES (
            sq_provizija_promotori_presmetka.nextval,
            CURRENT, tusername, 0,
            tcur_pag_id,
            tos_aneks_fakturaid,
            tpar_yearid,
            tprovizija,
            tpersonalec,
            1,
            tod_odatum, tdo_datum,
            tcur_provizijaispid,
            tdat_naplata,
            tproc_prov,
            tnaplata, tnaplata_den,
            tkoja_god,
            tbr_rati, trata,
            tprovizija / tbr_rati,
            tmesec
        );

        LET tpresmetki_vmeteni = tpresmetki_vmeteni + 1;

    END FOREACH; -- FAZA 2 presmetka

END FOREACH; -- agenti

RETURN 1, 'bodovi=' || tbodovi_vmeteni
        || '  presmetki=' || tpresmetki_vmeteni
        || '  preskokani=' || tpreskokni;

END FUNCTION;
