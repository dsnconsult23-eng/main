drop PROCEDURE vesna.zatvori_izvod;
CREATE PROCEDURE vesna.zatvori_izvod(tfin_izvod_iid  int8, 
			tuser_id int);
--returning integer,char(100);



define tpar_vid_izvodid,tpar_filijalaid,  trbr ,     tpat_tip_dokumentid ,     tpar_clientid ,     _br_stavka,tpar_tip_kniziid int;
define    tsifra_zatvaranje ,     ttr_desc,     tpar_statusid ,     tpar_valutaid,tos_aneks_fakturaid,tpar_tip_dokumentid,trata,tos_ponuda_detailid,tkolku int;  
define tiznos_naplata ,     tiznos_naplata_den ,     tiznos_isplata ,     tiznos_isplata_den,tiznos,	tiznos_denari,tsaldo , tsaldo_den,tsaldo_vk, tsaldo_vk_den,tprop_napl,tprop_napl_den dec;
define tdata_faktura,		tdata_valuta,tdatum,tt date;
define sid,tpar_client,tfin_stavkaid,tfin_izvod_hid,tos_zaem_amort_planid, tl_steta_likvidacija_korisniciid,tpar_tip_kniziidlikv int;
define tl_steta_likvidacijaid,	tl_stetaid,	tl_steta_korisniciid int;
define tusername char(30);
define tpar_tip_dokument varchar(5);
define tvaluta varchar(3);
define tos_aneksid,tos_zbiren_aneksid int8;
define tpar_tip_stetaid,tos_ponudaid int8;
define tpar_tip_steta varchar(6); 
define tdesc varchar(255);
define _dolzina,m,i,haha int;
define  tsfin_stavkaid varchar(20);
{
on exception
ROLLBACK WORK;
return -1,'GRE[KA';
end exception;}
--set debug file to 'err_zatvori_izvod_test.sql';
--trace on;

--BEGIN WORK;

set isolation to dirty read;


select username into tusername from adm_user
where userid=tuser_id;



----------------------------------------------
  select    fin_izvod_iid ,   rbr ,     pat_tip_dokumentid ,
     par_clientid ,     os_aneksid ,     sifra_zatvaranje ,
     tr_desc ,     iznos_naplata ,     iznos_naplata_den ,
     iznos_isplata ,     iznos_isplata_den ,        
     par_statusid ,     par_valutaid, fin_izvod_hid,par_tip_kniziid,nvl(os_zbiren_aneksid,0),nvl(os_zaem_amort_planid,0),	
	 nvl(l_steta_likvidacija_korisniciid,0), desc
	

     
     into tfin_izvod_iid ,  trbr ,     tpat_tip_dokumentid ,
     tpar_clientid ,     tos_aneksid ,     tsifra_zatvaranje ,
     ttr_desc ,    tiznos_naplata ,     tiznos_naplata_den ,
     tiznos_isplata ,     tiznos_isplata_den ,        
     tpar_statusid ,     tpar_valutaid,tfin_izvod_hid,tpar_tip_kniziid,tos_zbiren_aneksid,tos_zaem_amort_planid, tl_steta_likvidacija_korisniciid, tdesc
from fin_izvod_i
where fin_izvod_iid=tfin_izvod_iid
--and sifra_zatvaranje is    null
and edinica is null
and nal_vid is null
and dat_nalog is null
and nalog is null;
select par_tip_dokument into tpar_tip_dokument
  from par_tip_dokument
where par_tip_dokumentid=tpat_tip_dokumentid;

if tdesc='UU' then
 return;
end if;


select datum  into tdatum
from fin_izvod_h
where fin_izvod_hid=tfin_izvod_hid;

if tpar_tip_dokument='PREM' then

if tos_zbiren_aneksid =0    then
if tpar_tip_kniziid is null then

select  count(*) into tkolku 
 from os_aneks_faktura f,os_aneks o
where  f.os_aneksid=o.os_aneksid
and os_aneks_rataid=tos_aneksid
and f_rs<>'N';
--nd f.os_aneksid||o.par_yearid||f.rata=tos_aneksid;

select datum  into tdatum
from fin_izvod_h
where fin_izvod_hid=tfin_izvod_hid;

--if year(tdatum )>2012 then

 select sum(	iznos-vrati_naplata(os_aneks_fakturaid )),	sum(iznos_denari-vrati_naplata_den(os_aneks_fakturaid ))
into tsaldo_vk, tsaldo_vk_den

 from os_aneks_faktura f,os_aneks o
