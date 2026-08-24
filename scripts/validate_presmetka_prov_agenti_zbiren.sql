-- Read-only validation for vesna.presmetka_prov_agenti_zbiren.
-- Replace the month/year literals in every query before running.
-- Example used below: mesec = '04', godina = '2026'.

-- 1) Duplicate rows in the final monthly summary.
-- If this returns rows, the calculation was probably run more than once
-- without deleting/replacing previous rows for the same agent/month/year.
select
    z.mesec,
    vrati_godina(z.par_yearid) godina,
    z.par_agentid,
    count(*) row_count
from provizija_promotori_zbiren z
where z.mesec = '04'
  and vrati_godina(z.par_yearid) = '2026'
group by 1, 2, 3
having count(*) > 1;

-- 2) Agents present in source calculation input but missing from final summary.
select s.par_agentid
from (
    select par_agentid, mesec, vrati_godina(par_yearid) godina
    from provizija_promotori_bodovi
    where tip_produkcija in (1, 2)

    union

    select par_agentid, mesec, vrati_godina(par_yearid) godina
    from lc_provizija_agent_bodovi
    where tip_produkcija in (1, 2)
      and par_statusid = 1

    union

    select par_agentid, mesec, godina
    from agenti_provizija1
    where tip_provizija in ('Лична', 'Тимска')
) s
where s.mesec = '04'
  and s.godina = '2026'
  and not exists (
      select 1
      from provizija_promotori_zbiren z
      where z.par_agentid = s.par_agentid
        and z.mesec = s.mesec
        and vrati_godina(z.par_yearid) = s.godina
  )
order by 1;

-- 6) Detail segment: personal and team points by policy and agent.
-- This is the first operational check: every policy that generated points,
-- grouped by agent and production type.
-- If lc_provizija_agent_bodovi does not have os_polisaid, replace
-- vrati_polisa(os_polisaid) with the correct policy column/function.
select
    d.par_agentid,
    d.tip_produkcija,
    case
        when d.tip_produkcija = 1 then 'Лична'
        when d.tip_produkcija = 2 then 'Тимска'
        else 'Друго'
    end tip_produkcija_naziv,
    d.polisa,
    sum(d.br_bodovi) br_bodovi,
    sum(d.iznos_bod) iznos_bod,
    count(*) broj_stavki
from (
    select
        par_agentid,
        tip_produkcija,
        vrati_polisa(os_polisaid) polisa,
        br_bodovi,
        iznos_bod
    from provizija_promotori_bodovi
    where mesec = '04'
      and vrati_godina(par_yearid) = '2026'
      and tip_produkcija in (1, 2)

    union all

    select
        par_agentid,
        tip_produkcija,
        vrati_polisa(os_polisaid) polisa,
        br_bodovi,
        iznos_bod
    from lc_provizija_agent_bodovi
    where mesec = '04'
      and vrati_godina(par_yearid) = '2026'
      and par_statusid = 1
      and tip_produkcija in (1, 2)
) d
group by 1, 2, 3, 4
order by 1, 2, 4;

-- 7) Detail anomaly: same policy counted more than once for the same
-- agent and same production type. Review returned rows manually.
select
    d.par_agentid,
    d.tip_produkcija,
    d.polisa,
    count(*) broj_stavki,
    sum(d.br_bodovi) br_bodovi,
    sum(d.iznos_bod) iznos_bod
from (
    select
        par_agentid,
        tip_produkcija,
        vrati_polisa(os_polisaid) polisa,
        br_bodovi,
        iznos_bod
    from provizija_promotori_bodovi
    where mesec = '04'
      and vrati_godina(par_yearid) = '2026'
      and tip_produkcija in (1, 2)

    union all

    select
        par_agentid,
        tip_produkcija,
        vrati_polisa(os_polisaid) polisa,
        br_bodovi,
        iznos_bod
    from lc_provizija_agent_bodovi
    where mesec = '04'
      and vrati_godina(par_yearid) = '2026'
      and par_statusid = 1
      and tip_produkcija in (1, 2)
) d
group by 1, 2, 3
having count(*) > 1
order by 1, 2, 3;

