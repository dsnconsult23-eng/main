CREATE FUNCTION vesna.generiraj_pretarifiranje (tos_polisaid integer,

ntpar_periodid int8, 
ntperiod int,
ntpar_premijaid int8, 
ntpremija decimal(20,2),
tuser_id integer,
tdatum_pretarifiranje date,
tdatum_vaznost date)
returning integer,char(100);
{
procedurata vraka:

- kod na greska
1 ako se e ok i ako e izvrseno
-1 ako se pojavi nekoja neregularnost

- poraka poradi koja e nastanata greskata
}

define  dali_pregled,tpar_agentid,nrows,dali_odobril,t,tageplust,k , kolku, tgodini ,     tgodini_osiguruvanje,max_podbroj,den_sk, mesec_sk,kolku_isp int;
define tprist_starost,tperiod_osig,tos_produktid,godina_otkup int;
define gama,alfa,tkamatna_stapka,beta,nx_age, dx_age,nx_agek,a_age_k,nx_tageplust, dx_tageplust,mx_tageplust,ddx_tageplust,trx_t,aa dec;
define a_xt_kt,nx_agen,gp,db,d,dx_agen,mx_age,mx_agen,a_beta,gamma1,alfa1,a_doziv,a_mesano dec;
define SA_doziv,SA_mesano,cash_value_doz,SA,unit_cost, gp_doz,cash_value_mesano dec;
define mr_mesano,pred_presm_mr,gp_mesano,net_profit,a_x_n,a_x_k,mr_doz,alfa2,CV,mr_doz_predpresm,_otkup,platena_premija,comision,a_xt_nt dec;
define tusername char(30);
define tpol,tpromena_polisa,za_naredna_godina,tpol_brak char(1);
define tponuda_broj char(10);
define tponuda_podbroj,tpolisa_podbroj,tpar_nacin_plati char(3);
define ts_tar_gr,tos_produkt_tsid, dali_polisa,tosigurenik_par_client ,broj,tpar_polisa_promenaid,tvrska_os_ponudaid,pod_broj,tos_polisaid_stara,tos_ponudaid int;
define tpolisa_broj char(7);
define tdatum_ponuda,tgodisnica_aneks date;
define dali_proknizeno,dali_ima_aneks,tos_aneksid_posleden,terr,tpar_administrativni_trosid,max_broj,tos_polisaid1,terr1,dali_proknizeno_stavka int;
define  poraka,tporaka char(100);
define tcomision ,     tfaktor_zilimier ,     tzilimer_rezerva ,tneto_rezerva, tkazna_otkup,totkupna_vred,tosigur_vred,tmatematcka_rezerva decimal;
define tpar_trosoci_produkt char(3);
define l1,l2,l3,l4,edin_bruto_premija,neto_premija,ddx_agen,ddx_age,tkazna_otkup_kap,discont,tocka4,tkap_premija, tkapitalizirana_vred,tpreth_premija decimal;
define tprodukt char(4);
define tkoja_godina_pretarf,tos_polisaid_nova,toos_aneks_fakturaid,toos_aneks_fakturaid1 int;
define tpolisa_pod_broj char(3);
define tskadenca_datum_od,odreden_datum,odreden_datum_sk,tdatum_plateno date;
define tpar_premijaid,tpar_periodid,tperiod int8; 
define tpremija decimal(20,2);
define tpar_Tablica_SmrtId int;
define tos_produkt_uplataid,tpar_nacin_platiid,nb,ageb,dali_pretarif,ti,tpar_statusid, tvrska_os_ponudaid_n int;
define mx_tagebplust, mx_tagenb,ddx_tagenb,tneto_rezerva_brak,totkupna_vred_brak,taxt_kt_brak,nx_tagenb,nx_agebplust,ddx_agebplust,rx_age,rx_agek,rx_agen,rx_tageplust,tq_x_pr dec;
define  tedin_neto_premija_brak, tedin_bruto_premija_brak, tcom_brak, tedin_osig_suma_brak, SAb ,mx_tageb,nx_ageb,ddx_ageb,tax_n_brak,a_xt_nt1 dec;
define tv_0,tp_0,tl_a_x_nt,tv_x,tp_x,tq_x,ti_x,gtl_a_x_nt,axn4,alpha2,AExn,axk,kaxn_k,alpha1,nesreken_slucaj,bxn_nezgoda_deca,deca,tinvest_premija decimal ;
define Osxn,tvx_net,tqi_x,	nv_x,np_x,tKFt,	tRkft,	tRedt,ga_xt_nt,tvx_zilimer,tvwk_x,nqi_x,tdelta, tdopl_deca,s17,s11,tosig_suma,tpremija_den,tprocent_smrt decimal;
define tbr_osig_lica,tkolku_novi,tpar_valutaid,tos_produkt_invest_fondid,tos_produkt_invest_smrtid,tos_tipproduktid,tbr_rati,trata int;
define tpar_polisa_promena varchar(5);
define tdatecrated,tdatumraganje,tskadenca_datum_do date;
define tpremija_za_rata,tpremija_smrt,talfa_trosok ,tbeta_trosok , edin_bruto_premija_doz,    tgama_trosok ,     tpremija_invest ,     tucestvo_trosoci ,     tucestvo_invest,g_smrt,tdelta_dopl,a_xt_nminust dec;
define tstatusid,tfaktura_int int8;
define tinv_clientid int8;
define tpolisa_broj1 varchar(10);
define tfaktura_broj  varchar(20);
define tgodina_kap varchar(4);
define izminat_period_meseci,izminati_celi_godini,izminati_meseci,trazlika integer;



on exception
ROLLBACK WORK;
return -1,'НАСТАНАТА Е ГРЕШКА';
end exception;

set debug file to "err_generiraj_pretarifiranje.sql";
trace on;

set isolation to dirty read;

BEGIN WORK;

let tpar_premijaid=ntpar_premijaid;
let tpar_periodid=ntpar_periodid;
let tperiod=ntperiod;
let tpremija=ntpremija;

if ntpar_periodid in (621,623)  then
let  tpar_premijaid=ntpar_periodid;
let  tpremija=ntperiod;
let tpar_periodid=0;
let tperiod=0;
end if;
select os_ponudaid into tos_ponudaid
from os_polisa
where os_polisaid=tos_polisaid;


select ponuda_broj, ponuda_podbroj ,os_produktid ,ponuda_podbroj,skadenca_datum_od,day(skadenca_datum_od), month(skadenca_datum_od),datum_ponuda,os_produkt_uplataid
into tponuda_broj, tponuda_podbroj,tos_produktid,max_podbroj,tskadenca_datum_od, den_sk, mesec_sk,tdatum_ponuda,tos_produkt_uplataid
from os_ponuda where os_ponudaid=tos_ponudaid;

if tponuda_podbroj='000' then
select count(*) into dali_polisa from os_ponuda where ponuda_broj=tponuda_broj and os_produktid=tos_produktid  ;  


end if; 

--UL --10.12.2020
select os_tipproduktid 		into tos_tipproduktid
from  os_produkt         where os_produktid=tos_produktid;
select otp_code  into tprodukt from os_tipprodukt 
where os_tipproduktid=tos_tipproduktid ;
if tprodukt='UL'   then        
if tpar_premijaid=0 then
select nvl(iznos_premija,0)
into tpremija
from os_ponuda_detail
where os_ponudaid=tos_ponudaid
and ts_vid_rizik='Or'; 
end if;
execute  procedure ul_pretarifiranje_period (tos_polisaid ,tpar_premijaid ,tpremija ,tpar_periodid,tperiod , tuser_id ,tdatum_pretarifiranje,tdatum_vaznost )
into terr1,tos_polisaid1,tporaka;
if terr1<>-1 then
let tos_polisaid_nova=terr1;
commit work;
return  tos_polisaid_nova,'ПОЛИСАТА   Е       ИЗГЕНЕРИРАНА';
end if;


if terr1=-1 then
ROLLBACK WORK;
return -1,tporaka;
end if;
end if; 
--Ul-10.12.2020





select par_nacin_platiid into tpar_nacin_platiid
from os_produkt_uplata
where os_produkt_uplataid=tos_produkt_uplataid;

select par_nacin_plati,br_rati
into tpar_nacin_plati, tbr_rati
from par_nacin_plati
where par_nacin_platiid=tpar_nacin_platiid;

select username into tusername from adm_user
where userid=tuser_id;

let tkoja_godina_pretarf=year(tdatum_vaznost) - year(tskadenca_datum_od);

let odreden_datum=date(ADD_MONTHS(tskadenca_datum_od,3)+tkoja_godina_pretarf units  year);

let odreden_datum_sk=date(tskadenca_datum_od+tkoja_godina_pretarf units  year);

if tdatum_pretarifiranje>= tdatum_vaznost then 

let tkoja_godina_pretarf=tkoja_godina_pretarf+1;

end if;

let tfaktura_broj='';
execute procedure vrati_polisa(tos_polisaid) into tpolisa_broj1;

foreach select  first 1 vrati_godina(par_yearid),vrati_faktura_broj(os_aneks_fakturaid) ,vrati_faktura_brojint((os_aneks_fakturaid))
into tgodina_kap, tfaktura_broj ,tfaktura_int
from  fin_stavka,os_ponuda p, os_produkt o , os_polisa l
where l.os_polisaid=fin_stavka.os_polisaid and  
o.os_produktid=p.os_produktid
and l.os_ponudaid=p.os_ponudaid
and  o.sifra_polisa||'/'||l.polisa_broj=tpolisa_broj1
group  by 1,2,3
having sum(nvl(iznos_d,0)- nvl(iznos_p,0))=0
order by 1 desc ,3 desc
end foreach;

select  first 1 data_valuta   into tdatum_plateno

from os_aneks_faktura x0 ,os_aneks x1 , par_year x2
where x0.os_aneksid = x1.os_aneksid
and x2.par_yearid=x1.par_yearid 
and upper (((x1.os_aneks || '/' ) || trim(par_year )) ||'-'|| x0.rata )   =tfaktura_broj;

