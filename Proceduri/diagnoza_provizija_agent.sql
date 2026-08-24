-- ============================================================
-- diagnoza_provizija_agent
-- Pomosna procedura za proverka zosto ne se presmetuva
-- provizija za daden agent i polisa.
--
-- Parametri:
--   tpar_agentid  - ID na agentot (pr. 1809)
--   tpolisa_broj  - broj na polisa (pr. '26/000773')
--   tmesec        - mesec na presmetka (pr. '06')
--   tgodina       - godina na presmetka (pr. '2025')
--
-- Upotreba:
--   EXECUTE FUNCTION vesna.diagnoza_provizija_agent(1809, '26/000773', '06', '2025');
-- ============================================================

DROP FUNCTION IF EXISTS vesna.diagnoza_provizija_agent(INT, VARCHAR(20), CHAR(2), CHAR(4));

CREATE FUNCTION vesna.diagnoza_provizija_agent(
    tpar_agentid   INT,
    tpolisa_broj   VARCHAR(20),
    tmesec         CHAR(2),
    tgodina        CHAR(4)
)
RETURNING LVARCHAR(4000);

DEFINE tresult          LVARCHAR(4000);
DEFINE tkolku           INT;
DEFINE tos_polisaid     INT;
DEFINE tos_ponudaid     INT;
DEFINE tos_produktid    INT;
DEFINE tpar_agentid_pol INT;
DEFINE tpromotor        INT;
DEFINE tsifra_polisa    VARCHAR(2);
DEFINE tpar_status      VARCHAR(1);
DEFINE tskadenca        DATE;
DEFINE tdatum_min_fin   DATE;
DEFINE tdatum_max_fin   DATE;
DEFINE tod_odatum       DATE;
DEFINE tdo_datum        DATE;
DEFINE tpar_yearid      INT;
DEFINE tcela_naplata    DECIMAL(18,4);
DEFINE tiznos_d         DECIMAL(18,4);
DEFINE tkolku_bodovi    INT;
DEFINE tkolku_presmetka INT;
DEFINE tpar_provtipid   INT;
DEFINE tdatum_ponuda    DATE;
DEFINE tkoja_god        INT;
DEFINE tproc            DECIMAL(10,4);
DEFINE tposrednik       INT;
DEFINE tpodredeni       INT;
DEFINE tfakt_vkupno     INT;
DEFINE tfakt_plateni    INT;
DEFINE tfakt_neplateni  INT;
DEFINE tfakt_id         INT;
DEFINE tfakt_naplata    DECIMAL(18,4);
DEFINE tfakt_dolg       DECIMAL(18,4);
DEFINE tfakt_datum      DATE;
DEFINE tpodred_agentid  INT;
DEFINE tpodred_polisi   INT;
DEFINE tpodred_bodovi   INT;
DEFINE tpodred_presm    INT;
DEFINE tnad_pag_pokriva INT;
DEFINE tnad2_agentid    INT;
DEFINE tnad2_pokriva    INT;
DEFINE tblok10_defid    INT;
DEFINE tblok10_datumod  DATE;
DEFINE tblok10_datumdo  DATE;

ON EXCEPTION
    RETURN '[GRESKA] Nastanata e neocekvana greska vo dijagnozata';
END EXCEPTION;

set isolation to dirty read;

LET tod_odatum = MDY(1, 1, tgodina::INT);
LET tod_odatum = MDY(tmesec::INT, 1, tgodina::INT);
LET tdo_datum  = LAST_DAY(tod_odatum);

SELECT par_yearid INTO tpar_yearid
FROM par_year WHERE par_year = tgodina;

LET tresult = '=== DIJAGNOZA agent=' || tpar_agentid
           || ' polisa=' || tpolisa_broj
           || ' ' || tmesec || '/' || tgodina
           || ' ===' || CHR(10);


-- ============================================================
-- BLOK 1: Dali polisata postoi
-- ============================================================
SELECT COUNT(*) INTO tkolku FROM os_polisa WHERE polisa_broj_cel = tpolisa_broj;
IF tkolku = 0 THEN
    LET tresult = tresult || '[FAIL] Polisata ' || tpolisa_broj || ' NE POSTOI vo os_polisa.' || CHR(10);
    RETURN tresult;
END IF;
LET tresult = tresult || '[OK]   Polisata postoi vo os_polisa.' || CHR(10);

