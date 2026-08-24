CREATE FUNCTION vesna.presmetka_prov_agenti_lc_newprov(tmesec char(2) , tgodina char(4) ,tuser_id int )
		returning integer,char(100);
{
procedurata vraka:
       
        - kod na greska
                  1 ako se e ok i ako e izvrseno 
                 -1 ako se pojavi nekoja neregularnost
        - poraka poradi koja e nastanata greskata
}

define  tpar_provizija_agentid , tpar_clientid ,tpar_agentid ,  tpar_provizijadefid ,  tpar_provizijatipid ,  tpar_provizijaispid ,  tpar_statusid,tpar_tip_kniziid  int;
define tos_aneks_fakturaid,tos_polisaid,tos_aneksid,tpar_yearid,tpar_yearid1,tos_ponudaid,tos_produktid,tperiod_osig,koja_god,trata  int;
define tnaplata, tnaplata_den, tiznos_d	,tiznos_d_den,tprovizija ,tpersonalec,vkupna_premija,tbr_rati,tosig_suma,tpremija_zivot,tproc_prov,tdat_naplata,tvk_bodovi_ag_nad,tppd_from_nad,	tppd_to_nad  dec;
define tusername char(30);
define tskadenca_datum_od,tod_odatum, tdo_datum,tdatum_prekin,tmin_datum date;
define dali_presmetana,netreba,tposrednik_par_client,dali_posrednik,tos_produkt_uplataid,tpar_nacin_platiid, tppi_onetime,tprovizija_agent_zbirenid int;
define tstartni_poeni,BB_iznos,tppd_valueval,tstartni_poeni_nadreden,tppd_valueval_nadr,BB_iznos_nadr,tiznos_bod,tkumul_bodovi,tvk_bodovi_ag,bb,tkumul_bodovi_preth dec;
define tpar_posrednik,dali_presm,tos_aneksid_prv,tpar_yearid_prva,tind_grupno,tbr_osig_lica,tbr_osig_lica_ponuda int;
define tppd_from,	tppd_to,	tppd_tipprodukcija,	tppd_valueden,	tpar_valutaid,tpar_nadreden_agentid, tpar_provizijadefid_nadreden   ,tppd_nadredenid, tppd_nadredenid_nad,mesec_pteh ,tpar_provizija_agentid_max ,tpar_valutaid_a 	 int;
define tpar_nacin_plati char(3);
define  tcela_naplata	,tcela_naplata_den,tsaldo,tbr_bodovi dec;
define tpar_nadreden_agentid_nad,tpar_provizijadefid_nadreden_nad,tpar_nadreden_agentid_nad1,tdali_postoi,tkolku_prv,dali_postoi,dali_ima,tpar_provizija_agentid_nadreden int;
define tstartni_poeni_nadreden_nad,tppd_valueval_nadr_nad,BB_iznos_nadr_nad  ,tlc_bodovi dec;
define ttip_provizija varchar(1);
define tsorabotnici,	tlicni_bodovi,	tsorab_bodovi,	tvk_bodovi,tkolku_agenti int;
define tvk_bodovi_uslov,tvk_bodovi_sorabotnici,tvk_bodovi_agent,tvk_bodovi_aa,tlc_bodovi_sorabotnici,tvk_premija,tiznos_cel,tiznt_eur,tnaplata_19,tprocent_provizija dec ;
define tpag_datumod,tdatum_ponuda date;
define tsifra_polisa varchar(2);
define tf_popust boolean;
define  tpar_status_aktiven varchar(1);
on exception
	--ROLLBACK WORK;
        return -1,'NASTANATA E GRE[KA';
end exception;

--set debug file to 'err_presmetka_prov_agenti_lc.sql';
--trace on;

set isolation to dirty read;  

--BEGIN WORK;
let tod_odatum='01.'||tmesec||'.'||tgodina;
 let tdo_datum=LAST_DAY(tod_odatum);

select par_yearid into tpar_yearid
from par_year 
where par_year = tgodina;
select count(*) into dali_presmetana
from lc_provizija_agent_zbiren
where  mesec = tmesec
and    par_yearid = tpar_yearid;

if  dali_presmetana>0 then
	--ROLLBACK WORK;
   -- return -1,'VEKE E PRESMETANA PROVIZIJATA';
end if; 

select username into tusername from adm_user
where userid=tuser_id;

foreach select
     par_provizija_agentid ,     par_clientid ,     par_agentid ,     par_provizijadefid ,
     a.par_provizijatipid ,     par_provizijaispid ,     a.par_statusid ,nvl(startni_poeni,0) ,nvl(lc_vk_bodovi,0), pag_datumod 
     into tpar_provizija_agentid ,    tpar_clientid ,     tpar_agentid ,     tpar_provizijadefid ,
     tpar_provizijatipid ,     tpar_provizijaispid ,     tpar_statusid ,tstartni_poeni,tvk_bodovi_aa,tpag_datumod
 from provizija_agent a , par_provizijatip b
 
where a.par_provizijatipid=b.par_provizijatipid
 and b.tip_provizija='I'
-- and par_agentid in (4490,4791,4786,4411)


and   ((tdo_datum between pag_datumod and pag_datumdo) or (tdo_datum >= pag_datumod and pag_datumdo is null))
order by par_agentid asc 


select sum(nvl(br_bodovi,0)) into tvk_bodovi_ag   
 from lc_provizija_agent_bodovi
where par_agentid=tpar_agentid
and par_provizijatipid=tpar_provizijatipid;

select min(pag_datumod) into tmin_datum
from provizija_agent a , par_provizijatip b
 where a.par_provizijatipid=b.par_provizijatipid
 and b.tip_provizija='I'
 and par_agentid=tpar_agentid;