where  f.os_aneksid=o.os_aneksid
and os_aneks_rataid=tos_aneksid 
and f_rs<>'N';
--and f.os_aneksid||o.par_yearid||f.rata=tos_aneksid;
--(select  os_aneksid1||rata 
--from izvod_aneks 
--where os_aneksid= tos_aneksid);


foreach   select os_aneks_fakturaid,par_tip_dokumentid,	rata,	os_ponuda_detailid,	data_faktura,	data_valuta,iznos, iznos_denari, 	iznos-vrati_naplata(os_aneks_fakturaid ),	iznos_denari-vrati_naplata_den(os_aneks_fakturaid )
into tos_aneks_fakturaid,tpar_tip_dokumentid,	trata,
	tos_ponuda_detailid,	tdata_faktura,
		tdata_valuta,	tiznos,	tiznos_denari, tsaldo , tsaldo_den

 from os_aneks_faktura f,os_aneks o
where  f.os_aneksid=o.os_aneksid
and os_aneks_rataid=tos_aneksid
and f_rs<>'N'
--and f.os_aneksid||o.par_yearid||f.rata=tos_aneksid

if tsaldo_vk <>0 then

let tprop_napl=round(tsaldo/tsaldo_vk*tiznos_naplata,2);
select valuta into tvaluta from par_valuta
where par_valutaid=tpar_valutaid;
if tsaldo_vk_den <>0 then
let tprop_napl_den =round(tsaldo_den/tsaldo_vk_den*tiznos_naplata_den);
else 
execute procedure konverzija(tdatum,tprop_napl,  tvaluta,'MKD') into tprop_napl_den;	
end if;
else
continue foreach;
end if;
if tprop_napl>tsaldo then
let tprop_napl=tsaldo;
end if;



if tprop_napl_den>tsaldo_den then
let tprop_napl_den=tsaldo_den;
end if;
{
select valuta into tvaluta from par_valuta
where par_valutaid=tpar_valutaid;

	
execute procedure konverzija(tdatum,tiznos,  tvaluta,'MKD') into tiznos_den;	
}
update izvod_broevi set broj=broj+1;
select broj into tsifra_zatvaranje from izvod_broevi;


select fin_stavkaid into tfin_stavkaid
from fin_stavka where os_aneks_fakturaid=tos_aneks_fakturaid
and iznos_d is not null;

if tprop_napl<> 0 then

let sid=sq_fin_stavka.nextval;	

insert into fin_stavka (fin_stavkaid, datecreated, usercreated, version, par_filijalaid,
    par_tip_dokumentid, par_tip_kniziid, par_clientid, os_aneks_fakturaid,
    par_yearid, datum, datum_stavka,datum_fakt_valuta, par_valutaid,
    par_kursid, os_polisaid,par_agent_id, fin_izvod_iid, pat_tip_platiid,
    sifra_zatvaranje, grupa_fin_stavkaid, f_rs,
    iznos_p,   iznos_p_den,  par_statusid)
  select sid,current, tusername,0, par_filijalaid,
   par_tip_dokumentid, par_tip_kniziid, par_clientid, os_aneks_fakturaid,
   par_yearid,tdatum, tdatum,tdatum,par_valutaid,
   par_kursid,os_polisaid, par_agent_id,tfin_izvod_iid,pat_tip_platiid,
   tsifra_zatvaranje ,tfin_stavkaid, 'R',tprop_napl,
   tprop_napl_den, 1
   from fin_stavka 
   where fin_stavkaid=tfin_stavkaid;
   
   select par_clientid into tpar_client  from fin_stavka
    where fin_stavkaid=tfin_stavkaid;
   update fin_stavka set iznos_otvoren=nvl(iznos_otvoren,0)-tiznos_denari
   where fin_stavkaid=tfin_stavkaid;

	insert into log_zatvaranje(     log_zatvaranjeid ,     
     datecreated ,  usercreated ,     version ,     sifra_zatvaranje ,     vid_zat ,
     sifra_trans_0 ,     sifra_trans_z ,     fin_izvod_iid ,
     par_client ,     iznos_isplata ,     iznos_isplata_den ,
     iznos_naplata ,     iznos_naplata_den ,     par_statusid)
      values (log_zatvaranjeid.nextval, current, tusername,0,tsifra_zatvaranje ,'00' 
      ,tfin_stavkaid ,sid ,tfin_izvod_iid ,tpar_client ,0 ,0 ,tprop_napl ,tprop_napl_den ,1);
end if; 
end foreach;

