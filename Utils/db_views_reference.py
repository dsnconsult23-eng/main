"""
Референца на Informix VIEW дефиниции користени во извештаите за фактури
(routers/report_fakturi.py). Чувани тука за брз пристап до точните
колони/join-ови без потреба повторно да се бараат од базата.

Не се извршуваат од овој фајл — ова е само документација/константи.
"""

REPORT_FAKTURI_COLUMNS = [
    "os_aneks_fakturaid", "os_aneks", "os_aneksid", "par_yearid", "faktura",
    "datum_aneks", "data_faktura", "data_valuta", "br_rati", "par_clientid",
    "client_id", "client_naziv", "tip_knizi", "iznos", "iznos_denari",
    "naplata", "naplata_den", "polisa_broj", "datum_knizenje",
    "dogovoruvac_prav_fiz", "rata", "broker_par_client", "posrednik_par_client",
    "par_agentid", "broker_name", "posrednik_name", "par_agent_name", "f_rs",
    "zamenska_polisa", "promotor_id", "promotor_name", "usercreated",
    "kreditna_partija", "nacin_plakanje", "skadenca_datum_od",
    "sap_risk_business", "rok_plakanje", "os_polisaid", "premija_tbs",
    "par_prod_kanalid", "prodazen_kanal", "ponuda_broj",
]

REPORT_FAKTURI_VIEW_SQL = """
CREATE VIEW vesna.report_fakturi (
    os_aneks_fakturaid, os_aneks, os_aneksid, par_yearid, faktura,
    datum_aneks, data_faktura, data_valuta, br_rati, par_clientid,
    client_id, client_naziv, tip_knizi, iznos, iznos_denari,
    naplata, naplata_den, polisa_broj, datum_knizenje,
    dogovoruvac_prav_fiz, rata, broker_par_client, posrednik_par_client,
    par_agentid, broker_name, posrednik_name, par_agent_name, f_rs,
    zamenska_polisa, promotor_id, promotor_name, usercreated,
    kreditna_partija, nacin_plakanje, skadenca_datum_od,
    sap_risk_business, rok_plakanje, os_polisaid, premija_tbs,
    par_prod_kanalid, prodazen_kanal, ponuda_broj
) AS
SELECT
    x0.os_aneks_fakturaid,
    x1.os_aneks,
    x0.os_aneksid,
    x1.par_yearid,
    (x1.os_aneks || '/' || vesna.vrati_godina(x1.par_yearid) || '-' || x0.rata),
    CASE WHEN (x0.f_rs = 'S' AND x4.datecreated > x1.datum_aneks)
         THEN x4.datecreated ELSE x1.datum_aneks END,
    x0.data_faktura,
    x0.data_valuta,
    x1.br_rati,
    CASE WHEN x4.par_tip_platiid != 36 THEN x1.par_clientid ELSE x4.dogovoruvac_par_client END,
    CASE WHEN x4.par_tip_platiid != 36
         THEN vesna.vrati_client_id(x1.par_clientid)
         ELSE vesna.vrati_client_id(x4.dogovoruvac_par_client) END,
    CASE WHEN x4.par_tip_platiid != 36
         THEN vesna.vrati_client_name(x1.par_clientid)
         ELSE vesna.vrati_client_name(x4.dogovoruvac_par_client) END,
    vesna.vrati_tip_knizi(x0.par_tip_kniziid),
    x0.iznos,
    x0.iznos_denari,
    vesna.vrati_naplata(x0.os_aneks_fakturaid),
    vesna.vrati_naplata_den(x0.os_aneks_fakturaid),
    (vesna.vrati_sifra_polisa(x2.os_ponudaid) || '/' || x2.polisa_broj),
    x3.dat_nalog,
    CASE WHEN x4.par_tip_platiid != 36
         THEN vesna.vrati_client_pf(x1.par_clientid)
         ELSE vesna.vrati_client_pf(x4.dogovoruvac_par_client) END,
    x0.rata,
    x4.broker_par_client,
    x4.posrednik_par_client,
    x4.par_agentid,
    vesna.vrati_client_name(x4.broker_par_client),
    vesna.vrati_client_name(x4.posrednik_par_client),
    vesna.vrati_agent_name(x4.par_agentid),
    x3.f_rs,
    CASE WHEN (x4.par_polisa_promenaid = 517 AND x0.data_valuta < x4.datecreated)
         THEN vesna.vrati_polisa_(x4.os_ponudaid) END,
    x4.promotor_par_agent,
    vesna.vrati_agent_name(x4.promotor_par_agent),
    x4.usercreated,
    x4.kreditna_partija,
    vesna.vrati_nacin_isplata_name(x4.os_produkt_uplataid),
    x4.skadenca_datum_od,
    vesna.vrati_sap_risk_business(x0.os_ponuda_detailid),
    x4.rok_plakanje,
    x2.os_polisaid,
    vesna.vrati_premija_tbs(x4.os_ponudaid),
    x4.par_prod_kanalid,
    vesna.vrati_prod_kanal(x4.par_prod_kanalid),
    x4.ponuda_broj
FROM
    viki.os_aneks_faktura x0,
    viki.os_aneks x1,
    viki.os_polisa x2,
    viki.fin_stavka x3,
    viki.os_ponuda x4
WHERE
    x0.os_aneksid = x1.os_aneksid
    AND x2.os_polisaid = x1.os_polisaid
    AND x3.os_aneks_fakturaid = x0.os_aneks_fakturaid
    AND x3.iznos_d IS NOT NULL
    AND x4.os_ponudaid = x2.os_ponudaid
    AND NVL(x3.f_rs, 'R') != 'N';
"""

