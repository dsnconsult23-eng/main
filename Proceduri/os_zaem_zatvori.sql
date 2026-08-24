drop PROCEDURE appuser.os_zaem_zatvori1;
CREATE PROCEDURE appuser.os_zaem_zatvori1 (tos_zaemid int,tdatum_zatvaranje date, 	tpar_zaem_zatvaranjeid int ,tuserchanged varchar(100)) 
define lid int;
define rlid int;
define tnaplata,tnaplata_den decimal(20,2);
define tpar_filijalaid,tpar_tip_dokumentid,tpar_tip_kniziid,tpar_clientid,tos_zaemid_st int;
define tos_zaem_amort_planid,tpar_yearid,tpar_valutaid,tpar_kursid,tpar_agent_id,tpat_tip_platiid int;
define tdatum_fakt_valuta,tdatum , tdatum_knizi  date;
define tiznos_d,tiznos_d_den decimal(20,2);


--set debug file to "err_os_zaem_zatvori.sql";
--trace on;
 
  if nvl(tpar_zaem_zatvaranjeid,0)<>0 then 
  
  foreach select fs.fin_stavkaid, fs.par_filijalaid,
    fs.par_tip_dokumentid,fs.par_tip_kniziid,fs.par_clientid,fs.os_zaemid,fs.os_zaem_amort_planid,
    fs.par_yearid,fs.datum_fakt_valuta,fs.par_valutaid,
    fs.par_kursid, fs.par_agent_id,fs.pat_tip_platiid,fs.iznos_d,fs.iznos_d_den,
    vrati_naplata_zaem_fin(fs.os_zaem_amort_planid,fs.par_tip_kniziid),
    vrati_naplata_zaem_fin_den(fs.os_zaem_amort_planid,fs.par_tip_kniziid), datum , datum_knizi 
  into lid,tpar_filijalaid,tpar_tip_dokumentid,tpar_tip_kniziid,tpar_clientid,tos_zaemid_st,tos_zaem_amort_planid,
    tpar_yearid,tdatum_fakt_valuta,tpar_valutaid,
    tpar_kursid,tpar_agent_id,tpat_tip_platiid,tiznos_d,tiznos_d_den,tnaplata,tnaplata_den,tdatum , tdatum_knizi 
  from fin_stavka fs
  where fs.os_zaemid=tos_zaemid
  and fs.datum>tdatum_zatvaranje
  and fs.iznos_d is not null
  and par_tip_kniziid=2067
    and not exists (select 1
                  from fin_stavka s
                  where s.os_zaem_amort_planid=fs.os_zaem_amort_planid
                  and s.par_tip_kniziid=fs.par_tip_kniziid
                  and s.f_rs='S')


if tnaplata<>0 then 
  insert into fin_stavka (fin_stavkaid, datecreated, usercreated, version, par_filijalaid,
    par_tip_dokumentid, par_tip_kniziid, par_clientid, os_zaemid,os_zaem_amort_planid,
    par_yearid, datum, datum_knizi,datum_stavka,datum_fakt_valuta, par_valutaid,
    par_kursid, par_agent_id, pat_tip_platiid,
    iznos_otvoren, f_rs,iznos_d, iznos_d_den,
    par_statusid)
  values (sq_fin_stavka.nextval,current, tuserchanged,0, tpar_filijalaid,
    tpar_tip_dokumentid,tpar_tip_kniziid,tpar_clientid,tos_zaemid_st,tos_zaem_amort_planid,
    tpar_yearid,tdatum , tdatum_knizi ,current,tdatum_fakt_valuta,tpar_valutaid,
    tpar_kursid, tpar_agent_id,tpat_tip_platiid,
    0,'S',
    (-1)*(tiznos_d),
    (-1)*(tiznos_d_den),
    1);

    else 

  update fin_stavka set f_rs='N' , userchanged=tuserchanged, datechanged=current 
  where fin_stavkaid=lid;
    end if;
  end foreach;
  end if; 
  
  
end procedure;
