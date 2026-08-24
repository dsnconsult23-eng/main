CREATE FUNCTION vesna.presmetka_prov_agenti_zbiren_test (tmesec char(2) , tgodina char(4) ,tuser_id int )
		returning integer,char(100);
{
procedurata vraka:
       
        - kod na greska
                  1 ako se e ok i ako e izvrseno 
                 -1 ako se pojavi nekoja neregularnost
        - poraka poradi koja e nastanata greskata
}

define  tpar_provizija_agentid , tpar_clientid ,tpar_agentid ,  tpar_provizijadefid ,  tpar_provizijatipid ,  tpar_provizijaispid ,  tpar_statusid,tpar_tip_kniziid  int;
define tpar_yearid,tprovizija_agent_zbirenid,tppd_nadredenid int;
define tnaplata, tnaplata_den, tiznos_d	,tiznos_d_den,tprovizija ,tpersonalec,vkupna_premija,tbr_rati,tosig_suma,tpremija_zivot,tproc_prov,tdat_naplata dec;
define tusername char(30);
define tskadenca_datum_od,tod_odatum, tdo_datum,tdatum_prekin,tdatum_ponuda, tpoceten_datum,tdatecreated date;
define tnovi_polisi_prov_lp ,     tnovi_polisi_prov_tp ,     tnovi_polisi_prov,tkrajni_bodovi_tp dec;
define tbodovi_licna_prod,tbodovi_timska_prod ,     tbodovi_period,tnovi_bonus_bodovi_lp , tkrajni_bodovi_lp,    tnovi_bonus_bodovi_tp ,     tnovi_bonus_bodovi ,tnovi_storno_bodovi_lp , tnovi_storno_bodovi_tp , tnovi_storno_bodovi   dec; 
define  tstorno_polisi_prov_lp ,     tstorno_polisi_prov_tp ,     tstorno_polisi_prov , 
	 tbonus_polisi_prov_lp ,     tbonus_polisi_prov_tp ,     tbonus_polisi_prov , 
	 tnovi_polisi_inkaso_lp ,     tnovi_polisi_inkaso_tp ,     tnovi_inkaso_prov ,
     tstorno_polisi_inkaso_lp ,     tstorno_polisi_inkaso_tp ,     tstorno_inkaso_prov ,talfa_struk ,     trolling_tim ,     trolling_vk  ,
	 tbonus_polisi_inkaso_lp ,     tbonus_polisi_inkaso_tp ,     tbonus_inkaso_prov , tstartni_poeni_lp,
	tbruto_provizija ,     tbodovi_sl_pozicija_lp ,    tbodovi_sl_pozicija_tp ,     troling_bodovi_sl_pozicija,tlicni_bodovi,ttimiski_bodovi dec; 
define tkumul_bodovi,tkumul_bodovi_preth,tstorno_bodovi_preth, tstartni_poeni,tstorno_bodovi_kumul,tstorno_bodovi,tstorno_bodovi_mesec,tppd_to,tbodovi_sl, tstartni_poeni_tp,tpps_bodovido,tprovizija_mkd dec; 	
define ttmesec_nadren varchar(2);
define tpar_yearid_next int;
define tbodovi_sledna_pozicija dec;
define tkurs_eur dec;


on exception
	--ROLLBACK WORK;
        return -1,'NASTANATA E GRE[KA';
end exception;


set isolation to dirty read;  
--set debug file to 'err_presmetka_prov111.sql';
--trace on;
--BEGIN WORK;
let tod_odatum='01.'||tmesec||'.'||tgodina;
 let tdo_datum=LAST_DAY(tod_odatum);

select par_yearid into tpar_yearid
from par_year 
where par_year = tgodina;

delete from provizija_promotori_zbiren
where mesec=tmesec
and par_yearid=tpar_yearid;

