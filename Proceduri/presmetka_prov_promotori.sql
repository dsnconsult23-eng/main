CREATE FUNCTION vesna.presmetka_prov_promotori(tmesec char(2) , tgodina char(4) ,tuser_id int )
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
define tnaplata, tnaplata_den, tiznos_d	,tiznos_d_den,tprovizija ,tpersonalec,vkupna_premija,tbr_rati,tosig_suma,tpremija_zivot,tproc_prov,tdat_naplata dec;
define tusername char(30);
define tskadenca_datum_od,tod_odatum,tdatum_do_polisa, tdo_datum,tdatum_prekin,tdatum_ponuda, tpoceten_datum,tdatecreated,tdatum1 date;
define dali_presmetana,netreba,tposrednik_par_client,dali_posrednik,tos_produkt_uplataid,tpar_nacin_platiid, tppi_onetime,tprovizija_agent_zbirenid int;
define tstartni_poeni,BB_iznos,tppd_valueval,tstartni_poeni_nadreden,tppd_valueval_nadr,BB_iznos_nadr,tiznos_bod,tkumul_bodovi,tvk_bodovi_ag,bb,tkumul_bodovi_preth dec;
define tpar_posrednik,dali_presm,tos_aneksid_prv,tpar_yearid_prva,tind_grupno,tbr_osig_lica,tbr_osig_lica_ponuda int;
define tppd_from,	tppd_to,tppd_to1,	tppd_tipprodukcija,	tppd_valueden,	tpar_valutaid,tpar_nadreden_agentid, tpar_provizijadefid_nadreden   ,tppd_nadredenid ,mesec_pteh   	 int;
define tpar_nacin_plati char(3);define tkolku int;
define  tcela_naplata	,tcela_naplata_den,tsaldo,tbr_bodovi dec;
define tpar_nadreden_agentid_nad,tpar_provizijadefid_nadreden_nad,tpar_nadreden_agentid_nad1,tdali_postoi,tkolku_prv,dali_postoi,tdogovoruvac_par_client int;
define tstartni_poeni_nadreden_nad,tppd_valueval_nadr_nad,BB_iznos_nadr_nad, tstorno_bodovi,tduplirani_bodovi,tbod_sorabotnik,tprocent_vtor_uslov,kolku_boda_treba_vu	 dec;
define ttip_provizija,tprva_licna_polisa,tprva_druga_polisa  varchar(1);
define tdenovi_lp,tdenovi_tp,tppd_level,tpar_client_agent,tmeseci_vtor_uslov,tmeseci_sorabotnik,dali_drugo_nivo,tteam_milionerid,dali_team_manager,terr int;
define tpath,tporaka varchar(255);
define tvk_bodovi_granka_sam,tsum_bodovi_granki,tppd_valueval1,tvk_bodovi_granka,tvk_storno_bodovi,storno_bodovi_polisa,tstorno_bodovi_kumul,tstorno_bodovi_preth,tstorno_bodovi_mesec decimal;
define tpremija_zdravstveno,tpremija_nezgoda,tbod_podreden,tbr_bodovi_m,provizija_licna,tbod_licna,tbr_bodovi_licna,BB_povisoko_nivo,BB_ponisko_nivo dec;
define tpolisa_broj,ngodina varchar(7);
define tvk_bodovi_ag_preth,BB_povisoko_nivo_duplo,BB_ponisko_nivo_duplo,max_bodovi,tiznt_eur,tnaplata_19,tprocent_provizija dec;
define tpar_agentid_podnego1,tpar_agentid_podnego,dali_ima_podnego,dali_team_milioner,tlevel  int;
define  tpar_status_aktiven,ttip_produkcija varchar(1);
define tsifra_polisa varchar(2);

on exception
	--ROLLBACK WORK;
        return -1,'NASTANATA E GRE[KA';
end exception;

--set debug file to 'err_presmetka_prov11.sql';
--trace on;



BEGIN
ON EXCEPTION IN (-206)
      create temp   table t(
		Path varchar(255),
		CONNECT_BY_ISLEAF integer, 
		agent int);


END EXCEPTION
DELETE FROM t;
END

set isolation to dirty read;  
set optimization high;
--BEGIN WORK;
let tod_odatum='01.'||tmesec||'.'||tgodina;
 let tdo_datum=LAST_DAY(tod_odatum);
 
 if tdo_datum=MDY(12,31,year(tdo_datum)) then
   let tdatum_do_polisa=MDY(1,15,year(tdo_datum)+1);
 else
  let tdatum_do_polisa=MDY(month(tdo_datum)+1,15,year(tdo_datum));
 end if; 

select par_yearid into tpar_yearid
from par_year 
where par_year = tgodina;
select count(*) into dali_presmetana
from provizija_promotori_zbiren
where  mesec = tmesec
and    par_yearid = tpar_yearid;

if  dali_presmetana>0 then--samo da se izbrise zbiren ---
delete from provizija_promotori_zbiren
where mesec=tmesec
and par_yearid=tpar_yearid;
	--ROLLBACK WORK;
   -- return -1,'VEKE E PRESMETANA PROVIZIJATA';
end if; 

let ngodina=tgodina;
execute  FUNCTION vesna.presmetka_prov_agenti_lc(tmesec  , tgodina ,tuser_id ) into terr, tporaka;
-- Koristi ja generaliziranata prepresmetka: bez fiksna polisa/faktura,
-- so istoriska konfiguracija, blokada za status Z i bez fallback za iznos_bod=0.
execute  FUNCTION vesna.presmetka_prov_agenti_lc_prepresmetka_new(tmesec  , tgodina ,tuser_id ) into terr, tporaka;
execute  FUNCTION vesna.presmetka_prov_agenti_lc_newprov(tmesec  , tgodina ,tuser_id ) into terr, tporaka;


select username into tusername from adm_user
where userid=tuser_id;

foreach select Par_ProvizijaTipid, tip_provizija --1
into tpar_provizijatipid,ttip_provizija
 from Par_ProvizijaTip
where tip_provizija='P'





foreach select--2
     par_provizija_agentid ,     par_clientid ,     par_agentid ,     par_provizijadefid ,
          par_provizijaispid ,     par_statusid ,nvl(startni_poeni,0) ,nvl(lc_vk_bodovi,0) ,nvl(storno_bodovi,0) 
     into tpar_provizija_agentid ,    tpar_clientid ,     tpar_agentid ,     tpar_provizijadefid ,
          tpar_provizijaispid ,     tpar_statusid ,tstartni_poeni,tvk_bodovi_ag,tstorno_bodovi 
 from provizija_agent
where  ((tdo_datum between pag_datumod and pag_datumdo) or (tdo_datum >= pag_datumod and pag_datumdo is null))
 and par_provizijatipid=tpar_provizijatipid --and par_agentid=1809
 order by par_provizijadefid 	desc



select sum(br_bodovi+duplirani_bodovi) into tvk_bodovi_ag
 from provizija_promotori_bodovi
where par_agentid=tpar_agentid;

select pps_bodoviod,	pps_bodovido,	par_valutaid,		pps_valueval,bod_sorabotnik,	
meseci_sorabotnik,	procent_vtor_uslov,	nvl(meseci_vtor_uslov,0)


into tppd_from,	tppd_to,	tpar_valutaid,	tppd_valueval,tbod_sorabotnik,	
tmeseci_sorabotnik,	tprocent_vtor_uslov,	tmeseci_vtor_uslov
from par_provizijadef_St
where par_provizijadefid=tpar_provizijadefid
and nvl(pps_valueden,1) ='1' 

and   ((tdo_datum between pps_datumod and pps_datumdo) or (tdo_datum >= pps_datumod and pps_datumdo is null));
 
 
 
 

select nvl(Max(provizija_promotori_zbirenid),0)
into tprovizija_agent_zbirenid
 from provizija_promotori_zbiren
where par_agentid=tpar_agentid;
--and   mesec <tmesec
--and    par_yearid < tpar_yearid;


select nvl(vk_bodovi,0)
into tvk_bodovi_ag
 from provizija_promotori_zbiren
where par_agentid=tpar_agentid
and  provizija_promotori_zbirenid=tprovizija_agent_zbirenid;

let tvk_bodovi_ag_preth=tvk_bodovi_ag;