if tvk_bodovi_ag is null  then let tvk_bodovi_ag=0; end if;

 let tvk_bodovi_ag=tvk_bodovi_ag+ tvk_bodovi_aa;

select tip_provizija into ttip_provizija
from  par_provizijatip
where par_provizijatipid=tpar_provizijatipid;


--if tpar_provizijatipid= 56 then --- Agenti - sopstvena provizija + meguprovizija --smeneto da bide po tip na provizija I agenti 
--if ttip_provizija='I' then 

select ppd_from,	ppd_to,	ppd_tipprodukcija,	ppd_valueden,	par_valutaid,	ppd_valueval,ppd_nadredenid
into tppd_from,	tppd_to,	tppd_tipprodukcija,	tppd_valueden,	tpar_valutaid,	tppd_valueval,tppd_nadredenid
 from par_provizijadef
where par_provizijadefid=tpar_provizijadefid;

--uslov za promena na bodovite	

/*select sorabotnici,	licni_bodovi,	sorab_bodovi,	vk_bodovi
into tsorabotnici,	tlicni_bodovi,	tsorab_bodovi,	tvk_bodovi
 from vesna.par_provizijadef_uslov 
 where par_provizijadefid=tpar_provizijadefid;*/

----tuka promena vo bodovite ----

select nvl(par_status_aktiven,'A') into tpar_status_aktiven from par_agent 
where par_agentid=tpar_agentid;

if tpar_status_aktiven='Z' then 
continue foreach;
end if; 

foreach 
select os_aneks_fakturaid,p.os_polisaid , o.period_osig,o.os_produktid,  o.promotor_par_agent, os_produkt_uplataid,
vrati_premija_zivot (o.os_ponudaid,o.os_produktid) ,nvl(o.br_osig_lica,1),o.os_ponudaid,o.datum_ponuda, sum(iznos_p), sum(iznos_p_den) 
into tos_aneks_fakturaid,tos_polisaid ,tperiod_osig,tos_produktid,tposrednik_par_client, tos_produkt_uplataid,tpremija_zivot, 
tbr_osig_lica_ponuda,tos_ponudaid,tdatum_ponuda ,tnaplata, tnaplata_den
 from fin_stavka f, os_polisa p, os_ponuda o, os_produkt a
where p.os_polisaid=f.os_polisaid
and o.os_ponudaid=p.os_ponudaid
and a.os_produktid=o.os_produktid 
and iznos_p is not null
and (o.par_agentid=tpar_agentid   or promotor_par_agent=tpar_agentid) 
and o.datum_ponuda>=tmin_datum
--and  skadenca_datum_od>= date('01.06.2023')
and p.os_polisaid not in (select os_polisaid
from lc_provizija_agent_bodovi  where par_agentid=tpar_agentid)
and a.os_tipproduktid not in (1622,15)
and f.par_tip_kniziid in (285)
and  datum between '01.10.2023' and tdo_datum
and o.broker_par_client is null 
group by 1,2,3,4,5,6,7,8,9,10
having  sum(iznos_p_den) <>0
order by o.datum_ponuda
let netreba=0;

if nvl(tposrednik_par_client,0)<>0 then 
	if tposrednik_par_client <>tpar_agentid  then 
		let netreba=1;
	end if;
end if; 


if  netreba=1 then 
continue foreach; 
end if;


select f_popust into tf_popust 
from os_polisa
where os_polisaid=tos_polisaid;

if  tf_popust='t' then 
continue foreach; 
end if;



select nvl(sum(nvl(iznos_premija,0)),0)
into tvk_premija 
from os_ponuda_detail
where os_ponudaid=tos_ponudaid
--and ts_vid_rizik='Or'
and datum_pocetok is null;


select nvl(br_osig_lica,1) 
 into tbr_osig_lica
from os_produkt 
where os_produktid=tos_produktid;

if tbr_osig_lica>1 then 
let tind_grupno=2;
else
let tind_grupno=1;
end if;



select pps_bodoviod,	pps_bodovido,	par_valutaid,		pps_valueval
into tppd_from,	tppd_to,	tpar_valutaid,	tppd_valueval
from par_provizijadef_St
where par_provizijadefid=tpar_provizijadefid
and pps_valueden=tind_grupno 

and   ((tod_odatum between pps_datumod and pps_datumdo) or (tod_odatum >= pps_datumod and pps_datumdo is null));
---proverka dali se presmetani bodovi ----

select count(*) into dali_presm
from lc_provizija_agent_bodovi 
where os_polisaid=tos_polisaid
and par_agentid=tpar_agentid;

if dali_presm>0 then
continue foreach;
end if;

select par_nacin_platiid into tpar_nacin_platiid
  from   os_produkt_uplata
  where os_produkt_uplataid=tos_produkt_uplataid;
  
  select par_nacin_plati into tpar_nacin_plati
  from par_nacin_plati
  where par_nacin_platiid=tpar_nacin_platiid;




if netreba=0 then 
-------BB=UP/1000-----
if tpar_nacin_plati='005' then
let BB=( tvk_premija*tbr_osig_lica_ponuda)/1000;
else 
let BB=(tvk_premija* tperiod_osig*tbr_osig_lica_ponuda)/1000;
end if;


let BB_iznos=tppd_valueval*BB;

insert into lc_provizija_agent_bodovi(     lc_provizija_agent_bodoviid ,          datecreated ,
          usercreated ,     version ,     mesec ,     par_yearid ,     par_agentid ,     os_polisaid ,  
		  br_bodovi ,     par_statusid,iznos_bod,tip_produkcija,datum_presmetka,iznos_bod_den,par_provizijatipid) 
	 values ( sq_lc_provizija_agent_bodovi.nextval ,current ,tusername ,0 ,
	 tmesec, tpar_yearid,tpar_agentid,tos_polisaid,BB,1,BB_iznos,'1',tod_odatum,tppd_valueval,tpar_provizijatipid);
