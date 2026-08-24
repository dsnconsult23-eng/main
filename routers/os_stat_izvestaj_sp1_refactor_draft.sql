-- Informix SPL draft for SP-1 optimization in appuser.os_stat_izvestaj
-- Purpose:
-- 1. Build one base temp set for the policy universe for the requested period
-- 2. Reuse that base set for active/capitalized/otkup/skluceni calculations
-- 3. Reduce repeated scans over os_ponuda/os_polisa/os_ponuda_detail/os_produkt
--
-- This is a draft proposal, not a drop-in replacement for the whole function.
-- It is intended to replace the current SP-1 block step by step.

create temp table sp1_base
(
    polisa_broj             varchar(20),
    grupa_sp1               varchar(20),
    grupa_tar               varchar(20),
    grupa_tarifa            varchar(20),
    br_osigurenici          int,
    br_osigurenici_kolekt   int,
    osig_suma               decimal(20,2),
    par_statusid            int,
    datum_polisa            date
) with no log;

insert into sp1_base
(
    polisa_broj,
    grupa_sp1,
    grupa_tar,
    grupa_tarifa,
    br_osigurenici,
    br_osigurenici_kolekt,
    osig_suma,
    par_statusid,
    datum_polisa
)
select
    t.polisa_broj,
    vrati_grupa(d.os_ponuda_detailid),
    vrati_grupa_tar(d.os_ponuda_detailid),
    vrati_grupa_tarifa(d.os_ponuda_detailid),
    nvl(br_osig_aktivni, 1),
    case
        when vrati_tipprodukt(p.os_tipproduktid) in ('КР', 'КЖ') then nvl(br_osig_aktivni, 1)
        else 0
    end,
    case
        when nvl(o.par_valutaid, p.par_valutaid) = 363 then nvl(osig_suma_smrt, osig_suma)
        else nvl(osig_suma_smrt, osig_suma) * tkurs
    end,
    o.par_statusid,
    t.datum_polisa
from os_ponuda o,
     os_ponuda_detail d,
     os_produkt p,
     os_polisa t
where o.os_ponudaid = d.os_ponudaid
  and o.os_produktid = p.os_produktid
  and o.os_ponudaid = t.os_ponudaid
  and skadenca_datum_od <= tdatum_do
  and skadenca_datum_do >= tdatum_do
  and o.par_statusid in (13, 17, 18, 20, 21, 42)
  and o.ponuda_podbroj = maxpodbroj_datum(o.ponuda_broj, t.polisa_broj, o.os_produktid, tdatum_do);


create temp table sp1_agg_main
(
    grupa_sp1             varchar(20),
    akt_polisi            int,
    br_osigurenici        int,
    br_osigurenici_kolekt int,
    kapitalizirani        int,
    otkup                 int,
    skl_dog               int,
    osig_suma             decimal(20,2)
) with no log;

insert into sp1_agg_main
select
    grupa_sp1,
    count(case when par_statusid in (13, 17, 18, 42) then 1 end),
    sum(case when par_statusid in (13, 17, 18, 42) then br_osigurenici else 0 end),
    sum(case when par_statusid in (13, 17, 18, 42) then br_osigurenici_kolekt else 0 end),
    count(case when par_statusid = 18 then 1 end),
    count(case when par_statusid in (20, 21) then 1 end),
    count(case when datum_polisa between tod_datum_godina and tdatum_do
                and par_statusid in (17, 18) then 1 end),
    sum(case when par_statusid in (13, 17, 18, 42) then osig_suma else 0 end)
from sp1_base
group by 1;


create temp table sp1_agg_tar
(
    grupa_sp1             varchar(20),
    akt_polisi            int,
    br_osigurenici        int,
    br_osigurenici_kolekt int,
    kapitalizirani        int,
    otkup                 int,
    skl_dog               int
) with no log;

insert into sp1_agg_tar
select
    grupa_tar,
    count(case when par_statusid in (13, 17, 18, 42) then 1 end),
    sum(case when par_statusid in (13, 17, 18, 42) then br_osigurenici else 0 end),
    sum(case when par_statusid in (13, 17, 18, 42) then br_osigurenici_kolekt else 0 end),
    count(case when par_statusid = 18 then 1 end),
    count(case when par_statusid in (20, 21) then 1 end),
    count(case when datum_polisa between tod_datum_godina and tdatum_do
                and par_statusid in (17, 18) then 1 end)