else
select  count(*) into tkolku 
{from os_aneks_faktura
where  os_aneksid||rata in 
(select  os_aneksid1||rata 
from izvod_aneks 
where os_aneksid= tos_aneksid)}
 from os_aneks_faktura f,os_aneks o
where  f.os_aneksid=o.os_aneksid
and os_aneks_rataid=tos_aneksid
--and f.os_aneksid||o.par_yearid||f.rata=tos_aneksid
and par_tip_kniziid=tpar_tip_kniziid
and f_rs<>'N';


select datum  into tdatum
from fin_izvod_h
where fin_izvod_hid=tfin_izvod_hid;

--if year(tdatum )>2012 then

 select sum(	iznos-vrati_naplata(os_aneks_fakturaid )),	sum(iznos_denari-vrati_naplata_den(os_aneks_fakturaid ))
into tsaldo_vk, tsaldo_vk_den

{ from os_aneks_faktura
where  os_aneksid||rata in 
(select  os_aneksid1||rata 
from izvod_aneks 
where os_aneksid= tos_aneksid)}
 from os_aneks_faktura f,os_aneks o
where  f.os_aneksid=o.os_aneksid
and os_aneks_rataid=tos_aneksid
--and f.os_aneksid||o.par_yearid||f.rata=tos_aneksid
and par_tip_kniziid=tpar_tip_kniziid
and f_rs<>'N';


foreach   select os_aneks_fakturaid,par_tip_dokumentid,	rata,	os_ponuda_detailid,	data_faktura,	data_valuta,iznos, iznos_denari, 	iznos-vrati_naplata(os_aneks_fakturaid ),	iznos_denari-vrati_naplata_den(os_aneks_fakturaid )
into tos_aneks_fakturaid,tpar_tip_dokumentid,	trata,
	tos_ponuda_detailid,	tdata_faktura,
		tdata_valuta,	tiznos,	tiznos_denari, tsaldo , tsaldo_den

{ from os_aneks_faktura
where  os_aneksid||rata in 
(select  os_aneksid1||rata 
from izvod_aneks 
where os_aneksid= tos_aneksid)}
 from os_aneks_faktura f,os_aneks o
where  f.os_aneksid=o.os_aneksid
and os_aneks_rataid=tos_aneksid
--and f.os_aneksid||o.par_yearid||f.rata=tos_aneksid
and par_tip_kniziid=tpar_tip_kniziid
and f_rs<>'N'



if tsaldo_vk <>0 then

let tprop_napl=round(tsaldo/tsaldo_vk*tiznos_naplata,2);
let tprop_napl_den =round(tsaldo_den/tsaldo_vk_den*tiznos_naplata_den);
else
continue foreach;
end if;
if tprop_napl>tsaldo then
let tprop_napl=tsaldo;
end if;



if tprop_napl_den>tsaldo_den then
let tprop_napl_den=tsaldo_den;
end if;
{
select valuta into tvaluta from par_valuta
where par_valutaid=tpar_valutaid;

	
execute procedure konverzija(tdatum,tiznos,  tvaluta,'MKD') into tiznos_den;	
}
update izvod_broevi set broj=broj+1;
select broj into tsifra_zatvaranje from izvod_broevi;


select fin_stavkaid into tfin_stavkaid
from fin_stavka where os_aneks_fakturaid=tos_aneks_fakturaid
and iznos_d is not null;

if tprop_napl<> 0 then

let sid=sq_fin_stavka.nextval;	

insert into fin_stavka (fin_stavkaid, datecreated, usercreated, version, par_filijalaid,
    par_tip_dokumentid, par_tip_kniziid, par_clientid, os_aneks_fakturaid,
    par_yearid, datum, datum_stavka,datum_fakt_valuta, par_valutaid,
    par_kursid, os_polisaid,par_agent_id, fin_izvod_iid, pat_tip_platiid,
    sifra_zatvaranje, grupa_fin_stavkaid, f_rs,
    iznos_p,   iznos_p_den,  par_statusid)
  select sid,current, tusername,0, par_filijalaid,
   par_tip_dokumentid, par_tip_kniziid, par_clientid, os_aneks_fakturaid,
   par_yearid,tdatum, tdatum,tdatum,par_valutaid,
   par_kursid,os_polisaid, par_agent_id,tfin_izvod_iid,pat_tip_platiid,
   tsifra_zatvaranje ,tfin_stavkaid, 'R',tprop_napl,
   tprop_napl_den, 1
   from fin_stavka 
   where fin_stavkaid=tfin_stavkaid;
   
   select par_clientid into tpar_client  from fin_stavka
    where fin_stavkaid=tfin_stavkaid;
   update fin_stavka set iznos_otvoren=nvl(iznos_otvoren,0)-tiznos_denari
   where fin_stavkaid=tfin_stavkaid;

	insert into log_zatvaranje(     log_zatvaranjeid ,     
     datecreated ,  usercreated ,     version ,     sifra_zatvaranje ,     vid_zat ,
     sifra_trans_0 ,     sifra_trans_z ,     fin_izvod_iid ,
     par_client ,     iznos_isplata ,     iznos_isplata_den ,
     iznos_naplata ,     iznos_naplata_den ,     par_statusid)
      values (log_zatvaranjeid.nextval, current, tusername,0,tsifra_zatvaranje ,'00' 
      ,tfin_stavkaid ,sid ,tfin_izvod_iid ,tpar_client ,0 ,0 ,tprop_napl ,tprop_napl_den ,1);