if tvk_bodovi_ag is null  then let tvk_bodovi_ag=0; end if;
if tvk_bodovi_ag=0 then let tvk_bodovi_ag=tstartni_poeni; end if;
let tvk_bodovi_ag=tvk_bodovi_ag+BB;

select sum(nvl(br_bodovi,0)) into tlc_bodovi    from lc_provizija_agent_bodovi
where par_agentid=tpar_agentid
and tip_produkcija=1
and par_provizijatipid=tpar_provizijatipid;
--and datum_presmetka=tod_odatum;

let tlc_bodovi=tlc_bodovi+BB;


--sorabotnici 

select count(*) 
into tkolku_agenti 
from par_agent_st
where par_nadreden_agentid = tpar_agentid 
and   ((tdo_datum between pas_datumod and pas_datumdo) or (tdo_datum >= pas_datumod and pas_datumdo is null));

select sum(nvl(br_bodovi,0)) into tlc_bodovi_sorabotnici    from lc_provizija_agent_bodovi
where par_agentid in (select par_agentid

from par_agent_st
where par_nadreden_agentid = tpar_agentid 
and   ((tdo_datum between pas_datumod and pas_datumdo) or (tdo_datum >= pas_datumod and pas_datumdo is null)))
and tip_produkcija=1
and par_provizijatipid=tpar_provizijatipid
and datum_presmetka=tod_odatum;


select sum(nvl(br_bodovi,0)) into tvk_bodovi_sorabotnici    from lc_provizija_agent_bodovi
where par_agentid in (select par_agentid
from par_agent_st
where par_nadreden_agentid = tpar_agentid 
and   ((tdo_datum between pas_datumod and pas_datumdo) or (tdo_datum >= pas_datumod and pas_datumdo is null)))
and tip_produkcija=1
and par_provizijatipid=tpar_provizijatipid;




select sum(nvl(br_bodovi,0)) into tvk_bodovi_agent    from lc_provizija_agent_bodovi
where par_agentid in (select par_agentid
from par_agent_st
where par_nadreden_agentid = tpar_agentid 
and   ((tdo_datum between pas_datumod and pas_datumdo) or (tdo_datum >= pas_datumod and pas_datumdo is null)))
and tip_produkcija=1
and par_provizijatipid=tpar_provizijatipid;


let tvk_bodovi_uslov=tvk_bodovi_sorabotnici+tlc_bodovi+tvk_bodovi_aa;

foreach select sorabotnici,	licni_bodovi,	sorab_bodovi,	vk_bodovi
into tsorabotnici,	tlicni_bodovi,	tsorab_bodovi,	tvk_bodovi
 from vesna.par_provizijadef_uslov 
 where par_provizijadefid=tpar_provizijadefid
---  tsorabotnici,	tlicni_bodovi,	tsorab_bodovi,	tvk_bodovi
if nvl(tvk_bodovi_ag,0)>=tppd_to and  nvl(tlc_bodovi,0)>=tlicni_bodovi  and (nvl(tkolku_agenti,0)>= tsorabotnici ) and nvl(tlc_bodovi_sorabotnici,0)>=tsorab_bodovi and  nvl(tvk_bodovi_uslov,0)>=tvk_bodovi then 





---- proverka dali im a veke insert -----
select count(*)  into tdali_postoi from 
provizija_agent
where par_agentid=tpar_agentid
and pag_datumod=tdatum_ponuda+1 UNITS DAY
and par_provizijadefid=tppd_nadredenid;

if tdali_postoi=0 then 


let tpar_provizijadefid=tppd_nadredenid;

select ppd_from,	ppd_to,	ppd_tipprodukcija,	ppd_valueden,	par_valutaid,	ppd_valueval
into tppd_from,	tppd_to,	tppd_tipprodukcija,	tppd_valueden,	tpar_valutaid,	tppd_valueval
 from par_provizijadef
where par_provizijadefid=tppd_nadredenid;

select pps_bodoviod,	pps_bodovido,	par_valutaid,	pps_valueden,	pps_valueval
into tppd_from,	tppd_to,tppd_valueden,	tpar_valutaid,	tppd_valueval
from par_provizijadef_St
where par_provizijadefid=tppd_nadredenid
and pps_valueden=tind_grupno 
and   ((tdo_datum between pps_datumod and pps_datumdo) or (tdo_datum >= pps_datumod and pps_datumdo is null));




update provizija_agent set pag_datumdo=tdatum_ponuda
where par_provizija_agentid=tpar_provizija_agentid;



insert into provizija_agent(par_provizija_agentid ,       datecreated ,      usercreated ,
     version ,         par_agentid ,     par_provizijadefid ,     par_provizijatipid ,
     par_provizijaispid ,     startni_poeni ,     vk_bodovi ,     par_statusid ,     pag_datumod,f_avtomatski  ) 

	 select sq_provizija_agent.nextval ,current ,tusername ,0 ,  par_agentid ,     tppd_nadredenid ,     par_provizijatipid ,
     par_provizijaispid ,     startni_poeni ,     tvk_bodovi_ag ,     par_statusid ,    tdatum_ponuda +1 UNITS DAY,'a'
from provizija_agent
where par_provizija_agentid=tpar_provizija_agentid	 ;


end if;

end if;
end foreach; 
--let BB_iznos=tppd_valueval*BB;