-- 8) Control segment: policy-detail points rolled up to agent totals,
-- compared with provizija_promotori_zbiren.
select
    coalesce(src.par_agentid, z.par_agentid) par_agentid,
    nvl(src.licni_bodovi_po_polisa, 0) licni_bodovi_po_polisa,
    nvl(z.bodovi_licna_prod, 0) z_bodovi_licna_prod,
    nvl(src.licni_bodovi_po_polisa, 0) - nvl(z.bodovi_licna_prod, 0) diff_licni_bodovi,
    nvl(src.timski_bodovi_po_polisa, 0) timski_bodovi_po_polisa,
    nvl(z.bodovi_timska_prod, 0) z_bodovi_timska_prod,
    nvl(src.timski_bodovi_po_polisa, 0) - nvl(z.bodovi_timska_prod, 0) diff_timski_bodovi,
    nvl(src.licna_vrednost_po_polisa, 0) licna_vrednost_po_polisa,
    nvl(z.novi_polisi_prov_lp, 0) z_novi_polisi_prov_lp,
    nvl(src.licna_vrednost_po_polisa, 0) - nvl(z.novi_polisi_prov_lp, 0) diff_licna_vrednost,
    nvl(src.timska_vrednost_po_polisa, 0) timska_vrednost_po_polisa,
    nvl(z.novi_polisi_prov_tp, 0) z_novi_polisi_prov_tp,
    nvl(src.timska_vrednost_po_polisa, 0) - nvl(z.novi_polisi_prov_tp, 0) diff_timska_vrednost
from (
    select
        par_agentid,
        sum(case when tip_produkcija = 1 then br_bodovi else 0 end) licni_bodovi_po_polisa,
        sum(case when tip_produkcija = 2 then br_bodovi else 0 end) timski_bodovi_po_polisa,
        sum(case when tip_produkcija = 1 then iznos_bod else 0 end) licna_vrednost_po_polisa,
        sum(case when tip_produkcija = 2 then iznos_bod else 0 end) timska_vrednost_po_polisa
    from (
        select par_agentid, tip_produkcija, br_bodovi, iznos_bod
        from provizija_promotori_bodovi
        where mesec = '04'
          and vrati_godina(par_yearid) = '2026'
          and tip_produkcija in (1, 2)

        union all

        select par_agentid, tip_produkcija, br_bodovi, iznos_bod
        from lc_provizija_agent_bodovi
        where mesec = '04'
          and vrati_godina(par_yearid) = '2026'
          and par_statusid = 1
          and tip_produkcija in (1, 2)
    ) x
    group by 1
) src
full outer join (
    select
        par_agentid,
        sum(bodovi_licna_prod) bodovi_licna_prod,
        sum(bodovi_timska_prod) bodovi_timska_prod,
        sum(novi_polisi_prov_lp) novi_polisi_prov_lp,
        sum(novi_polisi_prov_tp) novi_polisi_prov_tp
    from provizija_promotori_zbiren
    where mesec = '04'
      and vrati_godina(par_yearid) = '2026'
    group by 1
) z on z.par_agentid = src.par_agentid
where nvl(src.licni_bodovi_po_polisa, 0) <> nvl(z.bodovi_licna_prod, 0)
   or nvl(src.timski_bodovi_po_polisa, 0) <> nvl(z.bodovi_timska_prod, 0)
   or nvl(src.licna_vrednost_po_polisa, 0) <> nvl(z.novi_polisi_prov_lp, 0)
   or nvl(src.timska_vrednost_po_polisa, 0) <> nvl(z.novi_polisi_prov_tp, 0)
order by 1;

-- 9) Inkaso commission by agent.
-- This shows the final inkaso values that should be reviewed after the
-- policy/points segment is clean.
select
    z.par_agentid,
    sum(z.novi_polisi_inkaso_lp) inkaso_licna,
    sum(z.novi_polisi_inkaso_tp) inkaso_timska,
    sum(z.novi_inkaso_prov) vkupno_inkaso,
    sum(z.bruto_provizija) bruto_provizija,
    sum(z.bonus_inkaso_prov) bonus_inkaso_prov
from provizija_promotori_zbiren z
where z.mesec = '04'
  and vrati_godina(z.par_yearid) = '2026'
group by 1
order by 1;

-- 10) Inkaso formula check by agent.
-- Expected formula from the procedure:
-- inkaso personal = max(storno personal + new personal - bonus personal, 0)
-- inkaso team     = max(storno team + new team - bonus team, 0)
-- Because SQL cannot reuse tbonus_polisi_prov_lp/tp, this query rebuilds
-- the bonus part from agenti_provizija. If the procedure should use only
-- the current month, keep the mesec/godina filters below.
select
    z.par_agentid,
    z.novi_polisi_inkaso_lp final_inkaso_licna,
    case
        when nvl(z.storno_polisi_prov_lp, 0) + nvl(z.novi_polisi_prov_lp, 0) - nvl(b.bonus_licna, 0) < 0
        then 0
        else nvl(z.storno_polisi_prov_lp, 0) + nvl(z.novi_polisi_prov_lp, 0) - nvl(b.bonus_licna, 0)
    end expected_inkaso_licna,
    z.novi_polisi_inkaso_tp final_inkaso_timska,
    case
        when nvl(z.storno_polisi_prov_tp, 0) + nvl(z.novi_polisi_prov_tp, 0) - nvl(b.bonus_timska, 0) < 0
        then 0
        else nvl(z.storno_polisi_prov_tp, 0) + nvl(z.novi_polisi_prov_tp, 0) - nvl(b.bonus_timska, 0)
    end expected_inkaso_timska,
    z.novi_inkaso_prov final_vkupno_inkaso
