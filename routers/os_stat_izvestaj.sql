CREATE FUNCTION appuser.os_stat_izvestaj (mesec int, godina int )
         returning integer,char(100);
{
procedurata vraka:

         - kod na greska
                   1 ako se e ok i ako e izvrseno
                  -1 ako se pojavi nekoja neregularnost
         - poraka poradi koja e nastanata greskata }

define tstat_izvestaiid int;
define tdo_datum,tod_datum_godina,tod_odatum ,tdatum_do date;
define tgrupa_sp1,tvid_stavka  varchar(20);
define  takt_polisi  , tbr_osigurenici  ,tbr_osigurenici_kolekt ,tkapitalizirani, totkup,tskl_dog,tkolku, 	tpar_prod_kanalid int;
define tbruto_premija,tbruto_premija12,tedin_premija dec; 
define tednokrat_premija,tosig_suma, tisp_iznos,totk_iznos dec;
define tprij_neiz ,  tprij_izv , todb ,   tisp ,   totk ,  trezr_izv   ,  trezr_neiz ,tstorno_polisi ,tkap_polisi  ,i int;
define tkurs decimal(20,4);
define tprod_kanal,tbroker_name varchar(100);
define 	tbroj_polisi,	tprovizija, tstorno_premija  , totkup_premija   dec;

 on exception
    -- ROLLBACK WORK;
         return -1,'НАСТАНАТА Е ГРЕШКА'; 
      end exception;



set isolation to dirty read;

 set debug file to "err_os_stat_izvestaj.sql"; 
trace on;




--BEGIN WORK;
create temp table sp1_analitika( grupa_sp1 VARCHAR(20),polisa_broj  VARCHAR(20),  akt_polisi int , br_osigurenici int ,br_osigurenici_kolekt int, osig_suma decimal(20,2) ) ; 
create temp table sp1_kap_polisi( grupa_sp1 VARCHAR(20),polisa_broj  VARCHAR(20),  kapitalizirani int ) ; 
create temp table sp1_otkup( grupa_sp1 VARCHAR(20), polisa_broj  VARCHAR(20),  otkup int  ) ; 
create temp table sp1_skl_dog( grupa_sp1 VARCHAR(20),polisa_broj  VARCHAR(20),  skl_dog int ) ; 
create temp table sp1_bruto_premija( grupa_sp1 VARCHAR(20),  bruto_premija   dec ) ; 
create temp table sp1_bruto_premija12( grupa_sp1 VARCHAR(20),  bruto_premija12  dec ) ; 
create temp table sp1_edin_premija( grupa_sp1 VARCHAR(20),  edin_premija dec  ) ;
create temp table sp1_ednokrat_premija( grupa_sp1 VARCHAR(20),  ednokrat_premija dec  ) ;
create temp table sp1_analitika_tar( grupa_sp1 VARCHAR(20),polisa_broj  VARCHAR(20),  akt_polisi int , br_osigurenici int ,br_osigurenici_kolekt int,
 kapitalizirani int ,  otkup int, skl_dog int ) ;
 create temp table sp1_analitika_tarifa( grupa_sp1 VARCHAR(20),polisa_broj  VARCHAR(20),  akt_polisi int , br_osigurenici int ,br_osigurenici_kolekt int,
 kapitalizirani int ,  otkup int, skl_dog int ) ;
let tdatum_do=LAST_DAY(mdy(mesec,1,godina) );
let tdo_datum=LAST_DAY(mdy(month(tdatum_do) -3,1,year(tdatum_do) ));
let tod_odatum=LAST_DAY(mdy(month(tdatum_do),1,year(tdatum_do)-1 )) +1 UNITS DAY;
let tod_datum_godina=mdy(1,1,year(tdatum_do) );



if  today - tdatum_do>30 then 
return '-1','Заклучен е СП';
end if;

SELECT count(*) into tkolku
FROM stat_izvestai
where stat_izvestaj='SP-1'
and datum=tdatum_do;

if tkolku>0 then 
delete 
FROM stat_izvestai
where stat_izvestaj='SP-1'
and datum=tdatum_do;
end if; 

select max(stat_izvestaiid)  into tstat_izvestaiid from stat_izvestai;
insert  into stat_izvestai (stat_izvestaiid,	datecreated,	usercreated	,version,	datum,	stat_izvestaj,	vid_stavka) 
SELECT tstat_izvestaiid+stat_izvestaiid,current,6,0,tdatum_do,stat_izvestaj, vid_stavka  FROM stat_izvestai
where stat_izvestaj='SP-1'
and datum=tdo_datum;
--order by  stat_izvestaiid;



execute  function vrati_kurs(tdo_datum,'EUR') into tkurs; 

---------------------------analitika za sp1
insert   into sp1_analitika( grupa_sp1,  akt_polisi ,  br_osigurenici,br_osigurenici_kolekt, osig_suma ) 
select vrati_grupa(d.os_ponuda_detailid ) grupa_sp1,    count(*) akt_polisi ,
sum(nvl(br_osig_aktivni,1) )  br_osigurenici,
sum( case when vrati_tipprodukt (p.os_tipproduktid) in ('КР','КЖ') then 
 nvl(br_osig_aktivni,1) else 0 end) br_osigurenici_kolekt,
 sum(case when nvl(o.par_valutaid,p.par_valutaid)=363 then  nvl(osig_suma_smrt,osig_suma) else nvl(osig_suma_smrt,osig_suma)*tkurs end )
from os_ponuda o, os_ponuda_detail d, os_produkt p, os_polisa t
where o.os_ponudaid=d.os_ponudaid 
and o.os_produktid=p.os_produktid
and o.os_ponudaid=t.os_ponudaid 
and skadenca_datum_od<=tdatum_do
and skadenca_datum_do>=tdatum_do
and o.par_statusid in  (17,18,13, 42) 
and ponuda_podbroj=maxpodbroj_datum(o.ponuda_broj , t.polisa_broj, o.os_produktid, tdatum_do )
group by 1;
--------------------
--set debug file to "err_os_stat_izvestaj.sql"; 
--trace on;

--kapitalizirani polisi
insert  into sp1_kap_polisi( grupa_sp1, kapitalizirani) 
select vrati_grupa(d.os_ponuda_detailid ) grupa_sp1,  count(*)  kapitalizirani
from os_ponuda o, os_ponuda_detail d, os_polisa t
where o.os_ponudaid=d.os_ponudaid
and o.os_ponudaid=t.os_ponudaid  
and skadenca_datum_od<=tdatum_do
and skadenca_datum_do>=tdatum_do
and o.par_statusid in (18) ---,11,12,14,39,40,41)
and ponuda_podbroj=maxpodbroj_datum(o.ponuda_broj , t.polisa_broj, o.os_produktid, tdatum_do )
group by 1;

--otkup 