select nvl(storno_bodovi,0)
into tvk_storno_bodovi
 from provizija_promotori_zbiren
where par_agentid=tpar_agentid
and  provizija_promotori_zbirenid=tprovizija_agent_zbirenid;


select nvl(par_status_aktiven,'A') into tpar_status_aktiven from par_agent 
where par_agentid=tpar_agentid;


if ttip_provizija= 'P' then --- Agenti - sopstvena provizija + meguprovizija
select ppd_from,	ppd_to,	ppd_tipprodukcija,	ppd_valueden,	par_valutaid,	ppd_valueval,ppd_nadredenid,nvl(denovi_lp,0),	nvl(denovi_tp,0) ,ppd_level
into tppd_from,	tppd_to,	tppd_tipprodukcija,	tppd_valueden,	tpar_valutaid,	tppd_valueval,tppd_nadredenid,tdenovi_lp,tdenovi_tp,tppd_level
 from par_provizijadef
where par_provizijadefid=tpar_provizijadefid;

----tuka promena vo bodovite ----

let netreba=0;

foreach 
select os_aneks_fakturaid,p.os_polisaid , o.period_osig,o.os_produktid,  o.dogovoruvac_par_client, os_produkt_uplataid,
vrati_premija_zivot (o.os_ponudaid,o.os_produktid) ,nvl(o.br_osig_lica,1),o.datum_ponuda, f.par_tip_kniziid,o.os_ponudaid,o.datecreated,
  p.polisa_broj,o.promotor_par_agent,sum(iznos_p), sum(iznos_p_den) 
into tos_aneks_fakturaid,tos_polisaid ,tperiod_osig,tos_produktid,tdogovoruvac_par_client, tos_produkt_uplataid,tpremija_zivot, 
tbr_osig_lica_ponuda,tdatum_ponuda,tpar_tip_kniziid,tos_ponudaid,tdatecreated,tpolisa_broj,tposrednik_par_client,tnaplata, tnaplata_den
 from fin_stavka f, os_polisa p, os_ponuda o--, os_produkt a
where p.os_polisaid=f.os_polisaid
and o.os_ponudaid=p.os_ponudaid --and o.os_ponudaid=1
--and a.os_produktid=o.os_produktid 
						   
and iznos_p is not null
and  vrati_polisa(p.os_polisaid) not in (select vrati_polisa(os_polisaid ) from 
provizija_promotori_bodovi
where tip_produkcija='1'
and par_agentid=tpar_agentid ) and (o.par_agentid=tpar_agentid   or promotor_par_agent=tpar_agentid) 
and  skadenca_datum_od>= date('01.02.2023')-- '01.02.2017'
and f.par_tip_kniziid in (285,1128,1567 )
and  datum between date('01.02.2023') and tdo_datum
--and a.os_tipproduktid<>1622
and datum_polisa<=tdatum_do_polisa--tdo_datum+15 units day
group by 1,2,3,4,5,6,7,8,9,10,11,12,13,14
having  sum(iznos_p_den) <>0
order  by o.datum_ponuda,o.datecreated, p.polisa_broj, f.par_tip_kniziid

if nvl(tposrednik_par_client,0)<>0 then 
	if tposrednik_par_client <>tpar_agentid  then 
		let netreba=1;
	end if;
end if; 


if  netreba=1 then 
continue foreach; 
end if;



--set debug file to 'err_presmetka_prov11.sql';
--trace on;
if tpar_status_aktiven='Z' then 
continue foreach;
end if; 

select sifra_polisa into tsifra_polisa
from os_produkt
where os_produktid=tos_produktid;

if  tsifra_polisa='19' then
    continue foreach;
end if;


let netreba=0;
let tprva_licna_polisa='0';
let tprva_druga_polisa='0';
let storno_bodovi_polisa=0;
let bb_povisoko_nivo=0;
let tduplirani_bodovi=0;

select nvl(br_osig_lica,1) 
 into tbr_osig_lica
from os_produkt 
where os_produktid=tos_produktid;

if tbr_osig_lica>1 then 
let tind_grupno=2;
else
let tind_grupno=1;
end if;

select os_ponudaid into tos_ponudaid 
from os_polisa
where os_polisaid=tos_polisaid;


if tpar_tip_kniziid=1128 then
execute  function vrati_premija_nezgoda (tos_ponudaid ,tos_produktid) into tpremija_nezgoda;
end if;


if tpar_tip_kniziid=1567 then
execute  function vrati_premija_zdravstveno (tos_ponudaid ,tos_produktid) into tpremija_zdravstveno;
end if;


select pps_bodoviod,	pps_bodovido,	par_valutaid,		pps_valueval,bod_sorabotnik,	
meseci_sorabotnik,	procent_vtor_uslov,	nvl(meseci_vtor_uslov,0)


into tppd_from,	tppd_to,	tpar_valutaid,	tppd_valueval,tbod_sorabotnik,	
tmeseci_sorabotnik,	tprocent_vtor_uslov,	tmeseci_vtor_uslov
from par_provizijadef_St
where par_provizijadefid=tpar_provizijadefid
and nvl(pps_valueden,1) =tind_grupno 

and   ((tdatum_ponuda between pps_datumod and pps_datumdo) or (tdatum_ponuda >= pps_datumod and pps_datumdo is null));
---proverka dali se presmetani bodovi ----
let tppd_valueval1=tppd_valueval;

select count(*) into dali_presm
from provizija_promotori_bodovi 
where vrati_polisa(os_polisaid) = vrati_polisa(tos_polisaid )
--os_polisaid=tos_polisaid
and par_tip_kniziid=tpar_tip_kniziid;


select par_client_id,poceten_datum
into tpar_client_agent, tpoceten_datum
from par_agent
where par_agentid=tpar_agentid;

if dali_presm>0 then
continue foreach;
end if;
if tppd_level=1 then 
if tdenovi_lp<>0 then
if (tdogovoruvac_par_client=tpar_client_agent)
 and (tdatum_ponuda between tpoceten_datum and tpoceten_datum+tdenovi_lp) then
let tprva_licna_polisa='1';


end if;
end if;

if tdenovi_tp<>0 then
if (tdogovoruvac_par_client<>tpar_client_agent)
 and (tdatum_ponuda between tpoceten_datum and tpoceten_datum+tdenovi_tp) then
let tprva_druga_polisa='1';

end if;
end if;

end if;


select par_nacin_platiid into tpar_nacin_platiid
  from   os_produkt_uplata
  where os_produkt_uplataid=tos_produkt_uplataid;
  
  select par_nacin_plati into tpar_nacin_plati
  from par_nacin_plati
  where par_nacin_platiid=tpar_nacin_platiid;




if netreba=0 then 
-------BB=UP/1000-----
if tpar_tip_kniziid=285 then 
if tpar_nacin_plati='005' then
let BB=( tpremija_zivot*tbr_osig_lica_ponuda)/520;
else 
let BB=(tperiod_osig* tpremija_zivot*tbr_osig_lica_ponuda)/520;
end if;
else
if tpar_tip_kniziid=1128 then
	let BB=( tpremija_nezgoda*tbr_osig_lica_ponuda)/333;
end if;

if tpar_tip_kniziid=1567 then
	let BB=( tpremija_zdravstveno*tbr_osig_lica_ponuda)/333;
end if;


end if;
----tuka treba da ima proverka ----ako go nadminuva limitot treba da pominuva vo povisoko novo -------samiot agent09.12.2014
let tvk_bodovi_ag_preth=tvk_bodovi_ag;
if tvk_bodovi_ag is null  then let tvk_bodovi_ag=0; end if;
if tvk_bodovi_ag=0 then let tvk_bodovi_ag=tstartni_poeni; end if;
let tvk_bodovi_ag=tvk_bodovi_ag+BB;


if tvk_storno_bodovi is null  then let tvk_storno_bodovi=0; end if;
if tvk_storno_bodovi=0 then let tvk_storno_bodovi=tstorno_bodovi; end if;
if tprva_druga_polisa='1' or tprva_licna_polisa='1' then
let tduplirani_bodovi=BB;
end if; 
if tvk_storno_bodovi<>0 then
let tvk_storno_bodovi=tvk_storno_bodovi-BB;
let storno_bodovi_polisa=BB;
end if;

let tvk_bodovi_ag=tvk_bodovi_ag+tduplirani_bodovi;