from sp1_base
where grupa_tar like '19%'
group by 1;


create temp table sp1_agg_tarifa
(
    grupa_sp1             varchar(20),
    akt_polisi            int,
    br_osigurenici        int,
    br_osigurenici_kolekt int,
    kapitalizirani        int,
    otkup                 int,
    skl_dog               int
) with no log;

insert into sp1_agg_tarifa
select
    grupa_tarifa,
    count(case when par_statusid in (13, 17, 18, 42) then 1 end),
    sum(case when par_statusid in (13, 17, 18, 42) then br_osigurenici else 0 end),
    sum(case when par_statusid in (13, 17, 18, 42) then br_osigurenici_kolekt else 0 end),
    count(case when par_statusid = 18 then 1 end),
    count(case when par_statusid in (20, 21) then 1 end),
    count(case when datum_polisa between tod_datum_godina and tdatum_do
                and par_statusid in (17, 18) then 1 end)
from sp1_base
where grupa_tarifa like '19%'
group by 1;


-- Premium temp tables can stay separate initially.
-- These are already set-based and cheaper than the repeated policy joins above.
-- Once sp1_base is adopted, the next step would be:
-- 1. keep sp1_bruto_premija, sp1_bruto_premija12, sp1_edin_premija, sp1_ednokrat_premija as-is
-- 2. replace the current foreach+update block with one set-based update per level


-- Suggested replacement for the current main SP-1 row loop:
--
-- foreach select a.grupa_sp1, ...
--   update stat_izvestai ...
-- end foreach;
--
-- can be rewritten conceptually as:
--
-- update stat_izvestai s
--    set kol100 = (select n.akt_polisi from sp1_agg_main n where n.grupa_sp1 = s.vid_stavka),
--        kol102 = (select n.br_osigurenici from sp1_agg_main n where n.grupa_sp1 = s.vid_stavka),
--        kol103 = (select n.br_osigurenici_kolekt from sp1_agg_main n where n.grupa_sp1 = s.vid_stavka),
--        kol104 = (select n.kapitalizirani from sp1_agg_main n where n.grupa_sp1 = s.vid_stavka),
--        kol105 = (select n.otkup from sp1_agg_main n where n.grupa_sp1 = s.vid_stavka),
--        kol106 = (select n.skl_dog from sp1_agg_main n where n.grupa_sp1 = s.vid_stavka),
--        kol200 = (select nvl(p.bruto_premija, 0) / 1000 from sp1_bruto_premija p where p.grupa_sp1 = s.vid_stavka),
--        kol201 = (select nvl(e.ednokrat_premija, 0) / 1000 from sp1_ednokrat_premija e where e.grupa_sp1 = s.vid_stavka),
--        kol202 = (select nvl(e.edin_premija, 0) / 1000 from sp1_edin_premija e where e.grupa_sp1 = s.vid_stavka),
--        kol203 = (select nvl(p12.bruto_premija12, 0) / 1000 from sp1_bruto_premija12 p12 where p12.grupa_sp1 = s.vid_stavka),
--        kol204 = 0,
--        kol205 = 0,
--        kol206 = 0,
--        kol207 = 0
--  where s.stat_izvestaj = 'SP-1'
--    and s.datum = tdatum_do
--    and exists (select 1 from sp1_agg_main n where n.grupa_sp1 = s.vid_stavka);
--
-- In Informix this style should be validated in your environment,
-- but even if correlated subqueries are kept, it still removes SPL row-by-row loops.


-- Rollout order proposal:
-- 1. Introduce sp1_base
-- 2. Replace sp1_analitika / sp1_kap_polisi / sp1_otkup / sp1_skl_dog derivation with sp1_base aggregates
-- 3. Keep existing premium temp tables unchanged
-- 4. Replace first foreach/update block only
-- 5. Validate output against current function for one month
-- 6. Then refactor tariff/tarifa aggregate updates