end if; 
end foreach;
end if;
else---ako zbiren aneks

select  count(*) into tkolku 

 from os_aneks_faktura , os_aneks 
where  os_aneks.os_aneksid=os_aneks_faktura.os_aneksid
and os_zbiren_aneksid||par_yearid||rata=tos_zbiren_aneksid
and f_rs<>'N' ;


select datum  into tdatum
from fin_izvod_h
where fin_izvod_hid=tfin_izvod_hid;

--if year(tdatum )>2012 then

 select sum(	iznos-vrati_naplata(os_aneks_fakturaid )),	sum(iznos_denari-vrati_naplata_den(os_aneks_fakturaid ))
into tsaldo_vk, tsaldo_vk_den

 from os_aneks_faktura , os_aneks  , os_zbiren_aneks  b
where  os_aneks.os_aneksid=os_aneks_faktura.os_aneksid
and b.os_zbiren_aneksid=os_aneks.os_zbiren_aneksid
and b.os_zbiren_aneksid||b.par_yearid||rata=tos_zbiren_aneksid
and f_rs<>'N' ;

---da se vidi dali ima vneseno polisi li ne 
BEGIN
ON EXCEPTION IN (-206)
create temp   table tmp_knizi_polisa(
polisa_broj varchar(20),
oznaka char(1))		;
--create unique index uix_tmp_knizi on tmp_knizi_polisa(polisa_broj);	
END EXCEPTION
DELETE FROM tmp_knizi_polisa;
END

let _dolzina= LENGTH (trim(tdesc));
let i=1;
while i<=_dolzina
let tsfin_stavkaid=null;
execute  function locate(tdesc,';') into  m;
if m=0 then
let tsfin_stavkaid=SUBSTRING(tdesc FROM 1 FOR _dolzina);

else 
let tsfin_stavkaid=SUBSTRING(tdesc FROM 1 FOR m-1);
end if;

--select tsfin_stavkaid into tfin_stavkaid from sysdual;
insert into tmp_knizi_polisa values (tsfin_stavkaid,'1');
let tdesc=SUBSTRING(tdesc FROM m+1 FOR _dolzina);
if m=0 then 

let i=_dolzina+1;
else
let i=i+m-1;
end if;
end while;

select count(*) into haha from tmp_knizi_polisa;
if haha>0 then 


 select sum(	iznos-vrati_naplata(os_aneks_fakturaid )),	sum(iznos_denari-vrati_naplata_den(os_aneks_fakturaid ))
into tsaldo_vk, tsaldo_vk_den

 from os_aneks_faktura , os_aneks ,os_polisa p , tmp_knizi_polisa t, os_zbiren_aneks  b
where  os_aneks.os_aneksid=os_aneks_faktura.os_aneksid
and os_aneks.os_polisaid=p.os_polisaid
and p.polisa_broj_cel=t.polisa_broj 
and b.os_zbiren_aneksid=os_aneks.os_zbiren_aneksid
and b.os_zbiren_aneksid||b.par_yearid||rata=tos_zbiren_aneksid
--and vrati_polisa(os_polisaid)=t.polisa_broj
and f_rs<>'N' ;



foreach   select os_aneks_fakturaid,par_tip_dokumentid,	rata,	os_ponuda_detailid,	data_faktura,	data_valuta,iznos, iznos_denari, 	iznos-vrati_naplata(os_aneks_fakturaid ),	iznos_denari-vrati_naplata_den(os_aneks_fakturaid )
into tos_aneks_fakturaid,tpar_tip_dokumentid,	trata,
	tos_ponuda_detailid,	tdata_faktura,
		tdata_valuta,	tiznos,	tiznos_denari, tsaldo , tsaldo_den
 from os_aneks_faktura , os_aneks ,os_polisa p , tmp_knizi_polisa t , os_zbiren_aneks  b