SELECT os_polisaid INTO tos_polisaid FROM os_polisa WHERE polisa_broj_cel = tpolisa_broj;
SELECT os_ponudaid INTO tos_ponudaid FROM os_polisa WHERE os_polisaid = tos_polisaid;

SELECT os_produktid, skadenca_datum_od, datum_ponuda
INTO   tos_produktid, tskadenca, tdatum_ponuda
FROM   os_ponuda WHERE os_ponudaid = tos_ponudaid;


-- ============================================================
-- BLOK 2: Vrzanost na agentot so polisata
-- ============================================================
SELECT nvl(par_agentid, 0), nvl(promotor_par_agent, 0)
INTO   tpar_agentid_pol, tpromotor
FROM   os_ponuda WHERE os_ponudaid = tos_ponudaid;

IF tpar_agentid_pol = tpar_agentid THEN
    LET tresult = tresult || '[OK]   Agentot e vrzan (par_agentid).' || CHR(10);
ELSE
    IF tpromotor = tpar_agentid THEN
        LET tresult = tresult || '[OK]   Agentot e vrzan (promotor_par_agent).' || CHR(10);
    ELSE
        LET tresult = tresult || '[FAIL] Agentot NE E vrzan. par_agentid='
                              || tpar_agentid_pol || ' promotor=' || tpromotor || CHR(10);
    END IF;
END IF;

-- Posrednik blok (netreba flag, linii 198-207 vo glavnata procedura)
IF tpromotor <> 0 AND tpromotor <> tpar_agentid THEN
    LET tresult = tresult || '[FAIL] POSREDNIK BLOK: promotor_par_agent=' || tpromotor
                          || ' != ' || tpar_agentid || ' -> ke se preskokne.' || CHR(10);
ELSE
    LET tresult = tresult || '[OK]   Posrednik blok: nema blokiranje.' || CHR(10);
END IF;


-- ============================================================
-- BLOK 3: Status na agentot
-- ============================================================
SELECT nvl(par_status_aktiven, 'A') INTO tpar_status
FROM   par_agent WHERE par_agentid = tpar_agentid;

IF tpar_status = 'Z' THEN
    LET tresult = tresult || '[FAIL] Agent status=Z (zatvoren) -> ke se preskokne.' || CHR(10);
ELSE
    LET tresult = tresult || '[OK]   Status na agent: ' || tpar_status || CHR(10);
END IF;


-- ============================================================
-- BLOK 4: Aktiven zapis vo provizija_agent so tip P za mesecot
-- ============================================================
SELECT COUNT(*) INTO tkolku
FROM   provizija_agent
WHERE  par_agentid = tpar_agentid
  AND  ((tdo_datum BETWEEN pag_datumod AND pag_datumdo) OR
        (tdo_datum >= pag_datumod AND pag_datumdo IS NULL));

IF tkolku = 0 THEN
    LET tresult = tresult || '[FAIL] Nema aktiven zapis vo provizija_agent za '
                          || tmesec || '/' || tgodina || CHR(10);
ELSE
    SELECT COUNT(*) INTO tpar_provtipid
    FROM   provizija_agent pa, par_provizijadef pd, par_provizijatip pt
    WHERE  pa.par_agentid = tpar_agentid
      AND  pd.par_provizijadefid = pa.par_provizijadefid
      AND  pt.par_provizijatipid = pd.par_provizijatipid
      AND  pt.tip_provizija = 'P'
      AND  ((tdo_datum BETWEEN pag_datumod AND pag_datumdo) OR
            (tdo_datum >= pag_datumod AND pag_datumdo IS NULL));

    IF tpar_provtipid = 0 THEN
        LET tresult = tresult || '[FAIL] Zapis postoi vo provizija_agent no tip_provizija<>P.' || CHR(10);
    ELSE
        LET tresult = tresult || '[OK]   Aktiven zapis vo provizija_agent so tip P.' || CHR(10);
    END IF;
END IF;


-- ============================================================
-- BLOK 5: sifra_polisa i skadenca_datum_od
-- ============================================================
SELECT sifra_polisa INTO tsifra_polisa FROM os_produkt WHERE os_produktid = tos_produktid;
LET tresult = tresult || '[INFO] sifra_polisa=' || tsifra_polisa
                      || '  datum_ponuda=' || tdatum_ponuda
                      || '  skadenca=' || tskadenca || CHR(10);

IF tsifra_polisa = '19' THEN
    LET tresult = tresult || '[WARN] sifra=19 -> bodovite se preskoknat, no presmetkata e mozna.' || CHR(10);