select username into tusername from adm_user
where userid=tuser_id;

 
select par_agentid,'1'  tip_produkcija,mesec,  godina,sum(bodovi_tekoven_mesec_l) bodovi_tekoven_mesec_l, sum(iznos_bodovi_tekoven_mesec_l) iznos_bodovi_tekoven_mesec_l, 
sum(bodovi_tekoven_mesec_t) bodovi_tekoven_mesec_t,  sum( iznos_bodovi_tekoven_mesec_t) iznos_bodovi_tekoven_mesec_t,sum(provizija_tekoven_mesec_l) provizija_tekoven_mesec_l 
 , sum(provizija_tekoven_mesec_t)provizija_tekoven_mesec_t
from 
(select par_agentid, tip_produkcija,mesec, vrati_godina(par_yearid) godina, sum(br_bodovi) bodovi_tekoven_mesec_l, sum(iznos_bod)  iznos_bodovi_tekoven_mesec_l,0  bodovi_tekoven_mesec_t, 0  iznos_bodovi_tekoven_mesec_t,0 provizija_tekoven_mesec_l  ,0 provizija_tekoven_mesec_t
from provizija_promotori_bodovi
where tip_produkcija=1
and par_statusid=1
group by 1,2,3,4
 union all
select par_agentid, tip_produkcija,mesec, vrati_godina(par_yearid) godina, sum(br_bodovi), sum(iznos_bod) ,0  bodovi_tekoven_mesec_t, 0  iznos_bodovi_tekoven_mesec_t,0 provizija_tekoven_mesec_l  ,0 provizija_tekoven_mesec_t
from lc_provizija_agent_bodovi
where tip_produkcija=1
and par_statusid=1
group by 1,2,3,4
union all 
select par_agentid, tip_produkcija,mesec, vrati_godina(par_yearid) godina, 0 bodovi_tekoven_mesec_l, 0 iznos_bodovi_tekoven_mesec_l,sum(br_bodovi) bodovi_tekoven_mesec_t, sum(iznos_bod)  iznos_bodovi_tekoven_mesec_t,0 provizija_tekoven_mesec_l  ,0 provizija_tekoven_mesec_t
from provizija_promotori_bodovi
where tip_produkcija=2
and par_statusid=1
group by 1,2,3,4
 union all
select par_agentid, tip_produkcija,mesec, vrati_godina(par_yearid) godina, 0 bodovi_tekoven_mesec_l, 0 iznos_bodovi_tekoven_mesec_l,sum(br_bodovi) bodovi_tekoven_mesec_t, sum(iznos_bod)  iznos_bodovi_tekoven_mesec_t,0 provizija_tekoven_mesec_l ,0 provizija_tekoven_mesec_t 
from lc_provizija_agent_bodovi
where tip_produkcija=2
and par_statusid=1
group by 1,2,3,4
 union all 
 
select par_agentid, '1' tip_produkcija,mesec,  godina,  0 bodovi_tekoven_mesec_l, 0 iznos_bodovi_tekoven_mesec_l,0 bodovi_tekoven_mesec_t, 0 iznos_bodovi_tekoven_mesec_t ,sum(iznos_provizija) provizija_tekoven_mesec_l ,0 provizija_tekoven_mesec_t
 from agenti_provizija  
where   tip_provizija='Лична'
and mesec=tmesec
and godina=tgodina
group by 1,2,3,4

 union all 
 
select par_agentid, '2' tip_produkcija,mesec,  godina,  0 bodovi_tekoven_mesec_l, 0 iznos_bodovi_tekoven_mesec_l,0 bodovi_tekoven_mesec_t, 0 iznos_bodovi_tekoven_mesec_t ,0 provizija_tekoven_mesec_l ,sum(iznos_provizija) provizija_tekoven_mesec_t
 from agenti_provizija  
where   tip_provizija='Тимска'
and mesec=tmesec
and godina=tgodina
group by 1,2,3,4) a 
where mesec=tmesec
and godina=tgodina 
group by 1,2,3,4