insert  into sp1_otkup( grupa_sp1, otkup) 
select vrati_grupa(d.os_ponuda_detailid ) grupa_sp1,  count(*) otkup
from os_ponuda o, os_ponuda_detail d, os_polisa t
where o.os_ponudaid=d.os_ponudaid 
and o.os_ponudaid=t.os_ponudaid 
and skadenca_datum_od<=tdatum_do
and skadenca_datum_do>=tdatum_do
and o.par_statusid in (20,21) ---,11,12,14,39,40,41)
and ponuda_podbroj=maxpodbroj_datum(o.ponuda_broj , t.polisa_broj, o.os_produktid, tdatum_do)
group by 1;



---skluceni dogovori 
insert  into sp1_skl_dog( grupa_sp1,skl_dog) 
select vrati_grupa(d.os_ponuda_detailid ) grupa_sp1, count(*) 
from os_ponuda o, os_ponuda_detail d,  os_polisa p
where o.os_ponudaid=d.os_ponudaid 
and o.os_ponudaid=p.os_ponudaid
and p.datum_polisa between tod_datum_godina and tdatum_do
and o.par_statusid in (17,18) 
and ponuda_podbroj=maxpodbroj_datum(o.ponuda_broj , p.polisa_broj, o.os_produktid, tdatum_do )
group by 1;

-----
insert   into sp1_analitika_tar( grupa_sp1,  akt_polisi ,  br_osigurenici,br_osigurenici_kolekt, kapitalizirani,  otkup, skl_dog ) 
select grupa_sp1,   sum( akt_polisi) ,
sum(  br_osigurenici),sum(  br_osigurenici_kolekt), sum(  kapitalizirani), sum(  otkup),sum( skl_dog)
from (
select vrati_grupa_tar(d.os_ponuda_detailid ) grupa_sp1,    count( distinct polisa_broj ) akt_polisi ,
sum(nvl(br_osig_aktivni,1) )  br_osigurenici,
sum( case when vrati_tipprodukt (p.os_tipproduktid) in ('КР','КЖ') then 
 nvl(br_osig_aktivni,1) else 0 end) br_osigurenici_kolekt,0 kapitalizirani, 0 otkup,0 skl_dog
from os_ponuda o, os_ponuda_detail d, os_produkt p, os_polisa t
where o.os_ponudaid=d.os_ponudaid 
and o.os_produktid=p.os_produktid
and o.os_ponudaid=t.os_ponudaid 
and skadenca_datum_od<=tdatum_do
and skadenca_datum_do>=tdatum_do
and o.par_statusid in  (17,18,13, 42) 
and ponuda_podbroj=maxpodbroj_datum(o.ponuda_broj , t.polisa_broj, o.os_produktid, tdatum_do )
group by 1 
union
select vrati_grupa_tar(d.os_ponuda_detailid ) grupa_sp1,   0 akt_polisi ,
0  br_osigurenici,0 br_osigurenici_kolekt, count( distinct polisa_broj) kapitalizirani, 0 otkup,0 skl_dog
from os_ponuda o, os_ponuda_detail d, os_polisa t
where o.os_ponudaid=d.os_ponudaid
and o.os_ponudaid=t.os_ponudaid  
and skadenca_datum_od<=tdatum_do
and skadenca_datum_do>=tdatum_do
and o.par_statusid in (18) ---,11,12,14,39,40,41)
and ponuda_podbroj=maxpodbroj_datum(o.ponuda_broj , t.polisa_broj, o.os_produktid, tdatum_do )
group by 1
union
select vrati_grupa_tar(d.os_ponuda_detailid ) grupa_sp1, 0 akt_polisi ,
0  br_osigurenici,0 br_osigurenici_kolekt,0 kapitalizirani,   count(distinct polisa_broj) otkup,0 skl_dog

from os_ponuda o, os_ponuda_detail d, os_polisa t
where o.os_ponudaid=d.os_ponudaid 
and o.os_ponudaid=t.os_ponudaid 
and skadenca_datum_od<=tdatum_do
and skadenca_datum_do>=tdatum_do
and o.par_statusid in (20,21) ---,11,12,14,39,40,41)
and ponuda_podbroj=maxpodbroj_datum(o.ponuda_broj , t.polisa_broj, o.os_produktid, tdatum_do)
group by 1 
union
select vrati_grupa_tar(d.os_ponuda_detailid ) grupa_sp1, 0 akt_polisi ,
0  br_osigurenici,0 br_osigurenici_kolekt,0 kapitalizirani,   0 otkup, count(distinct polisa_broj )  skl_dog
from os_ponuda o, os_ponuda_detail d,  os_polisa p
where o.os_ponudaid=d.os_ponudaid 
and o.os_ponudaid=p.os_ponudaid
and p.datum_polisa between tod_datum_godina and tdatum_do
and o.par_statusid in (17,18) 
and ponuda_podbroj=maxpodbroj_datum(o.ponuda_broj , p.polisa_broj, o.os_produktid, tdatum_do )
group by 1)  a
group by 1;
-----


insert   into sp1_analitika_tarifa( grupa_sp1,  akt_polisi ,  br_osigurenici,br_osigurenici_kolekt, kapitalizirani,  otkup, skl_dog ) 
select grupa_sp1,   sum( akt_polisi) ,
sum(  br_osigurenici),sum(  br_osigurenici_kolekt), sum(  kapitalizirani), sum(  otkup),sum( skl_dog)
from (
select vrati_grupa_tarifa(d.os_ponuda_detailid ) grupa_sp1,    count( distinct polisa_broj ) akt_polisi ,
sum(nvl(br_osig_aktivni,1) )  br_osigurenici,
sum( case when vrati_tipprodukt (p.os_tipproduktid) in ('КР','КЖ') then 
 nvl(br_osig_aktivni,1) else 0 end) br_osigurenici_kolekt,0 kapitalizirani, 0 otkup,0 skl_dog
from os_ponuda o, os_ponuda_detail d, os_produkt p, os_polisa t
where o.os_ponudaid=d.os_ponudaid 
and o.os_produktid=p.os_produktid
and o.os_ponudaid=t.os_ponudaid 
and skadenca_datum_od<=tdatum_do
and skadenca_datum_do>=tdatum_do
and o.par_statusid in  (17,18,13, 42) 
and ponuda_podbroj=maxpodbroj_datum(o.ponuda_broj , t.polisa_broj, o.os_produktid, tdatum_do )
group by 1 
union
select vrati_grupa_tarifa(d.os_ponuda_detailid ) grupa_sp1,   0 akt_polisi ,
0  br_osigurenici,0 br_osigurenici_kolekt, count( distinct polisa_broj) kapitalizirani, 0 otkup,0 skl_dog
from os_ponuda o, os_ponuda_detail d, os_polisa t
where o.os_ponudaid=d.os_ponudaid
and o.os_ponudaid=t.os_ponudaid  
and skadenca_datum_od<=tdatum_do
and skadenca_datum_do>=tdatum_do
and o.par_statusid in (18) ---,11,12,14,39,40,41)
and ponuda_podbroj=maxpodbroj_datum(o.ponuda_broj , t.polisa_broj, o.os_produktid, tdatum_do )
group by 1
union
select vrati_grupa_tarifa(d.os_ponuda_detailid ) grupa_sp1, 0 akt_polisi ,
0  br_osigurenici,0 br_osigurenici_kolekt,0 kapitalizirani,   count(distinct polisa_broj) otkup,0 skl_dog