where  os_aneks.os_aneksid=os_aneks_faktura.os_aneksid
and os_aneks.os_polisaid=p.os_polisaid
and p.polisa_broj_cel=t.polisa_broj 
and b.os_zbiren_aneksid=os_aneks.os_zbiren_aneksid
--and vrati_polisa(os_polisaid)=t.polisa_broj
and b.os_zbiren_aneksid||b.par_yearid||rata=tos_zbiren_aneksid
and f_rs<>'N' 

--set debug file to 'err_zatvori_izvod_test.sql';
--trace on;

if tsaldo_vk <>0 then

let tprop_napl=round(tsaldo/tsaldo_vk*tiznos_naplata,2);

select valuta into tvaluta from par_valuta
where par_valutaid=tpar_valutaid;

if tsaldo_vk_den <>0 then
let tprop_napl_den =round(tsaldo_den/tsaldo_vk_den*tiznos_naplata_den);
else 
execute procedure konverzija(tdatum,tprop_napl,  tvaluta,'MKD') into tprop_napl_den;	
end if;
--let tprop_napl_den =round(tsaldo_den/tsaldo_vk_den*tiznos_naplata_den);
else
continue foreach;
end if;
if tprop_napl>tsaldo then
let tprop_napl=tsaldo;
end if;



if tprop_napl_den>tsaldo_den then
let tprop_napl_den=tsaldo_den;
end if;
{
select valuta into tvaluta from par_valuta
where par_valutaid=tpar_valutaid;

	
execute procedure konverzija(tdatum,tiznos,  tvaluta,'MKD') into tiznos_den;	
}
update izvod_broevi set broj=broj+1;
select broj into tsifra_zatvaranje from izvod_broevi;


select fin_stavkaid into tfin_stavkaid
from fin_stavka where os_aneks_fakturaid=tos_aneks_fakturaid
and iznos_d is not null;

if tprop_napl<> 0 then

let sid=sq_fin_stavka.nextval;	

insert into fin_stavka (fin_stavkaid, datecreated, usercreated, version, par_filijalaid,
    par_tip_dokumentid, par_tip_kniziid, par_clientid, os_aneks_fakturaid,
    par_yearid, datum, datum_stavka,datum_fakt_valuta, par_valutaid,
    par_kursid, os_polisaid,par_agent_id, fin_izvod_iid, pat_tip_platiid,
    sifra_zatvaranje, grupa_fin_stavkaid, f_rs,
    iznos_p,   iznos_p_den,  par_statusid)
  select sid,current, tusername,0, par_filijalaid,
   par_tip_dokumentid, par_tip_kniziid, par_clientid, os_aneks_fakturaid,
   par_yearid,tdatum, tdatum,tdatum,par_valutaid,
   par_kursid,os_polisaid, par_agent_id,tfin_izvod_iid,pat_tip_platiid,
   tsifra_zatvaranje ,tfin_stavkaid, 'R',tprop_napl,
   tprop_napl_den, 1
   from fin_stavka 
   where fin_stavkaid=tfin_stavkaid;
   
   select par_clientid into tpar_client  from fin_stavka
    where fin_stavkaid=tfin_stavkaid;
   update fin_stavka set iznos_otvoren=nvl(iznos_otvoren,0)-tiznos_denari
   where fin_stavkaid=tfin_stavkaid;

	insert into log_zatvaranje(     log_zatvaranjeid ,     
     datecreated ,  usercreated ,     version ,     sifra_zatvaranje ,     vid_zat ,
     sifra_trans_0 ,     sifra_trans_z ,     fin_izvod_iid ,
     par_client ,     iznos_isplata ,     iznos_isplata_den ,
     iznos_naplata ,     iznos_naplata_den ,     par_statusid)
      values (log_zatvaranjeid.nextval, current, tusername,0,tsifra_zatvaranje ,'00' 
      ,tfin_stavkaid ,sid ,tfin_izvod_iid ,tpar_client ,0 ,0 ,tprop_napl ,tprop_napl_den ,1);
end if; 
end foreach;
else 
------end polisi 
foreach   select os_aneks_fakturaid,par_tip_dokumentid,	rata,	os_ponuda_detailid,	data_faktura,	data_valuta,iznos, iznos_denari, 	iznos-vrati_naplata(os_aneks_fakturaid ),	iznos_denari-vrati_naplata_den(os_aneks_fakturaid )
into tos_aneks_fakturaid,tpar_tip_dokumentid,	trata,
	tos_ponuda_detailid,	tdata_faktura,
		tdata_valuta,	tiznos,	tiznos_denari, tsaldo , tsaldo_den

 from os_aneks_faktura , os_aneks ,os_zbiren_aneks b