into temp zbiren;


-- Opt1: aktivni polisi so max pod_broj -- eden pat namesto correlated subquery po red
select polisa_broj_cel, max(polisa_pod_broj) as max_pod_broj
from os_polisa
where status_polisa = 'K'
group by 1
into temp polisa_max with no log;

-- Presmetana inkaso provizija po agent/polisa/tip (aktivni polisi, posled 48 meseci)
select a.par_agentid, p.polisa_broj_cel as polisa, a.tip_produkcija,
       sum(a.iznos_bod) as provizija
from lc_provizija_agent_bodovi a
join os_polisa p  on a.os_polisaid = p.os_polisaid
join os_ponuda o  on p.os_ponudaid = o.os_ponudaid
join polisa_max pm on pm.polisa_broj_cel = p.polisa_broj_cel
                  and pm.max_pod_broj    = p.polisa_pod_broj
where a.par_statusid = 1
  and o.skadenca_datum_od >= DATE(EXTEND(ADD_MONTHS(tdo_datum, -48), YEAR TO MONTH))
group by 1, 2, 3

union all

select a.par_agentid, p.polisa_broj_cel, a.tip_produkcija,
       sum(a.iznos_bod)
from provizija_promotori_bodovi a
join os_polisa p  on a.os_polisaid = p.os_polisaid
join os_ponuda o  on p.os_ponudaid = o.os_ponudaid
join polisa_max pm on pm.polisa_broj_cel = p.polisa_broj_cel
                  and pm.max_pod_broj    = p.polisa_pod_broj
where o.skadenca_datum_od >= DATE(EXTEND(ADD_MONTHS(tdo_datum, -48), YEAR TO MONTH))
and a.par_statusid=1
group by 1, 2, 3

into temp inkaso_ta with no log;

-- Isplatena inkaso provizija po agent/polisa (od agenti_provizija1)
select par_agentid, polisa_broj, sum(iznos_provizija) as prov
from agenti_provizija1
group by 1, 2
into temp inkaso_sa with no log;

-- Opt4: kurs EUR eden pat za celiot mesec

let tkurs_eur = vrati_kurs(tdo_datum, 'EUR');
if tkurs_eur is null or tkurs_eur = 0 then let tkurs_eur = 1; end if;

foreach select par_agentid, bodovi_tekoven_mesec_l,  iznos_bodovi_tekoven_mesec_l, 
 bodovi_tekoven_mesec_t,  iznos_bodovi_tekoven_mesec_t,provizija_tekoven_mesec_l,provizija_tekoven_mesec_t
 into tpar_agentid,tbodovi_licna_prod,tnovi_polisi_prov_lp ,       
  tbodovi_timska_prod,   tnovi_polisi_prov_tp ,tbodovi_sl_pozicija_lp,tbodovi_sl_pozicija_tp
 from zbiren 
-- where par_agentid=679
 
 
-- set debug file to 'err_presmetka_prov111.sql';
--trace on;
let tstartni_poeni_lp=0;
let tstartni_poeni_tp=0;
select  first 1 nvl(startni_poeni_lp,0) ,nvl(startni_poeni,0),par_provizijadefid, par_provizijatipid
into tstartni_poeni_lp, tstartni_poeni_tp,tpar_provizijadefid,tpar_provizijatipid
from provizija_agent
where par_agentid=tpar_agentid
and  ((tdo_datum between pag_datumod and pag_datumdo) or (tdo_datum >= pag_datumod and pag_datumdo is null));

 

 

 select sum(case when nvl(duplirani_bodovi,0)=0 then iznos_bod else iznos_bod*2 end  ),
  sum(br_bodovi) +nvl(sum(nvl(duplirani_bodovi,0)),0)