from os_ponuda o, os_ponuda_detail d, os_polisa t
where o.os_ponudaid=d.os_ponudaid 
and o.os_ponudaid=t.os_ponudaid 
and skadenca_datum_od<=tdatum_do
and skadenca_datum_do>=tdatum_do
and o.par_statusid in (20,21) ---,11,12,14,39,40,41)
and ponuda_podbroj=maxpodbroj_datum(o.ponuda_broj , t.polisa_broj, o.os_produktid, tdatum_do)
group by 1 
union
select vrati_grupa_tarifa(d.os_ponuda_detailid ) grupa_sp1, 0 akt_polisi ,
0  br_osigurenici,0 br_osigurenici_kolekt,0 kapitalizirani,   0 otkup, count(distinct polisa_broj )  skl_dog
from os_ponuda o, os_ponuda_detail d,  os_polisa p
where o.os_ponudaid=d.os_ponudaid 
and o.os_ponudaid=p.os_ponudaid
and p.datum_polisa between tod_datum_godina and tdatum_do
and o.par_statusid in (17,18) 
and ponuda_podbroj=maxpodbroj_datum(o.ponuda_broj , p.polisa_broj, o.os_produktid, tdatum_do )
group by 1)  a
group by 1;

--bruto premija
insert  into sp1_bruto_premija( grupa_sp1,  bruto_premija) 
select sap_risk_business[3,10],  sum(nvl(iznos_p,0)) bruto_premija 
from stavka 
where dat_nalog between tod_datum_godina and tdatum_do
and  konto[1,3]='700'
group by 1;
------
---bruto premija - 12 meseci
insert  into sp1_bruto_premija12( grupa_sp1,  bruto_premija12) 
select sap_risk_business[3,10], sum(nvl(iznos_p,0)) bruto_premija 
from stavka 
where dat_nalog between tod_odatum and tdatum_do
and  konto[1,3]='700'
and sap_risk_business is not null
group by 1; 



---edin_premija 
insert  into sp1_edin_premija( grupa_sp1,  edin_premija) 
select sap_risk_business[3,10], sum(nvl(iznos_p,0)) bruto_premija 
from stavka s ,os_polisa p, os_ponuda po  , os_produkt pr
where s.dokument[1,10] =p.polisa_broj_cel
and s.dokument[11,14]=p.polisa_pod_broj
and p.os_ponudaid=po.os_ponudaid
and po.os_produktid=pr.os_produktid
and vrati_tipprodukt (pr.os_tipproduktid) not in     ('КР','КЖ')
and  s.dat_nalog between tod_datum_godina and tdatum_do
and  konto[1,3]='700'
and sap_risk_business is not null
group by 1;

insert  into sp1_ednokrat_premija( grupa_sp1,  ednokrat_premija) 
select sap_risk_business[3,10], sum(nvl(iznos_p,0)) bruto_premija 
from stavka s ,os_polisa p, os_ponuda po  
where s.dokument[1,10] =p.polisa_broj_cel
and s.dokument[11,14]=p.polisa_pod_broj
and p.os_ponudaid=po.os_ponudaid
and vrati_nacin_plati_code(po.os_produkt_uplataid)='005'
and  s.dat_nalog between tod_datum_godina and tdatum_do
and  konto[1,3]='700'
and sap_risk_business is not null
group by 1;

--set debug file to "err_os_stat_izvestaj.sql"; 
--trace on;


foreach select a.grupa_sp1 ,  akt_polisi  , br_osigurenici  ,br_osigurenici_kolekt ,nvl(kapitalizirani,0), nvl(otkup,0) ,nvl(skl_dog,0) ,nvl(bruto_premija,0) 
,nvl(bruto_premija12,0),nvl(edin_premija,0), nvl(ednokrat_premija,0)  
into tgrupa_sp1 ,  takt_polisi  , tbr_osigurenici  ,tbr_osigurenici_kolekt ,tkapitalizirani, totkup,tskl_dog,tbruto_premija,tbruto_premija12,tedin_premija, tednokrat_premija
from sp1_analitika a ,outer sp1_kap_polisi b ,outer sp1_otkup c ,outer sp1_skl_dog d, outer sp1_bruto_premija e ,outer sp1_bruto_premija12 f ,outer sp1_edin_premija g
,outer sp1_ednokrat_premija h
where a.grupa_sp1=b.grupa_sp1
and a.grupa_sp1=c.grupa_sp1
and a.grupa_sp1=d.grupa_sp1
and a.grupa_sp1=e.grupa_sp1
and a.grupa_sp1=f.grupa_sp1
and a.grupa_sp1=g.grupa_sp1 
and a.grupa_sp1=h.grupa_sp1

update stat_izvestai set  kol100=takt_polisi, 	kol102=tbr_osigurenici,	kol103=tbr_osigurenici_kolekt,
	kol104=tkapitalizirani,	kol105=totkup, 	kol106=tskl_dog,	kol200=tbruto_premija/1000,	kol201=tednokrat_premija/1000,
	kol202=tedin_premija/1000,	kol203=tbruto_premija12/1000, kol204=0, kol206=0, kol205=0, ---da se proveri dali mozze da se zeme od konto 
	kol207=0
where stat_izvestaj='SP-1'
and vid_stavka=tgrupa_sp1
and datum=tdatum_do;

end foreach ;

---   да се наполнат --- 190101,190201,190202,190203

foreach select a.grupa_sp1,  sum(akt_polisi)  , sum(br_osigurenici)  ,sum(br_osigurenici_kolekt) ,sum(nvl(kapitalizirani,0)), sum(nvl(otkup,0)) ,
sum(nvl(skl_dog,0))
into tgrupa_sp1 ,  takt_polisi  , tbr_osigurenici  ,tbr_osigurenici_kolekt ,tkapitalizirani, totkup,tskl_dog
from sp1_analitika_tar a 
where  a.grupa_sp1 like '19%'
group by a.grupa_sp1

update stat_izvestai set  kol100=takt_polisi, 	kol102=tbr_osigurenici,	kol103=tbr_osigurenici_kolekt,
	kol104=tkapitalizirani,	kol105=totkup, 	kol106=tskl_dog,	
 kol204=0, kol206=0, kol205=0, ---da se proveri dali mozze da se zeme od konto 
	kol207=0