END IF;

IF tskadenca < DATE('01.02.2023') THEN
    LET tresult = tresult || '[FAIL] skadenca_datum_od=' || tskadenca
                          || ' < 01.02.2023 -> ne vleguva vo bodovi.' || CHR(10);
ELSE
    LET tresult = tresult || '[OK]   skadenca_datum_od e >= 01.02.2023.' || CHR(10);
END IF;


-- ============================================================
-- BLOK 6: fin_stavka - knizenja 285/1128/1567
-- ============================================================
SELECT COUNT(*), MIN(datum), MAX(datum)
INTO   tkolku, tdatum_min_fin, tdatum_max_fin
FROM   fin_stavka f, os_polisa p
WHERE  p.os_polisaid = f.os_polisaid
  AND  p.os_polisaid = tos_polisaid
  AND  f.par_tip_kniziid IN (285, 1128, 1567)
  AND  iznos_p IS NOT NULL;

IF tkolku = 0 THEN
    LET tresult = tresult || '[FAIL] Nema fin_stavka so par_tip_kniziid IN(285,1128,1567).' || CHR(10);
ELSE
    LET tresult = tresult || '[OK]   fin_stavka: ' || tkolku || ' zapisi  ('
                          || tdatum_min_fin || ' - ' || tdatum_max_fin || ')' || CHR(10);

    -- Dali datumot e vo dozvoleniot period za bodovi
    SELECT COUNT(*) INTO tkolku
    FROM   fin_stavka f, os_polisa p
    WHERE  p.os_polisaid = f.os_polisaid
      AND  p.os_polisaid = tos_polisaid
      AND  f.par_tip_kniziid IN (285, 1128, 1567)
      AND  iznos_p IS NOT NULL
      AND  datum BETWEEN DATE('01.02.2023') AND tdo_datum
      AND  p.datum_polisa <= tdo_datum + 15 UNITS DAY;

    IF tkolku = 0 THEN
        LET tresult = tresult || '[FAIL] fin_stavka postoi no datum e NADVOR od dozvoleniot period'
                              || ' (01.02.2023 - ' || tdo_datum || ').' || CHR(10);
    ELSE
        LET tresult = tresult || '[OK]   fin_stavka ima ' || tkolku || ' zapisi vo dozvoleniot period.' || CHR(10);
    END IF;
END IF;


-- ============================================================
-- BLOK 7: provizija_promotori_bodovi - dali veche postoi
-- ============================================================
SELECT COUNT(*) INTO tkolku_bodovi
FROM   provizija_promotori_bodovi
WHERE  vrati_polisa(os_polisaid) = vrati_polisa(tos_polisaid)
  AND  par_agentid = tpar_agentid
  AND  tip_produkcija = '1';

IF tkolku_bodovi > 0 THEN
    LET tresult = tresult || '[INFO] Bodovi VEK]E POSTOI (' || tkolku_bodovi
                          || ' zapisi, tip=1). Presmetkata treba da prodolzi.' || CHR(10);
ELSE
    LET tresult = tresult || '[WARN] Nema bodovi (provizija_promotori_bodovi tip=1)'
                          || ' -> toa e prichinata nema isplata.' || CHR(10);
END IF;


-- ============================================================
-- BLOK 8: Celosna naplata PO FAKTURA (kako vo glavnata procedura)
-- Glavnata procedura proveruva tcela_naplata=tiznos_d
-- per os_aneks_fakturaid, ne vkupno za polisata.
-- ============================================================
LET tfakt_vkupno    = 0;
LET tfakt_plateni   = 0;
LET tfakt_neplateni = 0;

LET tresult = tresult || '[INFO] Naplata po faktura (period: last 3 meseci do ' || tdo_datum || '):' || CHR(10);