into tstorno_polisi_prov_lp,tnovi_storno_bodovi_lp
from provizija_promotori_bodovi
where datum_presmetka<tod_odatum
and par_agentid=tpar_agentid
and tip_produkcija='1'
and par_statusid=1;
if tstorno_polisi_prov_lp is null then 
select sum(iznos_bod), sum(br_bodovi) 
into tstorno_polisi_prov_lp,tnovi_storno_bodovi_lp
from lc_provizija_agent_bodovi
where datum_presmetka<tod_odatum
and par_agentid=tpar_agentid
and par_provizijatipid=tpar_provizijatipid
and par_statusid=1
and tip_produkcija='1';
end if; 


if tstorno_polisi_prov_lp is null then let tstorno_polisi_prov_lp=0; end if;
if tnovi_storno_bodovi_lp is null then let tnovi_storno_bodovi_lp=0; end if;
 select sum(iznos_bod), sum(br_bodovi) 
into tstorno_polisi_prov_tp,tnovi_storno_bodovi_tp
from provizija_promotori_bodovi
where datum_presmetka<tod_odatum
and par_agentid=tpar_agentid
and tip_produkcija='2'
and par_statusid=1;

if tstorno_polisi_prov_tp is null then
 select sum(iznos_bod), sum(br_bodovi) 
into tstorno_polisi_prov_tp,tnovi_storno_bodovi_tp
from lc_provizija_agent_bodovi
where datum_presmetka<tod_odatum
and par_statusid=1
and par_agentid=tpar_agentid
and tip_produkcija='2';

end if;

if tstorno_polisi_prov_tp is null then let tstorno_polisi_prov_tp=0; end if;
if tnovi_storno_bodovi_tp is null then let tnovi_storno_bodovi_tp=0; end if;
let tnovi_storno_bodovi_lp=tnovi_storno_bodovi_lp+tstartni_poeni_lp;
let tnovi_storno_bodovi_tp=tnovi_storno_bodovi_tp+tstartni_poeni_tp;

 
-- Opt2: LP + TP provizija vo eden SELECT
select NVL(sum(case when tip_provizija='Лична'  then iznos_provizija else 0 end), 0),
       NVL(sum(case when tip_provizija='Тимска' then iznos_provizija else 0 end), 0)
into tbonus_polisi_prov_lp, tbonus_polisi_prov_tp
from agenti_provizija
where par_agentid = tpar_agentid;


let tbodovi_period= tbodovi_licna_prod+tbodovi_timska_prod;
let tnovi_polisi_prov =tnovi_polisi_prov_lp+tnovi_polisi_prov_tp;
let  tnovi_storno_bodovi=tnovi_storno_bodovi_lp+ tnovi_storno_bodovi_tp;
let tstorno_polisi_prov= tstorno_polisi_prov_lp+tstorno_polisi_prov_tp ;

let tbruto_provizija=tbodovi_sl_pozicija_lp+tbodovi_sl_pozicija_tp;
-- LP inkaso ostanato: presmetana (tip=1, aktivni polisi, 48 meseci) - isplatena po polisa
select NVL(sum(t.provizija) - NVL(sum(s.prov), 0), 0)
into tnovi_polisi_inkaso_lp
from inkaso_ta t
left join inkaso_sa s on s.par_agentid = t.par_agentid
                     and s.polisa_broj  = t.polisa
where t.par_agentid    = tpar_agentid
  and t.tip_produkcija = 1;

if tnovi_polisi_inkaso_lp is null then let tnovi_polisi_inkaso_lp = 0; end if;
if tnovi_polisi_inkaso_lp < 0    then let tnovi_polisi_inkaso_lp = 0; end if;

-- TP inkaso ostanato: presmetana (tip=2, aktivni polisi, 48 meseci) - isplatena po polisa
select NVL(sum(t.provizija) - NVL(sum(s.prov), 0), 0)
into tnovi_polisi_inkaso_tp
from inkaso_ta t
left join inkaso_sa s on s.par_agentid = t.par_agentid
                     and s.polisa_broj  = t.polisa