if tvk_bodovi_ag>tppd_to  and tvk_storno_bodovi<=0 then 

----- vo slucaj koga preminuva vo naredno nivo --20.04.2017
select count(*)  into tdali_postoi from 
provizija_agent
where par_agentid=tpar_agentid
and pag_datumod=tdo_datum+1 UNITS DAY
and par_provizijadefid=tppd_nadredenid;
let BB_povisoko_nivo=tvk_bodovi_ag-tppd_to;
if tprva_druga_polisa='0' then ---18.07.2017
if BB_povisoko_nivo>0 and tdali_postoi=0 then 
	--if BB-BB_povisoko_nivo<0 then
	--let BB_ponisko_nivo=tppd_to-BB;
	--else

	let BB_ponisko_nivo=BB+tduplirani_bodovi-BB_povisoko_nivo;
	--end if;
	let BB_iznos=tppd_valueval*BB_ponisko_nivo;
	if BB_povisoko_nivo-tduplirani_bodovi<0 and (tduplirani_bodovi>0 )  then 
	let BB_ponisko_nivo=BB_ponisko_nivo/2;
	let BB_povisoko_nivo=BB_povisoko_nivo/2;
	let BB_iznos=tppd_valueval*BB_ponisko_nivo;
	else
	let BB_povisoko_nivo=BB_povisoko_nivo-tduplirani_bodovi;
	end if;
	
	if tduplirani_bodovi>0 then 
	let BB_ponisko_nivo_duplo=BB_ponisko_nivo;
	else
	let BB_ponisko_nivo_duplo=0;
	end if;
	
insert into provizija_promotori_bodovi(     provizija_promotori_bodoviid ,          datecreated ,
          usercreated ,     version ,     mesec ,     par_yearid ,     par_agentid ,     os_polisaid ,  
		  br_bodovi ,     par_statusid,iznos_bod,tip_produkcija,datum_presmetka,promotor_par_agentid,
		  prva_licna_polisa,prva_druga_polisa,bod,duplirani_bodovi,storno_bodovi,par_tip_kniziid) 
	 values ( sq_provizija_promotori_bodovi.nextval ,current ,tusername ,0 ,
	 tmesec, tpar_yearid,tpar_agentid,tos_polisaid,BB_ponisko_nivo,1,BB_iznos,'1',tod_odatum,tpar_agentid,
	 tprva_licna_polisa,tprva_druga_polisa,tppd_valueval, BB_ponisko_nivo_duplo,storno_bodovi_polisa,tpar_tip_kniziid);
 end if; 
end if;



 select ppd_from,	ppd_to,	ppd_tipprodukcija,	ppd_valueden,	par_valutaid,	ppd_valueval
into tppd_from,	tppd_to1,	tppd_tipprodukcija,	tppd_valueden,	tpar_valutaid,	tppd_valueval
 from par_provizijadef
where par_provizijadefid=tppd_nadredenid;

select pps_bodoviod,	pps_bodovido,	par_valutaid,	pps_valueden,	pps_valueval
into tppd_from,	tppd_to1,tppd_valueden,	tpar_valutaid,	tppd_valueval
from par_provizijadef_St
where par_provizijadefid=tppd_nadredenid
and nvl(pps_valueden,1)=tind_grupno 
and   ((tdo_datum between pps_datumod and pps_datumdo) or (tdo_datum >= pps_datumod and pps_datumdo is null));

---ima nivoa  so 2 uslovi-----
let  dali_drugo_nivo=0;


if tmeseci_vtor_uslov=0 then 
let dali_drugo_nivo=1;
else
let kolku_boda_treba_vu=tppd_to* tmeseci_vtor_uslov*0.01;
insert into t 
SELECT 
SYS_CONNECT_BY_PATH(par_agentid, ',') Path,CONNECT_BY_ISLEAF ,tpar_agentid
      FROM par_agent_st v
where  par_agentid in (select par_agentid from provizija_agent where par_provizijatipid=tpar_provizijatipid  and 
((today between pag_datumod and pag_datumdo) or (today >= pag_datumod and pag_datumdo is null)))
and par_nadreden_agentid in (select par_agentid from provizija_agent where par_provizijatipid=tpar_provizijatipid  and 
((today between pag_datumod and pag_datumdo) or (today >= pag_datumod and pag_datumdo is null)))
 and   ((today between pas_datumod and pas_datumdo) or (today >= pas_datumod and pas_datumdo is null))
      START WITH par_nadreden_agentid=tpar_agentid
      CONNECT BY par_nadreden_agentid = PRIOR par_agentid;

	  
select  nvl(sum(nvl(br_bodovi,0)),0)+nvl(sum(nvl(duplirani_bodovi,0)),0)
into  tvk_bodovi_granka_sam
from provizija_promotori_bodovi
where  par_agentid=tpar_agentid
and tip_produkcija='1' 
and date('01.'||mesec||'.'||vrati_godina(par_yearid))  between tod_datum- tmeseci_vtor_uslov units month and  tod_odatum;

insert into provizija_promotori_vtoruslov(     provizija_promotori_vtoruslovid ,   datecreated , usercreated ,     version ,
     mesec ,     par_yearid ,     datum_presmetka ,     par_agentid ,     path ,     tip_produkcija ,     br_bodovi ,     par_statusid) 
	 values ( sq_provizija_promotori_vtoruslov.nextval, current,tusername ,0 , tmesec, tpar_yearid,tod_odatum,
	 tpar_agentid,tpar_agentid,1,BB,tvk_bodovi_granka,1);

let tsum_bodovi_granki=0;	  
foreach select  '('||SUBSTR(path,2,LENGTH(path) )||')' into tpath
 from t where  connect_by_isleaf=1  
	  
select  nvl(sum(nvl(br_bodovi,0)),0)+nvl(sum(nvl(duplirani_bodovi,0)),0)
into  tvk_bodovi_granka
from provizija_promotori_bodovi
where  par_agentid in (tpath)
and tip_produkcija='2' 
and date('01./'||mesec||vrati_godina(par_yearid))  between tod_datum- tmeseci_vtor_uslov units month  and  tod_odatum;

/*if tvk_bodovi_granka_otkaci>tvk_bodovi_granka  then  
 let tsum_bodovi_granki=tsum_bodovi_granki+tvk_bodovi_granka;
continue foreach;
else
 let tpath1= tpath;
 let tvk_bodovi_granka_otkaci=tvk_bodovi_granka;
end if;*/

insert into provizija_promotori_vtoruslov(     provizija_promotori_vtoruslovid ,   datecreated , usercreated ,     version ,
     mesec ,     par_yearid ,     datum_presmetka ,     par_agentid ,     path ,     tip_produkcija ,     br_bodovi ,     par_statusid) 
	 values ( sq_provizija_promotori_vtoruslov.nextval, current,tusername ,0 , tmesec, tpar_yearid,tod_odatum,
	 tpar_agentid,tpath,'2',BB,tvk_bodovi_granka,1);
	 
end foreach; 

/*select  path,max(br_bodovi) into  tpath,tvk_bodovi_granka_otkaci
from provizija_promotori_vtoruslov
where where  par_agentid=tpar_agentid
and mesec=tmesec
and par_yearid=tpar_yearid
group by 1
*/

if tsum_bodovi_granki>kolku_boda_treba_vu then
let dali_drugo_nivo=1;
end if;

end if;

---- proverka dali im a veke insert -----
select count(*)  into tdali_postoi from 
provizija_agent
where par_agentid=tpar_agentid
and pag_datumod=tdo_datum+1 UNITS DAY
and par_provizijadefid=tppd_nadredenid;



if tdali_postoi=0  and dali_drugo_nivo=1 then 

update provizija_agent set pag_datumdo=tdo_datum
where par_provizija_agentid=tpar_provizija_agentid;




insert into provizija_agent(par_provizija_agentid ,       datecreated ,      usercreated ,
     version ,         par_agentid ,     par_provizijadefid ,     par_provizijatipid ,
     par_provizijaispid ,     startni_poeni ,     vk_bodovi ,     par_statusid ,     pag_datumod ,f_avtomatski ) 

	 select sq_provizija_agent.nextval ,current ,tusername ,0 ,  par_agentid ,     tppd_nadredenid ,     par_provizijatipid ,
     par_provizijaispid ,     startni_poeni ,     tvk_bodovi_ag ,     par_statusid ,     tdo_datum+1 UNITS DAY,'a'