where stat_izvestaj='SP-1'
and vid_stavka=tgrupa_sp1
and datum=tdatum_do;

end foreach ;
--1901, 1902

foreach select a.grupa_sp1,  sum(akt_polisi)  , sum(br_osigurenici)  ,sum(br_osigurenici_kolekt) ,sum(nvl(kapitalizirani,0)), sum(nvl(otkup,0)) ,
sum(nvl(skl_dog,0))
into tgrupa_sp1 ,  takt_polisi  , tbr_osigurenici  ,tbr_osigurenici_kolekt ,tkapitalizirani, totkup,tskl_dog
from sp1_analitika_tarifa a 
where  a.grupa_sp1  like '19%'

group by a.grupa_sp1

update stat_izvestai set  kol100=takt_polisi, 	kol102=tbr_osigurenici,	kol103=tbr_osigurenici_kolekt,
	kol104=tkapitalizirani,	kol105=totkup, 	kol106=tskl_dog,	
 kol204=0, kol206=0, kol205=0, ---da se proveri dali mozze da se zeme od konto 
	kol207=0
where stat_izvestaj='SP-1'
and vid_stavka=tgrupa_sp1
and datum=tdatum_do;

end foreach ;

-- set debug file to "err_os_stat_izvestaj.sql"; 
--trace on;

foreach select vid_stavka[1,6], sum(nvl(kol200,0)) ,sum(nvl(kol203,0)),sum(nvl(kol202,0)), sum(nvl(kol201,0) ) 
into tgrupa_sp1 , tbruto_premija,tbruto_premija12,tedin_premija, tednokrat_premija
from stat_izvestai
where stat_izvestaj='SP-1'
and datum=tdatum_do
and length(vid_stavka)>4
and vid_stavka like '19%'
group by vid_stavka[1,6]

update stat_izvestai set  	kol200=tbruto_premija,	kol201=tednokrat_premija,
	kol202=tedin_premija,	kol203=tbruto_premija12, kol204=0, kol206=0, kol205=0,
	kol207=0
where stat_izvestaj='SP-1'
and vid_stavka=tgrupa_sp1
and datum=tdatum_do;

end foreach ;


foreach select vid_stavka[1,4], sum(nvl(kol200,0)) ,sum(nvl(kol203,0)),sum(nvl(kol202,0)), sum(nvl(kol201,0) ) 
into tgrupa_sp1 , tbruto_premija,tbruto_premija12,tedin_premija, tednokrat_premija
from stat_izvestai
where stat_izvestaj='SP-1'
and datum=tdatum_do
and length(vid_stavka)>4
and vid_stavka like '19%'
group by vid_stavka[1,4]

update stat_izvestai set  	kol200=tbruto_premija,	kol201=tednokrat_premija,
	kol202=tedin_premija,	kol203=tbruto_premija12, kol204=0, kol206=0, kol205=0,
	kol207=0
where stat_izvestaj='SP-1'
and vid_stavka=tgrupa_sp1
and datum=tdatum_do;

end foreach ;


foreach select vid_stavka[1,2],  sum(kol100)  , sum(kol102)  ,sum(kol103) ,sum(nvl(kol104,0)), sum(nvl(kol105,0)) ,
sum(nvl(kol106,0)) ,sum(nvl(kol200,0)) ,sum(nvl(kol203,0)),sum(nvl(kol202,0)), sum(nvl(kol201,0) ) 
into tgrupa_sp1 ,  takt_polisi  , tbr_osigurenici  ,tbr_osigurenici_kolekt ,tkapitalizirani, totkup,
tskl_dog,tbruto_premija,tbruto_premija12,tedin_premija, tednokrat_premija
from stat_izvestai
where stat_izvestaj='SP-1'
and datum=tdatum_do
and vid_stavka[1,2] like '19%'
and vid_stavka  in ('1901','1902')
group by vid_stavka[1,2]

update stat_izvestai set  kol100=takt_polisi, 	kol102=tbr_osigurenici,	kol103=tbr_osigurenici_kolekt,
	kol104=tkapitalizirani,	kol105=totkup, 	kol106=tskl_dog,	kol200=tbruto_premija,	kol201=tednokrat_premija,
	kol202=tedin_premija,	kol203=tbruto_premija12, kol204=0, kol206=0, kol205=0, ---da se proveri dali mozze da se zeme od konto 
	kol207=0
where stat_izvestaj='SP-1'
and vid_stavka=tgrupa_sp1
and datum=tdatum_do;

end foreach ;




select sum(kol100)  , sum(kol102)  ,sum(kol103) ,sum(nvl(kol104,0)), sum(nvl(kol105,0)) ,
sum(nvl(kol106,0)) ,sum(nvl(kol200,0)) ,sum(nvl(kol203,0)),sum(nvl(kol202,0)), sum(nvl(kol201,0) ) 
into  takt_polisi  , tbr_osigurenici  ,tbr_osigurenici_kolekt ,tkapitalizirani, totkup,tskl_dog,tbruto_premija,tbruto_premija12,tedin_premija, tednokrat_premija
from stat_izvestai
where stat_izvestaj='SP-1'
and datum=tdatum_do
and vid_stavka in ('19','20','21','22','23','24','25');

update stat_izvestai set  kol100=takt_polisi, 	kol102=tbr_osigurenici,	kol103=tbr_osigurenici_kolekt,
	kol104=tkapitalizirani,	kol105=totkup, 	kol106=tskl_dog,	kol200=tbruto_premija,	kol201=tednokrat_premija,
	kol202=tedin_premija,	kol203=tbruto_premija12, kol204=0, kol206=0, kol205=0, ---da se proveri dali mozze da se zeme od konto 
	kol207=0
where stat_izvestaj='SP-1'
and vid_stavka='0000'
and datum=tdatum_do;





----sp--2
SELECT count(*) into tkolku
FROM stat_izvestai
where stat_izvestaj='SP-2'
and datum=tdatum_do;

if tkolku>0 then 
delete 
FROM stat_izvestai
where stat_izvestaj='SP-2'
and datum=tdatum_do;
end if; 