--insert into lc_provizija_agent_bodovi(     lc_provizija_agent_bodoviid ,          datecreated ,
   --       usercreated ,     version ,     mesec ,     par_yearid ,     par_agentid ,     os_polisaid ,  
--		  br_bodovi ,     par_statusid,iznos_bod,tip_produkcija,datum_presmetka,iznos_bod_den,par_provizijatipid) 
--	 values ( sq_lc_provizija_agent_bodovi.nextval ,current ,tusername ,0 ,
--	 tmesec, tpar_yearid,tpar_agentid,tos_polisaid,BB,1,BB_iznos,'1',tod_odatum,tppd_valueval,tpar_provizijatipid);
	 
end if;	 
----tuka treba i delot za plus EUR na nadredeniot 

if   vrati_polisa(tos_polisaid)like '25%' then 
continue foreach; 
end if; 

select nvl(par_nadreden_agentid,0)
into tpar_nadreden_agentid
from par_agent
where par_agentid = tpar_agentid;
----tuka ke cita od par_agent stavki

select nvl(par_nadreden_agentid,0)
into tpar_nadreden_agentid
from par_agent_st
where par_agentid = tpar_agentid
and   ((tdo_datum between pas_datumod and pas_datumdo) or (tdo_datum >= pas_datumod and pas_datumdo is null));


if tpar_nadreden_agentid<>0 then 
----ako ima nadreden 
select  par_provizijadefid ,nvl(startni_poeni,0) ,par_provizija_agentid
     into     tpar_provizijadefid_nadreden  ,     tstartni_poeni_nadreden,tpar_provizija_agentid_nadreden
 from provizija_agent
where  ((tdo_datum between pag_datumod and pag_datumdo) or (tdo_datum >= pag_datumod and pag_datumdo is null))
and par_agentid=tpar_nadreden_agentid
and par_provizijatipid=tpar_provizijatipid;

-----------ako ima bodovi pominuvtpar_provizija_agentid_nadredena vo povisoko novo 

select ppd_from,	ppd_to,ppd_nadredenid
into tppd_from_nad,	tppd_to_nad,	tppd_nadredenid_nad
 from par_provizijadef
where par_provizijadefid=tpar_provizijadefid_nadreden;


select pps_bodoviod,	pps_bodovido
into tppd_from_nad,	tppd_to_nad
from par_provizijadef_St
where par_provizijadefid=tpar_provizijadefid_nadreden

and   ((tod_odatum between pps_datumod and pps_datumdo) or (tod_odatum >= pps_datumod and pps_datumdo is null));






select sum(nvl(br_bodovi,0)) into tlc_bodovi    from lc_provizija_agent_bodovi
where par_agentid=tpar_nadreden_agentid
and tip_produkcija=1
and par_provizijatipid=tpar_provizijatipid;
--and datum_presmetka=tod_odatum;

let tlc_bodovi=tlc_bodovi;

select sum(nvl(br_bodovi,0)) into tvk_bodovi_ag_nad   
 from lc_provizija_agent_bodovi
where par_agentid=tpar_nadreden_agentid
and par_provizijatipid=tpar_provizijatipid;


if tvk_bodovi_ag_nad is null  then let tvk_bodovi_ag_nad=0; end if;
if tvk_bodovi_ag_nad=0 then let tvk_bodovi_ag_nad=tstartni_poeni_nadreden; end if;
let tvk_bodovi_ag_nad=tvk_bodovi_ag_nad+BB;
--sorabotnici 

select count(*) 
into tkolku_agenti 
from par_agent_st
where par_nadreden_agentid = tpar_nadreden_agentid 
and   ((tdo_datum between pas_datumod and pas_datumdo) or (tdo_datum >= pas_datumod and pas_datumdo is null));

select sum(nvl(br_bodovi,0)) into tlc_bodovi_sorabotnici    from lc_provizija_agent_bodovi
where par_agentid in (select par_agentid

from par_agent_st
where par_nadreden_agentid = tpar_nadreden_agentid 
and   ((tdo_datum between pas_datumod and pas_datumdo) or (tdo_datum >= pas_datumod and pas_datumdo is null)))
and tip_produkcija=1
and par_provizijatipid=tpar_provizijatipid
and datum_presmetka=tod_odatum;

if tlc_bodovi_sorabotnici is null then let tlc_bodovi_sorabotnici=0; end if;


select sum(nvl(br_bodovi,0)) into tvk_bodovi_sorabotnici    from lc_provizija_agent_bodovi
where par_agentid in (select par_agentid
from par_agent_st
where par_nadreden_agentid = tpar_nadreden_agentid 
and   ((tdo_datum between pas_datumod and pas_datumdo) or (tdo_datum >= pas_datumod and pas_datumdo is null)))
and tip_produkcija=1
and par_provizijatipid=tpar_provizijatipid;

if tvk_bodovi_sorabotnici is null then let tvk_bodovi_sorabotnici=0; end if;



select sum(nvl(br_bodovi,0)) into tvk_bodovi_agent    from lc_provizija_agent_bodovi
where par_agentid in (select par_agentid
from par_agent_st
where par_nadreden_agentid = tpar_nadreden_agentid 
and   ((tdo_datum between pas_datumod and pas_datumdo) or (tdo_datum >= pas_datumod and pas_datumdo is null)))
and tip_produkcija=1
and par_provizijatipid=tpar_provizijatipid;
if tvk_bodovi_aa is null then let tvk_bodovi_aa=0; end if; 
if tlc_bodovi is null then let tlc_bodovi=0; end if; 


let tvk_bodovi_uslov=tvk_bodovi_sorabotnici+tlc_bodovi+tvk_bodovi_aa;

foreach select sorabotnici,	licni_bodovi,	sorab_bodovi,	vk_bodovi
into tsorabotnici,	tlicni_bodovi,	tsorab_bodovi,	tvk_bodovi
 from vesna.par_provizijadef_uslov 
 where par_provizijadefid=tpar_provizijadefid_nadreden