from provizija_agent
where par_provizija_agentid=tpar_provizija_agentid	 ;


end if;

end if;

let BB_iznos=tppd_valueval*BB;
if tprva_druga_polisa='0' then
let tduplirani_bodovi=0;
else
let BB_iznos=tppd_valueval1*BB;
end if; 

--if tprva_druga_polisa='1' or --18.07.2017
if tprva_licna_polisa='1' then
let tduplirani_bodovi=BB;
end if; 

 if BB_povisoko_nivo>0 and tdali_postoi=0  and tprva_licna_polisa='1' then 
 let BB_iznos=tppd_valueval*BB_povisoko_nivo;
 
 	if tduplirani_bodovi>0 then 
	let BB_povisoko_nivo_duplo=BB_povisoko_nivo;
	else
	let BB_povisoko_nivo_duplo=0;
	end if;
	
 
 insert into provizija_promotori_bodovi(     provizija_promotori_bodoviid ,          datecreated ,
          usercreated ,     version ,     mesec ,     par_yearid ,     par_agentid ,     os_polisaid ,  
		  br_bodovi ,     par_statusid,iznos_bod,tip_produkcija,datum_presmetka,promotor_par_agentid,
		  prva_licna_polisa,prva_druga_polisa,bod,duplirani_bodovi,storno_bodovi,par_tip_kniziid) 
	 values ( sq_provizija_promotori_bodovi.nextval ,current ,tusername ,0 ,
	 tmesec, tpar_yearid,tpar_agentid,tos_polisaid,BB_povisoko_nivo,1,BB_iznos,'1',tod_odatum,tpar_agentid,
	 tprva_licna_polisa,tprva_druga_polisa,tppd_valueval, BB_povisoko_nivo_duplo,storno_bodovi_polisa,tpar_tip_kniziid);
 
 else

insert into provizija_promotori_bodovi(     provizija_promotori_bodoviid ,          datecreated ,
          usercreated ,     version ,     mesec ,     par_yearid ,     par_agentid ,     os_polisaid ,  
		  br_bodovi ,     par_statusid,iznos_bod,tip_produkcija,datum_presmetka,promotor_par_agentid,
		  prva_licna_polisa,prva_druga_polisa,bod,duplirani_bodovi,storno_bodovi,par_tip_kniziid) 
	 values ( sq_provizija_promotori_bodovi.nextval ,current ,tusername ,0 ,
	 tmesec, tpar_yearid,tpar_agentid,tos_polisaid,BB,1,BB_iznos,'1',tod_odatum,tpar_agentid,
	 tprva_licna_polisa,tprva_druga_polisa,tppd_valueval, tduplirani_bodovi,storno_bodovi_polisa,tpar_tip_kniziid);
end if;	 
--if tprva_druga_polisa='1' or tprva_licna_polisa='1' then	 --- na najviskoto novo se odzemaat ------
if  tprva_licna_polisa='1' then	 --- na najviskoto novo se odzemaat ------samo za licna polisa 

--- da se proveri prvo dali ima poveke

select count(*) into dali_team_milioner from provizija_agent
where par_provizijadefid=1140;

let tpar_agentid=tpar_agentid;

if dali_team_milioner=1 then 
	select par_agentid into tteam_milionerid from provizija_agent
	where par_provizijadefid=1140;
else 	
foreach 
	SELECT  first  1 par_nadreden_agentid ,level
	into tteam_milionerid, tlevel 
      FROM par_agent_st v
where  par_agentid in (select par_agentid from provizija_agent where par_provizijatipid=1093  and 
((tdo_datum between pag_datumod and pag_datumdo) or (tdo_datum >= pag_datumod and pag_datumdo is null)))
and par_nadreden_agentid in (select par_agentid from provizija_agent where par_provizijatipid=1093  and 
((tdo_datum between pag_datumod and pag_datumdo) or (tdo_datum >= pag_datumod and pag_datumdo is null))and  par_provizijadefid=1140)
 and   ((tdo_datum between pas_datumod and pas_datumdo) or (tdo_datum >= pas_datumod and pas_datumdo is null))
      START WITH par_agentid=tpar_agentid
      CONNECT BY PRIOR   par_nadreden_agentid= par_agentid
order by level desc 
end foreach;
if tteam_milionerid is null then 

	select first 1  par_agentid into tteam_milionerid from provizija_agent
	where par_provizijadefid=286;
end if;	
end if; 
insert into provizija_promotori_bodovi(     provizija_promotori_bodoviid ,          datecreated ,
          usercreated ,     version ,     mesec ,     par_yearid ,     par_agentid ,     os_polisaid ,  
		  br_bodovi ,     par_statusid,iznos_bod,tip_produkcija,datum_presmetka,promotor_par_agentid,
		  prva_licna_polisa,prva_druga_polisa,bod,duplirani_bodovi,storno_bodovi,par_tip_kniziid) 
	 values ( sq_provizija_promotori_bodovi.nextval ,current ,tusername ,0 ,
	 tmesec, tpar_yearid,tteam_milionerid,tos_polisaid,(-1)*BB,1,(-1)*BB_iznos,'2',tod_odatum,tpar_agentid,
	 tprva_licna_polisa,tprva_druga_polisa,tppd_valueval, 0,storno_bodovi_polisa,tpar_tip_kniziid);
	 	 
end if;	 
	 
end if;	 
----tuka treba i delot za plus EUR na nadredeniot 
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

let dali_team_manager=0;

/*if tprva_druga_polisa='1' or tprva_licna_polisa='1' then	 --- na najviskoto novo se odzemaat ------

select count(*) into dali_team_manager from provizija_agent
where par_provizijadefid=286
and par_agentid=tpar_nadreden_agentid;
end if;*/
----ako ima nadreden 
select  par_provizijadefid ,nvl(startni_poeni,0) 
     into     tpar_provizijadefid_nadreden  ,     tstartni_poeni_nadreden
 from provizija_agent
where  ((tdo_datum between pag_datumod and pag_datumdo) or (tdo_datum >= pag_datumod and pag_datumdo is null))
and par_agentid=tpar_nadreden_agentid;

select 		ppd_valueval
into 	tppd_valueval_nadr
 from par_provizijadef
where par_provizijadefid=tpar_provizijadefid_nadreden;

select 	pps_valueval,bod_sorabotnik,meseci_sorabotnik,	procent_vtor_uslov,	nvl(meseci_vtor_uslov,0)
into tppd_valueval_nadr,tbod_sorabotnik,tmeseci_sorabotnik,	tprocent_vtor_uslov,	tmeseci_vtor_uslov
from par_provizijadef_St
where par_provizijadefid=tpar_provizijadefid_nadreden
and nvl(pps_valueden,1)=tind_grupno 
and   ((tdo_datum between pps_datumod and pps_datumdo) or (tdo_datum >= pps_datumod and pps_datumdo is null));

										  
		  
								
								  
/*
if tprva_druga_polisa='0' then
										 
let BB_iznos_nadr=(tppd_valueval_nadr*BB)-( tppd_valueval*BB);
else
let BB_iznos_nadr=(tppd_valueval_nadr*BB)-( tppd_valueval1*BB);
	   
																
	
															   
end if; */
if tprva_druga_polisa='0' then
if tppd_valueval_nadr=tppd_valueval1 then
let BB_iznos_nadr=(tppd_valueval_nadr*BB)-( tppd_valueval*BB);
else
let BB_iznos_nadr=(tppd_valueval_nadr*BB)-( tppd_valueval1*BB);
end if;
--let BB_iznos_nadr=(tppd_valueval_nadr*BB)-( tppd_valueval*BB);
else
let BB_iznos_nadr=(tppd_valueval_nadr*BB)-( tppd_valueval1*BB);
end if; 
if dali_team_manager=0 then 
if BB_iznos_nadr>0 then