select max(stat_izvestaiid)  into tstat_izvestaiid from stat_izvestai;
insert  into stat_izvestai (stat_izvestaiid,	datecreated,	usercreated	,version,	datum,	stat_izvestaj,	vid_stavka) 
SELECT tstat_izvestaiid+stat_izvestaiid,current,6,0,tdatum_do,stat_izvestaj, vid_stavka  FROM stat_izvestai
where stat_izvestaj='SP-2'
and datum=tdo_datum;
--create temp table sp2_osig_sumi( grupa_sp1 VARCHAR(20),  osig_suma decimal(20,2)  ) ; 
create temp table sp2_br_steti( grupa_sp1 VARCHAR(20), prij_neiz int,  prij_izv int, odb int,   isp int,   otk int,  rezr_izv  int ,  rezr_neiz int,isp_iznos dec ,otk_iznos  dec ) ; 
----Износ на                     договорени суми или годишни ануитети            (вклучувајќи ја и добивката)
--insert into  sp2_osig_sumi( grupa_sp1 ,  osig_suma   )
--select vrati_grupa(d.os_ponuda_detailid ) grupa_sp1,   sum(nvl(osig_suma_smrt,osig_suma))
--from os_ponuda o, os_ponuda_detail d, os_produkt p, os_polisa t
--where o.os_ponudaid=d.os_ponudaid 
--and o.os_produktid=p.os_produktid
--and o.os_ponudaid=t.os_ponudaid 
--and skadenca_datum_od<=tdatum_do
--and skadenca_datum_do>=tdatum_do
--and o.par_statusid in  (17,18,13, 42) 
--and ponuda_podbroj=maxpodbroj_datum(o.ponuda_broj , t.polisa_broj, o.os_produktid, tdatum_do)
--group by 1,2;



insert into  sp2_br_steti( grupa_sp1 , prij_neiz ,  prij_izv , odb ,   isp ,   otk ,  rezr_izv   ,  rezr_neiz ,isp_iznos,otk_iznos  )  
select  sap_risk_biznis, sum(prij_neiz)  ,  sum(prij_izv)  , sum(odb) ,   sum(isp ),  sum( otk)  ,  sum(rezr_izv )   , sum( rezr_neiz),
sum(isp_iznos),sum(otk_iznos) 
 from 
(select sap_risk_biznis[3,10],count(*) prij_neiz, 0 prij_izv,0 odb, 0  isp, 0  otk, 0 rezr_izv , 0 rezr_neiz,0  isp_iznos,0  otk_iznos
from sostojba_steta
where steta_datum_prijava between tod_datum_godina and tdatum_do  
and par_tip_stetaid<>4
group by 1
union 
select vrati_grupa(d.os_ponuda_detailid ) grupa_sp1, 0 prij_neiz,   count(*) prij_izv,0 odb, 0  isp, 0  otk, 0 rezr_izv , 0 rezr_neiz,0  isp_iznos,0  otk_iznos
from os_ponuda o, os_ponuda_detail d, os_produkt p, os_polisa t
where o.os_ponudaid=d.os_ponudaid 
and o.os_produktid=p.os_produktid
and o.os_ponudaid=t.os_ponudaid 
and skadenca_datum_do between tod_datum_godina and tdatum_do 
and o.par_statusid in  ( 36,37,38,42) 
and ponuda_podbroj=maxpodbroj_datum(o.ponuda_broj , t.polisa_broj, o.os_produktid, tdatum_do  )
group by 1,2
union
--odb steti
select sap_risk_biznis[3,10], 0 prij_neiz, 0 prij_izv,  count(*) odb, 0  isp, 0  otk , 0 rezr_izv , 0 rezr_neiz,0  isp_iznos,0  otk_iznos
from sostojba_steta 
where 1 = 1 and likv_datum >=tod_datum_godina  and likv_datum <=tdatum_do 
and vratilikizn_steta(l_stetaid,'01.01.2005',tdatum_do)= 0 
and par_tip_stetaid<>4
group by 1 
union 

select sap_risk_biznis[3,10], 0 prij_neiz, 0 prij_izv,  count(*) odb, 0  isp, 0  otk , count(*) rezr_izv , 0 rezr_neiz,
0  isp_iznos,0  otk_iznos
from sostojba_steta 
where 1 = 1  
and vratirezizn_steta(l_stetaid,'01.01.2005',tdatum_do)!= 0 
and par_tip_stetaid<>4
group by 1 

union
select sap_risk_biznis[3,10], 0 prij_neiz, 0 prij_izv,0 odb, sum(case when  par_tip_stetaid<>4 then  1 else 0 end )  isp,  
sum(case when  par_tip_stetaid=4 then  1 else 0 end )  otk  , 0 rezr_izv , 0 rezr_neiz,  sum(case when  par_tip_stetaid<>4 
then  vratilikizn_steta_den(l_stetaid,tod_datum_godina,tdatum_do) else 0 end )  isp_iznos,  
sum(case when  par_tip_stetaid=4 then  vratilikizn_steta_den(l_stetaid,tod_datum_godina,tdatum_do) else 0 end )  otk_iznos 
from sostojba_steta 
where 1 = 1 and likv_datum >=tod_datum_godina  and likv_datum <=tdatum_do 
and vratilikizn_steta(l_stetaid,tod_datum_godina,tdatum_do)!= 0 

group by 1) a
group by 1 ; 




foreach select a.grupa_sp1 , osig_suma, prij_neiz ,  prij_izv , odb ,   isp ,   otk ,  rezr_izv   ,  rezr_neiz ,isp_iznos,otk_iznos
  
into tgrupa_sp1 ,  tosig_suma, tprij_neiz ,  tprij_izv , todb ,   tisp ,   totk ,  trezr_izv   ,  trezr_neiz ,tisp_iznos,totk_iznos
from sp1_analitika a ,outer sp2_br_steti b 
where a.grupa_sp1=b.grupa_sp1


update stat_izvestai set  kol100=tosig_suma/1000, 	kol200=tprij_neiz,	kol200a=tprij_izv,
	kol201=todb,	kol202=trezr_neiz, 	kol203=trezr_izv,	kol204=0,	kol205=0,
	kol205a=0,	kol206=tisp, kol207=totk, kol300=0, kol301=tisp_iznos/1000, kol302=totk_iznos/1000
where stat_izvestaj='SP-2'
and vid_stavka=tgrupa_sp1
and datum=tdatum_do;

end foreach ;





--- да се наполнат --- 190101,190201,190202,190203
foreach select a.grupa_sp1[1,6] , sum(osig_suma), sum(prij_neiz) ,  sum(prij_izv) , sum(odb) ,  sum( isp ),  sum( otk) , 
sum( rezr_izv)   , sum( rezr_neiz ),sum(isp_iznos),sum(otk_iznos)
  
into tgrupa_sp1 ,  tosig_suma, tprij_neiz ,  tprij_izv , todb ,   tisp ,   totk ,  trezr_izv   ,  trezr_neiz ,tisp_iznos,totk_iznos
from sp1_analitika a ,outer sp2_br_steti b 
where a.grupa_sp1=b.grupa_sp1
and a.grupa_sp1 like '19%'
group by a.grupa_sp1[1,6]