---  tsorabotnici,	tlicni_bodovi,	tsorab_bodovi,	tvk_bodovi
if nvl(tvk_bodovi_ag_nad,0)>=tppd_to_nad and  nvl(tlc_bodovi,0)>=tlicni_bodovi  and (nvl(tkolku_agenti,0)>= tsorabotnici ) and nvl(tlc_bodovi_sorabotnici,0)>=tsorab_bodovi and  nvl(tvk_bodovi_uslov,0)>=tvk_bodovi then 





---- proverka dali im a veke insert -----
select count(*)  into tdali_postoi from 
provizija_agent
where par_agentid=tpar_nadreden_agentid
and pag_datumod=tdatum_ponuda+1 UNITS DAY
and par_provizijadefid=tppd_nadredenid_nad;



if tdali_postoi=0 then 

update provizija_agent set pag_datumdo=tdatum_ponuda
where par_provizija_agentid=tpar_provizija_agentid_nadreden;



insert into provizija_agent(par_provizija_agentid ,       datecreated ,      usercreated ,
     version ,         par_agentid ,     par_provizijadefid ,     par_provizijatipid ,
     par_provizijaispid ,     startni_poeni ,     vk_bodovi ,     par_statusid ,     pag_datumod,f_avtomatski  ) 

	 select sq_provizija_agent.nextval ,current ,tusername ,0 ,  par_agentid ,     tppd_nadredenid_nad ,     par_provizijatipid ,
     par_provizijaispid ,     startni_poeni ,     tvk_bodovi_ag_nad ,     par_statusid ,    tdatum_ponuda +1 UNITS DAY,'a'
from provizija_agent
where par_provizija_agentid=tpar_provizija_agentid_nadreden	 ;

--let tpar_provizijadefid_nadreden=tppd_nadredenid_nad;

end if;

end if;
end foreach; 
--------po visoko novo



select 		ppd_valueval
into 	tppd_valueval_nadr
 from par_provizijadef
where par_provizijadefid=tpar_provizijadefid_nadreden;

select 	pps_valueval
into tppd_valueval_nadr
from par_provizijadef_St
where par_provizijadefid=tpar_provizijadefid_nadreden
and pps_valueden=tind_grupno 
and   ((tdo_datum between pps_datumod and pps_datumdo) or (tdo_datum >= pps_datumod and pps_datumdo is null));
if tppd_valueval_nadr is not null then 
let BB_iznos_nadr=(tppd_valueval_nadr*BB)-( tppd_valueval*BB);

if BB_iznos_nadr<0 then let BB_iznos_nadr=0; end if; 



insert into lc_provizija_agent_bodovi(     lc_provizija_agent_bodoviid ,          datecreated ,
          usercreated ,     version ,     mesec ,     par_yearid ,     par_agentid ,     os_polisaid ,     br_bodovi ,     par_statusid,iznos_bod,tip_produkcija,datum_presmetka,iznos_bod_den ,par_provizijatipid) 
	 values ( sq_lc_provizija_agent_bodovi.nextval ,current ,tusername ,0 ,
	 tmesec, tpar_yearid,tpar_nadreden_agentid,tos_polisaid,BB,1,BB_iznos_nadr,'2', tod_odatum,tppd_valueval_nadr,tpar_provizijatipid);
end if;	
---proverka dali nadredeniot ima nadreden 
 select nvl(par_nadreden_agentid,0)
into tpar_nadreden_agentid_nad
from par_agent_st
where par_agentid = tpar_nadreden_agentid
and   ((tdo_datum between pas_datumod and pas_datumdo) or (tdo_datum >= pas_datumod and pas_datumdo is null));


while tpar_nadreden_agentid_nad <>0   ----1

select  par_provizijadefid ,nvl(startni_poeni,0) 
     into     tpar_provizijadefid_nadreden_nad  ,     tstartni_poeni_nadreden_nad
 from provizija_agent
where  ((tdo_datum between pag_datumod and pag_datumdo) or (tdo_datum >= pag_datumod and pag_datumdo is null))
and par_agentid=tpar_nadreden_agentid_nad;


select 	pps_valueval
into tppd_valueval_nadr_nad
from par_provizijadef_St
where par_provizijadefid=tpar_provizijadefid_nadreden_nad
and pps_valueden=tind_grupno 
and   ((tdo_datum between pps_datumod and pps_datumdo) or (tdo_datum >= pps_datumod and pps_datumdo is null));

let BB_iznos_nadr_nad=(tppd_valueval_nadr_nad*BB)-( tppd_valueval_nadr*BB);


if BB_iznos_nadr_nad<0 then let BB_iznos_nadr_nad=0; end if; 



insert into lc_provizija_agent_bodovi(     lc_provizija_agent_bodoviid ,          datecreated ,
          usercreated ,     version ,     mesec ,     par_yearid ,     par_agentid ,     os_polisaid ,     br_bodovi ,     par_statusid,iznos_bod,tip_produkcija,datum_presmetka,iznos_bod_den ,par_provizijatipid ) 
	 values ( sq_lc_provizija_agent_bodovi.nextval ,current ,tusername ,0 ,
	 tmesec, tpar_yearid,tpar_nadreden_agentid_nad,tos_polisaid,BB,1,BB_iznos_nadr_nad,'2', tod_odatum,tppd_valueval_nadr_nad,tpar_provizijatipid);
	 
 select nvl(par_nadreden_agentid,0)
into tpar_nadreden_agentid_nad1
from par_agent_st
where par_agentid = tpar_nadreden_agentid_nad
and   ((tdo_datum between pas_datumod and pas_datumdo) or (tdo_datum >= pas_datumod and pas_datumdo is null));	 