FOREACH
    SELECT DISTINCT f.os_aneks_fakturaid, f.datum
    INTO   tfakt_id, tfakt_datum
    FROM   fin_stavka f, os_polisa p
    WHERE  p.os_polisaid = f.os_polisaid
      AND  p.os_polisaid = tos_polisaid
      AND  f.par_tip_kniziid IN (285, 1128, 1567, 2974)
      AND  f.iznos_p IS NOT NULL
      AND  f.datum BETWEEN ADD_MONTHS(tdo_datum, -3) AND tdo_datum
    ORDER BY f.datum

    -- Iznos plateno za taa faktura (kako vo procedura linija 845)
    SELECT nvl(SUM(iznos_p), 0)
    INTO   tfakt_naplata
    FROM   fin_stavka
    WHERE  os_aneks_fakturaid = tfakt_id
      AND  datum <= tdo_datum
      AND  iznos_p IS NOT NULL
      AND  par_tip_kniziid IN (285, 1128, 1567, 2974);

    -- Iznos dolg za taa faktura (kako vo procedura linija 837)
    SELECT nvl(SUM(iznos_d), 0)
    INTO   tfakt_dolg
    FROM   fin_stavka
    WHERE  os_aneks_fakturaid = tfakt_id
      AND  iznos_d IS NOT NULL;

    LET tfakt_vkupno = tfakt_vkupno + 1;

    IF tfakt_naplata = tfakt_dolg THEN
        LET tfakt_plateni = tfakt_plateni + 1;
        LET tresult = tresult || '  [OK]   faktura=' || tfakt_id
                              || ' datum=' || tfakt_datum
                              || ' naplata=' || tfakt_naplata
                              || ' dolg=' || tfakt_dolg || ' -> CELOSO NAPLATENA' || CHR(10);
    ELSE
        LET tfakt_neplateni = tfakt_neplateni + 1;
        LET tresult = tresult || '  [FAIL] faktura=' || tfakt_id
                              || ' datum=' || tfakt_datum
                              || ' naplata=' || tfakt_naplata
                              || ' dolg=' || tfakt_dolg
                              || ' razlika=' || (tfakt_dolg - tfakt_naplata) || ' -> NE NAPLATENA' || CHR(10);
    END IF;
END FOREACH;

LET tresult = tresult || '[INFO] Fakturi vkupno=' || tfakt_vkupno
                      || '  celoso plateni=' || tfakt_plateni
                      || '  neplateni=' || tfakt_neplateni || CHR(10);

IF tfakt_vkupno = 0 THEN
    LET tresult = tresult || '[WARN] Nema faktури vo poslednite 3 meseci -> presmetkata nema da se izvede.' || CHR(10);
ELSE
    IF tfakt_plateni > 0 THEN
        LET tresult = tresult || '[OK]   Ima ' || tfakt_plateni || ' celoso plateni fakturi -> isplatata TREBA da se presmetka.' || CHR(10);
    ELSE
        LET tresult = tresult || '[FAIL] Nema nitu edna celoso platena faktura -> isplatata e blokirana.' || CHR(10);
    END IF;
END IF;


-- ============================================================
-- BLOK 9: provizija_promotori_presmetka - dali veche postoi
-- ============================================================
SELECT COUNT(*) INTO tkolku_presmetka
FROM   provizija_promotori_presmetka ppp, provizija_agent pa
WHERE  ppp.provizija_agentid = pa.par_provizija_agentid
  AND  pa.par_agentid = tpar_agentid
  AND  ppp.os_aneks_fakturaid IN (
           SELECT DISTINCT os_aneks_fakturaid
           FROM   fin_stavka f2, os_polisa p2
           WHERE  p2.os_polisaid = f2.os_polisaid
             AND  p2.os_polisaid = tos_polisaid
       );

IF tkolku_presmetka > 0 THEN
    LET tresult = tresult || '[INFO] Presmetka VEK]E POSTOI (' || tkolku_presmetka
                          || ' zapisi vo provizija_promotori_presmetka).' || CHR(10);
ELSE
    LET tresult = tresult || '[WARN] Nema zapis vo provizija_promotori_presmetka za ovoj agent+polisa.' || CHR(10);
END IF;


