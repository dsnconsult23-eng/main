CREATE FUNCTION appuser.r_obraboti_kreditni() returning int,varchar(255);
 define tkreditna,tpar_nacin_plati,tusername,tpolisa_broj varchar(50); 
 define tdatum date;
 define tstatus_kredit varchar(1);
 define trizikoid int;
 define tout int;
 define tporaka varchar(255);
 define pom int;
 define cnt_obraboteni, cnt_veke_obraboteni, cnt_nema_ponuda int;
 define tstatus_ponuda int;
 define tskadenca_do date;
 define tos_produkt_uplataid, tos_ponudaid,tpar_nacin_platid,tos_aneks_fakturaid,terr1,tfin_izvod_iid , tfin_stavkaid,tos_polisaid,tuser_id,tpar_statusid int;
 define tnaplata dec;


 {
   flag_upload se menuva vo 3 novi statusi:
     1- kreditnata partija e realizirana ili odbiena
     2- ponudata so kreditnata partija ne e seuste odobrena od Uniqa life
     3- ne e pronajdena takva partija
 
  }

  --set debug file to 'err_r_obraboti_kreditni.sql';
  --trace on;
 let tout=1;
 let tporaka='Обработката заврши успешно';
 let cnt_obraboteni=0;
 let cnt_veke_obraboteni=0;
 let cnt_nema_ponuda=0;
 
  foreach select riziko_kreditid,kreditna_partija, datum, status_kredit ,usercreated
      into trizikoid,tkreditna, tdatum,tstatus_kredit,tusername 
      from riziko_kredit 
      where flag_upload=0 
     -- and kreditna_partija='РК/Б00011865'
     and date(datecreated)=today
      --and status_kredit in('R','6')
    
      
      
      
      
      select userid into tuser_id
      from adm_user
      where username=tusername;
      
      
    select os_produkt_uplataid, os_ponudaid, a.par_statusid
      into tos_produkt_uplataid, tos_ponudaid,tpar_statusid
      from os_ponuda a , os_produkt  b
where a.os_produktid=b.os_produktid
and b.produkt||'/'||ponuda_broj=trim(tkreditna)
and ponuda_podbroj=vratipodbrojponuda(ponuda_broj, a.os_produktid  );



if tos_ponudaid is null then
 update riziko_kredit set flag_upload=5 where riziko_kreditid=trizikoid;--nema
 let cnt_nema_ponuda=cnt_nema_ponuda+1;
 CONTINUE FOREACH;
end if;



if tpar_statusid=20 then
 update riziko_kredit set flag_upload=8 where riziko_kreditid=trizikoid;--obrabotena e veke
 let cnt_veke_obraboteni=cnt_veke_obraboteni+1;
 CONTINUE FOREACH;
end if;


select par_nacin_platiid into tpar_nacin_platid
from os_produkt_uplata
where os_produkt_uplataid=tos_produkt_uplataid;
select par_nacin_plati into tpar_nacin_plati
from par_nacin_plati
where par_nacin_platiid=tpar_nacin_platid;

execute function vrati_polisa_broj (tos_ponudaid)  into tpolisa_broj;

select os_polisaid into tos_polisaid
from os_polisa
where os_ponudaid=tos_ponudaid;
 
if tpar_nacin_plati='004'  then ---mesecno --storno
/*
select nvl(sum (nvl(naplata,0)),0) into tnaplata  from report_fakturi 
where polisa_broj=tpolisa_broj
and data_faktura>=tdatum
and naplata>0;

if tnaplata>0 then 

---treba da se vnese nov stav vo fin_izvod_i so AVANS ----i da se stornira uplatata 

foreach select os_aneks_fakturaid, nvl(sum (nvl(naplata,0)),0) into tos_aneks_fakturaid, tnaplata  from report_fakturi 
where polisa_broj=tpolisa_broj
and data_faktura>=tdatum
and naplata>0

foreach select fin_izvod_iid , fin_stavkaid
 into tfin_izvod_iid , tfin_stavkaid
 from fin_stavka 
where os_aneks_fakturaid=tos_aneks_fakturaid
and iznos_p>0
/*
 insert into fin_stavka (fin_stavkaid, datecreated, usercreated, version, par_filijalaid,
    par_tip_dokumentid, par_tip_kniziid, par_clientid, os_aneks_fakturaid,
    par_yearid, datum, datum_knizi,datum_stavka,datum_fakt_valuta, par_valutaid,
    par_kursid, os_polisaid,par_agent_id,  pat_tip_platiid,
   iznos_otvoren, f_rs,iznos_p,    iznos_p_den,
    par_statusid,fin_izvod_iid)
select sq_fin_stavka.nextval,current, tusername,0,      par_filijalaid ,
     par_tip_dokumentid ,     par_tip_kniziid ,
     par_clientid ,     os_aneks_fakturaid ,     par_yearid ,  
	  datum, datum_knizi,datum_stavka,datum_fakt_valuta,
     par_valutaid ,    par_kursid ,     os_polisaid ,
     par_agent_id ,          pat_tip_platiid ,
      iznos_otvoren ,'S',(-1)*iznos_p, (-1)*iznos_p_den,   1,fin_izvod_iid
from fin_stavka
where fin_stavkaid=tfin_stavkaid;



end foreach;



end foreach;

end if; */
if tstatus_kredit=2 then
 execute  procedure pom_promena_status_polisa_sostorno (tos_polisaid,1,1,995,tdatum , tuser_id ) into terr1, tporaka;
else 
 execute  procedure pom_promena_status_polisa_sostorno (tos_polisaid,1,1,1774,tdatum , tuser_id ) into terr1, tporaka;
 end if;
 update riziko_kredit set flag_upload=1 where riziko_kreditid=trizikoid;
 let cnt_obraboteni=cnt_obraboteni+1;

end if;


if tpar_nacin_plati='005' and tstatus_kredit<>3 then --ednokratno
execute  FUNCTION pom_likvidirani_krediti_edoktratno  (tkreditna,	tuser_id,tdatum) into  terr1, tporaka;

 update riziko_kredit set flag_upload=1 where riziko_kreditid=trizikoid;
 let cnt_obraboteni=cnt_obraboteni+1;
end if;

if tpar_nacin_plati='005' and tstatus_kredit=3 then --ednokratno
execute  FUNCTION pom_likvidirani_krediti_ednoktratno_serticifate  (tkreditna,	tuser_id,tdatum) into  terr1, tporaka;

 update riziko_kredit set flag_upload=1 where riziko_kreditid=trizikoid;
 let cnt_obraboteni=cnt_obraboteni+1;
end if;

  end foreach;

 if cnt_obraboteni=0 and cnt_veke_obraboteni=0 and cnt_nema_ponuda=0 then
   let tporaka = 'Нема записи за обработка — сите се веќе обработени или нема нови денес.';
 else
   let tporaka = 'Обработени: '||cnt_obraboteni
               ||', Веќе сторнирани: '||cnt_veke_obraboteni
               ||', Не е најдена понуда: '||cnt_nema_ponuda;
 end if;
 return tout,tporaka;
end function;