let izminat_period_meseci=(YEAR(tdatum_plateno)-YEAR(tskadenca_datum_od))*12+MONTH(tdatum_plateno)-MONTH(tskadenca_datum_od);
let izminati_celi_godini=trunc(izminat_period_meseci/12);
let izminati_meseci=izminat_period_meseci-12*izminati_celi_godini;

let tkoja_godina_pretarf=izminati_celi_godini;


if tpar_periodid<>0  and tpar_premijaid>=0  then 
select polisa_broj ,polisa_pod_broj+1,os_polisaid
into tpolisa_broj, max_broj,tos_polisaid_stara
from os_polisa
where os_ponudaid=tos_ponudaid;


if tpar_premijaid=0 then
select nvl(iznos_premija,0)
into tpremija
from os_ponuda_detail
where os_ponudaid=tos_ponudaid
and ts_vid_rizik='Or'; 
end if;
if tpolisa_broj1 like '28/%'  then 
execute  procedure ul_pretarifiranje_period (tos_polisaid ,tpar_premijaid ,tpremija ,tpar_periodid,tperiod , tuser_id ,tdatum_pretarifiranje,tdatum_vaznost )
 
into terr1,tos_polisaid1,tporaka;
else 
execute  procedure generiraj_pretarifiranje_period (tos_polisaid ,tpar_premijaid ,tpremija ,tpar_periodid,tperiod , tuser_id ,tdatum_pretarifiranje,tdatum_vaznost )
 
into terr1,tos_polisaid1,tporaka;
end if;
if terr1<>-1 then
let tos_polisaid_nova=terr1;
end if;


if terr1=-1 then
ROLLBACK WORK;
return -1,tporaka;
end if;
end if;


if tpar_premijaid<>0  and tpar_periodid=0 then 


if nvl(tpremija,0) =0 then 
ROLLBACK WORK;
return -1,'Mora da vnesete premija ';
end if;
---- spored datum na pretarifiranje ----treba da se odluci za koja godina ke se pravi pretarifiranjeto ------
select nvl(iznos_premija,0)
into  tpreth_premija
from os_ponuda_detail
where os_ponudaid=tos_ponudaid
and ts_vid_rizik='Or';

----delot da se prekopira os_ponuda ---------
let tos_polisaid_nova=sq_os_ponudaid.nextval;
insert into 'viki'.os_ponuda(     os_ponudaid ,     datechanged ,     datecreated ,
userchanged ,     usercreated ,     version ,     os_produktid ,     ponuda_broj ,     ponuda_podbroj ,
vid_ponuda ,     datum_ponuda ,     par_filijalaid ,     par_agentid ,     par_prod_kanalid ,
broker_par_client ,     posrednik_par_client ,     skadenca_datum_od ,     skadenca_datum_do ,
valuta ,     dogovoruvac_par_client ,     osigurenik_par_client ,     par_profesijaid ,
prist_starost ,     period_osig ,     traenje_uplata ,     pol ,
vk_iznos_premija ,     vk_iznos_premija_den ,     prva_uplata ,     prva_uplata_den ,
datum_prva_uplata ,     abnormal_rizik ,     datum_prekin ,     pricina_prekin ,
br_osig_lica ,     par_statusid ,     kreditiranje ,
klasa ,     tr_desc ,     os_produkt_uplataid ,    
par_tip_platiid,par_polisa_promenaid,vrska_os_ponudaid,par_polisa_promenaid1,datum_proverka,datum_odobruvanje,polisa)
select
tos_polisaid_nova, today, tdatum_pretarifiranje, tusername,tusername,0,
os_produktid ,     ponuda_broj ,   prefill (max_podbroj+1,'0',3)  ,     vid_ponuda ,
datum_ponuda ,     par_filijalaid ,     par_agentid ,     par_prod_kanalid ,
broker_par_client ,     posrednik_par_client ,     skadenca_datum_od ,     skadenca_datum_do ,
valuta ,     dogovoruvac_par_client ,     osigurenik_par_client ,     par_profesijaid ,
prist_starost ,      period_osig ,     traenje_uplata ,     pol ,     vk_iznos_premija ,
vk_iznos_premija_den ,     prva_uplata ,     prva_uplata_den ,     datum_prva_uplata ,
abnormal_rizik ,       datum_prekin ,     pricina_prekin ,     br_osig_lica ,
par_statusid ,     kreditiranje ,     klasa ,     tr_desc ,     os_produkt_uplataid ,
par_tip_platiid,tpar_premijaid, tos_ponudaid,tpar_premijaid,tdatum_pretarifiranje,tdatum_pretarifiranje,'t'
from os_ponuda
where os_ponudaid=tos_ponudaid;

let nrows = 0;
let nrows = DBINFO('sqlca.sqlerrd2');
if nrows = 0 then
ROLLBACK WORK;
return                                 '-1','ПОНУДАТА НЕ Е       АЖУРИРАНА';
end if; 
select count(*) into kolku 
from os_ponuda_detail
where os_ponudaid=tos_ponudaid
and ts_vid_rizik='Dr' ;
if kolku>0 then
insert into os_ponuda_detail(     os_ponuda_detailid ,     datechanged ,     datecreated ,
userchanged ,     usercreated ,     version ,     dneven_nadmoest ,     edinecna_premija ,
iznos_premija ,     iznos_premija_den ,     kolicina ,     osig_suma ,     preth_premija ,
preth_premija_den ,     tablica_drid ,     ts_vid_rizik ,     par_statusid ,
os_ponudaid ,     os_produkt_ts_id ,     par_kursid ,     ts_tar_podgrupaid ,     os_produktid	,
ar_iznos_den,	ar_iznos,	ar_tip,os_produkt_zdravstvenoid)
select
sq_os_ponuda_detailid.nextval, today, today, tusername,tusername,0,
dneven_nadmoest ,     edinecna_premija ,     iznos_premija ,     iznos_premija_den ,
kolicina ,     osig_suma ,     preth_premija ,     preth_premija_den ,     tablica_drid ,
ts_vid_rizik ,     par_statusid ,     tos_polisaid_nova ,     os_produkt_ts_id ,     par_kursid ,
ts_tar_podgrupaid ,     os_produktid ,ar_iznos_den,	ar_iznos,	ar_tip,os_produkt_zdravstvenoid
from os_ponuda_detail
where os_ponudaid=tos_ponudaid
and ts_vid_rizik='Dr';
let nrows = 0;
let nrows = DBINFO('sqlca.sqlerrd2');
if nrows = 0 then
ROLLBACK WORK;
return                       '-1','ПОНУДАТА НЕ Е               АЖУРИРАНА';
end if; 

end if;	
insert into os_ponuda_detail(     os_ponuda_detailid ,     datechanged ,     datecreated ,
userchanged ,     usercreated ,     version ,     dneven_nadmoest ,     edinecna_premija ,
iznos_premija ,     iznos_premija_den ,     kolicina ,     osig_suma ,     preth_premija ,
preth_premija_den ,     tablica_drid ,     ts_vid_rizik ,     par_statusid ,
os_ponudaid ,     os_produkt_ts_id ,     par_kursid ,     ts_tar_podgrupaid ,     os_produktid	,
ar_iznos_den,	ar_iznos,	ar_tip)
select
sq_os_ponuda_detailid.nextval, today, today, tusername,tusername,0,
dneven_nadmoest ,     edinecna_premija ,     tpremija ,    konverzija(tdatum_pretarifiranje, tpremija, 'EUR','MKD') ,
kolicina ,     osig_suma ,     preth_premija ,     preth_premija_den ,     tablica_drid ,
ts_vid_rizik ,     par_statusid ,     tos_polisaid_nova ,     os_produkt_ts_id ,     par_kursid ,
ts_tar_podgrupaid ,     os_produktid ,ar_iznos_den,	ar_iznos,	ar_tip
from os_ponuda_detail
where os_ponudaid=tos_ponudaid
and ts_vid_rizik='Or';
let nrows = 0;
let nrows = DBINFO('sqlca.sqlerrd2');
if nrows = 0 then
ROLLBACK WORK;
return                                                   '-1','ПОНУДАТА НЕ Е     АЖУРИРАНА';
end if; 

select count(*) into kolku 
from os_ponuda_hobi
where os_ponudaid=tos_ponudaid;
if kolku>0 then
insert into os_ponuda_hobi(     os_ponuda_hobiid ,     datechanged ,     datecreated ,
userchanged ,     usercreated ,     version ,     par_statusid ,     os_ponudaid ,     par_hobiid
)
select sq_os_ponuda_hobiid.nextval, today, today, tusername,tusername,0,     
par_statusid ,
tos_polisaid_nova ,
par_hobiid
from os_ponuda_hobi
where os_ponudaid=tos_ponudaid;

let nrows = 0;
let nrows = DBINFO('sqlca.sqlerrd2');
if nrows = 0 then
ROLLBACK WORK;
return               '-1','ПОНУДАТА НЕ   Е                       АЖУРИРАНА';
end if; 
end if;		
select count(*) into kolku_isp 
from os_ponuda_isplata
where os_ponudaid=tos_ponudaid;
if kolku_isp>0 then
insert into os_ponuda_isplata(
os_ponuda_isplataid ,     datechanged ,     datecreated ,     userchanged ,     usercreated ,
version ,     br_rati ,     datum_do ,     godini_do ,     datum_od ,     par_statusid ,
os_ponudaid ,     os_produkt_isplataid ,     tr_desc,osig_suma) 
select sq_os_ponuda_hobiid.nextval, today, today, tusername,tusername,0,    
br_rati ,     datum_do ,     godini_do ,     datum_od ,     par_statusid ,
tos_polisaid_nova ,     os_produkt_isplataid ,
tr_desc,osig_suma
from 'vesna'.os_ponuda_isplata
where os_ponudaid=tos_ponudaid;