where  os_aneks.os_aneksid=os_aneks_faktura.os_aneksid
and b.os_zbiren_aneksid=os_aneks.os_zbiren_aneksid
and b.os_zbiren_aneksid||b.par_yearid||rata=tos_zbiren_aneksid
and f_rs<>'N' ---05102021
if tsaldo_vk <>0 then

let tprop_napl=round(tsaldo/tsaldo_vk*tiznos_naplata,2);

select valuta into tvaluta from par_valuta
where par_valutaid=tpar_valutaid;

if tsaldo_vk_den <>0 then
let tprop_napl_den =round(tsaldo_den/tsaldo_vk_den*tiznos_naplata_den);
else 
execute procedure konverzija(tdatum,tprop_napl,  tvaluta,'MKD') into tprop_napl_den;	
end if;
--let tprop_napl_den =round(tsaldo_den/tsaldo_vk_den*tiznos_naplata_den);
else
continue foreach;
end if;
if tprop_napl>tsaldo then
let tprop_napl=tsaldo;
end if;



if tprop_napl_den>tsaldo_den then
let tprop_napl_den=tsaldo_den;
end if;
{
select valuta into tvaluta from par_valuta
where par_valutaid=tpar_valutaid;

	
execute procedure konverzija(tdatum,tiznos,  tvaluta,'MKD') into tiznos_den;	
}
update izvod_broevi set broj=broj+1;
select broj into tsifra_zatvaranje from izvod_broevi;


select fin_stavkaid into tfin_stavkaid
from fin_stavka where os_aneks_fakturaid=tos_aneks_fakturaid
and iznos_d is not null;

if tprop_napl<> 0 then

let sid=sq_fin_stavka.nextval;	

insert into fin_stavka (fin_stavkaid, datecreated, usercreated, version, par_filijalaid,
    par_tip_dokumentid, par_tip_kniziid, par_clientid, os_aneks_fakturaid,
    par_yearid, datum, datum_stavka,datum_fakt_valuta, par_valutaid,
    par_kursid, os_polisaid,par_agent_id, fin_izvod_iid, pat_tip_platiid,
    sifra_zatvaranje, grupa_fin_stavkaid, f_rs,
    iznos_p,   iznos_p_den,  par_statusid)
  select sid,current, tusername,0, par_filijalaid,
   par_tip_dokumentid, par_tip_kniziid, par_clientid, os_aneks_fakturaid,
   par_yearid,tdatum, tdatum,tdatum,par_valutaid,
   par_kursid,os_polisaid, par_agent_id,tfin_izvod_iid,pat_tip_platiid,
   tsifra_zatvaranje ,tfin_stavkaid, 'R',tprop_napl,
   tprop_napl_den, 1
   from fin_stavka 
   where fin_stavkaid=tfin_stavkaid;
   
   select par_clientid into tpar_client  from fin_stavka
    where fin_stavkaid=tfin_stavkaid;
   update fin_stavka set iznos_otvoren=nvl(iznos_otvoren,0)-tiznos_denari
   where fin_stavkaid=tfin_stavkaid;

	insert into log_zatvaranje(     log_zatvaranjeid ,     
     datecreated ,  usercreated ,     version ,     sifra_zatvaranje ,     vid_zat ,
     sifra_trans_0 ,     sifra_trans_z ,     fin_izvod_iid ,
     par_client ,     iznos_isplata ,     iznos_isplata_den ,
     iznos_naplata ,     iznos_naplata_den ,     par_statusid)
      values (log_zatvaranjeid.nextval, current, tusername,0,tsifra_zatvaranje ,'00' 
      ,tfin_stavkaid ,sid ,tfin_izvod_iid ,tpar_client ,0 ,0 ,tprop_napl ,tprop_napl_den ,1);
end if; 
end foreach;
end if;---end polisi
end if;
end if;
-----ZAEM----------
if tpar_tip_dokument='ZAEM' then



 select nvl(sum(fs.iznos_d-(select nvl(sum(nvl(p.iznos_p,0)),0)
                            from fin_stavka p
                            where p.grupa_fin_stavkaid=fs.fin_stavkaid
                            and p.sifra_zatvaranje is not null)),0),
        nvl(sum(fs.iznos_d_den-(select nvl(sum(nvl(p.iznos_p_den,0)),0)
                                from fin_stavka p
                                where p.grupa_fin_stavkaid=fs.fin_stavkaid
                                and p.sifra_zatvaranje is not null)),0)