let tpar_nadreden_agentid_nad=tpar_nadreden_agentid_nad1;
let tppd_valueval_nadr=tppd_valueval_nadr_nad;


end  while;----1
	
end if;	 

---tuka treba da bide uslovot za premin na povisoko nivo


end foreach;



--end foreach;


--------od tuka 16.10.2023


-----isplata na provizijata  vo sluvaj samo ako e naplatena i zavisi od  nacionot na plakanje
foreach 
select os_aneks_fakturaid,f.os_polisaid ,datum,o.promotor_par_agent,sum(iznos_p), sum(iznos_p_den) 
into tos_aneks_fakturaid,tos_polisaid ,tdat_naplata, tposrednik_par_client,tnaplata, tnaplata_den
 from fin_stavka f, os_polisa p, os_ponuda o
where p.os_polisaid=f.os_polisaid
and o.os_ponudaid=p.os_ponudaid
and iznos_p is not null
and (o.par_agentid=tpar_agentid or promotor_par_agent=tpar_agentid)
and ((vrati_polisa(p.os_polisaid) in  (select vrati_polisa(os_polisaid) from lc_provizija_agent_bodovi   where par_provizijatipid =2738)) or vrati_polisa(p.os_polisaid)like '19%'  or vrati_polisa(p.os_polisaid)like '25%')
--and p.os_polisaid in  (select os_polisaid from lc_provizija_agent_bodovi)
--and  datum between '01/12/2017' and tdo_datum
and  datum between add_months(tdo_datum,-3) and tdo_datum
and (f.os_aneks_fakturaid not in (select os_aneks_fakturaid from lc_provizija_agent_presmetka , provizija_agent 
where lc_provizija_agent_presmetka.provizija_agentid=provizija_agent.par_provizija_agentid
and provizija_agent.par_agentid=tpar_agentid) or (vrati_polisa(p.os_polisaid)like '19%') or (vrati_polisa(p.os_polisaid)like '25%') )
and f.par_tip_kniziid in (285,1128,1567,2974 )
and o.broker_par_client is null 
group by 1,2,3,4
having  sum(iznos_p_den) <>0
order by 2,3 desc


select os_ponudaid
into tos_ponudaid
 from os_polisa
where os_polisaid=tos_polisaid;

select os_produktid,skadenca_datum_od,period_osig, os_produkt_uplataid,par_valutaid,nvl(procent_provizija,0)
into tos_produktid,tskadenca_datum_od,tperiod_osig,tos_produkt_uplataid,tpar_valutaid_a ,tprocent_provizija 
 from os_ponuda
where os_ponudaid=tos_ponudaid;


if tpar_valutaid_a is null then
    select par_valutaid into tpar_valutaid
    from os_produkt
    where os_produktid=tos_produktid;
else 
    let tpar_valutaid=tpar_valutaid_a;
end if;
select sifra_polisa into tsifra_polisa
from os_produkt
where os_produktid=tos_produktid;


select par_nacin_platiid into tpar_nacin_platiid
  from   os_produkt_uplata
  where os_produkt_uplataid=tos_produkt_uplataid;
  
  select par_nacin_plati into tpar_nacin_plati
  from par_nacin_plati
  where par_nacin_platiid=tpar_nacin_platiid;
  
  if tpar_nacin_plati='005' then
  let tppi_onetime=1;

  else
  let tppi_onetime=2;
  end if;
  

execute  function vrati_osig_suma_zivot(tos_ponudaid,tos_produktid) into tosig_suma;
execute  function vrati_premija_zivot(tos_ponudaid,tos_produktid) into tpremija_zivot;
select sum(nvl(iznos_d,0)),	sum(nvl(iznos_d_den,0))
into  tiznos_d	,tiznos_d_den
 from fin_stavka 
where os_aneks_fakturaid=tos_aneks_fakturaid
and iznos_d is not null;


---- proverka dali e naplatena celata polisa uste ednas 
select sum(nvl(iznos_p,0)),	sum(nvl(iznos_p_den,0))
into  tcela_naplata	,tcela_naplata_den
 from fin_stavka 
where os_aneks_fakturaid=tos_aneks_fakturaid
and par_tip_dokumentid=285
and  datum <= tdo_datum
and iznos_p is not null;

select unique os_aneksid 
into tos_aneksid
from os_aneks_faktura
where os_aneks_fakturaid=tos_aneks_fakturaid;

select unique par_tip_kniziid, rata

into tpar_tip_kniziid,trata
from os_aneks_faktura
where os_aneks_fakturaid=tos_aneks_fakturaid;

select par_yearid,iznos_premija,br_rati 
into tpar_yearid1 , vkupna_premija ,tbr_rati
from os_aneks
where os_aneksid=tos_aneksid;


select par_year into tgodina
from par_year 
where par_yearid=tpar_yearid1;

let tproc_prov=0;

let koja_god=tgodina-year(tskadenca_datum_od)+1;
select nvl(ppi_valueproc,0),par_provizijaispid
 into tproc_prov, tpar_provizijaispid
 from par_provizijaisp
where ppi_fromday=koja_god
and par_provizijatipid=tpar_provizijatipid
and ppi_onetime=tppi_onetime;

if tproc_prov is null then let tproc_prov=0; end if; 

----kolku pari treba da zeme za taa polisa----

select  sum(iznos_bod) into tiznos_bod
 from lc_provizija_agent_bodovi
where  os_polisaid=tos_polisaid
and par_agentid=tpar_agentid;


select  sum(iznos) into tiznos_cel

from os_aneks_faktura a , os_aneks b
 where a.os_aneksid=  b.os_aneksid
 and a.os_aneksid=  tos_aneksid
 and rata=trata
 and par_yearid=tpar_yearid1
 and par_tip_kniziid in (285,1128,1567,2974 );