KARTICA_KL_SINTETIKA_COLUMNS = [
    "fin_stavkaid", "datum", "datum_knizi", "par_tip_dokumentid", "par_clientid",
    "par_agent_id", "par_filijalaid", "par_tip_dokument", "polisa",
    "agent_naziv", "filijala_naziv", "client_id", "client_naziv",
    "iznos_d", "iznos_d_den", "iznos_p", "iznos_p_den", "dogovoruvac_prav_fiz",
    "faktura", "fakturaid", "fakturaint", "zbiren_aneks", "rizikid", "rizik",
]

KARTICA_KL_SINTETIKA_VIEW_SQL = """
CREATE VIEW vesna.kartica_kl_sintetika (
    fin_stavkaid, datum, datum_knizi, par_tip_dokumentid, par_clientid,
    par_agent_id, par_filijalaid, par_tip_dokument, polisa,
    agent_naziv, filijala_naziv, client_id, client_naziv,
    iznos_d, iznos_d_den, iznos_p, iznos_p_den, dogovoruvac_prav_fiz,
    faktura, fakturaid, fakturaint, zbiren_aneks, rizikid, rizik
) AS
SELECT
    x1.fin_stavkaid, x1.datum, x1.datum_knizi, x1.par_tip_dokumentid, x1.par_clientid,
    x1.par_agent_id, x1.par_filijalaid, x2.par_tip_dokument,
    (x5.sifra_polisa || '/' || x3.polisa_broj || ' ' || x3.polisa_pod_broj),
    vesna.vrati_agent_name(x1.par_agent_id),
    vesna.vrati_filijala_name(x1.par_filijalaid),
    vesna.vrati_client_id(x1.par_clientid),
    vesna.vrati_client_name(x1.par_clientid),
    SUM(x1.iznos_d), SUM(x1.iznos_d_den), SUM(x1.iznos_p), SUM(x1.iznos_p_den),
    vesna.vrati_client_pf(x4.dogovoruvac_par_client),
    vesna.vrati_faktura_broj(x1.os_aneks_fakturaid),
    vesna.vrati_faktura_brojint(x1.os_aneks_fakturaid),
    vesna.vrati_faktura_brojint(x1.os_aneks_fakturaid),
    vesna.vrati_zbiren_aneks_broj(x1.os_aneks_fakturaid),
    appuser.vrati_client_rizikid(x1.par_clientid),
    vesna.vrati_client_rizik(x1.par_clientid)
FROM
    viki.fin_stavka x1, viki.par_tip_dokument x2, viki.os_polisa x3,
    viki.os_ponuda x4, viki.os_produkt x5, viki.os_aneks_faktura x6, viki.os_aneks x7
WHERE
    x6.os_aneks_fakturaid = x1.os_aneks_fakturaid
    AND x2.par_tip_dokumentid = x1.par_tip_dokumentid
    AND x7.os_aneksid = x6.os_aneksid
    AND x1.os_polisaid = x3.os_polisaid
    AND x3.os_ponudaid = x4.os_ponudaid
    AND x5.os_produktid = x4.os_produktid
    AND x1.datum <= TODAY
    AND NVL(x1.f_rs, 'R') != 'N'
    AND x2.znak != 0
    AND x1.par_tip_dokumentid = 285
GROUP BY 1, x1.datum, x1.datum_knizi, x1.par_tip_dokumentid, x1.par_clientid,
    x1.par_agent_id, x1.par_filijalaid, x2.par_tip_dokument, 9, 10, 11, 12, 13,
    18, 19, 20, 21, 22, 23, 24
ORDER BY 20, 2;
"""

# Забелешка: os_ponuda.banka_par_client → vesna.par_client.par_clientid
# е клиентот со "административна забрана" врз полисата (join преку
# os_polisa.os_polisaid → os_ponuda.os_ponudaid). Ова НЕ е дел од
# ниту една од горните views — се додава рачно преку join во
# routers/report_fakturi.py (_build_sql, _build_sintetika_sql).