if BB_povisoko_nivo>0 and tdali_postoi=0  and tprva_druga_polisa='0' then 
	let BB_ponisko_nivo=BB-BB_povisoko_nivo;
	let BB_iznos_nadr=(tppd_valueval_nadr*BB_ponisko_nivo)-( tppd_valueval*BB_ponisko_nivo);
	insert into provizija_promotori_bodovi(     provizija_promotori_bodoviid ,          datecreated ,
          usercreated ,     version ,     mesec ,     par_yearid ,     par_agentid ,     os_polisaid ,     br_bodovi ,  
		  par_statusid,iznos_bod,tip_produkcija,datum_presmetka,promotor_par_agentid,bod,par_tip_kniziid,bod_podreden ) 
	 values ( sq_provizija_promotori_bodovi.nextval ,current ,tusername ,0 ,
	 tmesec, tpar_yearid,tpar_nadreden_agentid,tos_polisaid,BB_ponisko_nivo,1,
	 BB_iznos_nadr,'2', tod_odatum,tpar_agentid,tppd_valueval_nadr,tpar_tip_kniziid,tppd_valueval);
	 
	 let BB_iznos_nadr=(tppd_valueval_nadr*BB_povisoko_nivo)-( tppd_valueval*BB_povisoko_nivo);
	 insert into provizija_promotori_bodovi(     provizija_promotori_bodoviid ,          datecreated ,
     usercreated ,     version ,     mesec ,     par_yearid ,     par_agentid ,     os_polisaid ,     br_bodovi ,  
		par_statusid,iznos_bod,tip_produkcija,datum_presmetka,promotor_par_agentid,bod,par_tip_kniziid,bod_podreden ) 
	 values ( sq_provizija_promotori_bodovi.nextval ,current ,tusername ,0 ,
	 tmesec, tpar_yearid,tpar_nadreden_agentid,tos_polisaid,BB_povisoko_nivo,1,
	 BB_iznos_nadr,'2', tod_odatum,tpar_agentid,tppd_valueval_nadr,tpar_tip_kniziid,tppd_valueval);
	
else	
insert into provizija_promotori_bodovi(     provizija_promotori_bodoviid ,          datecreated ,
          usercreated ,     version ,     mesec ,     par_yearid ,     par_agentid ,     os_polisaid ,     br_bodovi ,  
		  par_statusid,iznos_bod,tip_produkcija,datum_presmetka,promotor_par_agentid,bod,par_tip_kniziid,bod_podreden ) 
	 values ( sq_provizija_promotori_bodovi.nextval ,current ,tusername ,0 ,
	 tmesec, tpar_yearid,tpar_nadreden_agentid,tos_polisaid,BB,1,
	 BB_iznos_nadr,'2', tod_odatum,tpar_agentid,tppd_valueval_nadr,tpar_tip_kniziid,tppd_valueval);
end if;
	 end if;	 
end if; 


---proverka dali nadredeniot ima nadreden -----02.06.2015 Slagjana 
 select nvl(par_nadreden_agentid,0)
into tpar_nadreden_agentid_nad
from par_agent_st
where par_agentid = tpar_nadreden_agentid
and   ((tdo_datum between pas_datumod and pas_datumdo) or (tdo_datum >= pas_datumod and pas_datumdo is null));


while tpar_nadreden_agentid_nad <>0   

select  par_provizijadefid ,nvl(startni_poeni,0) 
     into     tpar_provizijadefid_nadreden_nad  ,     tstartni_poeni_nadreden_nad
 from provizija_agent
where  ((tdo_datum between pag_datumod and pag_datumdo) or (tdo_datum >= pag_datumod and pag_datumdo is null))
and par_agentid=tpar_nadreden_agentid_nad;


select 	pps_valueval
into tppd_valueval_nadr_nad
from par_provizijadef_St
where par_provizijadefid=tpar_provizijadefid_nadreden_nad
and nvl(pps_valueden,1)=tind_grupno 
and   ((tdo_datum between pps_datumod and pps_datumdo) or (tdo_datum >= pps_datumod and pps_datumdo is null));

let BB_iznos_nadr_nad=(tppd_valueval_nadr_nad*BB)-( tppd_valueval_nadr*BB);
let dali_team_manager=0;

/*if tprva_druga_polisa='1' or tprva_licna_polisa='1' then	 --- na najviskoto novo se odzemaat ------

select count(*) into dali_team_manager from provizija_agent
where par_provizijadefid=286
and par_agentid=tpar_nadreden_agentid_nad;
end if;*/
if dali_team_manager=0 then 
if BB_iznos_nadr_nad>0 then 
insert into provizija_promotori_bodovi(     provizija_promotori_bodoviid ,          datecreated ,
          usercreated ,     version ,     mesec ,     par_yearid ,     par_agentid ,     os_polisaid ,  
		  br_bodovi ,     par_statusid,iznos_bod,tip_produkcija,datum_presmetka,promotor_par_agentid,bod,par_tip_kniziid,bod_podreden ) 
	 values ( sq_provizija_promotori_bodovi.nextval ,current ,tusername ,0 ,
	 tmesec, tpar_yearid,tpar_nadreden_agentid_nad,tos_polisaid,BB,1,BB_iznos_nadr_nad,'2', tod_odatum,tpar_nadreden_agentid,
	 tppd_valueval_nadr_nad,tpar_tip_kniziid,tppd_valueval_nadr);
end if; 	 
end if;	 
 select nvl(par_nadreden_agentid,0)
into tpar_nadreden_agentid_nad1
from par_agent_st
where par_agentid = tpar_nadreden_agentid_nad
and   ((tdo_datum between pas_datumod and pas_datumdo) or (tdo_datum >= pas_datumod and pas_datumdo is null));	 

let tpar_nadreden_agentid_nad=tpar_nadreden_agentid_nad1;
let tppd_valueval_nadr=tppd_valueval_nadr_nad;


end  while;--- dpo tuka 02.06.2015
	
end if;
end foreach;--3



-----isplata na provizijata  vo sluvaj samo ako e naplatena i zavisi od  nacionot na plakanje
foreach 
select os_aneks_fakturaid,f.os_polisaid ,datum,sum(iznos_p), sum(iznos_p_den) 
into tos_aneks_fakturaid,tos_polisaid ,tdat_naplata, tnaplata, tnaplata_den
 from fin_stavka f, os_polisa p, os_ponuda o
where p.os_polisaid=f.os_polisaid
and o.os_ponudaid=p.os_ponudaid
						   
and iznos_p is not null
--and o.promotor_par_agent=tpar_agentid
 and (o.par_agentid=tpar_agentid   or promotor_par_agent=tpar_agentid) 
 --and p.polisa_broj_cel='19/000517'
--and  vrati_polisa(p.os_polisaid)  in (select vrati_polisa(os_polisaid ) from provizija_promotori_bodovi)
and  datum between  add_months(tdo_datum,-3)  and tdo_datum
and f.par_tip_kniziid in (285,1128,1567,2974 )
and (f.os_aneks_fakturaid not in (select os_aneks_fakturaid from provizija_promotori_presmetka , provizija_agent 
where provizija_promotori_presmetka.provizija_agentid=provizija_agent.par_provizija_agentid
and provizija_agent.par_agentid=tpar_agentid) or (vrati_polisa(p.os_polisaid)like '19%') )
group by 1,2,3
having  sum(iznos_p_den) <>0
order by 2,3 desc

select nvl(par_status_aktiven,'A') into tpar_status_aktiven from par_agent 
where par_agentid=tpar_agentid;

if tpar_status_aktiven='Z' then 
continue foreach;
end if; 

--set debug file to 'err_presmetka_prov11.sql';
--trace on;


select os_ponudaid
into tos_ponudaid
 from os_polisa
where os_polisaid=tos_polisaid;

select os_produktid,skadenca_datum_od,period_osig, os_produkt_uplataid, nvl(par_valutaid,0),nvl(procent_provizija,0)
into tos_produktid,tskadenca_datum_od,tperiod_osig,tos_produkt_uplataid, tpar_valutaid,tprocent_provizija
 from os_ponuda
where os_ponudaid=tos_ponudaid;

if tpar_valutaid=0 then
    select par_valutaid into tpar_valutaid
    from os_produkt
    where os_produktid=tos_produktid;
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
and  datum <= tdo_datum
and iznos_p is not null
and par_tip_kniziid in (285,1128,1567,2974 );

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



let koja_god=tgodina-year(tskadenca_datum_od)+1;
select nvl(ppi_valueproc,0),par_provizijaispid
 into tproc_prov, tpar_provizijaispid
 from par_provizijaisp