let nrows = 0;
let nrows = DBINFO('sqlca.sqlerrd2');
if nrows = 0 then
ROLLBACK WORK;
return                 '-1','ПОНУДАТА НЕ Е                   АЖУРИРАНА';
end if; 
end if;
select count(*) into kolku 
from os_ponuda_korisnici
where os_ponudaid=tos_ponudaid;
if kolku>0 then
insert into 'vesna'.os_ponuda_korisnici(     os_ponuda_korisniciid ,     datechanged ,
datecreated ,     userchanged ,     usercreated ,     version ,
os_ponudaid ,     par_clientid ,     tip_osigiguruvawe ,     par_srodstvoid ,
par_statusid)
select sq_os_ponuda_korisnici.nextval, today, today, tusername,tusername,0,  
tos_polisaid_nova ,     par_clientid ,     tip_osigiguruvawe ,     par_srodstvoid ,
par_statusid from os_ponuda_korisnici
where os_ponudaid=tos_ponudaid;
end if;		
let nrows = 0;
let nrows = DBINFO('sqlca.sqlerrd2');
if nrows = 0 then
ROLLBACK WORK;
return                                                           '-1','ПОНУДАТА НЕ Е       АЖУРИРАНА';
end if; 
select count(*) into kolku 
from os_ponuda_prasalnik
where os_ponudaid=tos_ponudaid;
if kolku>0 then

insert into os_ponuda_prasalnik(     os_ponuda_prasalnikid ,     datechanged ,
datecreated ,     userchanged ,     usercreated ,     version ,     datum_odgovor ,
odgovor ,     par_statusid ,     os_ponudaid ,     os_produkt_prasalnikid ,     tr_desc
)select sq_os_ponuda_prasalnikid.nextval, today, today, tusername,tusername,0, 
datum_odgovor ,     odgovor ,     par_statusid ,     tos_polisaid_nova ,
os_produkt_prasalnikid ,     tr_desc
from 'vesna'.os_ponuda_prasalnik
where os_ponudaid=tos_ponudaid;

let nrows = 0;
let nrows = DBINFO('sqlca.sqlerrd2');
if nrows = 0 then
ROLLBACK WORK;
return                                         '-1','ПОНУДАТА     НЕ Е                  АЖУРИРАНА';
end if; 
end if;

select count(*) into kolku 
from os_ponuda_osigurenici
where os_ponudaid=tos_ponudaid;
if kolku>0 then

insert into os_ponuda_osigurenici(     os_ponuda_osigureniciid ,     datechanged ,
datecreated ,     userchanged ,     usercreated ,     version ,     os_ponudaid ,
par_clientid ,     datum_pocetok ,     datum_zavrsetok ,     par_statusid) 

select sq_os_ponuda_prasalnikid.nextval, today, today, tusername,tusername,0, 
tos_polisaid_nova,  par_clientid ,     datum_pocetok ,     datum_zavrsetok ,
par_statusid
from os_ponuda_osigurenici
where os_ponudaid=tos_ponudaid;

let nrows = 0;
let nrows = DBINFO('sqlca.sqlerrd2');
if nrows = 0 then
ROLLBACK WORK;
return '-1','ПОНУДАТА НЕ   Е     АЖУРИРАНА';
end if; 
end if;



update os_ponuda set polisa='t'
where os_ponudaid=tos_ponudaid;

-----the end copy ponuda 

let d=0; --Unit Costs (d) ne znam sto znaci i kaj referira sega za sega ke ja ostavam 0
let unit_cost=0;
let alfa2=40;

if (tos_produktid=60) or  (tos_produktid=622)  then 
let alfa2=40;
end if;

if tos_produktid=141 then 
let alfa2=35;
end if;
select prist_starost,period_osig,osigurenik_par_client,os_produktid ,traenje_uplata, ponuda_broj, ponuda_podbroj,par_polisa_promenaid,vrska_os_ponudaid,datum_ponuda,skadenca_datum_od
into tprist_starost,tperiod_osig,tosigurenik_par_client,tos_produktid,k , tponuda_broj, tponuda_podbroj,tpar_polisa_promenaid,tvrska_os_ponudaid,tdatum_ponuda,tskadenca_datum_od
from os_ponuda
where os_ponudaid=tos_polisaid_nova;
select godina into godina_otkup
from  os_produkt_otkup
where os_produktid=tos_produktid;


select produkt into tprodukt
from  os_produkt
where os_produktid=tos_produktid;


select pol into tpol
from par_client
where par_clientid=tosigurenik_par_client;

select polisa_broj ,polisa_pod_broj+1,os_polisaid
into tpolisa_broj, max_broj,tos_polisaid_stara
from os_polisa
where os_ponudaid=tos_ponudaid;
let tpolisa_pod_broj=prefill (max_broj,'0',3) ;


-- let tkoja_godina_pretarf=year(tdatum_pretarifiranje) - year(tskadenca_datum_od);

-------
---tuka delot ako e dozvolena promena na polisa so podbroj 001Slagjana 26.02.2013

let tos_polisaid1=sq_os_polisaid.nextval;
insert into os_polisa(os_polisaid,datechanged ,datecreated,userchanged,usercreated ,
version,polisa_broj,polisa_pod_broj,os_ponudaid,par_statusid,status_polisa,datum_polisa)
values (tos_polisaid1, today, today, tusername,tusername,0,tpolisa_broj, tpolisa_pod_broj
, tos_polisaid_nova,1,'K',today);
let nrows = 0;
let nrows = DBINFO('sqlca.sqlerrd2');
if nrows = 0 then
ROLLBACK WORK;
return '-1','ПОЛИСАТА НЕ Е АЖУРИРАНА';
end if;
select administrativni_tros,akvizacioni_tros,kamatna_stapka,inkaso_tros,par_administrativni_trosid,unit_cost_d

into gama,alfa,tkamatna_stapka,beta,tpar_administrativni_trosid,d
from os_produkt
where os_produktid=tos_produktid;


select administrativni_tros,akvizacioni_tros,kamatna_stapka,inkaso_tros,par_Tablica_SmrtId
into gama,alfa,tkamatna_stapka,beta,tpar_Tablica_SmrtId
from os_produkt_ts
where os_produktid=tos_produktid
and ts_vid_rizik='Or'
and ((tdatum_ponuda between datum_od and datum_do) or (tdatum_ponuda >=datum_od and datum_do is null));	

select par_trosoci_produkt into tpar_trosoci_produkt from par_trosoci_produkt 
where par_trosoci_produktid=tpar_administrativni_trosid;

foreach    select tp.ts_tar_podgrupaid  into ts_tar_gr
from ts_klasa k,ts_tarifa t, ts_tar_grupa tg, ts_tar_podgrupa tp
where  k.ts_klasaid=t.ts_klasaid
and tg.ts_tarifaid=t.ts_tarifaid
and tp.ts_tar_grupaid=tg.ts_tar_grupaid
and k.klasa||t.tarifa||tg.tar_grupa ='190101'
select count(*)   into kolku 
from os_produkt_ts
where ts_tar_podgrupaid=ts_tar_gr
and os_produktid=tos_produktid;
if kolku>0 then
select os_produkt_tsid  into tos_produkt_tsid  from os_produkt_ts
where ts_tar_podgrupaid=ts_tar_gr
and os_produktid=tos_produktid;
--   if tos_produkt_tsid is null  then
--            ROLLBACK WORK;
--  return '-1','ВО ПРОДУКТОТ       МОРА ДА       ИМАТЕ         ДЕФИНИРАНО       МЕШАНО                             ОСИГУРУВАЊЕ';
--        end if;

select os_polisaid
into tos_polisaid
from os_polisa
where os_ponudaid=tos_polisaid_nova;

select nvl(iznos_premija,0)
into gp
from os_ponuda_detail
where os_ponudaid=tos_polisaid_nova
and os_produkt_ts_id=tos_produkt_tsid;
end if;
end foreach; 
if gp=0  then
ROLLBACK WORK;
return '-1','ВО ПРОДУКТОТ МОРА ДА ИМАТЕ                     ДЕФИНИРАНО МЕШАНО ОСИГУРУВАЊЕ';
end if;

select nx,dx,mx ,ddx,rx
into nx_age, dx_age,mx_age,ddx_age,rx_age

from  tablica_komut_br
where godini=tprist_starost
and pol=tpol
and kamatna_stapka=tkamatna_stapka
and par_Tablica_SmrtId=tpar_Tablica_SmrtId;
select nx,rx
into nx_agek,rx_agek
from  tablica_komut_br
where godini=tprist_starost+k
and pol=tpol
and kamatna_stapka=tkamatna_stapka
and par_Tablica_SmrtId=tpar_Tablica_SmrtId;
select nx ,dx,mx,ddx,rx
into nx_agen,dx_agen,mx_agen,ddx_agen,rx_agen
from  tablica_komut_br
where godini=tprist_starost+tperiod_osig
and pol=tpol
and kamatna_stapka=tkamatna_stapka
and par_Tablica_SmrtId=tpar_Tablica_SmrtId;
let a_age_k=(nx_age- nx_agek)/dx_age;
let a_x_n = (nx_age- nx_agen)/dx_age;

if tpar_trosoci_produkt ='002' then ----tuka po staro ---promil za OS 03.06.2014Slagjana 

---sheet SA-----od kalkulatorot

let platena_premija=gp*k;
let platena_premija=gp*k;
---- sega za sega ke go ostavam fiksno otkako ke se resi  so provizijata sifrarnik
if tosigurenik_par_client is null then 
let comision=(platena_premija*1.5/100)+(platena_premija*1/100)+(platena_premija*0.5/100)+(platena_premija*0.5/100);
else
let comision=(platena_premija*3.30/100)+(platena_premija*1.60/100)+(platena_premija*1/100)+(platena_premija*0.60/100);
end if;
---     let cash_value_mesano=round((((mx_age-mx_agen)/dx_age+dx_agen/dx_age)*SA)+(alfa/1000*SA)+(gama/1000*SA*a_x_n));
--      let gp_mesano=round((cash_value_mesano/(a_x_k*(1-beta/100)))+(unit_cost/(1-beta/100)));
let cash_value_mesano=gp * ((a_age_k*(1-beta/100)));
let SA=round(((cash_value_mesano)-(comision))/(((mx_age-mx_agen)/dx_age+dx_agen/dx_age) +(gama/1000*a_x_n)));
let alfa=round((comision/SA)*1000,2);