where t.par_agentid    = tpar_agentid
  and t.tip_produkcija = 2;

if tnovi_polisi_inkaso_tp is null then let tnovi_polisi_inkaso_tp = 0; end if;
if tnovi_polisi_inkaso_tp < 0    then let tnovi_polisi_inkaso_tp = 0; end if;
let tnovi_inkaso_prov=tnovi_polisi_inkaso_lp+tnovi_polisi_inkaso_tp;
--set debug file to 'err_presmetka_prov111.sql';
--trace on;

let tpar_provizijadefid=tpar_provizijadefid;
let tppd_nadredenid=0;
 select nvl(ppd_nadredenid,0) into tppd_nadredenid
 from par_provizijadef
 where par_provizijadefid=tpar_provizijadefid;
 let tpps_bodovido=0;
 
 if tppd_nadredenid<>0 then 
 
 select pps_bodoviod
into tpps_bodovido
from par_provizijadef_St
where par_provizijadefid=tppd_nadredenid
and nvl(pps_valueden,1) ='1' 
and   ((tdo_datum between pps_datumod and pps_datumdo) or (tdo_datum >= pps_datumod and pps_datumdo is null));
 end if;
 if tpps_bodovido=0 then 
 let tbodovi_sledna_pozicija=0;
 else 
 let tbodovi_sledna_pozicija=tpps_bodovido-(tbodovi_period+tnovi_storno_bodovi);
 end if;
 
 if tbodovi_sledna_pozicija<0 then let tbodovi_sledna_pozicija=0; end if;
 
 
 
    SELECT NVL(sum(ROUND(iznos_provizija * tkurs_eur)), 0)
    into tprovizija_mkd
    FROM agenti_provizija
    where mesec    = tmesec
      and godina   = tgodina
      and par_agentid = tpar_agentid;
    
    
     if tprovizija_mkd is null then let tprovizija_mkd=0; end if;
    

insert into provizija_promotori_zbiren(     provizija_promotori_zbirenid ,       datecreated ,  usercreated , version ,     
mesec ,     par_yearid ,     par_agentid ,   bodovi_licna_prod,novi_polisi_prov_lp ,       
  bodovi_timska_prod,   novi_polisi_prov_tp ,bodovi_sl_pozicija_lp,bodovi_sl_pozicija_tp, storno_polisi_prov_lp,novi_storno_bodovi_lp,
    storno_polisi_prov_tp,novi_storno_bodovi_tp,  bodovi_period,novi_polisi_prov,novi_storno_bodovi,storno_polisi_prov,bruto_provizija,
    novi_polisi_inkaso_lp,novi_polisi_inkaso_tp,novi_inkaso_prov,rolling_VK ,bonus_inkaso_prov)
   values ( sq_provizija_promotori_zbiren.nextval, current ,tusername ,0 , 
	  tmesec, tpar_yearid,tpar_agentid,  
      tbodovi_licna_prod,tnovi_polisi_prov_lp ,       
  tbodovi_timska_prod,   tnovi_polisi_prov_tp ,tbodovi_sl_pozicija_lp,tbodovi_sl_pozicija_tp, tstorno_polisi_prov_lp,tnovi_storno_bodovi_lp,
    tstorno_polisi_prov_tp,tnovi_storno_bodovi_tp,  tbodovi_period,tnovi_polisi_prov,tnovi_storno_bodovi,tstorno_polisi_prov,tbruto_provizija,
    tnovi_polisi_inkaso_lp,tnovi_polisi_inkaso_tp,tnovi_inkaso_prov,tbodovi_sledna_pozicija,tprovizija_mkd );
      
      
   
end foreach;




drop table inkaso_ta;
drop table inkaso_sa;
drop table polisa_max;
drop table zbiren;

--commit work;
return 1,'PRESMETANA E PROVIZIJA';

end function;