where ppi_fromday=koja_god
and par_provizijatipid=tpar_provizijatipid
and ppi_onetime=tppi_onetime;

----kolku pari treba da zeme za taa polisa----
let tprva_druga_polisa='0'; 
-- Za tip na knizenje 2974 nema poseben bod-red (bodovite se na 285/1128).
-- SUM togash vrakja NULL, a formulata NULL / br_rati + 10% * naplata isto
-- stanuva NULL i presmetkata ne se vnesuva. Nula e pravilnata osnova za
-- 2974, bidejki za ovoj tip provizijata e 10% od naplatata.
select  nvl(sum(iznos_bod),0) into tiznos_bod
 from provizija_promotori_bodovi
where  vrati_polisa(os_polisaid) = vrati_polisa(tos_polisaid )
and par_agentid=tpar_agentid
and par_tip_kniziid=tpar_tip_kniziid;

select first 1  prva_druga_polisa into tprva_druga_polisa
 from provizija_promotori_bodovi
where  vrati_polisa(os_polisaid) = vrati_polisa(tos_polisaid )
and par_agentid=tpar_agentid
and par_tip_kniziid=tpar_tip_kniziid
and br_bodovi<0;

if tprva_druga_polisa='1' then 
continue foreach;
end if; 

select first 1  prva_licna_polisa into tprva_licna_polisa
 from provizija_promotori_bodovi
where  vrati_polisa(os_polisaid) = vrati_polisa(tos_polisaid )
and par_agentid=tpar_agentid
and par_tip_kniziid=tpar_tip_kniziid;


let tpersonalec=0.10;

-- Reset za sekoja faktura; ne dozvoluvaj iznos od prethodniot FOREACH red.
let tprovizija=0;


 
--if tnaplata=tiznos_d then 
 if tcela_naplata=tiznos_d or   tsifra_polisa='19' then 

if tsifra_polisa<>'19' then 
if tpar_tip_kniziid =285 then 
let tprovizija=(tiznos_bod*tproc_prov*0.01)/tbr_rati;
else
--let tprovizija=(tnaplata*20*0.01);
--let tproc_prov=20;
if koja_god<5 then 
let tprovizija=tiznos_bod/tbr_rati+0.1* tnaplata;
else 
let tprovizija=0;
end if; 
end if;
end if; 



if tsifra_polisa='19' then
if tprocent_provizija<>0 then let tproc_prov=tprocent_provizija;  else let tproc_prov=20;  end if; 
if tpar_valutaid=363 then 
execute procedure konverzija (tdo_datum,tnaplata,'MKD','EUR') into tiznt_eur;
let tprovizija=(tiznt_eur*tproc_prov*0.01);
--let tproc_prov=20;
else 
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



select count(*) into dali_postoi
from provizija_promotori_presmetka
where os_aneks_fakturaid=tos_aneks_fakturaid;
 if tprva_licna_polisa='1' then
	let tprovizija=tprovizija*2;
 end if;

select nvl(sum(naplata),0) into tnaplata_19 from provizija_promotori_presmetka
where os_aneks_fakturaid=tos_aneks_fakturaid;
if tsifra_polisa='19' then 
if tcela_naplata>=tnaplata_19   then
select count(*) into dali_postoi
from provizija_promotori_presmetka
where os_aneks_fakturaid=tos_aneks_fakturaid
and provizija_agentid=tpar_provizija_agentid;
else 
let dali_postoi=1;
end if; 
else 
let dali_postoi=0;
end if;
if tprovizija<> 0 then 
if dali_postoi=0 then
insert into provizija_promotori_presmetka(
     provizija_promotori_presmetkaid ,     datecreated ,
     usercreated ,     version ,     provizija_agentid ,
     os_aneks_fakturaid ,     par_yearid ,     iznos_provizija ,
     iznos_peronalen ,     par_statusid ,     pap_datumod ,     pap_datumdo,par_provizijaispid, dat_naplata,proc_prov , naplata ,
	 naplata_den, koja_godina,br_rati, rata, prov_rata,mesec  ) 
 values (sq_provizija_promotori_presmetka.nextval ,current ,tusername ,0 , 
tpar_provizija_agentid, tos_aneks_fakturaid,tpar_yearid ,tprovizija ,tpersonalec ,1 , tod_odatum,tdo_datum,tpar_provizijaispid,tdat_naplata,tproc_prov, 
tnaplata,tnaplata_den,koja_god,tbr_rati,trata,tprovizija/tbr_rati,tmesec);
end if;
end if;
end if;

end foreach; 
----tuka delot za nadredeniot -----
-----isplata na provizijata  vo sluvaj samo ako e naplatena i zavisi od  nacionot na plakanje




-------------------tuka delot za storno na polisi---za namaluvanje na bodovite  na agentot 

foreach 
select p.os_polisaid , o.period_osig,o.datum_prekin,vrati_premija_zivot (o.os_ponudaid,o.os_produktid) , sum(iznos_d), sum(iznos_d_den) 
into tos_polisaid ,tperiod_osig,tdatum_prekin, tpremija_zivot, tnaplata, tnaplata_den
 from fin_stavka f, os_polisa p, os_ponuda o
where p.os_polisaid=f.os_polisaid
and o.os_ponudaid=p.os_ponudaid
						   
and iznos_d is not null
and vrati_polisa(p.os_polisaid)  in (select vrati_polisa(os_polisaid )
 from provizija_promotori_bodovi
where  par_agentid=tpar_agentid)
and par_polisa_statusid=1
and f.par_tip_kniziid in (285,1128)
and  datum_prekin between tod_odatum and tdo_datum
and f.datum between tod_odatum and tdo_datum
group by 1,2,3,4
having  sum(iznos_d_den) <>0

let BB=0;
let BB_iznos=0;

select nvl(par_status_aktiven,'A') into tpar_status_aktiven from par_agent 
where par_agentid=tpar_agentid;

if tpar_status_aktiven='Z' then 
continue foreach;
end if; 

select os_ponudaid
into tos_ponudaid
 from os_polisa
where os_polisaid=tos_polisaid;

select os_produktid,skadenca_datum_od
into tos_produktid,tskadenca_datum_od
 from os_ponuda
where os_ponudaid=tos_ponudaid;



select par_year into tgodina
from par_year 
where par_yearid=tpar_yearid;



let koja_god=tgodina-year(tskadenca_datum_od)+1;

select  par_yearid into tpar_yearid_prva
from par_year 
where par_year=year(tskadenca_datum_od);

select sum(nvl(ppi_valueproc,0))
 into tproc_prov
 from par_provizijaisp
where ppi_fromday>=koja_god
and par_provizijatipid=tpar_provizijatipid;

----tuka delot za proverka dali naplatata e platena vo prvata godina --- ako e 100% storno na bodovi ----
if koja_god in (1,2) then 

select count(*)  into tkolku_prv
from os_aneks 
where vrati_polisa(os_polisaid) = vrati_polisa(tos_polisaid )
and  par_yearid = tpar_yearid_prva;

if tkolku_prv=1 then 
select os_aneksid into tos_aneksid_prv
from os_aneks 
where vrati_polisa(os_polisaid) = vrati_polisa(tos_polisaid )
and  par_yearid = tpar_yearid_prva;

select sum(iznos) -sum(naplata) into tsaldo
 from report_fakturi
where os_aneksid=tos_aneksid_prv
and f_rs='R';

if tsaldo>0 then 
let tproc_prov=100;
end if; 
end if;
end if;
----kolku pari treba da zeme za taa polisa----

select   sum(iznos_bod) , sum(br_bodovi) 
into tiznos_bod, tbr_bodovi 
 from provizija_promotori_bodovi
where  vrati_polisa(os_polisaid) = vrati_polisa(tos_polisaid )
and par_agentid=tpar_agentid;

select first 1  tip_produkcija
into ttip_produkcija
 from provizija_promotori_bodovi
where  vrati_polisa(os_polisaid) = vrati_polisa(tos_polisaid )
and par_agentid=tpar_agentid;


let BB=(-1)*(tproc_prov*tbr_bodovi)/100;
let BB_iznos=((-1)*tproc_prov*tiznos_bod/100);