into tsaldo_vk, tsaldo_vk_den
 from fin_stavka fs
where  fs.os_zaem_amort_planid=tos_zaem_amort_planid;


foreach   select fs.par_tip_kniziid,		fs.fin_stavkaid,	fs.datum,	fs.datum_knizi,fs.iznos_d, 
fs.iznos_d_den, 	fs.iznos_d-(select nvl(sum(nvl(p.iznos_p,0)),0)
                              from fin_stavka p
                              where p.grupa_fin_stavkaid=fs.fin_stavkaid
                              and p.sifra_zatvaranje is not null),
                fs.iznos_d_den-(select nvl(sum(nvl(p.iznos_p_den,0)),0)
                                from fin_stavka p
                                where p.grupa_fin_stavkaid=fs.fin_stavkaid
                                and p.sifra_zatvaranje is not null)
into tpar_tip_dokumentid,	tfin_stavkaid,
	tdata_faktura,		tdata_valuta,	tiznos,	tiznos_denari, tsaldo , tsaldo_den
 from fin_stavka fs
where  fs.os_zaem_amort_planid=tos_zaem_amort_planid
and fs.iznos_d is not null




if tsaldo_vk <>0 then

let tprop_napl=round(tsaldo/tsaldo_vk*tiznos_naplata,2);
let tprop_napl_den =round(tsaldo_den/tsaldo_vk_den*tiznos_naplata_den);
else
continue foreach;
end if;
if tprop_napl>tsaldo then
let tprop_napl=tsaldo;
end if;



if tprop_napl_den>tsaldo_den then
let tprop_napl_den=tsaldo_den;
end if;

update izvod_broevi set broj=broj+1;
select broj into tsifra_zatvaranje from izvod_broevi;




if tprop_napl<> 0 then

let sid=sq_fin_stavka.nextval;	

insert into fin_stavka (fin_stavkaid, datecreated, usercreated, version, par_filijalaid,
    par_tip_dokumentid, par_tip_kniziid, par_clientid, os_zaem_amort_planid,
    par_yearid, datum, datum_stavka,datum_fakt_valuta, par_valutaid,
    par_kursid, par_agent_id, fin_izvod_iid, pat_tip_platiid,
    sifra_zatvaranje, grupa_fin_stavkaid, f_rs,
    iznos_p,   iznos_p_den,  par_statusid, os_zaemid)
  select sid,current, tusername,0, par_filijalaid,
   par_tip_dokumentid, par_tip_kniziid, par_clientid, os_zaem_amort_planid,
   par_yearid,tdatum, tdatum,tdatum,par_valutaid,
   par_kursid, par_agent_id,tfin_izvod_iid,pat_tip_platiid,
   tsifra_zatvaranje ,tfin_stavkaid, 'R',tprop_napl,
   tprop_napl_den, 1,os_zaemid
   from fin_stavka 
   where fin_stavkaid=tfin_stavkaid;
   
   select par_clientid into tpar_client  from fin_stavka
    where fin_stavkaid=tfin_stavkaid;
   update fin_stavka set iznos_otvoren=nvl(iznos_otvoren,0)-tiznos_denari
   where fin_stavkaid=tfin_stavkaid;

	insert into log_zatvaranje(     log_zatvaranjeid ,     
     datecreated ,  usercreated ,     version ,     sifra_zatvaranje ,     vid_zat ,
     sifra_trans_0 ,     sifra_trans_z ,     fin_izvod_iid ,
     par_client ,     iznos_isplata ,     iznos_isplata_den ,
     iznos_naplata ,     iznos_naplata_den ,     par_statusid)
      values (log_zatvaranjeid.nextval, current, tusername,0,tsifra_zatvaranje ,'00' 
      ,tfin_stavkaid ,sid ,tfin_izvod_iid ,tpar_client ,0 ,0 ,tprop_napl ,tprop_napl_den ,1);
end if; 
end foreach;

end if;
-----END ZAEM-----------

-----STETI----------
if tpar_tip_dokument='STET' then


 select sum(iznos_valuta_isplata)
into tsaldo_vk
 from l_steta_likvidacija_korisnici 
where l_steta_likvidacija_korisniciid=tl_steta_likvidacija_korisniciid;