let db=d/(1-(beta/100));
let a_beta=(1-(beta/100))*a_age_k;
let gamma1= (gama/1000)*a_x_n;
let alfa1=alfa/1000;
let a_doziv=dx_agen/dx_age;
let a_mesano= (mx_age-mx_agen)/dx_age;
let SA_doziv=((GP-db)*a_beta)/(a_doziv+gamma1+alfa1);
let SA_mesano=((GP-db)*a_beta)/(a_doziv+gamma1+alfa1+a_mesano);
let SA=SA_mesano;
-------------end sheet SA
---sheet Output -------
let t=0;
while t<=tperiod_osig
let tageplust=tprist_starost+t;

select nx,dx ,mx
into nx_tageplust, dx_tageplust,mx_tageplust
from  tablica_komut_br
where godini=tageplust
and pol=tpol
and kamatna_stapka=tkamatna_stapka
and par_Tablica_SmrtId=tpar_Tablica_SmrtId;
if t<k then
let a_x_k=a_age_k;
else
let a_x_k=0;
end if;
if a_x_k=0 then
let a_xt_kt=0 ;
else
let a_xt_kt=(nx_tageplust- nx_agen)/dx_tageplust;
end if;
if t<tperiod_osig then
let a_x_n = (nx_age- nx_agen)/dx_age;
else
let a_x_n=0;
end if;
if t=tperiod_osig then
let cash_value_doz=0;
let cash_value_mesano=0;
else
let cash_value_doz=round(((dx_agen/dx_age)*SA)+(alfa/1000*SA)+(gama/1000*SA*a_x_n));
let cash_value_mesano=round((((mx_age-mx_agen)/dx_age+dx_agen/dx_age)*SA)+(alfa/1000*SA)+(gama/1000*SA*a_x_n));
---let cash_value_mesano=((((mx_age-mx_agen)/(dx_age+dx_agen))/dx_age)*SA)+(alfa/1000*SA)+(gama/1--000*SA*a_x_n);
end if;
if a_x_n=0 then
let gp_doz=0;
let gp_mesano=0;
else

if   a_x_k=0 then
let gp_doz=0;
let gp_mesano=0;
else 
let gp_doz=round((cash_value_doz/(a_x_k*(1-beta/100)))+(unit_cost/(1-beta/100)));
let gp_mesano=round((cash_value_mesano/(a_x_k*(1-beta/100)))+(unit_cost/(1-beta/100)));
end if;	
end if;
if  gp_doz = 0 then  let mr_doz_predpresm=0; else
let mr_doz_predpresm=((((dx_agen/dx_age)*SA)+(alfa2/1000*SA))/a_x_k)*a_xt_kt;  end if;
--let mr_doz=((dx_agen/dx_tageplust*SA)- (dx_agen/dx_age*SA)+(alfa2/1000*SA))/a_x_k;
let mr_doz=round((dx_agen/dx_tageplust*SA)- mr_doz_predpresm);
if gp_mesano=0 then
let pred_presm_mr =0;
else


--      let pred_presm_mr=((((mx_age-mx_agen)/dx_age+dx_agen/dx_age)*SA+(alfa2/1000)*SA)/a_x_k);
let pred_presm_mr=((((mx_age-mx_agen)/dx_age+dx_agen/dx_age)*SA+(alfa2/1000)*SA)/a_x_k)*a_xt_kt;
end if;
let mr_mesano=round((((mx_tageplust -mx_agen)/dx_tageplust+dx_agen/dx_tageplust)*SA)- pred_presm_mr);
--let mr_mesano=((((mx_age -mx_agen)/(dx_tageplust+dx_agen))/dx_tageplust)*SA)- pred_presm_mr;
--      let mr_mesano=round((((mx_age -mx_agen)/dx_age+dx_agen/dx_age)*SA)- pred_presm_mr);
--      let mr_mesano=round((((mx_age -mx_agen)/dx_tageplust+dx_agen/dx_tageplust)*SA)- pred_presm_mr);
if mr_mesano<0 then
let CV=0;
else
let cv=mr_mesano*power((1+tkamatna_stapka/100),(tperiod_osig-t));
if t=0 then
let net_profit=((((mx_age -mx_agen)/(dx_age+dx_agen))/dx_age)*SA)/a_xt_kt;
end if;
end if;
if t<=godina_otkup then
let _otkup=0;
else
let _otkup=mr_mesano;
end if;


----vo os_polisa_pretarifiranje se insertiraat site vrednosti od Shetot Output
insert  into os_polisa_pretarifiranje ( os_polisa_pretarifiranjeid ,datechanged,datecreated ,userchanged ,usercreated ,
version,os_polisaid,godini,godini_osiguruvanje,ax_k ,axt_kt,ax_n,cash_value_doz,gross_premium_doz,
matematcka_rezerva_doz,profit_doz,gross_premium,profit_Participation,
otkupna_vred,osigur_vred,kapitalizirana_vred,matematcka_rezerva,par_statusid,tip_promena,opis )
values
(sq_os_polisa_pretarifiranje.nextval, today, today, tusername,tusername,0, tos_polisaid1,tageplust,t,a_x_k,a_xt_kt,a_x_n,
cash_value_doz, gp_doz,mr_doz,0,gp_mesano,0, _otkup,cash_value_mesano,round(cv),round(mr_mesano),1,1,'ПРОМЕНЕТА ПОЛИСА - дел кој што продолжува да се плаќа');
let nrows = 0;
let nrows = DBINFO('sqlca.sqlerrd2');
if nrows = 0 then
ROLLBACK WORK;
return                                         '-1','ПОЛИСА               ДЕТАИЛ НЕ Е                           АЖУРИРАНА';
end if;
let t=t+1;
end while;

end if;	
-------------
-------------

if tpar_trosoci_produkt ='003' then ----tuka po novo ---% za GP 03.06.2014 Slagjana 

select lx into l1
from tablica_smrt
where godini=tprist_starost
and pol=tpol
and kamatna_stapka=tkamatna_stapka
and par_Tablica_SmrtId=tpar_Tablica_SmrtId;

select lx into l2
from tablica_smrt
where godini=tprist_starost+1
and pol=tpol
and kamatna_stapka=tkamatna_stapka
and par_Tablica_SmrtId=tpar_Tablica_SmrtId;


select lx into l3
from tablica_smrt
where godini=tprist_starost+2
and pol=tpol
and kamatna_stapka=tkamatna_stapka
and par_Tablica_SmrtId=tpar_Tablica_SmrtId;
select lx into l4
from tablica_smrt
where godini=tprist_starost+3
and pol=tpol
and kamatna_stapka=tkamatna_stapka
and par_Tablica_SmrtId=tpar_Tablica_SmrtId;

let a_mesano= (mx_age-mx_agen+ddx_agen)/ddx_age;---Ax,n
let a_age_k=(nx_age- nx_agek)/ddx_age;
let a_x_n = (nx_age- nx_agen)/ddx_age;
let neto_premija=a_mesano/a_age_k;--neto premija
let discont=1/(1+tkamatna_stapka/100);
let comision= 3.30/100+(1.60/100*l2/l1*discont)+(1/100*l3/l1*pow(discont,2))+(0.60/100*l4/l1*pow(discont,3));
let db=comision/a_age_k; 
---**
IF tpar_nacin_plati<>'005' then

let db=comision/a_age_k; --alfa
else

let db=0.065; --alfa

let gama=1;

end if;


---**
let gamma1= (gama/100)*(a_x_n/a_age_k);
let edin_bruto_premija=(db+neto_premija)/(1-gamma1);
--**
if k=1 then

let neto_premija=a_mesano;

let edin_bruto_premija=(mx_age-mx_agen+ddx_agen+db*ddx_age)/(ddx_age-(gama/100)*(nx_age-nx_agen));

else

let edin_bruto_premija=(db+neto_premija)/(1-gamma1);

let edin_bruto_premija=(db+neto_premija)/(1-gamma1);

end if;

if tprodukt='ФУ'  or tprodukt='ФЗ' then


if k=1 then--20.09.2017 promena

let db=0.065; --alfa

let gama=1;

let edin_bruto_premija=(ddx_agen+db*ddx_age)/(ddx_age-(gama/100)*(nx_age-nx_agen)-(mx_age-mx_agen));

else

let edin_bruto_premija=(ddx_agen+comision*ddx_age)/((1-gamma1)*(nx_age-nx_agek)-(rx_age-rx_agek-k*mx_agen));

let neto_premija=(ddx_agen+edin_bruto_premija*(rx_age-rx_agen-k*mx_agen))/(nx_age-nx_agek);

end if;

end if;





if tprodukt='КЖ' then

let neto_premija=(mx_age-mx_agen+ddx_agen)/(nx_age-nx_agek);

let s17=(mx_age-mx_agen+ddx_agen);

let s11=(nx_age-nx_agek);

let edin_bruto_premija=(s17+(gama/100)*s11)/((s11*(1-beta/100))- (ddx_age*tperiod_osig*alfa/100));

end if;
--**

let SA_mesano=1/edin_bruto_premija;
let SA=SA_mesano*gp;


-------------end sheet SA
---sheet                       премии,       резерви... -------
let t=0;
while t<=tperiod_osig
let tageplust=tprist_starost+t;



select nx,dx ,mx,ddx,rx
into nx_tageplust, dx_tageplust,mx_tageplust,ddx_tageplust,rx_tageplust
from  tablica_komut_br
where godini=tageplust
and pol=tpol
and kamatna_stapka=tkamatna_stapka
and par_Tablica_SmrtId=tpar_Tablica_SmrtId; 



let tcomision=0;
if k<>1 then 
if t=0 then 
let tcomision= 3.30/100+(1.60/100*l2/l1*discont)+(1/100*l3/l1*power(discont,2))+(0.60/100*l4/l1*power(discont,3));

end if;
if t=1 then 
let tcomision= 1.60/100+(1/100*l3/l1*discont)+(0.60/100*l4/l1*power(discont,2));