-- ============================================================
-- BLOK 10: Specijalen uslov za agent 1809/1922 (datum_ponuda)
-- Agent 1809 go smenil par_provizijadefid (274->286) na 01.06.2022.
-- Za stari polisi (datum_ponuda < 01.06.2022) treba star zapis (274),
-- za novi polisi (datum_ponuda >= 01.06.2022) treba nov zapis (286).
-- Zatoa vo glavnata procedura (linii 1327-1344) se bara po datum_ponuda.
-- ============================================================
IF tpar_agentid = 1809 OR tpar_agentid = 1922 THEN
    LET tresult = tresult || '[INFO] Spec.uslov 1809/1922: provizija_agent se bara po datum_ponuda='
                          || tdatum_ponuda || CHR(10);

    SELECT COUNT(*), MAX(par_provizijadefid), MAX(pag_datumod), MAX(pag_datumdo)
    INTO   tkolku, tblok10_defid, tblok10_datumod, tblok10_datumdo
    FROM   provizija_agent
    WHERE  par_agentid = tpar_agentid
      AND  ((tdatum_ponuda BETWEEN pag_datumod AND pag_datumdo) OR
            (tdatum_ponuda >= pag_datumod AND pag_datumdo IS NULL));

    IF tkolku = 0 THEN
        LET tresult = tresult || '[FAIL] Nema zapis vo provizija_agent koj go pokriva datum_ponuda='
                              || tdatum_ponuda || ' -> presmetkata nema da se izvede.' || CHR(10);
    ELSE
        LET tresult = tresult || '[OK]   Najden zapis: par_provizijadefid=' || tblok10_defid
                              || '  period=' || tblok10_datumod || ' - '
                              || nvl(tblok10_datumdo::VARCHAR(20), 'OTVOREN') || CHR(10);
    END IF;
END IF;


-- ============================================================
-- BLOK 11: par_provizijaisp - procent za taa godina osiguruvanje
-- ============================================================
LET tkoja_god = tgodina::INT - YEAR(tskadenca) + 1;
LET tresult = tresult || '[INFO] koja_god=' || tkoja_god || CHR(10);

SELECT COUNT(*) INTO tkolku
FROM   par_provizijaisp pi, par_provizijatip pt
WHERE  pi.par_provizijatipid = pt.par_provizijatipid
  AND  pt.tip_provizija = 'P'
  AND  pi.ppi_fromday = tkoja_god;

IF tkolku = 0 THEN
    LET tresult = tresult || '[FAIL] Nema procent vo par_provizijaisp za tip P, koja_god='
                          || tkoja_god || ' -> tprovizija ke bide 0.' || CHR(10);
ELSE
    SELECT nvl(SUM(ppi_valueproc), 0) INTO tproc
    FROM   par_provizijaisp pi, par_provizijatip pt
    WHERE  pi.par_provizijatipid = pt.par_provizijatipid
      AND  pt.tip_provizija = 'P'
      AND  pi.ppi_fromday = tkoja_god;
    LET tresult = tresult || '[OK]   Procent za provizija: ' || tproc || '% (koja_god=' || tkoja_god || ')' || CHR(10);
END IF;


-- ============================================================
-- BLOK 12: Agent 1809 kako NADREDEN (supervisor) - tip_produkcija='2'
-- Tretiot foreach vo glavnata procedura (linii 1292-1498)
-- Provizijata za nadredeniot se presmetuva od bodovite na podredenite.
-- ============================================================

-- 12a: Dali 1809 e nadreden vo par_agent_st vo toj period
SELECT COUNT(*) INTO tpodredeni
FROM   par_agent_st
WHERE  par_nadreden_agentid = tpar_agentid
  AND  ((tdo_datum BETWEEN pas_datumod AND pas_datumdo) OR
        (tdo_datum >= pas_datumod AND pas_datumdo IS NULL));

LET tresult = tresult || '[INFO] NADREDEN BLOK: agent ' || tpar_agentid
                      || ' ima ' || tpodredeni || ' podredeni vo par_agent_st za ovoj mesec.' || CHR(10);

IF tpodredeni = 0 THEN
    LET tresult = tresult || '[WARN] Agentot nema podredeni -> tretiot foreach nema da generira nadredena provizija.' || CHR(10);
END IF;

-- 12b: Dali postojat bodovi (tip=2) za nadredeniot od polisata
SELECT COUNT(*) INTO tpodred_bodovi
FROM   provizija_promotori_bodovi
WHERE  vrati_polisa(os_polisaid) = vrati_polisa(tos_polisaid)
  AND  par_agentid = tpar_agentid
  AND  tip_produkcija = '2';

IF tpodred_bodovi > 0 THEN
    LET tresult = tresult || '[OK]   Postojat bodovi tip=2 za nadredeniot za ovaa polisa (' || tpodred_bodovi || ' zapisi).' || CHR(10);
ELSE
    LET tresult = tresult || '[WARN] Nema bodovi tip=2 za nadredeniot za ovaa polisa.' || CHR(10);
END IF;

