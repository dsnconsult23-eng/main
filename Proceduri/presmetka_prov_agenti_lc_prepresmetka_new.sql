DROP FUNCTION IF EXISTS vesna.presmetka_prov_agenti_lc_prepresmetka_new(CHAR(2), CHAR(4), INT);
GO

CREATE FUNCTION vesna.presmetka_prov_agenti_lc_prepresmetka_new (tmesec char(2) , tgodina char(4) ,tuser_id int )
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
define tskadenca_datum_od,tod_odatum, tdo_datum,tdatum_prekin,tdatum_presmetka date;
define dali_presmetana,netreba,tposrednik_par_client,dali_posrednik,tos_produkt_uplataid,tpar_nacin_platiid, tppi_onetime,tprovizija_agent_zbirenid int;
define tstartni_poeni,BB_iznos,tppd_valueval,tstartni_poeni_nadreden,tppd_valueval_nadr,BB_iznos_nadr,tiznos_bod,tkumul_bodovi,tvk_bodovi_ag,bb,tkumul_bodovi_preth dec;
define tpar_posrednik,dali_presm,tos_aneksid_prv,tpar_yearid_prva,tind_grupno,tbr_osig_lica,tbr_osig_lica_ponuda int;
define tppd_from,	tppd_to,	tppd_tipprodukcija,	tppd_valueden,	tpar_valutaid,tpar_nadreden_agentid, tpar_provizijadefid_nadreden   ,tppd_nadredenid ,mesec_pteh ,tpar_provizija_agentid_max  	 int;
define tpar_nacin_plati char(3);
define  tcela_naplata	,tcela_naplata_den,tsaldo,tbr_bodovi dec;
define tpar_nadreden_agentid_nad,tpar_provizijadefid_nadreden_nad,tpar_nadreden_agentid_nad1,tdali_postoi,tkolku_prv,dali_postoi,dali_ima,terr int;
define tstartni_poeni_nadreden_nad,tppd_valueval_nadr_nad,BB_iznos_nadr_nad,tiznt_eur,tnaplata_19 dec;
define ttip_provizija varchar(1);
define tsifra_polisa varchar(2);
define tporaka varchar(255);
define  tpar_status_aktiven varchar(1);
define terror_isam int;
define tstep varchar(30);
-- Dijagnosticki brojaci: se vrakaat vo porakata na kraj od funkcijata.
define tcnt_kandidati,tcnt_vneseni,tcnt_neplateni,tcnt_neaktiven,tcnt_bez_proc,tcnt_bez_cfg,tcnt_duplikat,tcnt_nulta int;
on exception set terr, terror_isam
	--ROLLBACK WORK;
        return -1,'ERR='||terr||' ISAM='||terror_isam||' STEP='||tstep||' FAK='||nvl(tos_aneks_fakturaid,0);
end exception;

--set debug file to 'err_presmetka_prov_agenti_lcaa.sql';
--trace on;

set isolation to dirty read;  

--BEGIN WORK;
let tod_odatum='01.'||tmesec||'.'||tgodina;
 let tdo_datum=LAST_DAY(tod_odatum);

-- Reset na dijagnostikata za ova izvrsuvanje.
let tcnt_kandidati=0;
let tcnt_vneseni=0;
let tcnt_neplateni=0;
let tcnt_neaktiven=0;
let tcnt_bez_proc=0;
let tcnt_bez_cfg=0;
let tcnt_duplikat=0;
let tcnt_nulta=0;
let tstep='INIT';

select par_yearid into tpar_yearid
from par_year 
where par_year = tgodina;
select count(*) into dali_presmetana
from lc_provizija_agent_zbiren
where  mesec = tmesec
and    par_yearid = tpar_yearid;



select username into tusername from adm_user
where userid=tuser_id;






-----isplata na provizijata  vo sluvaj samo ako e naplatena i zavisi od  nacionot na plakanje
foreach 
select os_aneks_fakturaid,f.os_polisaid ,datum,sum(iznos_p), sum(iznos_p_den) ,c.par_agentid,c.datum_presmetka
into tos_aneks_fakturaid,tos_polisaid ,tdat_naplata, tnaplata, tnaplata_den,tpar_agentid,tdatum_presmetka
 from fin_stavka f, os_polisa p, os_ponuda o ,lc_provizija_agent_bodovi  c