from provizija_promotori_zbiren z
left join (
    select
        par_agentid,
        sum(case when tip_provizija = 'Лична' then iznos_provizija else 0 end) bonus_licna,
        sum(case when tip_provizija = 'Тимска' then iznos_provizija else 0 end) bonus_timska
    from agenti_provizija
    where mesec = '04'
      and godina = '2026'
      and tip_provizija in ('Лична', 'Тимска')
    group by 1
) b on b.par_agentid = z.par_agentid
where z.mesec = '04'
  and vrati_godina(z.par_yearid) = '2026'
  and (
      nvl(z.novi_polisi_inkaso_lp, 0) <>
      case
          when nvl(z.storno_polisi_prov_lp, 0) + nvl(z.novi_polisi_prov_lp, 0) - nvl(b.bonus_licna, 0) < 0
          then 0
          else nvl(z.storno_polisi_prov_lp, 0) + nvl(z.novi_polisi_prov_lp, 0) - nvl(b.bonus_licna, 0)
      end
      or nvl(z.novi_polisi_inkaso_tp, 0) <>
      case
          when nvl(z.storno_polisi_prov_tp, 0) + nvl(z.novi_polisi_prov_tp, 0) - nvl(b.bonus_timska, 0) < 0
          then 0
          else nvl(z.storno_polisi_prov_tp, 0) + nvl(z.novi_polisi_prov_tp, 0) - nvl(b.bonus_timska, 0)
      end
      or nvl(z.novi_inkaso_prov, 0) <> nvl(z.novi_polisi_inkaso_lp, 0) + nvl(z.novi_polisi_inkaso_tp, 0)
  )
order by 1;

-- 3) Reconcile current-month points and current-month commission sources
-- against the final summary. Any non-zero difference needs inspection.
select
    coalesce(src.par_agentid, z.par_agentid) par_agentid,
    nvl(src.bodovi_licna_prod, 0) src_bodovi_licna_prod,
    nvl(z.bodovi_licna_prod, 0) z_bodovi_licna_prod,
    nvl(src.bodovi_licna_prod, 0) - nvl(z.bodovi_licna_prod, 0) diff_bodovi_licna,
    nvl(src.bodovi_timska_prod, 0) src_bodovi_timska_prod,
    nvl(z.bodovi_timska_prod, 0) z_bodovi_timska_prod,
    nvl(src.bodovi_timska_prod, 0) - nvl(z.bodovi_timska_prod, 0) diff_bodovi_timska,
    nvl(src.provizija_licna, 0) src_provizija_licna,
    nvl(z.bodovi_sl_pozicija_lp, 0) z_provizija_licna,
    nvl(src.provizija_licna, 0) - nvl(z.bodovi_sl_pozicija_lp, 0) diff_provizija_licna,
    nvl(src.provizija_timska, 0) src_provizija_timska,
    nvl(z.bodovi_sl_pozicija_tp, 0) z_provizija_timska,
    nvl(src.provizija_timska, 0) - nvl(z.bodovi_sl_pozicija_tp, 0) diff_provizija_timska