update stat_izvestai set  kol100=tosig_suma/1000, 	kol200=tprij_neiz,	kol200a=tprij_izv,
	kol201=todb,	kol202=trezr_neiz, 	kol203=trezr_izv,	kol204=0,	kol205=0,
	kol205a=0,	kol206=tisp, kol207=totk, kol300=0, kol301=tisp_iznos/1000, kol302=totk_iznos/1000
where stat_izvestaj='SP-2'
and vid_stavka=tgrupa_sp1
and datum=tdatum_do;

end foreach ;


--1901, 1902
foreach select a.grupa_sp1[1,4] ,  sum(osig_suma), sum(prij_neiz) ,  sum(prij_izv) , sum(odb) ,  sum( isp ),  sum( otk) , 
sum( rezr_izv)   , sum( rezr_neiz ),sum(isp_iznos),sum(otk_iznos)
  
into tgrupa_sp1 ,  tosig_suma, tprij_neiz ,  tprij_izv , todb ,   tisp ,   totk ,  trezr_izv   ,  trezr_neiz ,tisp_iznos,totk_iznos
from sp1_analitika a ,outer sp2_br_steti b 
where a.grupa_sp1=b.grupa_sp1
and a.grupa_sp1 like '19%'
group by a.grupa_sp1[1,4]


update stat_izvestai set  kol100=tosig_suma/1000, 	kol200=tprij_neiz,	kol200a=tprij_izv,
	kol201=todb,	kol202=trezr_neiz, 	kol203=trezr_izv,	kol204=0,	kol205=0,
	kol205a=0,	kol206=tisp, kol207=totk, kol300=0, kol301=tisp_iznos/1000, kol302=totk_iznos/1000

where stat_izvestaj='SP-2'
and vid_stavka=tgrupa_sp1
and datum=tdatum_do;

end foreach ;


--19 

foreach select vid_stavka[1,2],  sum(kol100)  , sum(kol200)  ,sum(kol200a) ,sum(nvl(kol201,0)), sum(nvl(kol202,0)) ,
sum(nvl(kol203,0)) ,sum(nvl(kol206,0)) ,sum(nvl(kol207,0)),sum(nvl(kol301,0)), sum(nvl(kol302,0) ) 
into tgrupa_sp1 ,  tosig_suma, tprij_neiz ,  tprij_izv , todb ,   tisp ,   totk ,  trezr_izv   ,  trezr_neiz ,tisp_iznos,totk_iznos
from stat_izvestai
where stat_izvestaj='SP-2'
and datum=tdatum_do
and vid_stavka[1,2] like '19%'
group by vid_stavka[1,2]

update stat_izvestai set  kol100=tosig_suma, 	kol200=tprij_neiz,	kol200a=tprij_izv,
	kol201=todb,	kol202=trezr_neiz, 	kol203=trezr_izv,	kol204=0,	kol205=0,
	kol205a=0,	kol206=tisp, kol207=totk, kol300=0, kol301=tisp_iznos, kol302=totk_iznos

where stat_izvestaj='SP-2'
and vid_stavka=tgrupa_sp1
and datum=tdatum_do;

end foreach ;



select  sum(kol100)  , sum(kol200)  ,sum(kol200a) ,sum(nvl(kol201,0)), sum(nvl(kol202,0)) ,
sum(nvl(kol203,0)) ,sum(nvl(kol206,0)) ,sum(nvl(kol207,0)),sum(nvl(kol301,0)), sum(nvl(kol302,0) ) 
into   tosig_suma, tprij_neiz ,  tprij_izv , todb ,   tisp ,   totk ,  trezr_izv   ,  trezr_neiz ,tisp_iznos,totk_iznos
from stat_izvestai
where stat_izvestaj='SP-2'
and datum=tdatum_do
and vid_stavka in ('19','20','21','22','23','24','25');

update stat_izvestai set kol100=tosig_suma, 	kol200=tprij_neiz,	kol200a=tprij_izv,
	kol201=todb,	kol202=trezr_neiz, 	kol203=trezr_izv,	kol204=0,	kol205=0,
	kol205a=0,	kol206=tisp, kol207=totk, kol300=0, kol301=tisp_iznos, kol302=totk_iznos
where stat_izvestaj='SP-2'
and vid_stavka='0000'
and datum=tdatum_do;


---sp-5

SELECT count(*) into tkolku
FROM stat_izvestai
where stat_izvestaj='SP-5'
and datum=tdatum_do;

if tkolku>0 then 
delete 
FROM stat_izvestai
where stat_izvestaj='SP-5'
and datum=tdatum_do;
end if; 

select max(stat_izvestaiid)  into tstat_izvestaiid from stat_izvestai;
insert  into stat_izvestai (stat_izvestaiid,	datecreated,	usercreated	,version,	datum,	stat_izvestaj,	vid_stavka) 
SELECT tstat_izvestaiid+stat_izvestaiid,current,6,0,tdatum_do,stat_izvestaj, vid_stavka  FROM stat_izvestai
where stat_izvestaj='SP-5'
and datum=tdo_datum;

---sp-6

SELECT count(*) into tkolku
FROM stat_izvestai
where stat_izvestaj='SP-6'
and datum=tdatum_do;

if tkolku>0 then 
delete 
FROM stat_izvestai
where stat_izvestaj='SP-6'
and datum=tdatum_do;
end if; 

select max(stat_izvestaiid)  into tstat_izvestaiid from stat_izvestai;
insert  into stat_izvestai (stat_izvestaiid,	datecreated,	usercreated	,version,	datum,	stat_izvestaj,	vid_stavka) 
SELECT tstat_izvestaiid+stat_izvestaiid,current,6,0,tdatum_do,stat_izvestaj, vid_stavka  FROM stat_izvestai
where stat_izvestaj='SP-6'
and datum=tdo_datum;

-----analitika 

 create temp table sp6_analitika( grupa_sp1 VARCHAR(20),par_prod_kanalid int,  prod_kanal  VARCHAR(100) , broker_name  VARCHAR(100) ,bruto_premija dec,
 broj_polisi int , provizija dec ) ;
 
 
  insert into  sp6_analitika( grupa_sp1,par_prod_kanalid ,  prod_kanal   , broker_name   ,bruto_premija , broj_polisi  , provizija  ) 
