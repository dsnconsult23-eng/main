-- Debug procedura za agent_id = 679 - celosna logika od presmetka_prov_agenti_zbiren_test
-- Pokrenuvanje: EXECUTE PROCEDURE vesna.debug_agent_679('05', '2026', 1);

DROP PROCEDURE vesna.debug_agent_679;
CREATE PROCEDURE vesna.debug_agent_679(tmesec CHAR(2), tgodina CHAR(4), tuser_id INT)
    RETURNING CHAR(200);

DEFINE tod_odatum, tdo_datum DATE;
DEFINE tpar_yearid, tpar_provizijadefid, tpar_provizijatipid, tppd_nadredenid INT;
DEFINE tstartni_poeni_lp, tstartni_poeni_tp DEC;
DEFINE tbodovi_licna_prod, tbodovi_timska_prod, tbodovi_period DEC;
DEFINE tnovi_polisi_prov_lp, tnovi_polisi_prov_tp DEC;
DEFINE tstorno_polisi_prov_lp, tnovi_storno_bodovi_lp DEC;
DEFINE tstorno_polisi_prov_tp, tnovi_storno_bodovi_lp_lc DEC;
DEFINE tnovi_storno_bodovi_tp, tnovi_storno_bodovi_tp_lc DEC;
DEFINE tstorno_polisi_prov_tp2 DEC;
DEFINE tnovi_storno_bodovi DEC;
DEFINE tpps_bodovido, tbodovi_sledna_pozicija DEC;

ON EXCEPTION
    RETURN 'GRESKA vo izvrsuvanjeto';
END EXCEPTION;

SET ISOLATION TO DIRTY READ;
SET DEBUG FILE TO 'err_presmetka_prov111.sql';
TRACE ON;

LET tod_odatum = '01.' || tmesec || '.' || tgodina;
LET tdo_datum  = LAST_DAY(tod_odatum);

SELECT par_yearid INTO tpar_yearid
FROM par_year WHERE par_year = tgodina;

-- ── 1. Bodovi tekoven mesec (PPB + LC) ───────────────────────────────
SELECT
    NVL(SUM(CASE WHEN tip_produkcija='1' THEN br_bodovi ELSE 0 END), 0),
    NVL(SUM(CASE WHEN tip_produkcija='1' THEN iznos_bod ELSE 0 END), 0),
    NVL(SUM(CASE WHEN tip_produkcija='2' THEN br_bodovi ELSE 0 END), 0),
    NVL(SUM(CASE WHEN tip_produkcija='2' THEN iznos_bod ELSE 0 END), 0)
INTO tbodovi_licna_prod, tnovi_polisi_prov_lp,
     tbodovi_timska_prod, tnovi_polisi_prov_tp
FROM (
    SELECT tip_produkcija, br_bodovi, iznos_bod
    FROM provizija_promotori_bodovi
    WHERE par_agentid = 679 AND par_statusid = 1
      AND mesec = tmesec AND vrati_godina(par_yearid) = tgodina
    UNION ALL
    SELECT tip_produkcija, br_bodovi, iznos_bod
    FROM lc_provizija_agent_bodovi
    WHERE par_agentid = 679 AND par_statusid = 1
      AND mesec = tmesec AND vrati_godina(par_yearid) = tgodina
) x;

-- ── 2. Startni poeni ─────────────────────────────────────────────────
LET tstartni_poeni_lp   = 0;
LET tstartni_poeni_tp   = 0;
LET tpar_provizijadefid = 0;
LET tpar_provizijatipid = 0;

SELECT FIRST 1
    NVL(startni_poeni_lp, 0), NVL(startni_poeni, 0),
    par_provizijadefid, par_provizijatipid
INTO tstartni_poeni_lp, tstartni_poeni_tp,
     tpar_provizijadefid, tpar_provizijatipid
FROM provizija_agent
WHERE par_agentid = 679
  AND ((tdo_datum BETWEEN pag_datumod AND pag_datumdo)
       OR (tdo_datum >= pag_datumod AND pag_datumdo IS NULL));

-- ── 3. Storno LP od PPB ───────────────────────────────────────────────
LET tstorno_polisi_prov_lp = 0;
LET tnovi_storno_bodovi_lp = 0;

SELECT
    SUM(CASE WHEN NVL(duplirani_bodovi,0)=0 THEN iznos_bod ELSE iznos_bod*2 END),
    SUM(br_bodovi) + NVL(SUM(NVL(duplirani_bodovi,0)), 0)
INTO tstorno_polisi_prov_lp, tnovi_storno_bodovi_lp
FROM provizija_promotori_bodovi
WHERE datum_presmetka < tod_odatum
  AND par_agentid = 679 AND tip_produkcija = '1' AND par_statusid = 1;

-- ── 4. Fallback LC za LP ──────────────────────────────────────────────
LET tnovi_storno_bodovi_lp_lc = 0;
LET tstorno_polisi_prov_tp2   = 0;