from (
    select
        par_agentid,
        sum(bodovi_licna_prod) bodovi_licna_prod,
        sum(bodovi_timska_prod) bodovi_timska_prod,
        sum(provizija_licna) provizija_licna,
        sum(provizija_timska) provizija_timska
    from (
        select par_agentid, sum(br_bodovi) bodovi_licna_prod, 0 bodovi_timska_prod,
               0 provizija_licna, 0 provizija_timska
        from provizija_promotori_bodovi
        where tip_produkcija = 1
          and mesec = '04'
          and vrati_godina(par_yearid) = '2026'
        group by 1

        union all

        select par_agentid, sum(br_bodovi), 0, 0, 0
        from lc_provizija_agent_bodovi
        where tip_produkcija = 1
          and par_statusid = 1
          and mesec = '04'
          and vrati_godina(par_yearid) = '2026'
        group by 1

        union all

        select par_agentid, 0, sum(br_bodovi), 0, 0
        from provizija_promotori_bodovi
        where tip_produkcija = 2
          and mesec = '04'
          and vrati_godina(par_yearid) = '2026'
        group by 1

        union all

        select par_agentid, 0, sum(br_bodovi), 0, 0
        from lc_provizija_agent_bodovi
        where tip_produkcija = 2
          and par_statusid = 1
          and mesec = '04'
          and vrati_godina(par_yearid) = '2026'
        group by 1

        union all

        select par_agentid, 0, 0, sum(iznos_provizija), 0
        from agenti_provizija1
        where tip_provizija = 'Лична'
          and mesec = '04'
          and godina = '2026'
        group by 1

        union all

        select par_agentid, 0, 0, 0, sum(iznos_provizija)
        from agenti_provizija1
        where tip_provizija = 'Тимска'
          and mesec = '04'
          and godina = '2026'
        group by 1
    ) x
    group by 1
) src
full outer join (
    select
        z.par_agentid,
        sum(z.bodovi_licna_prod) bodovi_licna_prod,
        sum(z.bodovi_timska_prod) bodovi_timska_prod,
        sum(z.bodovi_sl_pozicija_lp) bodovi_sl_pozicija_lp,
        sum(z.bodovi_sl_pozicija_tp) bodovi_sl_pozicija_tp
    from provizija_promotori_zbiren z
    where z.mesec = '04'
      and vrati_godina(z.par_yearid) = '2026'
    group by 1
) z on z.par_agentid = src.par_agentid
where nvl(src.bodovi_licna_prod, 0) <> nvl(z.bodovi_licna_prod, 0)
   or nvl(src.bodovi_timska_prod, 0) <> nvl(z.bodovi_timska_prod, 0)
   or nvl(src.provizija_licna, 0) <> nvl(z.bodovi_sl_pozicija_lp, 0)
   or nvl(src.provizija_timska, 0) <> nvl(z.bodovi_sl_pozicija_tp, 0)
order by 1;

-- 4) Reconcile formulas that should be true inside each inserted summary row.
select
    z.par_agentid,
    z.bodovi_period,
    z.bodovi_licna_prod + z.bodovi_timska_prod expected_bodovi_period,
    z.novi_polisi_prov,
    z.novi_polisi_prov_lp + z.novi_polisi_prov_tp expected_novi_polisi_prov,
    z.novi_storno_bodovi,
    z.novi_storno_bodovi_lp + z.novi_storno_bodovi_tp expected_novi_storno_bodovi,
    z.storno_polisi_prov,
    z.storno_polisi_prov_lp + z.storno_polisi_prov_tp expected_storno_polisi_prov,
    z.bruto_provizija,
    z.bodovi_sl_pozicija_lp + z.bodovi_sl_pozicija_tp expected_bruto_provizija,
    z.novi_inkaso_prov,
    z.novi_polisi_inkaso_lp + z.novi_polisi_inkaso_tp expected_novi_inkaso_prov
from provizija_promotori_zbiren z
where z.mesec = '04'
  and vrati_godina(z.par_yearid) = '2026'
  and (
      nvl(z.bodovi_period, 0) <> nvl(z.bodovi_licna_prod, 0) + nvl(z.bodovi_timska_prod, 0)
      or nvl(z.novi_polisi_prov, 0) <> nvl(z.novi_polisi_prov_lp, 0) + nvl(z.novi_polisi_prov_tp, 0)
      or nvl(z.novi_storno_bodovi, 0) <> nvl(z.novi_storno_bodovi_lp, 0) + nvl(z.novi_storno_bodovi_tp, 0)
      or nvl(z.storno_polisi_prov, 0) <> nvl(z.storno_polisi_prov_lp, 0) + nvl(z.storno_polisi_prov_tp, 0)
      or nvl(z.bruto_provizija, 0) <> nvl(z.bodovi_sl_pozicija_lp, 0) + nvl(z.bodovi_sl_pozicija_tp, 0)
      or nvl(z.novi_inkaso_prov, 0) <> nvl(z.novi_polisi_inkaso_lp, 0) + nvl(z.novi_polisi_inkaso_tp, 0)
  )
order by 1;

-- 5) Bonus/paid commission conversion check.
select
    z.par_agentid,
    z.bonus_inkaso_prov final_bonus_inkaso_prov,
    nvl(src.provizija_mkd, 0) expected_bonus_inkaso_prov,
    nvl(z.bonus_inkaso_prov, 0) - nvl(src.provizija_mkd, 0) diff_bonus_inkaso_prov
from provizija_promotori_zbiren z
left join (
    select
        par_agentid,
        sum(round(iznos_provizija * vrati_kurs(last_day('01.04.2026'), 'EUR'))) provizija_mkd
    from agenti_provizija
    where mesec = '04'
      and godina = '2026'
    group by 1
) src on src.par_agentid = z.par_agentid
where z.mesec = '04'
  and vrati_godina(z.par_yearid) = '2026'
  and nvl(z.bonus_inkaso_prov, 0) <> nvl(src.provizija_mkd, 0)
order by 1;