let tpersonalec=0.10;

let tprovizija=0;
 
--if tnaplata=tiznos_d then 
 if tcela_naplata=tiznos_d  then 

if tiznos_cel<>0  and tproc_prov <>0 then 
let tprovizija=(tiznos_d/tiznos_cel)*(tiznos_bod*tproc_prov*0.01)/tbr_rati;
else
let tprovizija=0;
end if; 
end if;

let netreba=0;
 if tcela_naplata=tiznos_d  then 
if tsifra_polisa='25'  and  tpar_tip_kniziid =285  then
let tprovizija=tiznos_cel*0.3;
end if;
end if; 

if tsifra_polisa in ('19','25') then

if nvl(tposrednik_par_client,0)<>0 then 
	if tposrednik_par_client <>tpar_agentid  then 
		let netreba=1;
	end if;
end if; 


if  netreba=1 then 
continue foreach; 
end if;



if tpar_valutaid=363 then 
if tprocent_provizija<>0 then let tproc_prov=tprocent_provizija;  else let tproc_prov=20;  end if; 
execute procedure konverzija (tdo_datum,tnaplata,'MKD','EUR') into tiznt_eur;
let tprovizija=(tiznt_eur*tproc_prov*0.01);
--let tproc_prov=20;
else 
if tprocent_provizija<>0 then let tproc_prov=tprocent_provizija;  else let tproc_prov=20;  end if; 
let tprovizija=(tnaplata*tproc_prov*0.01);
--let tproc_prov=20;
end if;
end if;

if tsifra_polisa='25' and tcela_naplata=tiznos_d and  tpar_tip_kniziid =285  then
select first 1  nvl(ppi_valueproc,0),par_provizijaispid
 into tproc_prov, tpar_provizijaispid
 from par_provizijaisp
where ppi_fromday=koja_god
and par_provizijatipid=1432
and ppi_onetime=tppi_onetime;

if tpar_valutaid=363 then 
execute procedure konverzija (tdo_datum,tnaplata,'MKD','EUR') into tiznt_eur;
let tprovizija=(tiznt_eur*tproc_prov*0.01);
else 
let tprovizija=(tnaplata*tproc_prov*0.01);
end if;
end if;



select count(1) into dali_postoi
from lc_provizija_agent_presmetka
where os_aneks_fakturaid=tos_aneks_fakturaid
and provizija_agentid=tpar_provizija_agentid;


select nvl(sum(naplata),0) into tnaplata_19 from lc_provizija_agent_presmetka
where os_aneks_fakturaid=tos_aneks_fakturaid;

if tsifra_polisa='19' and dali_postoi>1 then 
if tcela_naplata>=tnaplata_19   then
select count(*) into dali_postoi
from lc_provizija_agent_presmetka
where os_aneks_fakturaid=tos_aneks_fakturaid
and provizija_agentid=tpar_provizija_agentid;
else 
let dali_postoi=1;
end if; 

end if;


if tnaplata<0 and tprovizija>0 then 
let tprovizija=(-1)*tprovizija;
end if; 



if tprovizija<> 0 then 
if dali_postoi=0 then
insert into lc_provizija_agent_presmetka(
     lc_provizija_agent_presmetkaid ,     datecreated ,
     usercreated ,     version ,     provizija_agentid ,
     os_aneks_fakturaid ,     par_yearid ,     iznos_provizija ,
     iznos_peronalen ,     par_statusid ,     pap_datumod ,     pap_datumdo,par_provizijaispid, dat_naplata,proc_prov , naplata ,
	 naplata_den, koja_godina,br_rati, rata, prov_rata,mesec, tip_prov  ) 
 values (sq_lc_provizija_agent_presmetka.nextval ,current ,tusername ,0 , 
tpar_provizija_agentid, tos_aneks_fakturaid,tpar_yearid ,tprovizija ,tpersonalec ,1 , tod_odatum,tdo_datum,tpar_provizijaispid,tdat_naplata,tproc_prov, 
tnaplata,tnaplata_den,koja_god,tbr_rati,trata,tprovizija/tbr_rati,tmesec , 'PR3-new');
end if;
end if;


end foreach; 

 end foreach; 

foreach 
select a.par_agentid, os_aneks_fakturaid,f.os_polisaid ,datum,sum(iznos_p), sum(iznos_p_den) 
into tpar_nadreden_agentid,tos_aneks_fakturaid,tos_polisaid ,tdat_naplata, tnaplata, tnaplata_den
 from fin_stavka f, os_polisa p, os_ponuda o, lc_provizija_agent_bodovi a 
where p.os_polisaid=f.os_polisaid
and o.os_ponudaid=p.os_ponudaid
and iznos_p is not null
and p.os_polisaid = a.os_polisaid 
and  a.tip_produkcija='2' 
and f.os_aneks_fakturaid not in (select os_aneks_fakturaid from lc_provizija_agent_presmetka , provizija_agent 
where lc_provizija_agent_presmetka.provizija_agentid=provizija_agent.par_provizija_agentid
and provizija_agent.par_agentid=a.par_agentid)
 and p.os_polisaid   in  (select os_polisaid from lc_provizija_agent_bodovi  where par_provizijatipid =2738)
and  datum between tod_odatum and tdo_datum
and f.par_tip_kniziid in (285,1128,1567,2974 )
group by 1,2,3,4
having  sum(iznos_p_den) <>0
order by 3,4 desc


if   vrati_polisa(tos_polisaid)like '25%' then 
continue foreach; 
end if;

 select      par_provizija_agentid ,     par_clientid ,          par_provizijadefid ,
     par_provizijatipid ,     par_provizijaispid ,     par_statusid ,nvl(startni_poeni,0) ,nvl(vk_bodovi,0) 
     into tpar_provizija_agentid ,    tpar_clientid ,         tpar_provizijadefid ,
     tpar_provizijatipid ,     tpar_provizijaispid ,     tpar_statusid ,tstartni_poeni,tvk_bodovi_ag
 from provizija_agent