end if;
if t=2 then 
let tcomision= 1/100+(0.60/100*l4/l1*discont);


end if;
if t=3 then 
let tcomision= 0.60/100;
end if;
else
if t=0 and ( tprodukt='ФУ'  or tprodukt='ФЗ') then 
let tcomision=0.065;
end if;  
end if; 

if t<k then
let a_x_k=a_age_k;
else
let a_x_k=0;
end if;

let a_xt_nt=(nx_tageplust- nx_agen)/ddx_tageplust;
if t<k then
let a_xt_kt=(nx_tageplust- nx_agek)/ddx_tageplust;
else
let a_xt_kt=0;
end if;



if t<tperiod_osig then
let a_x_n = (nx_age- nx_agen)/ddx_age;
else
let a_x_n=0;
end if;

if t>tperiod_osig then
let tneto_rezerva=0;
let tfaktor_zilimier=0;
let tzilimer_rezerva=0;
let mr_mesano=0;
let _otkup=0;
let CV=0;
else
let d=2.62901655306719;
let tneto_rezerva=(1-d/100*a_xt_nt-neto_premija*a_xt_kt)*SA;
if k=1 then 
let SA_doziv=(ddx_agen+db*ddx_age)/(ddx_age-(gama/100)*(nx_age-nx_agen));
let tfaktor_zilimier=3/100*SA_doziv*(a_xt_kt/a_age_k);
else
let tfaktor_zilimier=3/100*SA_mesano*(a_xt_nt/a_age_k);
end if;
let tzilimer_rezerva =tneto_rezerva-tfaktor_zilimier;
if  tprodukt='КЖ' then 
let neto_premija=neto_premija;

let a_xt_nt1=(mx_tageplust-mx_agen+ddx_agen)/ddx_tageplust;
let tneto_rezerva=a_xt_nt1-neto_premija*a_xt_nt;
let tfaktor_zilimier=2.5/100*a_xt_nt*(ddx_age/(nx_age-nx_agen));
let tzilimer_rezerva =tneto_rezerva-tfaktor_zilimier;

end if;	


if tzilimer_rezerva<0 then 
let tzilimer_rezerva=0;
let trx_t=0;	

end if;




if tprodukt='ФУ'  or  tprodukt='ФЗ' then
let ageb=18;
let nb=7;
let a_xt_nt1=ddx_agen/ddx_tageplust;
let a_xt_kt=a_xt_kt;
if k=1 then 
let trx_t=(mx_agen-k*mx_agen)/ddx_tageplust;
else
let trx_t=(rx_tageplust-rx_agek+t*mx_agen-k*mx_agen)/ddx_tageplust;
end if; 
let tneto_rezerva=(a_xt_nt1-neto_premija*a_xt_kt)*SA+(trx_t*gp);
let tfaktor_zilimier=3/100*(a_xt_kt/a_age_k);
let tzilimer_rezerva =tneto_rezerva-tfaktor_zilimier*SA;
if tzilimer_rezerva<0 then 
let tzilimer_rezerva=0;
end if;


let aa=a_xt_kt;
let mr_mesano=(a_xt_nt1+tcomision)*SA+((trx_t+(gamma1*a_xt_kt)-a_xt_kt)* gp);

if mr_mesano<0 then 
let mr_mesano=0;
end if;

select nvl(procent_kazna,0)
into tkazna_otkup
from  tablica_kazna_otkup
where godina=t+1
and kamatna_stapka=tkamatna_stapka; 

if t=tperiod_osig then 
let tkazna_otkup=0;
end if; 

let _otkup=mr_mesano*(1-tkazna_otkup/100);
if t<=godina_otkup then
let cv=0;
else
if t>=k then 
let pred_presm_mr=1;
else

select procent_kazna
into tkazna_otkup_kap
from  tablica_kazna_otkup
where godina is null
and kamatna_stapka=tkamatna_stapka; 
let pred_presm_mr=1-tkazna_otkup_kap/100;
---	  	во   период   на                                                                       капитализација	5%
end if;
let cv=mr_mesano*power((1+tkamatna_stapka/100),(tperiod_osig-t))*pred_presm_mr;
if k=1   then 
let cv=SA;
end if;
end if;

if tpol='F' then
let tpol_brak='M';
else
let tpol_brak='M';
end if;

select mx,nx,ddx
into mx_tageb,nx_ageb,ddx_ageb
from  tablica_komut_br_brak
where godini=ageb
and pol=tpol_brak
and kamatna_stapka=tkamatna_stapka;


select mx,nx,ddx
into mx_tagebplust,nx_agebplust,ddx_agebplust
from  tablica_komut_br_brak
where godini=ageb+t
and pol=tpol_brak
and kamatna_stapka=tkamatna_stapka;

select mx,ddx,nx
into mx_tagenb,ddx_tagenb,nx_tagenb
from  tablica_komut_br_brak
where godini=ageb+nb
and pol=tpol_brak
and kamatna_stapka=tkamatna_stapka;
let tax_n_brak=(nx_ageb-nx_tagenb)/ddx_ageb;
let taxt_kt_brak=(nx_agebplust-nx_tagenb)/ddx_ageb;
let tedin_neto_premija_brak=(mx_tageb-mx_tagenb+ddx_tagenb)/ddx_ageb;
let tedin_bruto_premija_brak=(tedin_neto_premija_brak+0.003*tax_n_brak )/(1- 0.01);
let tcom_brak=tedin_bruto_premija_brak* 0.01;
let tedin_osig_suma_brak= 1/tedin_bruto_premija_brak;
let SAb=round(SA*tedin_osig_suma_brak,2);
let tneto_rezerva_brak=(mx_tagebplust-mx_tagenb+ddx_tagenb)/ddx_agebplust* SAb +0.003*taxt_kt_brak*SAb;
if t<7 then 
let totkupna_vred_brak=0.92*tneto_rezerva_brak;
else 
if t=7 then 
let totkupna_vred_brak=tneto_rezerva_brak;
else 
let totkupna_vred_brak=null;
end if;
end if;

else
let tneto_rezerva_brak=0;
let totkupna_vred_brak=0;
let taxt_kt_brak=0;
if k=1  then
let mr_mesano=tzilimer_rezerva;
else
let mr_mesano=SA*(1-d/100*a_xt_nt+tcomision)+gp*(gamma1*a_xt_nt-a_xt_kt);
end if;
if tprodukt='КЖ' then 
let mr_mesano=0.04*a_xt_nt*(ddx_age/(nx_age-nx_agen));
end if;
if mr_mesano<0 then 
let mr_mesano=0;
end if;
if tprodukt='КЖ' then 
let tkazna_otkup=0;
if tneto_rezerva-tfaktor_zilimier<0 then
let _otkup=0;
else
if t<=godina_otkup then
let _otkup=0;
else
let _otkup=(tneto_rezerva-mr_mesano)*SA;
end if;
end if;
if t<=godina_otkup then
let cv=0;
else
let cv=_otkup*power((1+tkamatna_stapka/100),(tperiod_osig-t));
end if;
else
select nvl(procent_kazna,0)
into tkazna_otkup
from  tablica_kazna_otkup
where godina=t+1
and kamatna_stapka=tkamatna_stapka; 

if t=tperiod_osig then 
let tkazna_otkup=0;
end if; 

let _otkup=mr_mesano*(1-tkazna_otkup/100);
if t<=godina_otkup then
let cv=0;
else
if t>=k then 
let pred_presm_mr=1;
else

select procent_kazna
into tkazna_otkup_kap
from  tablica_kazna_otkup
where godina is null
and kamatna_stapka=tkamatna_stapka; 
let pred_presm_mr=1-tkazna_otkup_kap/100;
---	  	во                     период на                         капитализација	5%
end if;
if k=1 then
let cv=tosig_suma;
else
let cv=mr_mesano*power((1+tkamatna_stapka/100),(tperiod_osig-t))*pred_presm_mr;
end if; 
end if;
end if;	

end if;
end if;
----vo os_polisa_otkup se insertiraat site vrednosti od Shetot Output
insert  into os_polisa_pretarifiranje ( os_polisa_pretarifiranjeid ,datechanged,datecreated ,userchanged ,usercreated ,
version,os_polisaid,godini,godini_osiguruvanje,ax_k ,axt_kt,ax_n,cash_value_doz,gross_premium_doz,
matematcka_rezerva_doz,profit_doz,gross_premium,profit_Participation,
otkupna_vred,osigur_vred,kapitalizirana_vred,matematcka_rezerva,par_statusid,comision ,     faktor_zilimier ,
zilimer_rezerva ,     bruto_rezerva ,     kazna_otkup,neto_rezerva,tip_promena,opis )
values
(sq_os_polisa_pretarifiranje.nextval, today, today, tusername,tusername,0, tos_polisaid1,tageplust,t,a_x_k,a_xt_kt,a_xt_nt,
0, 0,0,0,0,0, _otkup,0,round(cv),round(mr_mesano),1,tcomision ,     tfaktor_zilimier ,
tzilimer_rezerva ,     mr_mesano ,                                            tkazna_otkup,tneto_rezerva,1,'ПРОМЕНЕТА ПОЛИСА - дел кој што продолжува     да се плаќа' );
let nrows = 0;
let nrows = DBINFO('sqlca.sqlerrd2');
if nrows = 0 then
ROLLBACK WORK;
return                                             '-1','ПОЛИСА               ДЕТАИЛ     НЕ Е АЖУРИРАНА';
end if;
let t=t+1;
end while;

end if;	


--vtor del promeneta polisa ---del koj se kapitalizira
select  kapitalizirana_vred into tkapitalizirana_vred
from os_polisa_otkup 
where os_polisaid=tos_polisaid_stara
and godini_osiguruvanje=tkoja_godina_pretarf;

let k=tkoja_godina_pretarf;

select nvl(iznos_premija,0)
into  tpreth_premija
from os_ponuda_detail
where os_ponudaid=tos_ponudaid
and ts_vid_rizik='Or';

let tkapitalizirana_vred=round(((tpreth_premija-tpremija)/tpreth_premija)*tkapitalizirana_vred);