select klasa,par_prod_kanalid,  prod_kanal,  broker_name , sum(bruto_premija) bruto_premija , sum(broj_polisi) broj_polisi , sum(provizija) provizija from (

select  case when po.par_prod_kanalid in (33,58) then '00'  else case when sap_risk_business[3,5]='21'  then sap_risk_business[3,5] else  sap_risk_business[7,8 ] end  end 
 klasa,po.par_prod_kanalid, k.desc_mk prod_kanal,  c.desc broker_name , sum(nvl(iznos_p,0)) bruto_premija , 0 broj_polisi,0 provizija 
from stavka s ,os_polisa p, os_ponuda po  , os_produkt pr, outer par_client  c , par_prod_kanal k 
where s.dokument[1,10] =p.polisa_broj_cel
and s.dokument[11,14]=p.polisa_pod_broj
and p.os_ponudaid=po.os_ponudaid
and po.os_produktid=pr.os_produktid
and po.broker_par_client=c.par_clientid
and po.par_prod_kanalid=k.par_prod_kanalid
and  s.dat_nalog between tod_datum_godina and tdatum_do
and  konto[1,3]='700'
and sap_risk_business is not null
group by 1 ,2,3,4
union 

select vrati_grupa_klasa(d.os_ponuda_detailid ) klasa,o.par_prod_kanalid, k.desc_mk prod_kanal,  c.desc broker_name ,0  bruto_premija,  count(distinct polisa_broj_cel ) broj_polisi,0 provizija 
from os_ponuda o, os_ponuda_detail d,  os_polisa p , outer par_client  c , par_prod_kanal k 
where o.os_ponudaid=d.os_ponudaid 
and o.os_ponudaid=p.os_ponudaid
and o.broker_par_client=c.par_clientid
and o.par_prod_kanalid=k.par_prod_kanalid                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
and p.datum_polisa between tod_datum_godina and tdatum_do
and o.par_statusid in (17,18) 
and o.par_prod_kanalid not  in (33,58)
and ponuda_podbroj=maxpodbroj_datum(o.ponuda_broj , p.polisa_broj, o.os_produktid, tdatum_do )
group by 1,2,3,4
union



select '00', o.par_prod_kanalid, k.desc_mk prod_kanal,  c.desc broker_name ,0 bruto_premija, count(distinct polisa_broj_cel ) broj_polisi,0 provizija 
from os_ponuda o, os_ponuda_detail d,  os_polisa p , outer par_client  c , par_prod_kanal k 
where o.os_ponudaid=d.os_ponudaid 
and o.os_ponudaid=p.os_ponudaid
and o.broker_par_client=c.par_clientid
and o.par_prod_kanalid=k.par_prod_kanalid                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
and p.datum_polisa between tod_datum_godina and tdatum_do
and o.par_statusid in (17,18) 
and o.par_prod_kanalid in (33,58)
and ponuda_podbroj=maxpodbroj_datum(o.ponuda_broj , p.polisa_broj, o.os_produktid, tdatum_do )
group by 1,2,3,4
union 
select case when x0.par_prod_kanalid in (33,58) then '00'  else case when vrati_grupa(x3.os_ponuda_detailid )='21'  
then vrati_grupa(x3.os_ponuda_detailid ) else  vrati_grupa_klasa(x3.os_ponuda_detailid ) end  end 
, x0.par_prod_kanalid, k.desc_mk prod_kanal,  c.desc broker_name ,0 bruto_premija, 0 broj_polisi ,sum(round(iznos_provizija*vrati_kurs(tdatum_do,'EUR'))) provizija    from 
  "viki".os_ponuda x0, 
  "viki".os_polisa x1, 
  "viki".os_aneks x2, 
  "viki".os_aneks_faktura x3, 
  "vesna".provizija_agent x4, 
  "vesna".provizija_agent_presmetka x5 ,
   outer par_client  c , par_prod_kanal k 
where (x1.os_ponudaid = x0.os_ponudaid) 
 AND (x3.os_aneks_fakturaid = x5.os_aneks_fakturaid )
 AND (x2.os_aneksid = x3.os_aneksid)
  AND (x2.os_polisaid = x1.os_polisaid)
 and x4.par_clientid = x0.broker_par_client
AND (x5.provizija_agentid = x4.par_provizija_agentid )
and x0.broker_par_client=c.par_clientid
and x0.par_prod_kanalid=k.par_prod_kanalid 
AND ( x4.par_provizijatipid NOT IN (56, 1350)    )
and pap_datumdo between tod_datum_godina and tdatum_do
 group by 1,2,3,4


) a
group by 1,2,3,4;
----analitika 
let i=0; 
foreach 
select case when par_prod_kanalid=33 then '200_'||ROW_NUMBER() over (order by par_prod_kanalid,	broker_name) 
  when par_prod_kanalid=58 then '300_'
    when par_prod_kanalid=62 and grupa_sp1='01' then '400(1)_1'
      when par_prod_kanalid=62 and grupa_sp1='02' then '400(2)_1'
       when par_prod_kanalid=62 and grupa_sp1='21' then '400(99)_1'
      when par_prod_kanalid=77 and grupa_sp1='01' then '100(1)'
      when par_prod_kanalid=77 and grupa_sp1='02' then '100(2)'
       when par_prod_kanalid=77 and grupa_sp1='21' then '100(99)' 
       when par_prod_kanalid=77 and grupa_sp1='00' then '100' 
       when par_prod_kanalid=62 and grupa_sp1='00' then '400' 
      when par_prod_kanalid=78 and grupa_sp1='00' then '9999' 
     when par_prod_kanalid=78 and grupa_sp1='01' then '9999(1)'
      when par_prod_kanalid=78 and grupa_sp1='02' then '9999(2)'
       when par_prod_kanalid=78 and grupa_sp1='21' then '9999-99'end ,
 grupa_sp1,	par_prod_kanalid,	prod_kanal,	broker_name,	bruto_premija,	broj_polisi,	provizija
 into tvid_stavka ,  tgrupa_sp1,	tpar_prod_kanalid,	tprod_kanal,	tbroker_name,	tbruto_premija,	tbroj_polisi,	tprovizija
 from  sp6_analitika
 
 
 if tpar_prod_kanalid=58 then 
 let i=i+1;
 let tvid_stavka =tvid_stavka||i;
 end if; 
 
 
 update  stat_izvestai set client_name=tbroker_name, kol101=tbroj_polisi,kol102=tbruto_premija,kol103 =nvl(tprovizija,0 )
where stat_izvestaj='SP-6'
and datum=tdatum_do
and vid_stavka =tvid_stavka;

end foreach;