IF tstorno_polisi_prov_lp IS NULL THEN
    SELECT SUM(iznos_bod), SUM(br_bodovi)
    INTO tstorno_polisi_prov_lp, tnovi_storno_bodovi_lp
    FROM lc_provizija_agent_bodovi
    WHERE datum_presmetka < tod_odatum AND par_agentid = 679
      AND par_provizijatipid = tpar_provizijatipid
      AND par_statusid = 1 AND tip_produkcija = '1';
    LET tnovi_storno_bodovi_lp_lc = NVL(tnovi_storno_bodovi_lp, 0);
END IF;

IF tstorno_polisi_prov_lp IS NULL THEN LET tstorno_polisi_prov_lp = 0; END IF;
IF tnovi_storno_bodovi_lp IS NULL THEN LET tnovi_storno_bodovi_lp = 0; END IF;

-- ── 5. Storno TP od PPB ───────────────────────────────────────────────
LET tstorno_polisi_prov_tp  = 0;
LET tnovi_storno_bodovi_tp  = 0;
LET tnovi_storno_bodovi_tp_lc = 0;

SELECT SUM(iznos_bod), SUM(br_bodovi)
INTO tstorno_polisi_prov_tp, tnovi_storno_bodovi_tp
FROM provizija_promotori_bodovi
WHERE datum_presmetka < tod_odatum
  AND par_agentid = 679 AND tip_produkcija = '2' AND par_statusid = 1;

-- ── 6. Fallback LC za TP ──────────────────────────────────────────────
IF tstorno_polisi_prov_tp IS NULL THEN
    SELECT SUM(iznos_bod), SUM(br_bodovi)
    INTO tstorno_polisi_prov_tp, tnovi_storno_bodovi_tp
    FROM lc_provizija_agent_bodovi
    WHERE datum_presmetka < tod_odatum AND par_agentid = 679
      AND par_statusid = 1 AND tip_produkcija = '2';
    LET tnovi_storno_bodovi_tp_lc = NVL(tnovi_storno_bodovi_tp, 0);
END IF;

IF tstorno_polisi_prov_tp IS NULL THEN LET tstorno_polisi_prov_tp = 0; END IF;
IF tnovi_storno_bodovi_tp IS NULL THEN LET tnovi_storno_bodovi_tp = 0; END IF;

-- ── 7. Dodavanje startni poeni ────────────────────────────────────────
LET tnovi_storno_bodovi_lp = tnovi_storno_bodovi_lp + tstartni_poeni_lp;
LET tnovi_storno_bodovi_tp = tnovi_storno_bodovi_tp + tstartni_poeni_tp;

-- ── 8. Zbir ──────────────────────────────────────────────────────────
LET tbodovi_period      = tbodovi_licna_prod + tbodovi_timska_prod;
LET tnovi_storno_bodovi = tnovi_storno_bodovi_lp + tnovi_storno_bodovi_tp;

-- ── 9. Sledna pozicija ────────────────────────────────────────────────
LET tppd_nadredenid         = 0;
LET tpps_bodovido           = 0;
LET tbodovi_sledna_pozicija = 0;

SELECT NVL(ppd_nadredenid, 0) INTO tppd_nadredenid
FROM par_provizijadef WHERE par_provizijadefid = tpar_provizijadefid;

IF tppd_nadredenid <> 0 THEN
    SELECT pps_bodoviod INTO tpps_bodovido
    FROM par_provizijadef_St
    WHERE par_provizijadefid = tppd_nadredenid
      AND NVL(pps_valueden, 1) = '1'
      AND ((tdo_datum BETWEEN pps_datumod AND pps_datumdo)
           OR (tdo_datum >= pps_datumod AND pps_datumdo IS NULL));
    LET tbodovi_sledna_pozicija = tpps_bodovido - (tbodovi_period + tnovi_storno_bodovi);
    IF tbodovi_sledna_pozicija < 0 THEN LET tbodovi_sledna_pozicija = 0; END IF;
END IF;

-- ── RETURN NA KRAJ ───────────────────────────────────────────────────
RETURN
    '1.tekoven: bod_LP=' || tbodovi_licna_prod || ' iznos_LP=' || tnovi_polisi_prov_lp
    || ' bod_TP=' || tbodovi_timska_prod || ' iznos_TP=' || tnovi_polisi_prov_tp
    || ' | 2.startni: lp=' || tstartni_poeni_lp || ' tp=' || tstartni_poeni_tp
    || ' | 3.storno_LP(PPB): iznos=' || tstorno_polisi_prov_lp || ' bodovi=' || (tnovi_storno_bodovi_lp - tstartni_poeni_lp)
    || ' lc_fallback=' || tnovi_storno_bodovi_lp_lc
    || ' | 4.storno_TP(PPB): iznos=' || tstorno_polisi_prov_tp || ' bodovi=' || (tnovi_storno_bodovi_tp - tstartni_poeni_tp)
    || ' lc_fallback=' || tnovi_storno_bodovi_tp_lc
    || ' | 5.po_startni: storno_lp=' || tnovi_storno_bodovi_lp || ' storno_tp=' || tnovi_storno_bodovi_tp
    || ' | 6.period=' || tbodovi_period || ' vk_storno=' || tnovi_storno_bodovi
    || ' rolling=' || tbodovi_sledna_pozicija;

END PROCEDURE;