insert into provizija_promotori_bodovi(     provizija_promotori_bodoviid ,          datecreated ,
          usercreated ,     version ,     mesec ,     par_yearid ,     par_agentid ,     os_polisaid ,  
		  br_bodovi ,     par_statusid,iznos_bod,tip_produkcija,datum_presmetka) 
	 values ( sq_provizija_promotori_bodovi.nextval ,current ,tusername ,0 ,
	 tmesec, tpar_yearid,tpar_agentid,tos_polisaid,BB,1,0,ttip_produkcija,tod_odatum);

 

end foreach;
----



end if;


---------------------------- tuka so alfa strukturat da se proveri kaj onie sto imaat 13.09.2017
let  dali_drugo_nivo=0;


if tmeseci_vtor_uslov>0 then 

let tpar_agentid=tpar_agentid;
select pps_bodoviod,	pps_bodovido,	par_valutaid,		pps_valueval,bod_sorabotnik,	
meseci_sorabotnik,	procent_vtor_uslov,	nvl(meseci_vtor_uslov,0)


into tppd_from,	tppd_to,	tpar_valutaid,	tppd_valueval,tbod_sorabotnik,	
tmeseci_sorabotnik,	tprocent_vtor_uslov,	tmeseci_vtor_uslov
from par_provizijadef_St
where par_provizijadefid=tpar_provizijadefid
and nvl(pps_valueden,1) ='1' 

and   ((tdo_datum between pps_datumod and pps_datumdo) or (tdo_datum >= pps_datumod and pps_datumdo is null));
 
let kolku_boda_treba_vu=tppd_to* tprocent_vtor_uslov*0.01;
/*insert into t
SELECT 
SYS_CONNECT_BY_PATH(par_agentid, ',') Path,CONNECT_BY_ISLEAF ,tpar_agentid agent
      FROM par_agent_st v
where  par_agentid in (select par_agentid from provizija_agent where par_provizijatipid=tpar_provizijatipid  and 
((today between pag_datumod and pag_datumdo) or (today >= pag_datumod and pag_datumdo is null)))
and par_nadreden_agentid in (select par_agentid from provizija_agent where par_provizijatipid=tpar_provizijatipid  and 
((today between pag_datumod and pag_datumdo) or (today >= pag_datumod and pag_datumdo is null)))
 and   ((today between pas_datumod and pas_datumdo) or (today >= pas_datumod and pas_datumdo is null))
      START WITH par_nadreden_agentid=tpar_agentid
      CONNECT BY par_nadreden_agentid = PRIOR par_agentid;*/


foreach	
select nvl(par_agentid,0)
into tpar_agentid_podnego
from par_agent_st
where par_nadreden_agentid = tpar_agentid
and   ((tdo_datum between pas_datumod and pas_datumdo) or (tdo_datum >= pas_datumod and pas_datumdo is null))

let tpath=',';

let tpath=tpath||tpar_agentid_podnego||',';
	  
while tpar_agentid_podnego <>0   

select count (* )  into dali_ima_podnego
from par_agent_st
where par_nadreden_agentid = tpar_agentid_podnego
and   ((tdo_datum between pas_datumod and pas_datumdo) or (tdo_datum >= pas_datumod and pas_datumdo is null)) ;
if dali_ima_podnego>0 then
foreach	 
 select nvl(par_agentid,0)
into tpar_agentid_podnego1
from par_agent_st
where par_nadreden_agentid = tpar_agentid_podnego
and   ((tdo_datum between pas_datumod and pas_datumdo) or (tdo_datum >= pas_datumod and pas_datumdo is null)) 


let tpath=tpath||tpar_agentid_podnego1||',';
end foreach;
let tpar_agentid_podnego=tpar_agentid_podnego1;
else
let tpar_agentid_podnego=0;
end if;
end  while;
insert into t values (tpath, 1,tpar_agentid);

end foreach;
	  
let tdatum1=tod_odatum- tmeseci_vtor_uslov units month;

	
select  nvl(sum(nvl(br_bodovi,0)),0)+nvl(sum(nvl(duplirani_bodovi,0)),0)
into  tvk_bodovi_granka_sam
from provizija_promotori_bodovi
where  par_agentid=tpar_agentid
and tip_produkcija='1' 
and MDY (mesec,1,vrati_godina(par_yearid)) between  tdatum1 and  tod_odatum;

insert into provizija_promotori_vtoruslov(     provizija_promotori_vtoruslovid ,   datecreated , usercreated ,     version ,
     mesec ,     par_yearid ,     datum_presmetka ,     par_agentid ,     path ,     tip_produkcija ,     br_bodovi ,     par_statusid) 
	 values ( sq_provizija_promotori_vtoruslov.nextval, current,tusername ,0 , tmesec, tpar_yearid,tod_odatum,
	 tpar_agentid,tpar_agentid,1,tvk_bodovi_granka_sam,1);

let tsum_bodovi_granki=0;	  
foreach select  SUBSTR(trim(path),2,LENGTH(trim(path))-2 ) into tpath
 from t where 
 connect_by_isleaf=1 
 and agent=tpar_agentid
	  
/*select  nvl(sum(nvl(br_bodovi,0)),0)+nvl(sum(nvl(duplirani_bodovi,0)),0)
into  tvk_bodovi_granka
from provizija_promotori_bodovi
where  par_agentid in (tpath)
--and tip_produkcija='2' 
and MDY (mesec,1,vrati_godina(par_yearid))  between tdatum1   and  tod_odatum;*/