select nx,dx,mx ,ddx
into nx_age, dx_age,mx_age,ddx_age

from  tablica_komut_br
where godini=tprist_starost
and pol=tpol
and kamatna_stapka=tkamatna_stapka
and par_Tablica_SmrtId=tpar_Tablica_SmrtId;
select nx,rx
into nx_agek,rx_agek
from  tablica_komut_br
where godini=tprist_starost+k
and pol=tpol
and kamatna_stapka=tkamatna_stapka
and par_Tablica_SmrtId=tpar_Tablica_SmrtId;
select nx ,dx,mx,ddx
into nx_agen,dx_agen,mx_agen,ddx_agen
from  tablica_komut_br
where godini=tprist_starost+tperiod_osig
and pol=tpol
and kamatna_stapka=tkamatna_stapka
and par_Tablica_SmrtId=tpar_Tablica_SmrtId;
let a_age_k=(nx_age- nx_agek)/dx_age;
let a_x_n = (nx_age- nx_agen)/dx_age;

--execute procedure premija_calculate_pretarif(tkapitalizirana_vred, tos_polisaid_nova,tkoja_godina_pretarf) into tkap_premija;
---let tkap_premija=260;
let a_x_k=a_age_k;
let cash_value_mesano=round((((mx_age-mx_agen)/dx_age+dx_agen/dx_age)*tkapitalizirana_vred)+(alfa/1000*SA)+(gama/1000*tkapitalizirana_vred*a_x_n));
let tkap_premija=round((cash_value_mesano/(a_x_k*(1-beta/100)))+(unit_cost/(1-beta/100)));
if tpar_trosoci_produkt ='002' then ----tuka po staro ---promil za OS 03.06.2014Slagjana 

---sheet SA-----od kalkulatorot

let platena_premija=tkap_premija*k;
---- sega za sega ke go ostavam fiksno otkako ke se resi  so provizijata sifrarnik
if tosigurenik_par_client is null then 
let comision=(platena_premija*1.5/100)+(platena_premija*1/100)+(platena_premija*0.5/100)+(platena_premija*0.5/100);
else
let comision=(platena_premija*3.30/100)+(platena_premija*1.60/100)+(platena_premija*1/100)+(platena_premija*0.60/100);
end if;
---     let cash_value_mesano=round((((mx_age-mx_agen)/dx_age+dx_agen/dx_age)*SA)+(alfa/1000*SA)+(gama/1000*SA*a_x_n));
--      let gp_mesano=round((cash_value_mesano/(a_x_k*(1-beta/100)))+(unit_cost/(1-beta/100)));
let cash_value_mesano=tkap_premija * ((a_age_k*(1-beta/100)));
let SA=round(((cash_value_mesano)-(comision))/(((mx_age-mx_agen)/dx_age+dx_agen/dx_age) +(gama/1000*a_x_n)));
let alfa=round((comision/SA)*1000,2);


let db=d/(1-(beta/100));
let a_beta=(1-(beta/100))*a_age_k;
let gamma1= (gama/1000)*a_x_n;
let alfa1=alfa/1000;
let a_doziv=dx_agen/dx_age;
let a_mesano= (mx_age-mx_agen)/dx_age;
let SA_doziv=((tkap_premija-db)*a_beta)/(a_doziv+gamma1+alfa1);
let SA_mesano=((tkap_premija-db)*a_beta)/(a_doziv+gamma1+alfa1+a_mesano);
let SA=SA_mesano;
let SA=tkapitalizirana_vred;
-------------end sheet SA
---sheet Output -------
let t=0;
while t<=tperiod_osig
let tageplust=tprist_starost+t;

select nx,dx ,mx
into nx_tageplust, dx_tageplust,mx_tageplust
from  tablica_komut_br
where godini=tageplust
and pol=tpol
and kamatna_stapka=tkamatna_stapka
and par_Tablica_SmrtId=tpar_Tablica_SmrtId;
if t<k then
let a_x_k=a_age_k;
else
let a_x_k=0;
end if;
if a_x_k=0 then
let a_xt_kt=0 ;
else
let a_xt_kt=(nx_tageplust- nx_agen)/dx_tageplust;
end if;
if t<tperiod_osig then
let a_x_n = (nx_age- nx_agen)/dx_age;
else
let a_x_n=0;
end if;
if t=tperiod_osig then
let cash_value_doz=0;
let cash_value_mesano=0;
else
let cash_value_doz=round(((dx_agen/dx_age)*SA)+(alfa/1000*SA)+(gama/1000*SA*a_x_n));
let cash_value_mesano=round((((mx_age-mx_agen)/dx_age+dx_agen/dx_age)*SA)+(alfa/1000*SA)+(gama/1000*SA*a_x_n));
---let cash_value_mesano=((((mx_age-mx_agen)/(dx_age+dx_agen))/dx_age)*SA)+(alfa/1000*SA)+(gama/1--000*SA*a_x_n);
end if;
if a_x_n=0 then
let gp_doz=0;
let gp_mesano=0;
else

if   a_x_k=0 then
let gp_doz=0;
let gp_mesano=0;
else 
let gp_doz=round((cash_value_doz/(a_x_k*(1-beta/100)))+(unit_cost/(1-beta/100)));
let gp_mesano=round((cash_value_mesano/(a_x_k*(1-beta/100)))+(unit_cost/(1-beta/100)));
end if;	
end if;
if  gp_doz = 0 then  let mr_doz_predpresm=0; else
let mr_doz_predpresm=((((dx_agen/dx_age)*SA)+(alfa2/1000*SA))/a_x_k)*a_xt_kt;  end if;
--let mr_doz=((dx_agen/dx_tageplust*SA)- (dx_agen/dx_age*SA)+(alfa2/1000*SA))/a_x_k;
let mr_doz=round((dx_agen/dx_tageplust*SA)- mr_doz_predpresm);
if gp_mesano=0 then
let pred_presm_mr =0;
else


--      let pred_presm_mr=((((mx_age-mx_agen)/dx_age+dx_agen/dx_age)*SA+(alfa2/1000)*SA)/a_x_k);
let pred_presm_mr=((((mx_age-mx_agen)/dx_age+dx_agen/dx_age)*SA+(alfa2/1000)*SA)/a_x_k)*a_xt_kt;
end if;
let mr_mesano=round((((mx_tageplust -mx_agen)/dx_tageplust+dx_agen/dx_tageplust)*SA)- pred_presm_mr);
--let mr_mesano=((((mx_age -mx_agen)/(dx_tageplust+dx_agen))/dx_tageplust)*SA)- pred_presm_mr;
--      let mr_mesano=round((((mx_age -mx_agen)/dx_age+dx_agen/dx_age)*SA)- pred_presm_mr);
--      let mr_mesano=round((((mx_age -mx_agen)/dx_tageplust+dx_agen/dx_tageplust)*SA)- pred_presm_mr);
if mr_mesano<0 then
let CV=0;
else
--let cv=mr_mesano*power((1+tkamatna_stapka/100),(tperiod_osig-t));
let cv=tkapitalizirana_vred;
if t=0 then
let net_profit=((((mx_age -mx_agen)/(dx_age+dx_agen))/dx_age)*SA)/a_xt_kt;
end if;
end if;
if t<tkoja_godina_pretarf then
let _otkup=0;
else
let _otkup=mr_mesano;
end if;


----vo os_polisa_pretarifiranje se insertiraat site vrednosti od Shetot Output
insert  into os_polisa_pretarifiranje ( os_polisa_pretarifiranjeid ,datechanged,datecreated ,userchanged ,usercreated ,
version,os_polisaid,godini,godini_osiguruvanje,ax_k ,axt_kt,ax_n,cash_value_doz,gross_premium_doz,
matematcka_rezerva_doz,profit_doz,gross_premium,profit_Participation,
otkupna_vred,osigur_vred,kapitalizirana_vred,matematcka_rezerva,par_statusid,tip_promena,opis )
values
(sq_os_polisa_pretarifiranje.nextval, today, today, tusername,tusername,0, tos_polisaid1,tageplust,t,a_x_k,a_xt_kt,a_x_n,
cash_value_doz, gp_doz,mr_doz,0,gp_mesano,0,_otkup,cash_value_mesano,round(cv),round(mr_mesano),1,2,'ПРОМЕНЕТА ПОЛИСА - дел кој     што се         капитализира');
let nrows = 0;
let nrows = DBINFO('sqlca.sqlerrd2');
if nrows = 0 then
ROLLBACK WORK;
return                                       '-1','ПОЛИСА                   ДЕТАИЛ НЕ Е         АЖУРИРАНА';
end if;
let t=t+1;
end while;

end if;	

if tpar_trosoci_produkt ='003' then
select nx,rx into nx_agek,rx_agek
from  tablica_komut_br
where godini=tprist_starost+k
and pol=tpol
and kamatna_stapka=tkamatna_stapka
and par_Tablica_SmrtId=tpar_Tablica_SmrtId;
select lx into l1
from tablica_smrt
where godini=tprist_starost
and pol=tpol
and kamatna_stapka=tkamatna_stapka
and par_Tablica_SmrtId=tpar_Tablica_SmrtId;

select lx into l2
from tablica_smrt
where godini=tprist_starost+1
and pol=tpol
and kamatna_stapka=tkamatna_stapka
and par_Tablica_SmrtId=tpar_Tablica_SmrtId;


select lx into l3
from tablica_smrt
where godini=tprist_starost+2
and pol=tpol
and kamatna_stapka=tkamatna_stapka;
select lx into l4
from tablica_smrt
where godini=tprist_starost+3
and pol=tpol
and kamatna_stapka=tkamatna_stapka
and par_Tablica_SmrtId=tpar_Tablica_SmrtId;

let a_mesano= (mx_age-mx_agen+ddx_agen)/ddx_age;
let a_age_k=(nx_age- nx_agek)/ddx_age;
let a_x_n = (nx_age- nx_agen)/ddx_age;
let neto_premija=a_mesano/a_age_k;
let discont=1/(1+tkamatna_stapka/100);
let comision= 3.30/100+(1.60/100*l2/l1*discont)+(1/100*l3/l1*pow(discont,2))+(0.60/100*l4/l1*pow(discont,3));
let db=comision/a_age_k; 
let gamma1= (gama/100)*(a_x_n/a_age_k);
let edin_bruto_premija=(db+neto_premija)/(1-gamma1);