-- 12c: Specijalen uslov za 1809/1922 kako nadreden:
--      provizija_agent se bara po datum_ponuda na polisata na podredeniot
--      (linii 1327-1344 vo glavnata procedura)
IF tpar_agentid = 1809 OR tpar_agentid = 1922 THEN
    SELECT COUNT(*) INTO tnad_pag_pokriva
    FROM   provizija_agent
    WHERE  par_agentid = tpar_agentid
      AND  ((tdatum_ponuda BETWEEN pag_datumod AND pag_datumdo) OR
            (tdatum_ponuda >= pag_datumod AND pag_datumdo IS NULL));

    LET tresult = tresult || '[INFO] NADREDEN spec.uslov 1809/1922: bara provizija_agent po datum_ponuda='
                          || tdatum_ponuda || CHR(10);

    IF tnad_pag_pokriva = 0 THEN
        LET tresult = tresult || '[FAIL] NADREDEN: Nema zapis vo provizija_agent koj go pokriva datum_ponuda='
                              || tdatum_ponuda
                              || ' -> nadredenata provizija nema da se presmetka!' || CHR(10);
    ELSE
        LET tresult = tresult || '[OK]   NADREDEN: Najden zapis vo provizija_agent za datum_ponuda=' || tdatum_ponuda || CHR(10);
    END IF;
END IF;

-- 12d: Dali postoi presmetka (tip=2) za nadredeniot
SELECT COUNT(*) INTO tpodred_presm
FROM   provizija_promotori_presmetka ppp, provizija_agent pa
WHERE  ppp.provizija_agentid = pa.par_provizija_agentid
  AND  pa.par_agentid = tpar_agentid
  AND  ppp.os_aneks_fakturaid IN (
           SELECT DISTINCT os_aneks_fakturaid
           FROM   fin_stavka f2, os_polisa p2
           WHERE  p2.os_polisaid = f2.os_polisaid
             AND  p2.os_polisaid = tos_polisaid
       );

IF tpodred_presm > 0 THEN
    LET tresult = tresult || '[INFO] NADREDEN: Presmetka VEK]E POSTOI (' || tpodred_presm || ' zapisi).' || CHR(10);
ELSE
    LET tresult = tresult || '[WARN] NADREDEN: Nema presmetka vo provizija_promotori_presmetka za ovoj agent+polisa.' || CHR(10);
END IF;

-- ============================================================
-- BLOK 13: Vtoro nivo nadreden (nadreden na nadredeniot)
-- Odgovara na while loopot vo glavnata procedura (linii 710-756)
-- ============================================================

-- Prvo bara par_nadreden_agentid od aktivniot zapis (ne NULL proverka)
SELECT nvl(par_nadreden_agentid, 0) INTO tnad2_agentid
FROM   par_agent_st
WHERE  par_agentid = tpar_agentid
  AND  ((tdo_datum BETWEEN pas_datumod AND pas_datumdo) OR
        (tdo_datum >= pas_datumod AND pas_datumdo IS NULL));

IF tnad2_agentid = 0 THEN
    LET tresult = tresult || '[INFO] 2.NIVO NADREDEN: Agentot ' || tpar_agentid
                          || ' NEMA nadreden (par_nadreden_agentid=NULL) -> while loop ne se izvrsуva, toa e OK.' || CHR(10);
ELSE
    LET tresult = tresult || '[INFO] 2.NIVO NADREDEN: Nadredent na ' || tpar_agentid
                          || ' e agentid=' || tnad2_agentid || CHR(10);

    -- Proverka dali vtoroto nivo ima aktiven zapis vo provizija_agent
    SELECT COUNT(*) INTO tnad2_pokriva
    FROM   provizija_agent
    WHERE  par_agentid = tnad2_agentid
      AND  ((tdo_datum BETWEEN pag_datumod AND pag_datumdo) OR
            (tdo_datum >= pag_datumod AND pag_datumdo IS NULL));

    IF tnad2_pokriva = 0 THEN
        LET tresult = tresult || '[FAIL] 2.NIVO: Nadredeniot (agentid=' || tnad2_agentid
                              || ') nema aktiven zapis vo provizija_agent za ' || tmesec || '/' || tgodina
                              || ' -> vtoroto nivo nema da dobie provizija.' || CHR(10);
    ELSE
        LET tresult = tresult || '[OK]   2.NIVO: Nadredeniot (agentid=' || tnad2_agentid
                              || ') ima aktiven zapis vo provizija_agent.' || CHR(10);
    END IF;
END IF;


LET tresult = tresult || '=== KRAJ ===' || CHR(10);
RETURN tresult;

END FUNCTION;