where p.os_polisaid=f.os_polisaid
and o.os_ponudaid=p.os_ponudaid
and c.os_polisaid=p.os_polisaid 
and iznos_p is not null
and nvl(c.par_provizijatipid,0) <>2738
-- Opsta prepresmetka bez fiksna polisa/faktura. Gi opfaka site istorijski
-- fakturi so stari bodovi za koi nema zapis za konkretniot agent.
-- Ne se zemaat naplati po krajot na baraniot mesec.
and datum  between '1.5.2026' and tdo_datum
and f.os_aneks_fakturaid not in (select os_aneks_fakturaid from lc_provizija_agent_presmetka , provizija_agent 
where lc_provizija_agent_presmetka.provizija_agentid=provizija_agent.par_provizija_agentid
and provizija_agent.par_agentid=c.par_agentid)
--and c.tip_produkcija=1
and f.par_tip_kniziid in (285,1128,1567,2974 )
group by 1,2,3,6,7
having  sum(iznos_p_den) <>0
order by 2,3 desc 

-- Redot gi pominal pocetnite filtri: faktura, period, stari bodovi i tip knizenje.
let tcnt_kandidati=tcnt_kandidati+1;
let tstep='KANDIDAT';
-- Mora da se resetira za sekoj red; vo sprotivno moze da ostane iznos od prethodna faktura.
let tprovizija=0;

select nvl(par_status_aktiven,'A') into tpar_status_aktiven from par_agent 
where par_agentid=tpar_agentid;

-- Zatvoren agent ne dobiva ponatamosna provizija.
if tpar_status_aktiven='Z' then 
let tcnt_neaktiven=tcnt_neaktiven+1;
continue foreach;
end if; 


-- Bez istoriska konfiguracija nema bezbeden nacin da se odredi tip/procent.
select count(*) into tdali_postoi
from provizija_agent
where par_agentid=tpar_agentid
and ((tdatum_presmetka between pag_datumod and pag_datumdo)
     or (tdatum_presmetka>=pag_datumod and pag_datumdo is null));

if tdali_postoi=0 then
let tcnt_bez_cfg=tcnt_bez_cfg+1;
continue foreach;
end if;

select first 1 par_provizija_agentid,par_provizijatipid
into tpar_provizija_agentid,tpar_provizijatipid
 from provizija_agent
where par_agentid=tpar_agentid and   ((tdatum_presmetka between pag_datumod and pag_datumdo) or (tdatum_presmetka >= pag_datumod and pag_datumdo is null));


select tip_provizija into ttip_provizija
from  par_provizijatip
where par_provizijatipid=tpar_provizijatipid;

select os_ponudaid
into tos_ponudaid
 from os_polisa
where os_polisaid=tos_polisaid;

select os_produktid,skadenca_datum_od,period_osig, os_produkt_uplataid, nvl(par_valutaid,0)
into tos_produktid,tskadenca_datum_od,tperiod_osig,tos_produkt_uplataid, tpar_valutaid
 from os_ponuda
where os_ponudaid=tos_ponudaid;


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
  

--execute  function vrati_osig_suma_zivot(tos_ponudaid,tos_produktid) into tosig_suma;
--execute  function vrati_premija_zivot(tos_ponudaid,tos_produktid) into tpremija_zivot;
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
if ttip_provizija='N' then
select nvl(ppi_valueproc,0),par_provizijaispid
 into tproc_prov, tpar_provizijaispid
 from par_provizijaisp
where   tperiod_osig between  ppi_fromday and ppi_today 
 and par_provizijatipid=tpar_provizijatipid
and ppi_onetime=koja_god;
else 
select nvl(ppi_valueproc,0),par_provizijaispid
 into tproc_prov, tpar_provizijaispid
 from par_provizijaisp
where ppi_fromday=koja_god
and par_provizijatipid=tpar_provizijatipid
and ppi_onetime=tppi_onetime;
end if; 
----kolku pari treba da zeme za taa polisa----


if tproc_prov is null then let tproc_prov=0; end if; 
if tproc_prov=0 then
    -- Nema konfiguriran procent vo par_provizijaisp za godina/tip na plakanje.
    let tcnt_bez_proc=tcnt_bez_proc+1;
    continue foreach;
 end if;

