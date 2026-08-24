-- Book4.xlsx: контролирана проверка и ослободување за повторно книжење
-- Извор: 233 Excel реда, сведени на 185 уникатни пара (Фактура, SAP Risk Biznis).
-- ВАЖНО: Не се совпаѓа само по фактура, бидејќи една фактура може да има повеќе ризици.

CREATE TEMP TABLE book4_worklist (
    faktura             VARCHAR(40) NOT NULL,
    sap_risk_business   VARCHAR(40) NOT NULL
) WITH NO LOG;

INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('53631/2026-3', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('53631/2026-3', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('53617/2026-3', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('53617/2026-3', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('104589/2026-4', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('104589/2026-4', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('78010/2026-4', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('78010/2026-4', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('104589/2026-4', 'MK19020205');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('91988/2025-7', 'MK19020205');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('91988/2025-7', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('91988/2025-7', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106454/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('33633/2025-6', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('33633/2025-6', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84563/2025-10', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('89520/2025-8', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('89520/2025-8', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84577/2025-10', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84570/2025-10', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84570/2025-10', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84567/2025-10', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84567/2025-10', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84566/2025-10', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84565/2025-10', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84564/2025-10', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84564/2025-10', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84561/2025-10', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84556/2025-10', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84552/2025-10', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84552/2025-10', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84549/2025-10', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84549/2025-10', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84547/2025-10', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84547/2025-10', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84596/2025-10', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84596/2025-10', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('20513/2025-5', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('83310/2025-11', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('83310/2025-11', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('82225/2025-12', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('82225/2025-12', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('82218/2025-12', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('82218/2025-12', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('20513/2025-5', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106454/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106455/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106455/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106456/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106456/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106457/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106457/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106459/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106459/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106460/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106460/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106461/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106461/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106462/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106462/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106464/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106464/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106466/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106466/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106467/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106467/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106468/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106468/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106473/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106473/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106474/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106474/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106476/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106476/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106477/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106477/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106480/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106480/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106481/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106481/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106482/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106482/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106483/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106483/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106484/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106484/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106501/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106501/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84518/2025-10', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84518/2025-10', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84521/2025-10', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84521/2025-10', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84528/2025-10', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84530/2025-10', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84530/2025-10', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84531/2025-10', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('84546/2025-10', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('87215/2025-9', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('87215/2025-9', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('87216/2025-9', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('87216/2025-9', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('87217/2025-9', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('87217/2025-9', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('87218/2025-9', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('87218/2025-9', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('87184/2025-9', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('87184/2025-9', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('87193/2025-9', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('87193/2025-9', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('87196/2025-9', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('87196/2025-9', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('87198/2025-9', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('87198/2025-9', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('87199/2025-9', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('87199/2025-9', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('87200/2025-9', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('87200/2025-9', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('87201/2025-9', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('87201/2025-9', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('87226/2025-9', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('87226/2025-9', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('75985/2025-6', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('75985/2025-6', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('75989/2025-6', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('75989/2025-6', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('75992/2025-6', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('75992/2025-6', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('75995/2025-6', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('75995/2025-6', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('76001/2025-6', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('76001/2025-6', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('76002/2025-6', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('76002/2025-6', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('76005/2025-6', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('76005/2025-6', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('77960/2026-4', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('77960/2026-4', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('77975/2026-4', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('77975/2026-4', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('78038/2026-4', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('78038/2026-4', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('78542/2026-4', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('78542/2026-4', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('81127/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('81127/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('81135/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('81135/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('81148/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('81148/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('81152/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('81152/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('81154/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('81154/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106412/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106412/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106413/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106413/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106415/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106415/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106417/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106417/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106418/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106418/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106420/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106420/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106421/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106421/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106422/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106422/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106423/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106423/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106424/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106424/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106425/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106425/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106427/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106427/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106436/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106436/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106437/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106437/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106469/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106469/2026-1', 'MK19020202');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106571/2026-1', 'MK19020102');
INSERT INTO book4_worklist (faktura, sap_risk_business) VALUES ('106571/2026-1', 'MK19020202');

-- 1) Контрола: точно мапирање од report_fakturi до os_aneks_fakturaid.
SELECT
    wl.faktura,
    wl.sap_risk_business,
    rf.polisa_broj,
    rf.os_aneks_fakturaid,
    rf.datum_aneks,
    rf.data_faktura,
    rf.datum_knizenje,
    rf.tip_knizi,
    rf.iznos,
    rf.naplata,
    rf.f_rs
FROM book4_worklist wl
LEFT JOIN vesna.report_fakturi rf
  ON TRIM(rf.faktura) = TRIM(wl.faktura)
 AND TRIM(rf.sap_risk_business) = TRIM(wl.sap_risk_business)
ORDER BY wl.faktura, wl.sap_risk_business, rf.os_aneks_fakturaid;

-- 2) Контрола: листа на fin_stavka што би биле погодени.
SELECT
    wl.faktura,
    wl.sap_risk_business,
    rf.polisa_broj,
    fs.*
FROM book4_worklist wl
JOIN vesna.report_fakturi rf
  ON TRIM(rf.faktura) = TRIM(wl.faktura)
 AND TRIM(rf.sap_risk_business) = TRIM(wl.sap_risk_business)
JOIN viki.fin_stavka fs
  ON fs.os_aneks_fakturaid = rf.os_aneks_fakturaid
WHERE fs.iznos_d IS NOT NULL
  AND NVL(fs.f_rs, 'R') <> 'N'
ORDER BY wl.faktura, wl.sap_risk_business, fs.fin_stavkaid;

-- 3) Посебна проверка за здравствено/боледување.
-- Во Book4.xlsx се: 104589/2026-4 и 91988/2025-7 со MK19020205.
SELECT
    wl.faktura,
    wl.sap_risk_business,
    rf.polisa_broj,
    rf.os_aneks_fakturaid,
    rf.datum_aneks,
    rf.data_faktura,
    rf.datum_knizenje,
    fs.fin_stavkaid,
    fs.datum,
    fs.datum_knizi,
    fs.dat_nalog,
    fs.f_ko_po,
    fs.f_rs,
    fs.iznos_d,
    fs.iznos_p
FROM book4_worklist wl
JOIN vesna.report_fakturi rf
  ON TRIM(rf.faktura) = TRIM(wl.faktura)
 AND TRIM(rf.sap_risk_business) = TRIM(wl.sap_risk_business)
JOIN viki.fin_stavka fs
  ON fs.os_aneks_fakturaid = rf.os_aneks_fakturaid
WHERE wl.sap_risk_business = 'MK19020205'
ORDER BY wl.faktura, fs.dat_nalog, fs.fin_stavkaid;

-- 4) Пред ослободување: треба да нема неочекувани дупликати.
SELECT
    wl.faktura,
    wl.sap_risk_business,
    COUNT(DISTINCT rf.os_aneks_fakturaid) AS broj_faktura_id
FROM book4_worklist wl
LEFT JOIN vesna.report_fakturi rf
  ON TRIM(rf.faktura) = TRIM(wl.faktura)
 AND TRIM(rf.sap_risk_business) = TRIM(wl.sap_risk_business)
GROUP BY wl.faktura, wl.sap_risk_business
HAVING COUNT(DISTINCT rf.os_aneks_fakturaid) <> 1
ORDER BY wl.faktura, wl.sap_risk_business;

-- 5) UPDATE намерно е оставен коментиран.
-- Изврши го само ако контролите 1-4 се точни и ако „ослободување“
-- во оваа постапка навистина значи f_ko_po = NULL.
--
-- UPDATE viki.fin_stavka fs
--    SET f_ko_po = NULL
--  WHERE fs.f_ko_po = '1'
--    AND fs.iznos_d IS NOT NULL
--    AND NVL(fs.f_rs, 'R') <> 'N'
--    AND EXISTS (
--        SELECT 1
--        FROM vesna.report_fakturi rf
--        JOIN book4_worklist wl
--          ON TRIM(wl.faktura) = TRIM(rf.faktura)
--         AND TRIM(wl.sap_risk_business) = TRIM(rf.sap_risk_business)
--        WHERE rf.os_aneks_fakturaid = fs.os_aneks_fakturaid
--    );
--
-- По UPDATE:
-- SELECT COUNT(*) AS ostanati
-- FROM viki.fin_stavka fs
-- WHERE fs.f_ko_po = '1'
--   AND fs.iznos_d IS NOT NULL
--   AND NVL(fs.f_rs, 'R') <> 'N'
--   AND EXISTS (
--       SELECT 1
--       FROM vesna.report_fakturi rf
--       JOIN book4_worklist wl
--         ON TRIM(wl.faktura) = TRIM(rf.faktura)
--        AND TRIM(wl.sap_risk_business) = TRIM(rf.sap_risk_business)
--       WHERE rf.os_aneks_fakturaid = fs.os_aneks_fakturaid
--   );