foreach   select l_steta_likvidacijaid,	l_stetaid,	l_steta_korisniciid,	par_clientid,		par_valutaid,
	iznos_valuta_isplata
into tl_steta_likvidacijaid,	tl_stetaid,	tl_steta_korisniciid,	tpar_clientid,		tpar_valutaid,
	tsaldo
 from l_steta_likvidacija_korisnici 
where l_steta_likvidacija_korisniciid=tl_steta_likvidacija_korisniciid

select par_tip_stetaid, os_ponudaid into tpar_tip_stetaid,tos_ponudaid
from l_steta
where l_stetaid=tl_stetaid;

select par_tip_steta into tpar_tip_steta
from par_tip_steta
where par_tip_stetaid=tpar_tip_stetaid;

if tpar_tip_steta='5.2' then 

update os_ponuda set  par_statusid=38
where os_ponudaid=tos_ponudaid;
end if; 


select valuta into tvaluta from par_valuta
where par_valutaid=tpar_valutaid;

execute procedure konverzija(tdatum,tsaldo_vk,  tvaluta,'MKD') into tsaldo_vk_den;	
	
execute procedure konverzija(tdatum,tsaldo,  tvaluta,'MKD') into tsaldo_den;	

if tsaldo_vk <>0 then

let tprop_napl=round(tsaldo/tsaldo_vk*tiznos_isplata,2);
let tprop_napl_den =round(tsaldo_den/tsaldo_vk_den*tiznos_isplata_den);
else
continue foreach;
end if;
if tprop_napl>tsaldo then
let tprop_napl=tsaldo;
end if;



if tprop_napl_den>tsaldo_den then
let tprop_napl_den=tsaldo_den;
end if;

update izvod_broevi set broj=broj+1;
select broj into tsifra_zatvaranje from izvod_broevi;

select par_tip_kniziid  into tpar_tip_kniziidlikv from par_tip_knizi
where par_tip_knizi='LIKV';
foreach 
select first 1 fin_stavkaid, max(datum) 
 into tfin_stavkaid , tt from fin_stavka  
where l_stetaid=tl_stetaid
and nvl(iznos_p,0)<>0
and par_tip_kniziid=tpar_tip_kniziidlikv
and f_rs='R'
group by 1 order by 2 desc

exit foreach;  
end foreach;





if tprop_napl<> 0 then

let sid=sq_fin_stavka.nextval;	

insert into fin_stavka (fin_stavkaid, datecreated, usercreated, version, par_filijalaid,
    par_tip_dokumentid, par_tip_kniziid, par_clientid, 
    par_yearid, datum, datum_stavka,datum_fakt_valuta, par_valutaid,
    par_kursid, par_agent_id, fin_izvod_iid, pat_tip_platiid,
    sifra_zatvaranje, grupa_fin_stavkaid, f_rs,
    iznos_d,   iznos_d_den,  par_statusid, l_stetaid)
  select sid,current, tusername,0, par_filijalaid,
   par_tip_dokumentid, par_tip_kniziid, tpar_clientid, 
   par_yearid,tdatum, tdatum,tdatum,par_valutaid,
   par_kursid, par_agent_id,tfin_izvod_iid,pat_tip_platiid,
   tsifra_zatvaranje ,tfin_stavkaid, 'R',tprop_napl,
   tprop_napl_den, 1,l_stetaid
   from fin_stavka 
   where fin_stavkaid=tfin_stavkaid;
   
  -- select par_clientid into tpar_client  from fin_stavka
  --  where fin_stavkaid=tfin_stavkaid;


	insert into log_zatvaranje(     log_zatvaranjeid ,     
     datecreated ,  usercreated ,     version ,     sifra_zatvaranje ,     vid_zat ,
     sifra_trans_0 ,     sifra_trans_z ,     fin_izvod_iid ,
     par_client ,     iznos_isplata ,     iznos_isplata_den ,
     iznos_naplata ,     iznos_naplata_den ,     par_statusid)
      values (log_zatvaranjeid.nextval, current, tusername,0,tsifra_zatvaranje ,'00' 
      ,tfin_stavkaid ,sid ,tfin_izvod_iid ,tpar_clientid ,tprop_napl ,tprop_napl_den ,0 ,0 ,1);
end if; 
end foreach;

end if;
-----END STETI-----------


--update fin_izvod_i set sifra_zatvaranje=tsifra_zatvaranje,f_zatvoren='Z'
--where fin_izvod_iid=tfin_izvod_iid;

--end if;
-------------------------------------------------


--COMMIT WORK;
--return 1,'ZATVORENA E STAVKATA ';
end procedure;