select  sum(iznos_bod) into tiznos_bod
 from lc_provizija_agent_bodovi
where  os_polisaid=tos_polisaid
and par_agentid=tpar_agentid;

let tpersonalec=0.10;

 
-- Naplatata se sobira samo do krajot na baraniot mesec (tdo_datum), dodeka
-- dolgot e celiot iznos na fakturata. Faktura doplatena vo avgust e NP za juli.
if nvl(tcela_naplata,0)<>nvl(tiznos_d,0) then
let tcnt_neplateni=tcnt_neplateni+1;
else
--if tpar_provizijatipid=56 then
if ttip_provizija='A'  then 
if tpar_tip_kniziid =285 then 
let tprovizija=(tiznos_bod*tproc_prov*0.01)/tbr_rati;
else
let tprovizija=(tcela_naplata*20*0.01);
--let tprovizija=(tnaplata*20*0.01);--smeneto na  04.12.2018
let tproc_prov=20;
end if;
end if;

if ttip_provizija='N' then
if tpar_valutaid=363 then 
execute procedure konverzija (tdo_datum,tnaplata,'MKD','EUR') into tiznt_eur;
let tprovizija=(tiznt_eur*tproc_prov*0.01);
else 
let tprovizija=(tnaplata*tproc_prov*0.01);
end if;
end if;



select count(*) into dali_postoi
from lc_provizija_agent_presmetka
where os_aneks_fakturaid=tos_aneks_fakturaid
and provizija_agentid=tpar_provizija_agentid;


select sum(naplata) into tnaplata_19 from lc_provizija_agent_presmetka
where os_aneks_fakturaid=tos_aneks_fakturaid;
if tsifra_polisa='19' then 
if tcela_naplata=tnaplata_19   then
select count(*) into dali_postoi
from lc_provizija_agent_presmetka
where os_aneks_fakturaid=tos_aneks_fakturaid
and provizija_agentid=tpar_provizija_agentid;
else 
let dali_postoi=0;
end if; 
end if;
if tproc_prov is null then let tproc_prov=0; end if; 
if tprovizija<> 0 and tproc_prov<>0  then 
if dali_postoi=0 then
let tstep='INSERT_PRESMETKA';
insert into lc_provizija_agent_presmetka(
     lc_provizija_agent_presmetkaid ,     datecreated ,
     usercreated ,     version ,     provizija_agentid ,
     os_aneks_fakturaid ,     par_yearid ,     iznos_provizija ,
     iznos_peronalen ,     par_statusid ,     pap_datumod ,     pap_datumdo,par_provizijaispid, dat_naplata,proc_prov , naplata ,
	 naplata_den, koja_godina,br_rati, rata, prov_rata,mesec , tip_Prov ) 
 values (sq_lc_provizija_agent_presmetka.nextval ,current ,tusername ,0 , 
tpar_provizija_agentid, tos_aneks_fakturaid,tpar_yearid ,tprovizija ,tpersonalec ,1 , tod_odatum,tdo_datum,tpar_provizijaispid,tdat_naplata,tproc_prov, 
tnaplata,tnaplata_den,koja_god,tbr_rati,trata,tprovizija/tbr_rati,tmesec , 'PR3');
let tcnt_vneseni=tcnt_vneseni+1;
let tstep='INSERT_OK';
else
-- Za istata faktura i istoriska provizija_agent konfiguracija veke postoi zapis.
let tcnt_duplikat=tcnt_duplikat+1;
end if;
else
-- Gi pominal drugite proverki, no presmetaniot iznos ostanal nula.
let tcnt_nulta=tcnt_nulta+1;
end if;
end if;

end foreach; 






--commit work;
-- K=kandidati, I=vneseni, NP=neplateni, NA=neaktiven, BP=bez procent,
-- BC=bez istoriska konfiguracija, D=duplikati, N0=nulta provizija.
let tporaka='K='||tcnt_kandidati||' I='||tcnt_vneseni||' NP='||tcnt_neplateni||
             ' NA='||tcnt_neaktiven||' BP='||tcnt_bez_proc||' BC='||tcnt_bez_cfg||
             ' D='||tcnt_duplikat||' N0='||tcnt_nulta;
return 1,tporaka;

end function;
GO