IF tpar_nacin_plati<>'005' then
let db=comision/a_age_k; --alfa
else
let db=0.065; --alfa
let gama=1;
end if;

let gamma1= (gama/100)*(a_x_n/a_age_k);
if k=1 then
let neto_premija=a_mesano;
let edin_bruto_premija=(mx_age-mx_agen+ddx_agen+db*ddx_age)/(ddx_age-(gama/100)*(nx_age-nx_agen));
else
let edin_bruto_premija=(db+neto_premija)/(1-gamma1);
end if;

if tprodukt='ФУ'  or tprodukt='ФЗ' then


if k=1 then--20.09.2017 promena

let db=0.065; --alfa

let gama=1;

let edin_bruto_premija=(ddx_agen+db*ddx_age)/(ddx_age-(gama/100)*(nx_age-nx_agen)-(mx_age-mx_agen));

else

let edin_bruto_premija=(ddx_agen+comision*ddx_age)/((1-gamma1)*(nx_age-nx_agek)-(rx_age-rx_agek-k*mx_agen));

let neto_premija=(ddx_agen+edin_bruto_premija*(rx_age-rx_agen-k*mx_agen))/(nx_age-nx_agek);

end if;

end if;





if tprodukt='КЖ' then

let neto_premija=(mx_age-mx_agen+ddx_agen)/(nx_age-nx_agek);

let s17=(mx_age-mx_agen+ddx_agen);

let s11=(nx_age-nx_agek);

let edin_bruto_premija=(s17+(gama/100)*s11)/((s11*(1-beta/100))- (ddx_age*tperiod_osig*alfa/100));

end if;
--**

let SA_mesano=1/edin_bruto_premija;
let SA=tkapitalizirana_vred;



-------------end sheet SA
---sheet             премии,     резерви... -------
let t=0;
while t<=tperiod_osig
let tageplust=tprist_starost+t;

select nx,dx ,mx,ddx,rx
into nx_tageplust, dx_tageplust,mx_tageplust,ddx_tageplust,rx_tageplust
from  tablica_komut_br
where godini=tageplust
and pol=tpol
and kamatna_stapka=tkamatna_stapka
and par_Tablica_SmrtId=tpar_Tablica_SmrtId; 



let tcomision=0;
if k<>1 then 
if t=0 then 
let tcomision= 3.30/100+(1.60/100*l2/l1*discont)+(1/100*l3/l1*power(discont,2))+(0.60/100*l4/l1*power(discont,3));

end if;
if t=1 then 
let tcomision= 1.60/100+(1/100*l3/l1*discont)+(0.60/100*l4/l1*power(discont,2));


end if;
if t=2 then 
let tcomision= 1/100+(0.60/100*l4/l1*discont);


end if;
if t=3 then 
let tcomision= 0.60/100;
end if;
else
if t=0 and ( tprodukt='ФУ'  or tprodukt='ФЗ') then 
let tcomision=0.065;
end if;  
end if; 

if t<k then
let a_x_k=a_age_k;
else
let a_x_k=0;
end if;

let a_xt_nt=(nx_tageplust- nx_agen)/ddx_tageplust;
if t<k then
let a_xt_kt=(nx_tageplust- nx_agek)/ddx_tageplust;
else
let a_xt_kt=0;
end if;



if t<tperiod_osig then
let a_x_n = (nx_age- nx_agen)/ddx_age;
else
let a_x_n=0;
end if;

if t>tperiod_osig then
let tneto_rezerva=0;
let tfaktor_zilimier=0;
let tzilimer_rezerva=0;
let mr_mesano=0;
let _otkup=0;
let CV=0;
else
let d=2.62901655306719;
let tneto_rezerva=(1-d/100*a_xt_nt-neto_premija*a_xt_kt)*SA;
if k=1 then 
let SA_doziv=(ddx_agen+db*ddx_age)/(ddx_age-(gama/100)*(nx_age-nx_agen));
let tfaktor_zilimier=3/100*SA_doziv*(a_xt_kt/a_age_k);
else
let tfaktor_zilimier=3/100*SA_mesano*(a_xt_nt/a_age_k);	--21.09.2020
-- if a_xt_kt=0 then
--	let tfaktor_zilimier=0;
--else 
--	let tfaktor_zilimier=3/100*edin_bruto_premija*(a_xt_nt/a_xt_kt);
--end if; 	
end if;

let edin_bruto_premija_doz=(ddx_agen+(alfa/100)*ddx_age)/((1-(gama/100))*(nx_age-nx_agek));
let tfaktor_zilimier=0.03*edin_bruto_premija_doz*(a_xt_kt/a_age_k);
let tzilimer_rezerva =tneto_rezerva-SA*tfaktor_zilimier;
--let tzilimer_rezerva =tneto_rezerva-tfaktor_zilimier;
if              tprodukt='КЖ' then 
let neto_premija=neto_premija;

let a_xt_nt1=(mx_tageplust-mx_agen+ddx_agen)/ddx_tageplust;
let tneto_rezerva=a_xt_nt1-neto_premija*a_xt_nt;
let tfaktor_zilimier=2.5/100*a_xt_nt*(ddx_age/(nx_age-nx_agen));
let tzilimer_rezerva =tneto_rezerva-tfaktor_zilimier;

end if;	


if tzilimer_rezerva<0 then 
let tzilimer_rezerva=0;
let trx_t=0;	

end if;




if tprodukt='ФУ'  or                tprodukt='ФЗ' then
let ageb=18;
let nb=7;
let a_xt_nt1=ddx_agen/ddx_tageplust;
let a_xt_kt=a_xt_kt;
if k=1 then 
let trx_t=(mx_agen-k*mx_agen)/ddx_tageplust;
else
let trx_t=(rx_tageplust-rx_agek+t*mx_agen-k*mx_agen)/ddx_tageplust;
end if; 
let tneto_rezerva=(a_xt_nt1-neto_premija*a_xt_kt)*SA+(trx_t*gp);
let tfaktor_zilimier=(3/100)*(a_xt_kt/a_age_k);
let tzilimer_rezerva =tneto_rezerva-tfaktor_zilimier*SA;
if tzilimer_rezerva<0 then 
let tzilimer_rezerva=0;
end if;


let aa=a_xt_kt;
let mr_mesano=(a_xt_nt1+tcomision)*SA+((trx_t+(gamma1*a_xt_kt)-a_xt_kt)* gp);
--promena na 03.12.2018-21.09.2020
let mr_mesano=(a_xt_nt1+tcomision+(edin_bruto_premija*((gama/100))*a_xt_kt))*SA;--+((trx_t+(gamma1*a_xt_kt)-a_xt_kt)* gp);

if mr_mesano<0 then 
let mr_mesano=0;
end if;

select nvl(procent_kazna,0)
into tkazna_otkup
from  tablica_kazna_otkup
where godina=t+1
and kamatna_stapka=tkamatna_stapka; 

if t=tperiod_osig then 
let tkazna_otkup=0;
end if; 

let _otkup=mr_mesano*(1-tkazna_otkup/100);
if t<=godina_otkup then
let cv=0;
else
if t>=k then 
let pred_presm_mr=1;
else

select procent_kazna
into tkazna_otkup_kap
from  tablica_kazna_otkup
where godina is null
and kamatna_stapka=tkamatna_stapka; 
let pred_presm_mr=1-tkazna_otkup_kap/100;
---	  	во   период       на                                           капитализација	5%
end if;
let cv=mr_mesano*power((1+tkamatna_stapka/100),(tperiod_osig-t))*pred_presm_mr;
if k=1   then 
let cv=SA;
end if;
end if;

if tpol='F' then
let tpol_brak='M';
else
let tpol_brak='M';
end if;

select mx,nx,ddx
into mx_tageb,nx_ageb,ddx_ageb
from  tablica_komut_br_brak
where godini=ageb
and pol=tpol_brak
and kamatna_stapka=tkamatna_stapka;


select mx,nx,ddx
into mx_tagebplust,nx_agebplust,ddx_agebplust
from  tablica_komut_br_brak
where godini=ageb+t
and pol=tpol_brak
and kamatna_stapka=tkamatna_stapka;

select mx,ddx,nx
into mx_tagenb,ddx_tagenb,nx_tagenb
from  tablica_komut_br_brak
where godini=ageb+nb
and pol=tpol_brak
and kamatna_stapka=tkamatna_stapka;
let tax_n_brak=(nx_ageb-nx_tagenb)/ddx_ageb;
let taxt_kt_brak=(nx_agebplust-nx_tagenb)/ddx_ageb;
let tedin_neto_premija_brak=(mx_tageb-mx_tagenb+ddx_tagenb)/ddx_ageb;
let tedin_bruto_premija_brak=(tedin_neto_premija_brak+0.003*tax_n_brak )/(1- 0.01);
let tcom_brak=tedin_bruto_premija_brak* 0.01;
let tedin_osig_suma_brak= 1/tedin_bruto_premija_brak;
let SAb=round(SA*tedin_osig_suma_brak,2);
let tneto_rezerva_brak=(mx_tagebplust-mx_tagenb+ddx_tagenb)/ddx_agebplust* SAb +0.003*taxt_kt_brak*SAb;
if t<7 then 
let totkupna_vred_brak=0.92*tneto_rezerva_brak;
else 
if t=7 then 
let totkupna_vred_brak=tneto_rezerva_brak;
else 
let totkupna_vred_brak=null;
end if;
end if;