---sp-8
/*
SELECT count(*) into tkolku
FROM stat_izvestai
where stat_izvestaj='SP-8'
and datum=tdatum_do;

if tkolku>0 then 
delete 
FROM stat_izvestai
where stat_izvestaj='SP-8'
and datum=tdatum_do;
end if; 

select max(stat_izvestaiid)  into tstat_izvestaiid from stat_izvestai;
insert  into stat_izvestai (stat_izvestaiid,	datecreated,	usercreated	,version,	datum,	stat_izvestaj,	vid_stavka) 
SELECT tstat_izvestaiid+stat_izvestaiid,current,6,0,tdatum_do,stat_izvestaj, vid_stavka  FROM stat_izvestai
where stat_izvestaj='SP-8'
and datum=tdo_datum;

 create temp table sp8_analitika( par_prod_kanalid int,  prod_kanal  VARCHAR(100) , broker_name  VARCHAR(100) , storno_polisi int,otkup int  ,kap_polisi int   ,
 storno_premija dec , otkup_premija dec ) ;

insert into sp8_analitika( par_prod_kanalid ,  prod_kanal  , broker_name   , storno_polisi ,otkup   ,kap_polisi   ,
 storno_premija  , otkup_premija  )

select par_prod_kanalid, prod_kanal,  broker_name ,  sum(storno_polisi) storno_polisi, sum(otkup) otkup ,sum(kap_polisi) kap_polisi,
 sum(storno_premija) storno_premija, sum(otkup_premija) otkup_premija 
from(
select o.par_prod_kanalid, k.desc_mk prod_kanal,  c.desc broker_name ,  count(distinct polisa_broj_cel ) storno_polisi, 0 otkup , 0 kap_polisi, 0 storno_premija, 0 otkup_premija
from os_ponuda o,  os_polisa p , outer par_client  c , par_prod_kanal k 
where o.os_ponudaid=p.os_ponudaid
and o.broker_par_client=c.par_clientid
and o.par_prod_kanalid=k.par_prod_kanalid                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
and o.datum_prekin between tod_datum_godina and tdatum_do
and o.par_polisa_statusid=1 
and ponuda_podbroj=maxpodbroj_datum(o.ponuda_broj , p.polisa_broj, o.os_produktid, tdatum_do )
group by 1,2,3
union 
select o.par_prod_kanalid, k.desc_mk prod_kanal,  c.desc broker_name ,  0 storno_polisi,count(distinct polisa_broj_cel ) otkup , 0 kap_polisi,0 storno_premija, 0 otkup_premija
from os_ponuda o,  os_polisa p , outer par_client  c , par_prod_kanal k 
where  o.os_ponudaid=p.os_ponudaid
and o.broker_par_client=c.par_clientid
and o.par_prod_kanalid=k.par_prod_kanalid                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
and p.datum_polisa between tod_datum_godina and tdatum_do
and o.par_statusid=21
and ponuda_podbroj=maxpodbroj_datum(o.ponuda_broj , p.polisa_broj, o.os_produktid, tdatum_do )
group by 1,2,3
union 
select o.par_prod_kanalid, k.desc_mk prod_kanal,  c.desc broker_name ,  0 storno_polisi,  0 otkup ,    count(distinct polisa_broj_cel ) kap_polisi,0 storno_premija, 0 otkup_premija 
from os_ponuda o,  os_polisa p , outer par_client  c , par_prod_kanal k 
where o.os_ponudaid=p.os_ponudaid
and o.broker_par_client=c.par_clientid
and o.par_prod_kanalid=k.par_prod_kanalid                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
and p.datum_polisa between tod_datum_godina and tdatum_do
and o.par_polisa_statusid=181 
and ponuda_podbroj=maxpodbroj_datum(o.ponuda_broj , p.polisa_broj, o.os_produktid, tdatum_do )
group by 1,2,3
union 
select o.par_prod_kanalid, k.desc_mk prod_kanal,  c.desc broker_name ,  0 storno_polisi, 0 otkup , 0 kap_polisi,
 0 storno_premija,sum( vratilikizn_steta(l_stetaid,'01.01.2024',tdatum_do)) otkup_premija
from os_ponuda o,  os_polisa p , outer par_client  c , par_prod_kanal k , l_steta l
where  o.os_ponudaid=p.os_ponudaid
and o.broker_par_client=c.par_clientid
and o.par_prod_kanalid=k.par_prod_kanalid 
and  o.os_ponudaid=p.os_ponudaid                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           
and     par_tip_stetaid=4                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           
and p.datum_polisa between tod_datum_godina and tdatum_do
and o.par_statusid=21 
and ponuda_podbroj=maxpodbroj_datum(o.ponuda_broj , p.polisa_broj, o.os_produktid, tdatum_do )
group by 1,2,3
union
select  x4.par_prod_kanalid, k.desc_mk prod_kanal,  c.desc broker_name , 0 storno_polisi, 0 otkup , 0 kap_polisi,
abs(sum(iznos_denari)) storno_premija,0 otkup_premija 

from 
  "viki".os_aneks_faktura x0, 
  "viki".os_aneks x1, 
  "viki".os_polisa x2, 
  "viki".fin_stavka x3, 
  "viki".os_ponuda x4,
   outer par_client  c , par_prod_kanal k 
where x0.os_aneksid = x1.os_aneksid
 AND (x2.os_polisaid = x1.os_polisaid)
  AND  x3.os_aneks_fakturaid = x0.os_aneks_fakturaid
  
 AND (x3.iznos_d IS NOT NULL)
 AND (x4.os_ponudaid = x2.os_ponudaid)
 and x4.broker_par_client=c.par_clientid
and x4.par_prod_kanalid=k.par_prod_kanalid 
 AND x3.f_rs= 'S'
 and   x3.dat_nalog  between  tod_datum_godina and tdatum_do
  group by 1,2,3
 

) a
group by 1,2,3;

let i=0;
foreach 
select 
case when par_prod_kanalid=33 then '200_'||rank() over (order by par_prod_kanalid,	broker_name) 
  when par_prod_kanalid=58 then '300_'
    when par_prod_kanalid=62  then '400(1)_1'
      when par_prod_kanalid=77  then '100'
      when par_prod_kanalid=78  then '9999' 
end ,
       par_prod_kanalid ,  prod_kanal  , broker_name   , storno_polisi ,otkup   ,kap_polisi   ,
 storno_premija  , otkup_premija
into         tpar_prod_kanalid ,  tprod_kanal  , tbroker_name   , tstorno_polisi ,totkup   ,tkap_polisi   ,
 tstorno_premija  , totkup_premija  
   from sp8_analitika 
 
 if tpar_prod_kanalid=58 then 
 let i=i+1;
 let tvid_stavka =tvid_stavka||i;
 end if; 
 

 update  stat_izvestai set client_name=tbroker_name, kol100=tstorno_polisi,kol101=totkup,kol102 =tkap_polisi,kol200=tstorno_premija, kol201=totkup_premija
where stat_izvestaj='SP-8'
and datum=tdatum_do
and vid_stavka =tvid_stavka; 
 
 end foreach;
*/
drop  table sp1_analitika ; 
drop  table sp1_kap_polisi ; 
drop  table sp1_otkup ; 
drop  table sp1_skl_dog; 
drop table sp1_bruto_premija; 
drop  table sp1_bruto_premija12 ; 
drop  table sp1_edin_premija ; 
drop  table sp1_ednokrat_premija ; 
drop table   sp2_br_steti;
drop table sp1_analitika_tar;
drop table sp1_analitika_tarifa;
drop table  sp6_analitika;
drop table  sp8_analitika;
--commit work;
return '1','Generiran e SP';

end function;