where  ((tdo_datum between pag_datumod and pag_datumdo) or (tdo_datum >= pag_datumod and pag_datumdo is null))
 and par_agentid=tpar_nadreden_agentid;


select os_ponudaid
into tos_ponudaid
 from os_polisa
where os_polisaid=tos_polisaid;

select os_produktid,skadenca_datum_od,period_osig, os_produkt_uplataid,nvl(procent_provizija,0)
into tos_produktid,tskadenca_datum_od,tperiod_osig,tos_produkt_uplataid,tprocent_provizija
 from os_ponuda
where os_ponudaid=tos_ponudaid;



select par_nacin_platiid into tpar_nacin_platiid
  from   os_produkt_uplata
  where os_produkt_uplataid=tos_produkt_uplataid;
  
  select par_nacin_plati into tpar_nacin_plati
  from par_nacin_plati
  where par_nacin_platiid=tpar_nacin_platiid;
  
  if tpar_nacin_plati='005' then
  let tppi_onetime=1;

  else
  let tppi_onetime=2;
  end if;
 

execute  function vrati_osig_suma_zivot(tos_ponudaid,tos_produktid) into tosig_suma;
execute  function vrati_premija_zivot(tos_ponudaid,tos_produktid) into tpremija_zivot;
select sum(nvl(iznos_d,0)),	sum(nvl(iznos_d_den,0))
into  tiznos_d	,tiznos_d_den
 from fin_stavka 
where os_aneks_fakturaid=tos_aneks_fakturaid
and iznos_d is not null;


---- proverka dali e naplatena celata polisa uste ednas 
select sum(nvl(iznos_p,0)),	sum(nvl(iznos_p_den,0))
into  tcela_naplata	,tcela_naplata_den
 from fin_stavka 
where os_aneks_fakturaid=tos_aneks_fakturaid
and par_tip_dokumentid=285
and  datum <= tdo_datum
and iznos_p is not null;

select unique os_aneksid 
into tos_aneksid
from os_aneks_faktura
where os_aneks_fakturaid=tos_aneks_fakturaid;

select unique par_tip_kniziid, rata

into tpar_tip_kniziid,trata
from os_aneks_faktura
where os_aneks_fakturaid=tos_aneks_fakturaid;

select par_yearid,iznos_premija,br_rati 
into tpar_yearid1 , vkupna_premija ,tbr_rati
from os_aneks
where os_aneksid=tos_aneksid;


select par_year into tgodina
from par_year 
where par_yearid=tpar_yearid1;

let  tproc_prov=0;

let koja_god=tgodina-year(tskadenca_datum_od)+1;
select nvl(ppi_valueproc,0),par_provizijaispid
 into tproc_prov, tpar_provizijaispid
 from par_provizijaisp
where ppi_fromday=koja_god
and par_provizijatipid=tpar_provizijatipid
and ppi_onetime=tppi_onetime;

----kolku pari treba da zeme za taa polisa----
let tiznos_bod=0;
select  nvl(sum(iznos_bod),0) into tiznos_bod
 from lc_provizija_agent_bodovi
where  os_polisaid=tos_polisaid
and par_agentid=tpar_nadreden_agentid;





let tpersonalec=0.10;
select  sum(iznos) into tiznos_cel
from os_aneks_faktura a , os_aneks b
 where a.os_aneksid=  b.os_aneksid
 and a.os_aneksid=  tos_aneksid
 and rata=trata
 and par_yearid=tpar_yearid1
 and  par_tip_kniziid in (285,1128,1567,2974 );

let tprovizija=0;
 
--if tnaplata=tiznos_d then 
 if tcela_naplata=tiznos_d then

if tiznos_cel<>0 then 
if tiznos_bod=0 THEN
	let tprovizija=0; 
else 
let tprovizija=(tiznos_d/tiznos_cel)*(tiznos_bod*tproc_prov*0.01)/tbr_rati;
end if;
else
let tprovizija=0;
end if; 

end if;

if tnaplata<0 and tprovizija>0 then 
let tprovizija=(-1)*tprovizija;
end if; 


select count(*) into dali_postoi
from lc_provizija_agent_presmetka
where os_aneks_fakturaid=tos_aneks_fakturaid
and provizija_agentid=tpar_provizija_agentid;

if tprovizija<> 0 then 
if dali_postoi=0 then 
insert into lc_provizija_agent_presmetka(
     lc_provizija_agent_presmetkaid ,     datecreated ,
     usercreated ,     version ,     provizija_agentid ,
     os_aneks_fakturaid ,     par_yearid ,     iznos_provizija ,
     iznos_peronalen ,     par_statusid ,     pap_datumod ,     pap_datumdo,par_provizijaispid, dat_naplata,proc_prov , naplata ,
	 naplata_den, koja_godina,br_rati, rata, prov_rata,mesec  , tip_prov,iznos_bod) 
 values (sq_lc_provizija_agent_presmetka.nextval ,current ,tusername ,0 , 
tpar_provizija_agentid, tos_aneks_fakturaid,tpar_yearid ,tprovizija ,tpersonalec ,1 , tod_odatum,tdo_datum,tpar_provizijaispid,tdat_naplata,tproc_prov, 
tnaplata,tnaplata_den,koja_god,tbr_rati,trata,tprovizija/tbr_rati,tmesec, 'PR3-new_2',tiznos_bod);

end if;
end if;

end foreach; 


---end 16.10.2023



--commit work;
return 1,'PRESMETANA E PROVIZIJA';

end function;
GO