else
let tneto_rezerva_brak=0;
let totkupna_vred_brak=0;
let taxt_kt_brak=0;
if k=1  then
let mr_mesano=tzilimer_rezerva;
else
--let mr_mesano=SA*(1-d/100*a_xt_nt+tcomision)+gp*(gamma1*a_xt_nt-a_xt_kt);
let a_xt_nminust=((mx_tageplust- mx_agen)+ddx_agen)/ddx_tageplust;
let mr_mesano=SA*(a_xt_nminust+tcomision+edin_bruto_premija*((gama/100)*a_xt_kt)-edin_bruto_premija*a_xt_kt);
end if;
if tprodukt='КЖ' then 
let mr_mesano=0.04*a_xt_nt*(ddx_age/(nx_age-nx_agen));
end if;
if mr_mesano<0 then 
let mr_mesano=0;
end if;
if tprodukt='КЖ' then 
let tkazna_otkup=0;
if tneto_rezerva-tfaktor_zilimier<0 then
let _otkup=0;
else
if t<=godina_otkup then
let _otkup=0;
else
let _otkup=(tneto_rezerva-mr_mesano)*SA;
end if;
end if;
if t<=godina_otkup then
let cv=0;
else
let cv=_otkup*power((1+tkamatna_stapka/100),(tperiod_osig-t));
end if;
else
select nvl(procent_kazna,0)
into tkazna_otkup
from  tablica_kazna_otkup
where godina=t+1
and kamatna_stapka=tkamatna_stapka; 

if t=tperiod_osig then 
let tkazna_otkup=0;
end if; 

let _otkup=mr_mesano*(1-tkazna_otkup/100);
if t<=godina_otkup then
let cv=0;
else
if t>=k then 
let pred_presm_mr=1;
else

select procent_kazna
into tkazna_otkup_kap
from  tablica_kazna_otkup
where godina is null
and kamatna_stapka=tkamatna_stapka; 
let pred_presm_mr=1-tkazna_otkup_kap/100;
---	  	во               период на                                           капитализација	5%
end if;
if k=1 then
let cv=tkapitalizirana_vred;
else
let cv=tkapitalizirana_vred;
end if; 
end if;
end if;	

end if;
end if;

----vo os_polisa_otkup se insertiraat site vrednosti od Shetot Output
insert  into os_polisa_pretarifiranje ( os_polisa_pretarifiranjeid ,datechanged,datecreated ,userchanged ,usercreated ,
version,os_polisaid,godini,godini_osiguruvanje,ax_k ,axt_kt,ax_n,cash_value_doz,gross_premium_doz,
matematcka_rezerva_doz,profit_doz,gross_premium,profit_Participation,
otkupna_vred,osigur_vred,kapitalizirana_vred,matematcka_rezerva,par_statusid,comision ,     faktor_zilimier ,
zilimer_rezerva ,     bruto_rezerva ,     kazna_otkup,neto_rezerva,tip_promena,opis )
values
(sq_os_polisa_pretarifiranje.nextval, today, today, tusername,tusername,0, tos_polisaid1,tageplust,t,a_x_k,a_xt_kt,a_xt_nt,
0, 0,0,0,0,0, _otkup,0,round(cv),round(mr_mesano),1,tcomision ,     tfaktor_zilimier ,
tzilimer_rezerva , mr_mesano ,tkazna_otkup,tneto_rezerva,2,'ПРОМЕНЕТА ПОЛИСА - дел кој што се  капитализира' );
let nrows = 0;
let nrows = DBINFO('sqlca.sqlerrd2');
if nrows = 0 then
ROLLBACK WORK;
return                         '-1','ПОЛИСА               ДЕТАИЛ   НЕ   Е АЖУРИРАНА';
end if;
let t=t+1;
end while;

end if;	


-----the end ------------kapitalizacija 
----na kraj soberi --------insert into os_polisa_otkup-----
foreach 

select         godini ,     godini_osiguruvanje ,         round(sum(  otkupna_vred),0) ,
sum( osigur_vred) ,       round( sum( kapitalizirana_vred ),0),        sum( matematcka_rezerva) 
into  tgodini ,     tgodini_osiguruvanje ,         totkupna_vred ,
tosigur_vred ,        tkapitalizirana_vred ,        tmatematcka_rezerva
from os_polisa_pretarifiranje
where os_polisaid=tos_polisaid1
group by 1,2
order by 2

if tgodini_osiguruvanje=tperiod_osig then
update os_ponuda_detail set osig_suma=tkapitalizirana_vred
where os_ponudaid=tos_polisaid_nova
and ts_vid_rizik='Or';

if kolku_isp >0 then
update  os_ponuda_isplata set osig_suma =osigsuma_ispl_calculate(os_ponudaid,os_produkt_isplataid)
where os_ponudaid=tos_polisaid_nova;
end if;

end if;


insert into os_polisa_otkup(     os_polisa_otkupid ,     datechanged ,
datecreated ,     userchanged ,     usercreated ,     version ,
os_polisaid ,     godini ,     godini_osiguruvanje ,     otkupna_vred ,
osigur_vred ,     kapitalizirana_vred ,     matematcka_rezerva ,   par_statusid)

values(    os_polisa_otkupid.nextval, today, today, tusername,tusername,0,tos_polisaid1,
tgodini ,     tgodini_osiguruvanje ,  totkupna_vred ,
tosigur_vred ,        tkapitalizirana_vred ,        tmatematcka_rezerva,1) ;

end foreach;

end if;


let odreden_datum=date(ADD_MONTHS(tskadenca_datum_od,3)+tkoja_godina_pretarf units  year);

let odreden_datum_sk=date(tskadenca_datum_od+tkoja_godina_pretarf units  year);
if tdatum_pretarifiranje<= tdatum_vaznost then 
let za_naredna_godina='1';
else
let za_naredna_godina='0';
end if; 

select count(*) into dali_ima_aneks
from os_aneks 
where os_polisaid=tos_polisaid_stara;

select  max(os_aneksid)  into 
tos_aneksid_posleden 
from os_aneks 
where os_polisaid=tos_polisaid_stara;

select godisnica_aneks  into tgodisnica_aneks
from os_aneks
where os_aneksid=tos_aneksid_posleden;

if dali_ima_aneks >0 then 
if (tgodisnica_aneks>tdatum_vaznost and za_naredna_godina='1') or (za_naredna_godina='0') then 

select count(*) into dali_proknizeno
from fin_stavka 
where os_polisaid=tos_polisaid_stara
and nal_vid is not null
and os_aneks_fakturaid in (select os_aneks_fakturaid from os_aneks_faktura 
where os_aneksid= tos_aneksid_posleden );
if dali_proknizeno> 0 then 

foreach 
select os_aneks_fakturaid  into 
toos_aneks_fakturaid1
from os_aneks_faktura
where os_aneksid= tos_aneksid_posleden

select count(*) into dali_proknizeno_stavka
from fin_stavka
where os_polisaid=tos_polisaid
and nal_vid is not null
and iznos_d is not null
and os_aneks_fakturaid =toos_aneks_fakturaid1;

if dali_proknizeno_stavka>0 then 

let toos_aneks_fakturaid=sq_os_aneks_fakturaid.nextval ;
insert into os_aneks_faktura(     os_aneks_fakturaid ,     
datecreated ,          usercreated ,
version ,     os_aneksid ,     par_tip_dokumentid ,
par_tip_kniziid ,     rata ,     os_ponuda_detailid ,
data_faktura ,     data_valuta ,     iznos ,
iznos_denari ,     par_statusid
)  
select
toos_aneks_fakturaid,  current    ,   tusername,   0,
os_aneksid ,     par_tip_dokumentid ,
par_tip_kniziid ,     rata ,     os_ponuda_detailid ,     data_faktura ,
data_valuta ,     (-1)*iznos ,(-1)*iznos_denari ,     1
from os_aneks_faktura
where os_aneks_fakturaid= toos_aneks_fakturaid1;

insert into fin_stavka (fin_stavkaid, datecreated, usercreated, version, par_filijalaid,
par_tip_dokumentid, par_tip_kniziid, par_clientid, os_aneks_fakturaid,
par_yearid, datum, datum_knizi,datum_stavka,datum_fakt_valuta, par_valutaid,
par_kursid, os_polisaid,par_agent_id,  pat_tip_platiid,
iznos_otvoren, f_rs,iznos_d,    iznos_d_den,
par_statusid)
select sq_fin_stavka.nextval,current, tusername,0,      par_filijalaid ,
par_tip_dokumentid ,     par_tip_kniziid ,
par_clientid ,     toos_aneks_fakturaid ,     par_yearid ,     today ,
today ,     today ,     datum_fakt_valuta ,
par_valutaid ,    par_kursid ,     os_polisaid ,
par_agent_id ,          pat_tip_platiid ,
0 ,'S',(-1)*iznos_d,    (-1)*iznos_d_den,   1
from fin_stavka
where os_polisaid=tos_polisaid_stara
and os_aneks_fakturaid =toos_aneks_fakturaid1 
and iznos_d is not null; 
else

update fin_stavka set f_rs='N'
where os_polisaid=tos_polisaid
and os_aneks_fakturaid=toos_aneks_fakturaid1;
update os_aneks_faktura set f_rs='N'
where os_aneks_fakturaid=toos_aneks_fakturaid1;

end if;

end foreach;
update os_aneks set (iznos_premija,iznos_premija_den ,datechanged,userchanged,version,gener_aneks
)=( 0,0, current,tusername,1,1 ) 
where os_aneksid=tos_aneksid_posleden;

update os_ponuda set polisa='t'
where os_ponudaid=tos_polisaid_nova;

else

execute procedure generiraj_aneks_pretarifiranje (tos_polisaid_nova,tos_polisaid1,za_naredna_godina,tuser_id) into terr, poraka;
delete from fin_stavka
where os_aneks_fakturaid in (select os_aneks_fakturaid from
os_aneks_faktura where os_aneksid=tos_aneksid_posleden);
delete from os_aneks_faktura 
where os_aneksid=tos_aneksid_posleden;
delete from os_aneks
where os_aneksid=tos_aneksid_posleden;

select  max(os_aneksid)  into 
tos_aneksid_posleden 
from os_aneks 
where os_polisaid=tos_polisaid_stara;

end if;
end if; 
end if;


commit work;
return  tos_polisaid_nova,'ПОЛИСАТА   Е       ИЗГЕНЕРИРАНА';

end function;