PREPARE t_broj1 FROM 'select  nvl(sum(nvl(br_bodovi,0)),0)+nvl(sum(nvl(duplirani_bodovi,0)),0)  from provizija_promotori_bodovi where  par_agentid in ( '||tpath||' )  and MDY (mesec,1,vrati_godina(par_yearid))  between '''|| tdatum1 || ''' and '''||tod_odatum||'''';
declare  t_curs1  cursor  for  t_broj1; 
open  t_curs1; 
FETCH t_curs1 INTO  tvk_bodovi_granka;
  


insert into provizija_promotori_vtoruslov(     provizija_promotori_vtoruslovid ,   datecreated , usercreated ,     version ,
     mesec ,     par_yearid ,     datum_presmetka ,     par_agentid ,     path ,     tip_produkcija ,     br_bodovi ,     par_statusid) 
	 values ( sq_provizija_promotori_vtoruslov.nextval, current,tusername ,0 , tmesec, tpar_yearid,tod_odatum,
	 tpar_agentid,tpath,'2',tvk_bodovi_granka,1);
	CLOSE t_curs1;
  
   FREE t_curs1 ; 
   FREE t_broj1 ;
end foreach; 


select max(br_bodovi) into max_bodovi
from provizija_promotori_vtoruslov 
where mesec=tmesec
and par_yearid=tpar_yearid
and par_agentid=tpar_agentid;


select sum(br_bodovi) into tsum_bodovi_granki
from provizija_promotori_vtoruslov 
where mesec=tmesec
and par_yearid=tpar_yearid
and par_agentid=tpar_agentid
and br_bodovi<>max_bodovi;



if tsum_bodovi_granki>kolku_boda_treba_vu then
let dali_drugo_nivo=1;
end if;
select count(*)  into tdali_postoi from 
provizija_agent
where par_agentid=tpar_agentid
and pag_datumod=tdo_datum+1 UNITS DAY
and par_provizijadefid=tppd_nadredenid;



if tdali_postoi=0  and dali_drugo_nivo=1 then 

update provizija_agent set pag_datumdo=tdo_datum
where par_provizija_agentid=tpar_provizija_agentid;




insert into provizija_agent(par_provizija_agentid ,       datecreated ,      usercreated ,
     version ,         par_agentid ,     par_provizijadefid ,     par_provizijatipid ,
     par_provizijaispid ,     startni_poeni ,     vk_bodovi ,     par_statusid ,     pag_datumod ,f_avtomatski ) 

	 select sq_provizija_agent.nextval ,current ,tusername ,0 ,  par_agentid ,     tppd_nadredenid ,     par_provizijatipid ,
     par_provizijaispid ,     startni_poeni ,     tvk_bodovi_ag ,     par_statusid ,     tdo_datum+1 UNITS DAY,'a'
from provizija_agent
where par_provizija_agentid=tpar_provizija_agentid	 ;


end if;



end if;
--the end 13.09.2017





end foreach;

end foreach;--1

foreach 
select a.par_agentid, os_aneks_fakturaid,f.os_polisaid ,datum,datum_ponuda,sum(iznos_p), sum(iznos_p_den) 
into tpar_nadreden_agentid,tos_aneks_fakturaid,tos_polisaid ,tdat_naplata,tdatum_ponuda, tnaplata, tnaplata_den
 from fin_stavka f, os_polisa p, os_ponuda o, provizija_promotori_bodovi a 
where p.os_polisaid = f.os_polisaid 
and o.os_ponudaid=p.os_ponudaid
						   
and iznos_p is not null
and vrati_polisa(p.os_polisaid) = vrati_polisa(a.os_polisaid )
and f.par_tip_kniziid=a.par_tip_kniziid
and  a.tip_produkcija='2' 

and  datum between  add_months(tdo_datum,-3)  and tdo_datum
and f.par_tip_kniziid in (285,1128,1567 )
group by 1,2,3,4,5
having  sum(iznos_p_den) <>0
order by 3,4 desc 


if   vrati_polisa(tos_polisaid)like '25%' then 
continue foreach; 
end if;


select nvl(par_status_aktiven,'A') into tpar_status_aktiven from par_agent 
where par_agentid=tpar_nadreden_agentid;

if tpar_status_aktiven='Z' then 
continue foreach;
end if; 


--set debug file to 'err_presmetka_prov11.sql';
--trace on;
let tos_aneks_fakturaid=tos_aneks_fakturaid;
if (tpar_nadreden_agentid = 1809)or (tpar_nadreden_agentid = 1922) then 
 select      par_provizija_agentid ,     par_clientid ,          par_provizijadefid ,
     par_provizijatipid ,     par_provizijaispid ,     par_statusid ,nvl(startni_poeni,0) ,nvl(vk_bodovi,0) 
     into tpar_provizija_agentid ,    tpar_clientid ,         tpar_provizijadefid ,
     tpar_provizijatipid ,     tpar_provizijaispid ,     tpar_statusid ,tstartni_poeni,tvk_bodovi_ag
 from provizija_agent

where  ((tdatum_ponuda between pag_datumod and pag_datumdo) or (tdatum_ponuda >= pag_datumod and pag_datumdo is null))
 and par_agentid=tpar_nadreden_agentid;
else 
select      par_provizija_agentid ,     par_clientid ,          par_provizijadefid ,
     par_provizijatipid ,     par_provizijaispid ,     par_statusid ,nvl(startni_poeni,0) ,nvl(vk_bodovi,0) 
     into tpar_provizija_agentid ,    tpar_clientid ,         tpar_provizijadefid ,
     tpar_provizijatipid ,     tpar_provizijaispid ,     tpar_statusid ,tstartni_poeni,tvk_bodovi_ag
 from provizija_agent

where  ((tdo_datum between pag_datumod and pag_datumdo) or (tdo_datum >= pag_datumod and pag_datumdo is null))
 and par_agentid=tpar_nadreden_agentid;
end if;


select os_ponudaid
into tos_ponudaid
 from os_polisa
where os_polisaid=tos_polisaid;

select os_produktid,skadenca_datum_od,period_osig, os_produkt_uplataid
into tos_produktid,tskadenca_datum_od,tperiod_osig,tos_produkt_uplataid
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
and  datum <= tdo_datum
and iznos_p is not null
and par_tip_kniziid in (285,1128,1567 );

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



let koja_god=tgodina-year(tskadenca_datum_od)+1;
select nvl(ppi_valueproc,0),par_provizijaispid
 into tproc_prov, tpar_provizijaispid
 from par_provizijaisp
where ppi_fromday=koja_god
and par_provizijatipid=tpar_provizijatipid
and ppi_onetime=tppi_onetime;

----kolku pari treba da zeme za taa polisa----

-- I kaj nadredeniot NULL ne smee da se prenese vo formulata. Ako nema
-- bodovi, iznosot ostanuva 0 i nema da se kreira lazna provizija.
select  nvl(sum(iznos_bod),0) into tiznos_bod
 from provizija_promotori_bodovi
where  vrati_polisa(os_polisaid) = vrati_polisa(tos_polisaid )
and par_agentid=tpar_nadreden_agentid
and par_tip_kniziid=tpar_tip_kniziid;


let tpersonalec=0.10;
let tprovizija=0;


 
--if tnaplata=tiznos_d then 
 if tcela_naplata=tiznos_d then

if tpar_tip_kniziid =285 then 
let tprovizija=(tiznos_bod*tproc_prov*0.01)/tbr_rati;
else
if tpar_provizijadefid=286  then --- Team miloner
--let tprovizija=(tnaplata*20*0.01);
--let tproc_prov=20;
select first 1  bod_podreden,br_bodovi into tbod_podreden,tbr_bodovi_m
 from provizija_promotori_bodovi
where  vrati_polisa(os_polisaid) = vrati_polisa(tos_polisaid )
and par_agentid=tpar_nadreden_agentid
and par_tip_kniziid=tpar_tip_kniziid
and prva_licna_polisa='0'
;


select  bod,br_bodovi into tbod_licna,tbr_bodovi_licna
 from provizija_promotori_bodovi
where  vrati_polisa(os_polisaid) = vrati_polisa(tos_polisaid )
and par_agentid=tpar_nadreden_agentid
and par_tip_kniziid=tpar_tip_kniziid
and prva_licna_polisa='1';

let provizija_licna=((-1)*((tiznos_d*tbr_rati*0.1)-(tbod_licna*tbr_bodovi_licna)))/tbr_rati;

let tprovizija=((tiznos_d*tbr_rati*20*0.01)-(0.1*tiznos_d*tbr_rati+tbod_podreden*tbr_bodovi_m))/tbr_rati;
if provizija_licna is  not null then 
let tprovizija=tprovizija+provizija_licna;
end if;
else
let tprovizija=tiznos_bod/tbr_rati;
end if;
end if;


select count(*) into tkolku 
from provizija_promotori_presmetka
where os_aneks_fakturaid= tos_aneks_fakturaid
and provizija_agentid=tpar_provizija_agentid;


if  tkolku =0 then 
if tprovizija<> 0 then 
insert into provizija_promotori_presmetka(
     provizija_promotori_presmetkaid ,     datecreated ,
     usercreated ,     version ,     provizija_agentid ,
     os_aneks_fakturaid ,     par_yearid ,     iznos_provizija ,
     iznos_peronalen ,     par_statusid ,     pap_datumod ,     pap_datumdo,par_provizijaispid, dat_naplata,proc_prov , naplata ,
	 naplata_den, koja_godina,br_rati, rata, prov_rata,mesec  ) 
 values (sq_provizija_promotori_presmetka.nextval ,current ,tusername ,0 , 
tpar_provizija_agentid, tos_aneks_fakturaid,tpar_yearid ,tprovizija ,tpersonalec ,1 , tod_odatum,tdo_datum,tpar_provizijaispid,tdat_naplata,tproc_prov, 
tnaplata,tnaplata_den,koja_god,tbr_rati,trata,tprovizija/tbr_rati,tmesec);

end if;
end if; 
	   
end if;

end foreach; 
/*execute procedure presmetka_prov_promotori_zbiren(tmesec , tgodina ,tuser_id  ) into  terr,tporaka;
if terr=-1 then -----22022022
		ROLLBACK WORK;
        return -1,tporaka;
end if;*/


--execute  FUNCTION vesna.presmetka_prov_agenti_lc(tmesec  , tgodina ,tuser_id ) into terr, tporaka;
--execute  FUNCTION vesna.presmetka_prov_agenti_lc_prepresmetka(tmesec  , tgodina ,tuser_id ) into terr, tporaka;
--execute  FUNCTION vesna.presmetka_prov_agenti_lc_newprov(tmesec  , tgodina ,tuser_id ) into terr, tporaka;
--set debug file to 'err_presmetka_prov11.sql';
--trace on;

execute procedure presmetka_prov_agenti_zbiren(tmesec , ngodina ,tuser_id  ) into  terr,tporaka;
if terr=-1 then -----22022022
		--ROLLBACK WORK;
        return -1,tporaka;
end if;


--commit work;
drop table t;
return 1,'PRESMETANA E PROVIZIJA';

end function;
GO
