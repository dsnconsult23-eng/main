CREATE FUNCTION vesna.approval_zaem_fin_stavka (tos_zaemid integer,
		tuser_id integer)
		returning integer,char(100);
{
procedurata vraka:

        - kod na greska
                  1 ako se e ok i ako e izvrseno
                 -1 ako se pojavi nekoja neregularnost
        - poraka poradi koja e nastanata greskata
}

define  dali_pregled,tpar_agentid,nrows,dali_odobril,dali_polisa,tpar_polisa_promenaid,tos_polisaid,tos_aneks_fakturaid_n,tosid,dali_proknizeno_stavka int;
define tos_ponuda char(10);
define _ponuda_podbroj char(3);
define tos_produktid,tvrska_os_ponudaid,dali_abnormalen_pr int;
define tpromena_polisa,tpromena_aneks char(1);
define dali_proknizeno,dali_ima_aneks,tos_aneksid_posleden,terr,troleid int;
define tbroj_dogovor, tpar_yearid int;
define tusername char(30);
define tpar_filijalaid,tpar_tip_dokumentid,tpar_tip_kniziid,tpodnesitel_par_clientid,tpar_valutaid,tos_zaem_amort_planid,tpar_tip_kniziidk int;
define tanuitet,tanuitet_den,tkamata_den,tkamata,totplata_den,totplata decimal(20,2);
define tzaem_datum,tdatum_otplata date;


on exception
	ROLLBACK WORK;
        return -1,'NASTANATA E GRE[KA';
end exception;

set debug file to "err_approval_zaem.sql";
trace on;

set isolation to dirty read;

BEGIN WORK;

 select username into tusername from adm_user where userid=tuser_id;








	select par_agentid,par_filijalaid   into tpar_agentid,tpar_filijalaid
	from par_agent
	where userid=tuser_id;
	
	select par_yearid into tpar_yearid 
	from par_year
	where par_year=year(today);
	
	select  nvl(max(nvl(broj_dogovor,0)::int),0)+1 into tbroj_dogovor
	from os_zaem
	where dogovor_par_yearid=tpar_yearid;

	
	
		select podnesitel_par_clientid,par_valutaid, zaem_datum 
		into tpodnesitel_par_clientid,tpar_valutaid,tzaem_datum
    from os_zaem
	where os_zaemid=tos_zaemid;


	
	
select par_tip_dokumentid into tpar_tip_dokumentid from par_tip_dokument where
par_tip_dokument='ZAEM'; 

select par_tip_kniziid into tpar_tip_kniziid from par_tip_knizi where
par_tip_knizi='ZAEM';

select par_tip_kniziid into tpar_tip_kniziidk from par_tip_knizi where
par_tip_knizi='ZKAM';

foreach    select datum_otplata,		anuitet,os_zaem_amort_planid,otplata,	kamata

into tdatum_otplata,		tanuitet,tos_zaem_amort_planid,totplata,	tkamata

from os_zaem_amort_plan
	where os_zaemid=tos_zaemid

  execute procedure konverzija(tzaem_datum,totplata,'EUR','MKD') into totplata_den;
  execute procedure konverzija(tzaem_datum,tkamata,'EUR','MKD') into tkamata_den;

insert into fin_stavka (fin_stavkaid, datecreated, usercreated, version, par_filijalaid,
    par_tip_dokumentid, par_tip_kniziid, par_clientid, os_zaemid,os_zaem_amort_planid,
    par_yearid, datum, datum_knizi,datum_stavka,datum_fakt_valuta, par_valutaid,
     par_agent_id, fin_izvod_iid, 
    sifra_zatvaranje, grupa_fin_stavkaid,iznos_otvoren, f_rs,iznos_d,
    iznos_d_den,iznos_p,   iznos_p_den,  edinica, nal_vid ,
    nalog, dat_nalog, br_stavka, par_statusid)
values (sq_fin_stavka.nextval,current, tusername,0, tpar_filijalaid,
   tpar_tip_dokumentid,tpar_tip_kniziid,tpodnesitel_par_clientid,tos_zaemid,tos_zaem_amort_planid,
   tpar_yearid,tdatum_otplata,tdatum_otplata ,current,tdatum_otplata,tpar_valutaid,
   tpar_agentid,null,
   null,null,totplata_den, 'R',totplata,
   totplata_den, null, null, null, null, 
   null, null, null, 1); 

   
   insert into fin_stavka (fin_stavkaid, datecreated, usercreated, version, par_filijalaid,
    par_tip_dokumentid, par_tip_kniziid, par_clientid, os_zaemid,os_zaem_amort_planid,
    par_yearid, datum, datum_knizi,datum_stavka,datum_fakt_valuta, par_valutaid,
     par_agent_id, fin_izvod_iid, 
    sifra_zatvaranje, grupa_fin_stavkaid,iznos_otvoren, f_rs,iznos_d,
    iznos_d_den,iznos_p,   iznos_p_den,  edinica, nal_vid ,
    nalog, dat_nalog, br_stavka, par_statusid)
values (sq_fin_stavka.nextval,current, tusername,0, tpar_filijalaid,
   tpar_tip_dokumentid,tpar_tip_kniziidk,tpodnesitel_par_clientid,tos_zaemid,tos_zaem_amort_planid,
   tpar_yearid,tdatum_otplata,tdatum_otplata ,current,tdatum_otplata,tpar_valutaid,
   tpar_agentid,null,
   null,null,tkamata_den, 'R',tkamata,
   tkamata_den, null, null, null, null, 
   null, null, null, 1); 


end foreach;





commit work;
return '1',' ЗАЕМ Е  ОДОБРЕН';

end function;