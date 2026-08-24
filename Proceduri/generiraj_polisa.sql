CREATE FUNCTION vesna.generiraj_polisa(tos_ponudaid integer,
                tuser_id integer)
                returning integer,char(100);
{
procedurata vraka:

        - kod na greskasta
                  1 ako se e ok i ako e izvrseno
                 -1 ako se pojavi nekoja neregularnost
                 
        - poraka poradi koja e nastanata greskata
}

define  dali_pregled,tpar_agentid,nrows,dali_odobril,t,tageplust,k , kolku,troleid ,tpar_polisa_statusid,tos_aneksid,tos_produktid_vrska int;
define tprist_starost,tperiod_osig,tos_produktid,godina_otkup int;
define tgama,alfa,tkamatna_stapka,beta,nx_age, dx_age,nx_agek,a_age_k,nx_tageplust, dx_tageplust,mx_tageplust,ddx_tageplust, tiznos_den dec;
define a_xt_kt,nx_agen,gp,db,d,dx_agen,mx_age,mx_agen,a_beta,gamma1,alfa1,a_doziv,a_mesano dec;
define SA_doziv,SA_mesano,cash_value_doz,SA,unit_cost, gp_doz,cash_value_mesano dec;
define mr_mesano,pred_presm_mr,gp_mesano,net_profit,a_x_n,a_x_k,mr_doz,alfa2,CV,mr_doz_predpresm,_otkup,platena_premija,comision,a_xt_nt,trx_t,aa dec;
define tusername char(30);
define tpol,tpromena_polisa, tpromena_aneks, tzamena_polisa,tpol_brak,tpromena_cl_aneks  char(1);
define tponuda_broj char(10);
define tponuda_podbroj,tpolisa_podbroj,tvaluta char(3);
define ts_tar_gr,tos_produkt_tsid, dali_polisa,tosigurenik_par_client ,tos_polisaid,broj,tpar_polisa_promenaid,tvrska_os_ponudaid,pod_broj,tos_polisaid_stara,tperiod,tts_type_insuranceid int;
define tpolisa_broj char(7);
define tdatum_ponuda, tdatum_info date;
define dali_proknizeno,dali_ima_aneks,tos_aneksid_posleden,terr,novid,tos_aneks_fakturaid_posl,tpar_administrativni_trosid,dali_naplateno,tdogovoruvac_par_client,dali_polisa1 int;
define  poraka,toporaka char(100);
define tcomision ,     tfaktor_zilimier ,     tzilimer_rezerva ,tneto_rezerva, tkazna_otkup,tinzos,a_xt_nt1 decimal;
define tpar_trosoci_produkt,tpar_nacin_plati char(3);
define l1,l2,l3,l4,edin_bruto_premija,neto_premija,ddx_agen,ddx_age,tkazna_otkup_kap,discont,tnaplata_den,tnaplata,rx_age,rx_agek,rx_agen,rx_tageplust,tq_x_pr  decimal;
define tprodukt,ttip_produkt ,tprodukt1 char(4);
define tos_produkt_uplataid,tpar_nacin_platiid,nb,ageb,dali_pretarif,ti,tpar_statusid, tvrska_os_ponudaid_n,tpar_statusid_n int;
define mx_tagebplust, mx_tagenb,ddx_tagenb,tneto_rezerva_brak,totkupna_vred_brak,taxt_kt_brak,nx_tagenb,nx_agebplust,ddx_agebplust dec;
define  tedin_neto_premija_brak, tedin_bruto_premija_brak, tcom_brak, tedin_osig_suma_brak, SAb ,mx_tageb,nx_ageb,ddx_ageb,tax_n_brak dec;
define tv_0,tp_0,tl_a_x_nt,tv_x,tp_x,tq_x,ti_x,gtl_a_x_nt,axn4,alpha2,AExn,axk,kaxn_k,alpha1,nesreken_slucaj,bxn_nezgoda_deca,deca,tinvest_premija decimal ;
define Osxn,tvx_net,tqi_x,	nv_x,np_x,tKFt,	tRkft,	tRedt,ga_xt_nt,tvx_zilimer,tvwk_x,nqi_x,tdelta, tdopl_deca,s17,s11,tosig_suma,tpremija_den,tprocent_smrt decimal;
define tpar_Tablica_SmrtId,tbr_osig_lica,tkolku_novi,tpar_valutaid,tos_produkt_invest_fondid,tos_produkt_invest_smrtid,tos_tipproduktid,tbr_rati,trata int;
define tpar_polisa_promena varchar(5);
define tdatecrated,tdatumraganje,tskadenca_datum_do,tskadenca_datum_od,tdatum_faktura date;
define tpremija_za_rata,tpremija_smrt,talfa_trosok ,tbeta_trosok ,     tgama_trosok ,     tpremija_invest ,     tucestvo_trosoci ,     tucestvo_invest,g_smrt,ttt dec;
define tstatusid int8;
define tinv_clientid,tkolku_bolest int8;
define tdali_otkup varchar(1);
define tpolisa_broj_new,pol_ponuda_broj varchar(15);
define tf_dopolnitelno,tvinkulacija_broj,teee,tgodina_pristap,tos_aneks_rataid,dali int;
define tinvest_fond varchar(100);
define tsifra_polisa varchar(5);
define tponuda_prethodna char(10); --DODADENO NA 21.08.2025 ANETA 
 on exception
        ROLLBACK WORK;
        return       -1,'НАСТАНАТА Е ГРЕШКА';
end exception;

 --set debug file to "err_generiraj_ponuda.sql";
 --trace on;

set isolation to dirty read;

BEGIN WORK;

foreach select roleid into troleid from adm_userroles where userid=tuser_id
if troleid=750 then
	     ROLLBACK WORK;
     return -1,'НЕМАТЕ ПРИВИЛЕГИЈА ДА ГЕНЕРИРАТЕ ПОЛИСА.';
end if;
end foreach;
--proverka dali e pregledana ponudata

select count(*) into dali_pregled from os_ponuda
where os_ponudaid=tos_ponudaid
and datum_proverka  is  null;

if dali_pregled =1 then
                ROLLBACK WORK;
    return                             -1,'КОНКРЕТНАТА ПОНУДА НЕ Е ПРЕГЛЕДАНА';
end if;

select count(*) into dali_odobril from os_ponuda
where os_ponudaid=tos_ponudaid
and datum_odobruvanje  is  null;

if dali_odobril =1 then
                ROLLBACK WORK;
    return -1,'КОНКРЕТНАТА ПОНУДА НЕ Е ОДОБРЕНА';
end if;
select username into tusername from adm_user
where userid=tuser_id;
let tdali_otkup='0';
let gp=0 ;


select count(*) into dali_polisa1
from os_polisa
where os_ponudaid=tos_ponudaid;
select count(*) into dali_polisa
from os_polisa
where os_ponudaid=tos_ponudaid;
if dali_polisa =1 then
    ROLLBACK WORK;
    return   -1,'КОНКРЕТНАТА ПОЛИСА Е  ВЕЌЕ  ИЗГЕНЕРИРАНА';
end if;




select ponuda_broj, ponuda_podbroj ,os_produktid ,os_produkt_uplataid,skadenca_datum_do,dogovoruvac_par_client,os_produkt_invest_fondid,
os_produkt_invest_smrtid,invest_premija,skadenca_datum_od, par_Statusid,par_polisa_statusid
into tponuda_broj, tponuda_podbroj,tos_produktid,tos_produkt_uplataid,tskadenca_datum_do,tdogovoruvac_par_client,tos_produkt_invest_fondid,
tos_produkt_invest_smrtid,tinvest_premija,tskadenca_datum_od, tstatusid,tpar_polisa_statusid
from os_ponuda where os_ponudaid=tos_ponudaid;

 select produkt,inv_par_clientid,os_tipproduktid,sifra_polisa
		into tprodukt1, tinv_clientid,tos_tipproduktid, tsifra_polisa
 from  os_produkt where os_produktid=tos_produktid;
 
let pol_ponuda_broj=trim(tprodukt1) || '/'  || tponuda_broj;

select otp_code  into tprodukt from os_tipprodukt 
where os_tipproduktid=tos_tipproduktid ;

 if               tprodukt='РК' and nvl(tinv_clientid,0)<>0 and tstatusid<>40 then
	ROLLBACK WORK;
     	return -1,'ПОНУДАТА ТРЕБА ПРВО ДА СТАНЕ                     РЕАЛИЗИРАНА  ОД    СТРАНА НА  БАНКАТА.';
 end if;

select par_nacin_platiid into tpar_nacin_platiid
from os_produkt_uplata
where os_produkt_uplataid=tos_produkt_uplataid;

let tpar_polisa_promena='00000';

select par_nacin_plati,br_rati
 into tpar_nacin_plati, tbr_rati
from par_nacin_plati
where par_nacin_platiid=tpar_nacin_platiid;


select procent_smrt into tprocent_smrt
 from os_produkt_invest_smrt
 where os_produkt_invest_smrtid=tos_produkt_invest_smrtid;

if tponuda_podbroj='000' then
select count(*) into dali_polisa from os_ponuda where ponuda_broj=tponuda_broj and os_produktid=tos_produktid  ;  

if dali_polisa>1 then
	ROLLBACK WORK;
     	return  -1,'ПОСТОИ ПОНУДА СЕ ПОДБРОЈ РАЗЛИЧЕН     ОД 000';
end if;
end if; 



let d=0; --Unit Costs (d) ne znam sto znaci i kaj referira sega za sega ke ja ostavam 0
let unit_cost=0;
let alfa2=40;
        select prist_starost,period_osig,osigurenik_par_client,os_produktid ,traenje_uplata, 
		ponuda_broj, ponuda_podbroj,par_polisa_promenaid,vrska_os_ponudaid,datum_ponuda,par_polisa_statusid,br_osig_lica,datecreated
         into tprist_starost,tperiod_osig,tosigurenik_par_client,tos_produktid,k , tponuda_broj,
		 tponuda_podbroj,tpar_polisa_promenaid,tvrska_os_ponudaid,tdatum_ponuda,tpar_polisa_statusid,tbr_osig_lica,tdatecrated
        from os_ponuda
        where os_ponudaid=tos_ponudaid;
        select godina into godina_otkup
         from  os_produkt_otkup
         where os_produktid=tos_produktid;
         
if tponuda_podbroj<>'000' then
select count(*) into dali_polisa from l_steta
where par_tip_stetaid=8
and vrati_polisa(os_polisaid)in (select polisa_broj_cel  from os_polisa 
where  os_ponudaid=tvrska_os_ponudaid);

select count(*) into dali   from vesna.os_ponuda_detail
where os_ponudaid=tos_ponudaid
and ts_type_insuranceid=5;


if dali_polisa>0 and dali>0   then
	     ROLLBACK WORK;
     return  -1,'Понудата  има штета ТБС. Не може да се додаде ТБС осигурување!!';
end if;
end if;    
 
	select produkt,par_valutaid,os_tipproduktid
	into tprodukt,tpar_valutaid,tos_tipproduktid
        from  os_produkt
        where os_produktid=tos_produktid;
        select otp_code  into tprodukt from os_tipprodukt 
        where os_tipproduktid=tos_tipproduktid ;
		
	select otp_code  into ttip_produkt
	from os_tipprodukt
	where os_tipproduktid=tos_tipproduktid;
		 
	select valuta into tvaluta 
	from par_valuta
	where par_valutaid=tpar_valutaid;
		          
        select nvl(promena_polisa,0), nvl(promena_aneks,0),nvl(zamena_polisa,0) , par_polisa_promena,nvl(promena_cl_aneks,0),nvl(f_dopolnitelno,0)
	 into tpromena_polisa, tpromena_aneks, tzamena_polisa, tpar_polisa_promena,tpromena_cl_aneks,tf_dopolnitelno
 	from par_polisa_promena
 	where par_polisa_promenaid=tpar_polisa_promenaid;
 		let tpar_polisa_promena=tpar_polisa_promena;
		if tpar_polisa_promena is null then let tpar_polisa_promena='00000'; end if;

	if (tos_produktid=60) or  (tos_produktid=622)  then 
		let alfa2=40;
	end if;

	if tos_produktid=141 or  (tprodukt='КЖ' and tpar_polisa_promena='00016')  then 
		let alfa2=35;
	end if;
         select pol,datumraganje  into tpol,tdatumraganje
         from par_client
         where par_clientid=tosigurenik_par_client;
         
        if tosigurenik_par_client is null then 
		let tpol='K';
	end if; 
         -------
let  tpromena_polisa='0';
let  tpromena_aneks='0';
let tzamena_polisa='0';
let tpromena_cl_aneks='0';
let dali_pretarif=0;
let tpar_statusid=0;

         ---tuka delot ako e dozvolena promena na polisa so podbroj 001Slagjana 26.02.2013
if tponuda_podbroj <>'000' then   ---1  uslov 
		
		---- proverka dali e kapitalizirana ----

		select par_statusid, vrska_os_ponudaid   into  tpar_statusid, tvrska_os_ponudaid_n 
		from os_ponuda 
		where os_ponudaid=tvrska_os_ponudaid;
		
		if tpar_statusid=18 then
			let tvrska_os_ponudaid= tvrska_os_ponudaid_n;
		end if;

		select count(*) into dali_pretarif 
		from par_polisa_promena p  ,os_ponuda o 
		where o.par_polisa_promenaid=p.par_polisa_promenaid
		and os_ponudaid=tvrska_os_ponudaid
		and pretarifiranje=1;

		if dali_pretarif=0 then 
		
			select count(*) into dali_pretarif 
			from par_polisa_promena p  ,os_ponuda o 
			where o.par_polisa_promenaid=p.par_polisa_promenaid
			and os_ponudaid=tos_ponudaid
			and dali_otkup=1;
			--and par_polisa_promena='00023';
		end if;

		if dali_pretarif=0 then 
			if nvl(tpar_polisa_statusid,0) not in (1,2) then
				select count(*) into dali_pretarif from os_ponuda o 
				where  os_ponudaid=tvrska_os_ponudaid
				and par_polisa_statusid=181;
			end if;
		end if;
         
         	select nvl(promena_polisa,0), nvl(promena_aneks,0),nvl(zamena_polisa,0) , par_polisa_promena,nvl(promena_cl_aneks,0), nvl(dali_otkup,0)
		into tpromena_polisa, tpromena_aneks, tzamena_polisa, tpar_polisa_promena,tpromena_cl_aneks,tdali_otkup
 		from par_polisa_promena
 		where par_polisa_promenaid=tpar_polisa_promenaid;
				 
		select  first 1 polisa_broj, os_polisaid 
 		  into tpolisa_broj, tos_polisaid_stara
 		from os_polisa 
		Where os_ponudaid =tvrska_os_ponudaid;

if tpar_polisa_promena is null then let tpar_polisa_promena='00000'; end if;
 
if tpar_polisa_promena='00024' or tpar_polisa_promena='00025' or  tpar_polisa_promena='00023' then ---tuka delot za promena na profesija ---28.12.2016
if ttip_produkt='UL' then
execute  procedure polisa_promena_osigurenik_ul(tos_ponudaid,		tuser_id,tdatecrated,tdatecrated)into tos_polisaid, toporaka;

if tos_polisaid=-1 then
	   ROLLBACK WORK;
     return -1,'НЕ Е  ИЗГЕНЕРИРАНА                     ПОЛИСАТА. ';
end if;

else 

if   tpar_polisa_promena='00023' then 

update os_ponuda  set prist_starost=year(tdatecrated)-year(tdatumraganje)
where os_ponudaid=tos_ponudaid;

select   count(*)  into tkolku_bolest  from os_ponuda_ar_bolest a , popis_bolesti_ar b
where a.popis_bolesti_arid=b.popis_bolesti_arid
and  os_PonudaId=tos_ponudaid;
    if tkolku_bolest>0 then
    execute  FUNCTION pom_ar_calculate(tos_ponudaid,		tuser_id )into terr, toporaka;
    end if; 
end if;

execute  procedure polisa_promena_profesija(tos_ponudaid,tuser_id,tpar_polisa_promena)	 into tos_polisaid, toporaka;


if tos_polisaid=-1 then
	   ROLLBACK WORK;
     return       -1,'НЕ Е                                  ИЗГЕНЕРИРАНА       ПОЛИСАТА. ';
end if;


end if; 

end if;

		
if tpar_polisa_promena<>'00024' and  tpar_polisa_promena<>'00025'   and  tpar_polisa_promena<>'00023' then		--tuka		
				
				
 if ((tpromena_polisa ='1') and (tzamena_polisa='0')) or  (tpar_polisa_statusid=2) then
		--tuka		

				 select  first 1 polisa_broj, os_polisaid 
 				into tpolisa_broj, tos_polisaid_stara
 				from os_polisa
				where os_ponudaid =tvrska_os_ponudaid;

				select (max(nvl(polisa_pod_broj,0))+1)  into pod_broj 
				from os_polisa p, os_ponuda o
				where o.os_ponudaid=p.os_ponudaid
				and o.os_produktid=tos_produktid 
				and p.polisa_broj=tpolisa_broj;

				if pod_broj is null then  ---10052022

				select os_produktid
 				into  tos_produktid_vrska
 				from os_ponuda
				where os_ponudaid =tvrska_os_ponudaid;

				select (max(nvl(polisa_pod_broj,0))+1)  into pod_broj 
				from os_polisa p, os_ponuda o
				where o.os_ponudaid=p.os_ponudaid
				and o.os_produktid=tos_produktid_vrska
				and p.polisa_broj=tpolisa_broj; 

				end if; ---10052022

				if pod_broj is null then  let pod_broj=0; end if;
				let tpolisa_podbroj=prefill(pod_broj,'0',3);
 			 
 else 
				select  os_polisaid 
 				  into  tos_polisaid_stara
 				   from os_polisa
				where os_ponudaid =tvrska_os_ponudaid;
			--tuka treba da se napravi promenata da go site brojot napolisata soglasno Produkt poleto 09.06.2014
			select (max(nvl(polisa_broj,0))+1)  into broj  from os_polisa
			where os_ponudaid in (select os_ponudaid from os_ponuda p, os_produkt o
			where o.os_produktid=p.os_produktid
			and o.produkt=tprodukt1);
		
			
				if broj is null then  let broj=101; end if;
        let tpolisa_broj=prefill(broj,'0',6);
 			         let tpolisa_podbroj='000';
 			end if;
end if;			
 			
	else  
        
       -- select (max(nvl(polisa_broj,0))+1) into broj from os_polisa;-- brojot brojot na polisata da ide spored brojot na prodkot Slagjana
	   if tpar_polisa_promena<>'00024' and  tpar_polisa_promena<>'00025' and  tpar_polisa_promena<>'00023' then	
      	 if tdatum_ponuda<=date('01.02.2013') then
 			 

 			 select (max(nvl(polisa_broj,0))+1)  into broj from os_polisa
				where os_ponudaid in (select os_ponudaid from os_ponuda 
			where os_produktid=tos_produktid)
			and polisa_broj <'001198';
			else
			select (max(nvl(polisa_broj,0))+1)  into broj  from os_polisa
			where os_ponudaid in (select os_ponudaid from os_ponuda p, os_produkt o
			where o.os_produktid=p.os_produktid
			and o.produkt=tprodukt1);
			-- select (max(nvl(polisa_broj,0))+1)  into broj from os_polisa
			--	where os_ponudaid in (select os_ponudaid from os_ponuda 
			--where os_produktid=tos_produktid);
			end if;
			if broj is null then  let broj=101; end if;
        let tpolisa_broj=prefill(broj,'0',6);
           let tpolisa_podbroj='000';
        
      end if;
	 end if;--tuka
         ----
        --------insert vo os_polisa
       -- select (max(nvl(polisa_broj,0))+1) into broj from os_polisa;-- brojot brojot na polisata da ide spored brojot na prodkot Slagjana
         --select (max(nvl(polisa_broj,0))+1)  into broj from os_polisa
			--	where os_ponudaid in (select os_ponudaid from os_ponuda 
	--		where os_produktid=tos_produktid);
--if broj is null then  let broj=1; end if;
       -- let tpolisa_broj=prefill(broj,'0',6);
	--tuka	
	 		if tpar_polisa_promena<>'00024' and  tpar_polisa_promena<>'00025' and  tpar_polisa_promena<>'00023' then
	let tos_polisaid=sq_os_polisaid.nextval;
        insert into os_polisa(os_polisaid,datechanged ,datecreated,userchanged,usercreated ,
    version,polisa_broj,polisa_pod_broj,os_ponudaid,par_statusid,status_polisa,datum_polisa,ponuda_broj)
         values (tos_polisaid, today, today, tusername,tusername,0,tpolisa_broj, tpolisa_podbroj
         , tos_ponudaid,1,'K',today,pol_ponuda_broj);
          let nrows = 0;
                let nrows = DBINFO('sqlca.sqlerrd2');
                        if nrows = 0 then
                        ROLLBACK WORK;
          return                       '-1','ПОЛИСАТА НЕ Е                                                                   АЖУРИРАНА';
                end if;
        select administrativni_tros,akvizacioni_tros,kamatna_stapka,inkaso_tros,par_administrativni_trosid,unit_cost_d

        into tgama,alfa,tkamatna_stapka,beta,tpar_administrativni_trosid,d
        from os_produkt
        where os_produktid=tos_produktid;

select administrativni_tros,akvizacioni_tros,kamatna_stapka,inkaso_tros,par_Tablica_SmrtId
into tgama,alfa,tkamatna_stapka,beta,tpar_Tablica_SmrtId
from os_produkt_ts
where os_produktid=tos_produktid
and ts_vid_rizik='Or'
and ((tdatum_ponuda between datum_od and datum_do) or (tdatum_ponuda >=datum_od and datum_do is null));	


		
		select par_trosoci_produkt into tpar_trosoci_produkt from par_trosoci_produkt 
		where par_trosoci_produktid=tpar_administrativni_trosid;
	
		
if (tprodukt='КЖ' and tpar_polisa_promena<>'00016') then
	let tpar_trosoci_produkt='003';
end if;

if (tprodukt='КЖ' and tpar_polisa_promena='00016') and tdatum_ponuda>'16.05.2016' then
	let tpar_trosoci_produkt='003';
end if;

if  tprodukt='ФБ'  then 
if (tpar_polisa_promena='00001'  or tpar_polisa_promena='00000') or (tpar_polisa_statusid=2) then 
  execute procedure pom_generiraj_prv_aneks (tos_ponudaid,tos_polisaid,tuser_id) into terr, poraka;
    if terr=-1 then 
     ROLLBACK WORK;
     return                                   -1,'ПРОБЛЕМ СО                                                     ГЕНЕРИРАЊЕ НА АНЕКС .';
  
  end if;
end if; 
   let tpar_statusid_n=17;
    
    if tpar_statusid=18 then 
    let tpar_statusid_n=18;
    end if; 
    if tpar_polisa_promenaid=2 then 
     let tpar_statusid_n=17;
    end if; 
        update os_ponuda set polisa='t',par_statusid=tpar_statusid_n, 
	     userchanged=tusername, datechanged=current, version=version+1
        where os_ponudaid=tos_ponudaid;


commit work;

return    '1','ПОЛИСАТА Е      ИЗГЕНЕРИРАНА';
end if;


    foreach    select tp.ts_tar_podgrupaid  into ts_tar_gr
        from ts_klasa k,ts_tarifa t, ts_tar_grupa tg, ts_tar_podgrupa tp
        where  k.ts_klasaid=t.ts_klasaid
        and tg.ts_tarifaid=t.ts_tarifaid
        and tp.ts_tar_grupaid=tg.ts_tar_grupaid
        and k.klasa||t.tarifa||tg.tar_grupa ='190101'
		
	
						select count(*)   into kolku 
 					from os_produkt_ts
					where ts_tar_podgrupaid=ts_tar_gr
					and os_produktid=tos_produktid
					and ((tdatum_ponuda between datum_od and datum_do) or (tdatum_ponuda >=datum_od and datum_do is null));
	if tprodukt='РИ' or             tprodukt='РК' or tprodukt='КР' then 	
		let gp=0 ;
	end if; 

	if tprodukt='CL' then 	
		let gp=0 ;
	end if; 		 
	if ttip_produkt='UL'   and  tpar_polisa_promena<>'00023' then 	
		let gp=tinvest_premija ;
		
        select os_polisaid
        into tos_polisaid
        from os_polisa
        where os_ponudaid=tos_ponudaid
;

	end if;
	if kolku>0 then
        select os_produkt_tsid,ts_type_insuranceid  into tos_produkt_tsid,tts_type_insuranceid  from os_produkt_ts
        where ts_tar_podgrupaid=ts_tar_gr
        and os_produktid=tos_produktid
	and ((tdatum_ponuda between datum_od and datum_do) or (tdatum_ponuda >=datum_od and datum_do is null));
             --   if tos_produkt_tsid is null  then
            --            ROLLBACK WORK;
        --  return                     '-1','ВО                                                       ПРОДУКТОТ МОРА   ДА                 ИМАТЕ  ДЕФИНИРАНО             МЕШАНО  ОСИГУРУВАЊЕ';
        --        end if;

        select os_polisaid
        into tos_polisaid
        from os_polisa
        where os_ponudaid=tos_ponudaid
;


        select nvl(iznos_premija,0), osig_suma
        into gp, tosig_suma
        from os_ponuda_detail
        where os_ponudaid=tos_ponudaid
        and os_produkt_ts_id=tos_produkt_tsid
        and datum_pocetok is null;
		end if;
		end foreach; 
	


	
	if gp=0  and  tprodukt<>'РИ'   and  tprodukt<>'CL'  and                 tprodukt<>'РК' and  tprodukt<>'КР'  and  tprodukt<>'ФБ'  then
                        ROLLBACK WORK;
          return                     '-1','ВО    ПРОДУКТОТ  МОРА ДА ИМАТЕ               ДЕФИНИРАНО МЕШАНО                        ОСИГУРУВАЊЕ';
     end if;
	 
 if  tpar_polisa_promena='00016' then ---tuka delot za novite osigirenici za kolektivno  ---12.04.2017

select count(*) into tkolku_novi 
from os_ponuda_osigurenici
where os_ponudaid=tos_ponudaid
and par_statusid=34
and datum_pocetok=tdatecrated;
 if tkolku_novi>0 then 
 execute procedure konverzija(tdatecrated,gp,tvaluta,'MKD') into tpremija_den; 
 
 execute  function osig_suma_calculate(gp, tos_ponudaid) into tosig_suma;
 
 insert into os_ponuda_detail(     os_ponuda_detailid ,  datecreated ,      usercreated ,
     version , iznos_premija ,     iznos_premija_den ,     kolicina ,     osig_suma ,  ts_vid_rizik ,
          par_statusid ,     os_ponudaid ,      os_produkt_ts_id,datum_pocetok,ts_type_insuranceid) 
	 values (sq_os_ponuda_detailid.nextval , current, tusername,0 ,gp ,tpremija_den ,tkolku_novi ,tosig_suma ,
	 'Or' , 1,tos_ponudaid,tos_produkt_tsid,tdatecrated,tts_type_insuranceid);
 
  let tperiod_osig=year(tskadenca_datum_do)-year(tdatecrated);
  let k=tperiod_osig;
end if;


 
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
if dx_age=0 then
 let a_age_k=0;
else 
        let a_age_k=(nx_age- nx_agek)/dx_age;
end if;
if dx_age=0 then
let a_x_n =0;
else 
        let a_x_n = (nx_age- nx_agen)/dx_age;
end if;

---vo slucaj ako ima pretarifiranje ----prekopiranje na stavkite---16.02.2016 Slagjana
if dali_pretarif>0  or tdali_otkup='1'   then

        insert  into os_polisa_otkup ( os_polisa_otkupid ,datechanged,datecreated ,userchanged ,usercreated ,
    version,os_polisaid,godini,godini_osiguruvanje,ax_k ,axt_kt,ax_n,gross_premium_doz,
    matematcka_rezerva_doz,profit_doz,gross_premium,profit_Participation,
    otkupna_vred,osigur_vred,kapitalizirana_vred,matematcka_rezerva,par_statusid,     faktor_zilimier ,
     zilimer_rezerva ,     bruto_rezerva ,     kazna_otkup,neto_rezerva ,rx_fu,neto_rezerva_brak,otkupna_vred_brak,axt_kt_brak ,
    rata,	premija_za_rata,	premija_smrt,	alfa_trosok,	beta_trosok,	gama_trosok,	premija_invest,	ucestvo_trosoci,	
     ucestvo_invest,	datum_faktura,	f_udel,	f_kapitaizacija,	f_udel_odbelezi)
 select os_polisa_otkupid.nextval, today, today, tusername,tusername,0, tos_polisaid,godini,godini_osiguruvanje
 ,ax_k ,axt_kt,ax_n,gross_premium_doz,
    matematcka_rezerva_doz,profit_doz,gross_premium,profit_Participation,
    otkupna_vred,osigur_vred,kapitalizirana_vred,matematcka_rezerva,par_statusid,     faktor_zilimier ,
     zilimer_rezerva ,     bruto_rezerva ,     kazna_otkup,neto_rezerva ,rx_fu,neto_rezerva_brak,otkupna_vred_brak,axt_kt_brak,
    rata,	premija_za_rata,	premija_smrt,	alfa_trosok,	beta_trosok,	gama_trosok,	premija_invest,	ucestvo_trosoci,	
     ucestvo_invest,	datum_faktura,	f_udel,	f_kapitaizacija,	f_udel_odbelezi
	 from os_polisa_otkup
	 where os_polisaid=tos_polisaid_stara;


else





  if tpar_trosoci_produkt ='002'  and  tprodukt<>'КО' then ----tuka po staro ---promil za OS 03.06.2014Slagjana 

        ---sheet SA-----od kalkulatorot

        let platena_premija=gp*k;
        let platena_premija=gp*k;
        ---- sega za sega ke go ostavam fiksno otkako ke se resi  so provizijata sifrarnik
if tosigurenik_par_client is null then 
let comision=(platena_premija*1.5/100)+(platena_premija*1/100)+(platena_premija*0.5/100)+(platena_premija*0.5/100);
else
let comision=(platena_premija*3.30/100)+(platena_premija*1.60/100)+(platena_premija*1/100)+(platena_premija*0.60/100);
end if;
        ---     let cash_value_mesano=round((((mx_age-mx_agen)/dx_age+dx_agen/dx_age)*SA)+(alfa/1000*SA)+(tgama/1000*SA*a_x_n));
--      let gp_mesano=round((cash_value_mesano/(a_x_k*(1-beta/100)))+(unit_cost/(1-beta/100)));
let cash_value_mesano=gp * ((a_age_k*(1-beta/100)));
let SA=round(((cash_value_mesano)-(comision))/(((mx_age-mx_agen)/dx_age+dx_agen/dx_age) +(tgama/1000*a_x_n)));
let alfa=round((comision/SA)*1000,2);


        let db=d/(1-(beta/100));
        let a_beta=(1-(beta/100))*a_age_k;
        let gamma1= (tgama/1000)*a_x_n;
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
                let cash_value_doz=round(((dx_agen/dx_age)*SA)+(alfa/1000*SA)+(tgama/1000*SA*a_x_n));
                let cash_value_mesano=round((((mx_age-mx_agen)/dx_age+dx_agen/dx_age)*SA)+(alfa/1000*SA)+(tgama/1000*SA*a_x_n));
                ---let cash_value_mesano=((((mx_age-mx_agen)/(dx_age+dx_agen))/dx_age)*SA)+(alfa/1000*SA)+(tgama/1--000*SA*a_x_n);
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


              --let pred_presm_mr=((((mx_age-mx_agen)/dx_age+dx_agen/dx_age)*SA+(alfa2/1000)*SA)/a_x_k);
			if tprodukt='КЖ' then

			let pred_presm_mr=((((mx_age-mx_agen)/dx_age+dx_agen/dx_age)*SA+(alfa2/1000)*SA)/a_x_k)*a_xt_kt;
			else
			let pred_presm_mr=((((mx_age-mx_agen)/dx_age+dx_agen/dx_age)*SA+(alfa2/1000)*SA)/a_x_k)*a_xt_kt;
			end if;
        end if;
		
		
		   let mr_mesano=round((((mx_tageplust -mx_agen)/dx_tageplust+dx_agen/dx_tageplust)*SA));
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


        ----vo os_polisa_otkup se insertiraat site vrednosti od Shetot Output
        insert  into os_polisa_otkup ( os_polisa_otkupid ,datechanged,datecreated ,userchanged ,usercreated ,
    version,os_polisaid,godini,godini_osiguruvanje,ax_k ,axt_kt,ax_n,cash_value_doz,gross_premium_doz,
    matematcka_rezerva_doz,profit_doz,gross_premium,profit_Participation,
    otkupna_vred,osigur_vred,kapitalizirana_vred,matematcka_rezerva,par_statusid)
    values
    (os_polisa_otkupid.nextval, today, today, tusername,tusername,0, tos_polisaid,tageplust,t,a_x_k,a_xt_kt,a_x_n,
    cash_value_doz, gp_doz,mr_doz,0,gp_mesano,0, _otkup,cash_value_mesano,round(cv),round(mr_mesano),1);
    let nrows = 0;
                let nrows = DBINFO('sqlca.sqlerrd2');
                if nrows = 0 then
                ROLLBACK WORK;
          return                                                                       '-1','ПОЛИСА                                     ДЕТАИЛ НЕ   Е                 АЖУРИРАНА';
        end if;
        let t=t+1;
        end while;
		
	end if;	--05.12.2023
	-------------
	let  trx_t=0; let tneto_rezerva_brak=0;   let totkupna_vred_brak=0;   let taxt_kt_brak=0; 
	
	 if tpar_trosoci_produkt ='003' and tprodukt<>'РИ'  and  tprodukt<>'РК' then ----tuka po novo ---% za GP 03.06.2014 Slagjana 

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

		--let db=comision/a_age_k; 
		IF tpar_nacin_plati<>'005' then
		let db=comision/a_age_k; --alfa
		else
		let db=0.065; --alfa
		let tgama=1;
		end if;

		let gamma1= (tgama/100)*(a_x_n/a_age_k);
		if k=1 then
		let neto_premija=a_mesano;
		let edin_bruto_premija=(mx_age-mx_agen+ddx_agen+db*ddx_age)/(ddx_age-(tgama/100)*(nx_age-nx_agen));
		else
		let edin_bruto_premija=(db+neto_premija)/(1-gamma1);
		end if;
		if tprodukt='ФУ'  or tprodukt='ФЗ' then

		if k=1 then--20.09.2017 promena
		let db=0.065; --alfa
		let tgama=1;
		let edin_bruto_premija=(ddx_agen+db*ddx_age)/(ddx_age-(tgama/100)*(nx_age-nx_agen)-(mx_age-mx_agen));
		else
		let edin_bruto_premija=(ddx_agen+comision*ddx_age)/((1-gamma1)*(nx_age-nx_agek)-(rx_age-rx_agek-k*mx_agen));
		let neto_premija=(ddx_agen+edin_bruto_premija*(rx_age-rx_agen-k*mx_agen))/(nx_age-nx_agek);
		end if;
		end if; 
		
		if tprodukt='КЖ' then
		let neto_premija=(mx_age-mx_agen+ddx_agen)/(nx_age-nx_agek);
		let s17=(mx_age-mx_agen+ddx_agen);
		let s11=(nx_age-nx_agek);
		let edin_bruto_premija=(s17+(tgama/100)*s11)/((s11*(1-beta/100))- (ddx_age*tperiod_osig*alfa/100));
		end if;
		let SA_mesano=1/edin_bruto_premija;
        let SA=SA_mesano*gp;

		
        -------------end sheet SA
        ---sheet         премии,                                               резерви... -------
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
					let SA_doziv=(ddx_agen+db*ddx_age)/(ddx_age-(tgama/100)*(nx_age-nx_agen));
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
		
		
		
		
		if             tprodukt='ФУ'  or  tprodukt='ФЗ' then
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
		---	  	во     период     на                                                                                                 капитализација	5%
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
		---	  	во                               период на                                 капитализација	5%
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
      	if  t=tperiod_osig then 
 		let cv=tosig_suma;
		let _otkup=tosig_suma;
	end if;


        ----vo os_polisa_otkup se insertiraat site vrednosti od Shetot Output
        insert  into os_polisa_otkup ( os_polisa_otkupid ,datechanged,datecreated ,userchanged ,usercreated ,
    version,os_polisaid,godini,godini_osiguruvanje,ax_k ,axt_kt,ax_n,cash_value_doz,gross_premium_doz,
    matematcka_rezerva_doz,profit_doz,gross_premium,profit_Participation,
    otkupna_vred,osigur_vred,kapitalizirana_vred,matematcka_rezerva,par_statusid,comision ,     faktor_zilimier ,
     zilimer_rezerva ,     bruto_rezerva ,     kazna_otkup,neto_rezerva ,rx_fu,neto_rezerva_brak,otkupna_vred_brak,axt_kt_brak)
    values
    (os_polisa_otkupid.nextval, today, today, tusername,tusername,0, tos_polisaid,tageplust,t,a_x_k,a_xt_kt,a_xt_nt,
    0, 0,0,0,0,0, round(_otkup),0,round(cv),round(mr_mesano),1,tcomision ,     tfaktor_zilimier ,
     tzilimer_rezerva ,     mr_mesano ,    tkazna_otkup,tneto_rezerva, trx_t ,tneto_rezerva_brak,totkupna_vred_brak,taxt_kt_brak);
    let nrows = 0;
                let nrows = DBINFO('sqlca.sqlerrd2');
                if nrows = 0 then
                ROLLBACK WORK;
          return                                                         '-1','ПОЛИСА               ДЕТАИЛ НЕ Е    АЖУРИРАНА';
        end if;
        let t=t+1;
        end while;
		
	end if;	
end if;	
--end if;	 --5.12.2023
	---------------
	---noviot produkt 24.03.2016

if             tprodukt='КО' and  tpar_polisa_promena='00000'   then	
let t=0;


	select gama,doplatok_deca
	into tdelta, tdopl_deca
	from os_produkt_ts
	where os_produktid=tos_produktid
	and ts_vid_rizik='Or'
	and par_statusid=1;
while t<=tperiod_osig
   let tageplust=tprist_starost+t;
let tl_a_x_nt=0;
let axn4=0;

select qx,ix into tq_x,ti_x
from tablica_smrt
where godini=tprist_starost+t
and pol=tpol
and kamatna_stapka=tkamatna_stapka
and par_Tablica_SmrtId=tpar_Tablica_SmrtId;


let nqi_x=	tq_x+ti_x-(tq_x*ti_x);
let nv_x=power(1/(1+tkamatna_stapka/100),t);
execute  function vrati_px_t(t, tpol,tkamatna_stapka,tprist_starost,tpar_Tablica_SmrtId)  into np_x;


let ti=tperiod_osig-1;

WHILE (ti >=t) LOOP

let tv_x=power(1/(1+tkamatna_stapka/100),ti);
execute  function vrati_px_t(ti, tpol,tkamatna_stapka,tprist_starost,tpar_Tablica_SmrtId)  into tp_x;

if ti<4 then
let axn4=axn4+tv_x*tp_x;
end if;		
let tl_a_x_nt=tl_a_x_nt+tv_x*tp_x;	
LET ti = ti -1;

END LOOP;

let a_xt_nt=tl_a_x_nt/nv_x/np_x;

let gtl_a_x_nt=0;

if t=0 then 
let axk=tl_a_x_nt;
end if;
let ti=tperiod_osig;

WHILE (ti >=t) LOOP

let tv_x=power(1/(1+tkamatna_stapka/100),ti+1);
	
select qx,ix into tq_x,ti_x
from tablica_smrt
where godini=tprist_starost+ti
and pol=tpol
and kamatna_stapka=tkamatna_stapka
and par_Tablica_SmrtId=tpar_Tablica_SmrtId;
execute  function vrati_px_t(ti, tpol,tkamatna_stapka,tprist_starost,tpar_Tablica_SmrtId)  into tp_x;

let tqi_x=tq_x+ti_x-(tq_x*ti_x);
if 	ti=tperiod_osig then
let tv_x=power(1/(1+tkamatna_stapka/100),ti);
let gtl_a_x_nt=gtl_a_x_nt+tv_x*tp_x;	
else	
let gtl_a_x_nt=gtl_a_x_nt+tqi_x*tv_x*tp_x;	
end if;
 LET ti = ti -1;

END LOOP;

let ga_xt_nt=gtl_a_x_nt/nv_x/np_x;
let tfaktor_zilimier=0.035;

if t=0 then 
if tl_a_x_nt<>0 then
let neto_premija=gtl_a_x_nt/tl_a_x_nt;
else
let neto_premija=0;
end if;
let AExn=gtl_a_x_nt;

let alpha1=tkamatna_stapka/100;
let a_beta=beta/100;
let alpha2=0.01;
let gamma1= (tgama/100);
let kaxn_k=0;
let edin_bruto_premija=(AExn+gamma1*axk+gamma1*kaxn_k)/(axk*(1-a_beta)-k*(alpha1+alpha2*axn4));
let nesreken_slucaj=tdelta/100;
let deca=tdopl_deca/100;

let bxn_nezgoda_deca=edin_bruto_premija+nesreken_slucaj+deca;
let Osxn=1/bxn_nezgoda_deca;
let SA=Osxn*gp;
		


end if;

let tzilimer_rezerva=neto_premija+tfaktor_zilimier/axk;
let tvx_net=ga_xt_nt-neto_premija*a_xt_nt;
let tvx_zilimer=ga_xt_nt-tzilimer_rezerva*a_xt_nt;

if t<k then
	let tVWK_x=gamma1*(a_xt_nt-a_xt_nt*a_xt_nt/axk);

else
	let tVWK_x=gamma1*a_xt_nt;
end if;
let tVWK_x=0;
if t=tperiod_osig then
	let tKFt=1;
else
if 0.79+0.0075*t<0.8 then 

	let tKFt=0;
else
	let tKFt=0.79+0.0075*t;
end if;
end if;
 let tRkft=tKFt*(tvx_zilimer+tVWK_x);
let tRedt=tRkft/(gtl_a_x_nt+gamma1*a_xt_nt);

	
	if t<=godina_otkup then
              let cv=0;
			  let _otkup=0;
       else
		let _otkup=(tvx_zilimer+tVWK_x)*tKFt*SA;	
          let cv=_otkup/(ga_xt_nt+a_xt_nt*gamma1);
      end if;


 insert  into os_polisa_otkup ( os_polisa_otkupid ,datechanged,datecreated ,userchanged ,usercreated ,
    version,os_polisaid,godini,godini_osiguruvanje,ax_k ,axt_kt,ax_n,cash_value_doz,gross_premium_doz,
    matematcka_rezerva_doz,profit_doz,gross_premium,profit_Participation,
    otkupna_vred,osigur_vred,kapitalizirana_vred,matematcka_rezerva,par_statusid,comision ,     faktor_zilimier ,
     zilimer_rezerva ,     bruto_rezerva ,     kazna_otkup,neto_rezerva,qxt,	vt,	tpx,KFt,	Rkft,	Redt )
    values
    (os_polisa_otkupid.nextval, today, today, tusername,tusername,0, tos_polisaid,tageplust,t,tl_a_x_nt,a_xt_nt,a_xt_nt,
    0, 0,0,0,0,0, round(_otkup),SA,round(cv),tVWK_x,1,0 ,     tfaktor_zilimier ,
     tzilimer_rezerva , tvx_zilimer , 0,tvx_net,nqi_x,	nv_x,np_x,tKFt,	tRkft,	tRedt);
    let nrows = 0;
                let nrows = DBINFO('sqlca.sqlerrd2');
             if nrows = 0 then
                ROLLBACK WORK;
          return                                     '-1','ПОЛИСА                                     ДЕТАИЛ   НЕ Е                                           АЖУРИРАНА';
        end if;
	if t=0 then 
	update os_polisa set    osnova_premija= edin_bruto_premija* sa,
     premija_deca=deca*sa ,
     premija_nezgoda= nesreken_slucaj*sa
	where os_polisaid=tos_polisaid;
	
	end if; 
        let t=t+1;

    end while;

end if;
end if; --tuka

--- the end noviot produkt 24.03.2016
------UNIT LINK ------26.09.2017-----

if ttip_produkt='UL'  and  tpar_polisa_promena<>'00023' then 	
	let g_smrt=tprocent_smrt/100*gp*tperiod_osig;
	let t=1;

let db=alfa/100*gp*tperiod_osig;
let tdatum_faktura=tskadenca_datum_od;

while t<=tperiod_osig


select qx into tq_x_pr
from tablica_smrt
where godini=tprist_starost+t-1
and pol=tpol
and kamatna_stapka=tkamatna_stapka
and par_Tablica_SmrtId=tpar_Tablica_SmrtId;

let tq_x=1-power((1-tq_x_pr),(1/tbr_rati));
let tageplust=tprist_starost+t;
	let trata=1;
	while trata<=tbr_rati
	let talfa_trosok=0;
	let tbeta_trosok=0;
	let tpremija_za_rata=0;
	if tpar_nacin_plati='005' then 
		if t=0 then
			let tpremija_za_rata=gp;
		else
			let tpremija_za_rata=0;
		end if;
	else
		let tpremija_za_rata=gp/tbr_rati;
	end if; 
	if tpar_nacin_plati='005' then 
		let tpremija_smrt=(tq_x*120/100)*g_smrt;
		
		if t<=1 then 
			let talfa_trosok=alfa/100*gp;
			let tgama_trosok=2.5*gp;
		end if; 
	else
		--let tpremija_smrt=(1- power((1-tq_x*120/100),(1/tbr_rati)))*g_smrt;
		let tpremija_smrt=tq_x*g_smrt;
		if t<=5 then 
		
		if tskadenca_datum_od<'01.12.2017' then 
			let talfa_trosok=db/(5*tbr_rati);
		else
			if tperiod_osig>=25 then 
			let tperiod=25;
			else 
			let tperiod=tperiod_osig;
			end if;
			let db=alfa/100*gp*tperiod;
			
		if t=1 then
			let talfa_trosok=db*(3.5/alfa)/(tbr_rati);
			
		end if;
		if t>1 AND t<5  then
			let talfa_trosok=db*(1/alfa)/(tbr_rati);
		end if;
	
			
		end if ;
		
		end if; 
		let tbeta_trosok=beta/100*gp;
		let tgama_trosok=(1-0.45)*(1-0.3+tperiod_osig/100)*(0.5/100)*gp;
		
	end if;
	
		let tpremija_invest=tpremija_za_rata-(tpremija_smrt+talfa_trosok+(tbeta_trosok/tbr_rati)+(tgama_trosok/tbr_rati));
	if tpremija_za_rata=0 then
		let tucestvo_trosoci=0;
		let tucestvo_invest=0;
	else 

		let tucestvo_trosoci=((tpremija_smrt+talfa_trosok+(tbeta_trosok/tbr_rati)+(tgama_trosok/tbr_rati))/tpremija_za_rata)*100;
		let tucestvo_invest=(tpremija_invest/tpremija_za_rata)*100;
	end if;
		insert into os_polisa_otkup(os_polisa_otkupid , datecreated , usercreated ,     version ,     os_polisaid ,
		 godini ,     godini_osiguruvanje ,     qxt , rata ,premija_za_rata ,  premija_smrt ,     alfa_trosok ,
		 beta_trosok ,     gama_trosok ,     premija_invest ,     ucestvo_trosoci ,     ucestvo_invest ,     par_statusid,	datum_faktura)
		 values ( os_polisa_otkupid.nextval,  today, tusername,0, tos_polisaid,tageplust,t,tq_x,trata,tpremija_za_rata,tpremija_smrt,
		 talfa_trosok,tbeta_trosok/tbr_rati  ,     tgama_trosok/tbr_rati ,     tpremija_invest ,     tucestvo_trosoci ,     tucestvo_invest,1,	tdatum_faktura);
		let trata=trata+1;

	end while;

let t=t+1;
let tdatum_faktura=tdatum_faktura +1 units year;

end while;

---presmetka na informativna presmetka 09.8.2019
let tgodina_pristap =year(tskadenca_datum_od)-tprist_starost;
select invest_fond into tinvest_fond
 from os_produkt_invest_fond
 where os_produkt_invest_fondid=tos_produkt_invest_fondid;
 if tpolisa_podbroj<>'000' then 
    let tdatum_info=tdatecrated;
 else 
    let tdatum_info=tdatum_ponuda;
  end if;  

execute  FUNCTION info_fond_calculate(gp, tpol,tperiod_osig,k,tos_produktid,tos_polisaid,tprocent_smrt,tbr_rati,tgodina_pristap,tpar_nacin_plati, tskadenca_datum_od,tusername,tinvest_fond , tdatum_info ) into ttt;

if  (tpar_polisa_statusid=1) then 
execute  FUNCTION ul_kapitalizicija_polisa(tos_polisaid,tuser_id )into terr, toporaka;

 if terr=-1 then 
     ROLLBACK WORK;
     return -1,toporaka;
  
  end if;
end if; 
if  (tpar_polisa_statusid=2) then 


 
            if tpar_nacin_plati ='005' then
              let g_smrt=tprocent_smrt/100*tinvest_premija;
            else
              let g_smrt=tprocent_smrt/100*tinvest_premija*tperiod_osig;
            end if;
			
			update os_ponuda_detail set   osig_suma_smrt=g_smrt
			where os_ponudaid=tos_ponudaid;
			
			insert into os_polisa_otkup(os_polisa_otkupid , datecreated , usercreated ,     version ,     os_polisaid ,
		 godini ,     godini_osiguruvanje ,     qxt , rata ,premija_za_rata ,  premija_smrt ,     alfa_trosok ,
		 beta_trosok ,     gama_trosok ,     premija_invest ,     ucestvo_trosoci ,     ucestvo_invest ,     par_statusid,	datum_faktura,f_kapitaizacija)
			select os_polisa_otkupid.nextval,  today, tusername,0, tos_polisaid,		godini ,     godini_osiguruvanje ,     qxt , rata ,premija_za_rata ,  premija_smrt ,     alfa_trosok ,
		 beta_trosok ,     gama_trosok ,     premija_invest ,     ucestvo_trosoci ,     ucestvo_invest ,     par_statusid,	tdatecrated,1
		 from   os_polisa_otkup
		where os_polisaid=tos_polisaid_stara
		and f_udel=1;	

end if;


end if;
-----the end UNIT LINK -------26.09.2017------

--- ako e produktot za STB generiraj vinkulacija 30.12.2019

if tos_produktid=2040 and (tpar_polisa_promena='00001'  or tpar_polisa_promena='00000') then 

select max(vinkulacija_broj) +1 into tvinkulacija_broj from os_vinkulacija;


insert into os_vinkulacija(os_vinkulacijaid,datecreated,usercreated,	version,	datum_do,	datum_od,
	datum_vinkulacija,	vinkulacija_broj,	par_statusid,	os_polisaid,	par_clientid)
values(sq_os_vinkulacija.nextval, current, tusername, 0, tskadenca_datum_do,tskadenca_datum_od,tdatum_ponuda, 
tvinkulacija_broj, 1, tos_polisaid, 617);
end if;	
--generiraj prv aneks ---16.09.2019
if  dali_polisa1=0  then  
	if tpromena_aneks='2'  then 
  		execute procedure generiraj_prv_aneks_riziko (tos_ponudaid,tos_polisaid,tuser_id) into terr, poraka;
  		if terr=-1 then 
     			ROLLBACK WORK;
			return -1,'ПРОБЛЕМ СО ГЕНЕРИРАЊЕ НА АНЕКС.';
  
  		end if;
	end if;
	if (tpar_polisa_promena='00001'  or tpar_polisa_promena='00000') or (tpar_polisa_statusid=2) then 
  		execute procedure pom_generiraj_prv_aneks (tos_ponudaid,tos_polisaid,tuser_id) into terr, poraka;
    		if terr=-1 then 
     			ROLLBACK WORK;
     			return   -1,'ПРОБЛЕМ СО ГЕНЕРИРАЊЕ НА АНЕКС.';
  
  		end if;
	end if; 
end if; 


        
     ------07.06.2013 Slagjana  storno aneks     vo slucaj ako ima promena na polisa 
     if tpar_polisa_promenaid is not null and tpromena_polisa ='1'  and  tpromena_aneks='1' then 
-- select count(*) into dali_ima_aneks
-- from os_aneks 
-- where os_polisaid=tos_polisaid_stara;
--promena na datum vazenje vo odnos na datum na godisnica 05.12.2019 Slagjana 
if                tprodukt<>'КР'then 
execute  procedure vrati_polisa(tos_polisaid) into tpolisa_broj_new;

 select count(*) into dali_ima_aneks from os_aneks 
 where os_polisaid in (select os_polisaid from vw_pregled2_test
  where polisa_broj=tpolisa_broj_new)
 and godisnica_aneks=tdatecrated;
 
if tf_dopolnitelno=1 then 

if dali_ima_aneks=0 then
  select  max(os_aneksid)  into 
 tos_aneksid_posleden 
 from os_aneks 
 where os_polisaid in (select os_polisaid from vw_pregled2_test
  where polisa_broj=tpolisa_broj_new)
 and godisnica_aneks<tdatecrated;

update  os_aneks set gener_aneks=0, os_polisaid=tos_polisaid
where os_aneksid=tos_aneksid_posleden;

  execute procedure generiraj_aneks (tos_aneksid_posleden,tuser_id) into terr, poraka;
 else 
  select  max(os_aneksid)  into 
 tos_aneksid_posleden 
 from os_aneks 
 where os_polisaid in (select os_polisaid from vw_pregled2_test
  where polisa_broj=tpolisa_broj_new)
 and godisnica_aneks=tdatecrated;

update  os_aneks set gener_aneks=0, os_polisaid=tos_polisaid
where os_aneksid=tos_aneksid_posleden;

  execute procedure generiraj_aneks_dopolnitelno (tos_aneksid_posleden,tuser_id) into terr, poraka;
 
 end if; 
else


--promena na datum vazenje vo odnos na datum na godisnica 05.12.2019 Slagjana 

if dali_ima_aneks>0 then 

 select  max(os_aneksid)  into 
 tos_aneksid_posleden 
 from os_aneks 
 where os_polisaid=tos_polisaid_stara;

select count(*) into dali_proknizeno
from fin_stavka 
 where os_polisaid=tos_polisaid_stara
 and nal_vid is not null
and os_aneks_fakturaid in (select 
os_aneks_fakturaid from 
os_aneks_faktura where os_aneksid =tos_aneksid_posleden) ;


---proverka dali ima naplata 

select count(*) into dali_naplateno
from fin_stavka 
 where os_polisaid=tos_polisaid_stara
 and iznos_p is not null
and os_aneks_fakturaid in (select 
os_aneks_fakturaid from 
os_aneks_faktura where os_aneksid =tos_aneksid_posleden) ;



 if (dali_proknizeno> 0)  or (dali_naplateno >0) then 

 foreach select  os_aneks_fakturaid,iznos into tos_aneks_fakturaid_posl,tinzos 
 from os_aneks_faktura
 where os_aneksid= tos_aneksid_posleden
 and f_rs='R'
 
execute procedure vrati_naplata(tos_aneks_fakturaid_posl )  into tnaplata;

if tinzos-tnaplata<>0 then 

 let novid=sq_os_aneks_fakturaid.nextval;
insert into os_aneks_faktura(     os_aneks_fakturaid ,     
     datecreated ,          usercreated ,
     version ,     os_aneksid ,     par_tip_dokumentid ,
     par_tip_kniziid ,     rata ,     os_ponuda_detailid ,
     data_faktura ,     data_valuta ,  
	 iznos ,     iznos_denari ,   
	 par_statusid,f_rs)  
select
     novid,  current    ,   tusername,   0,
     os_aneksid ,     par_tip_dokumentid ,
     par_tip_kniziid ,     rata ,     os_ponuda_detailid ,     data_faktura ,
     data_valuta ,
	(iznos-vrati_naplata(os_aneks_fakturaid ))*(-1),	
	(iznos_denari-vrati_naplata_den(os_aneks_fakturaid ))*(-1) ,	    1,'S'
	 ---(-1)*iznos ,(-1)*iznos_denari 

from os_aneks_faktura
where os_aneks_fakturaid= tos_aneks_fakturaid_posl
and iznos-vrati_naplata(os_aneks_fakturaid )<>0;
--os_aneksid= tos_aneksid_posleden;
execute procedure vrati_naplata(tos_aneks_fakturaid_posl )  into tnaplata;
execute  procedure vrati_naplata_den(tos_aneks_fakturaid_posl )  into tnaplata_den;

 insert into fin_stavka (fin_stavkaid, datecreated, usercreated, version, par_filijalaid,
    par_tip_dokumentid, par_tip_kniziid, par_clientid, os_aneks_fakturaid,
    par_yearid, datum, datum_knizi,datum_stavka,datum_fakt_valuta, par_valutaid,
    par_kursid, os_polisaid,par_agent_id,  pat_tip_platiid,
   iznos_otvoren, f_rs,iznos_d,    iznos_d_den,
    par_statusid)
select sq_fin_stavka.nextval,current, tusername,0,      par_filijalaid ,
     par_tip_dokumentid ,     par_tip_kniziid ,
     par_clientid ,     novid ,     par_yearid ,     today ,
     today ,     today ,     datum_fakt_valuta ,
     par_valutaid ,    par_kursid ,     os_polisaid ,
     par_agent_id ,          pat_tip_platiid ,
      0 ,'S',(-1)*(iznos_d-tnaplata)
	  ,    (-1)*(iznos_d_den-tnaplata_den),   1
from fin_stavka
where os_aneks_fakturaid= tos_aneks_fakturaid_posl
and iznos_d-tnaplata_den<>0;
end if; 
--where os_polisaid=tos_polisaid_stara; 
-- update  os_aneks  set os_polisaid=tos_polisaid
 --where os_polisaid=tos_polisaid_stara;


-- update  fin_stavka   set os_polisaid=tos_polisaid
-- where os_polisaid=tos_polisaid_stara;
end foreach;
update os_aneks set (datechanged,userchanged,version,gener_aneks,os_polisaid
)=(  current,tusername,1,1,tos_polisaid ) 
where os_aneksid=tos_aneksid_posleden;

if tpar_polisa_promenaid <>706 then 
  execute procedure generiraj_aneks (tos_aneksid_posleden,tuser_id) into terr, poraka;
end if;

else


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

update  os_aneks set gener_aneks=0, os_polisaid=tos_polisaid
where os_aneksid=tos_aneksid_posleden;



  execute procedure generiraj_aneks (tos_aneksid_posleden,tuser_id) into terr, poraka;
---- ako nema proknizeno 
end if;
if tprodukt='КР' then--- tuka  da se povika _procedurata 02.04.2021
execute  procedure vrati_polisa(tos_polisaid) into tpolisa_broj_new;
	select count(*) into dali_ima_aneks from os_aneks_faktura
where os_aneksid in (
 select os_aneksid from os_aneks 
 where os_polisaid in (select os_polisaid from vw_pregled2_test
  where polisa_broj=tpolisa_broj_new))
   and ((tdatecrated >= data_faktura)  or (tdatecrated < data_faktura));
 if dali_ima_aneks>0 then 
foreach  select distinct  os_aneks_rataid into tos_aneks_rataid from os_aneks_faktura
where os_aneksid in (
 select os_aneksid from os_aneks 
 where os_polisaid in (select os_polisaid from vw_pregled2_test
  where polisa_broj=tpolisa_broj_new))
  and ((tdatecrated >= data_faktura)  or (tdatecrated < data_faktura))
  
    execute procedure kr_generiraj_aneks_promena  (tos_aneks_rataid, tos_ponudaid, tuser_id) into terr, poraka;

end foreach;
 
 
 end if; 
end if;
end if;
if tpromena_aneks='0' then 

update  os_aneks  set os_polisaid=tos_polisaid
 where os_polisaid=tos_polisaid_stara;
end if;
 
end if;    
end if;  
end if; --end za dopolnitelno 
     ----------------the end 
   if tpromena_aneks='0' and (tpar_polisa_promenaid is not null) then 
if tpromena_cl_aneks='1' then 
 select count(*) into dali_ima_aneks
 from os_aneks 
 where os_polisaid=tos_polisaid_stara;
if dali_ima_aneks>0 then 
 select  max(os_aneksid)  into 
 tos_aneksid_posleden 
 from os_aneks 
 where os_polisaid=tos_polisaid_stara;
 
 
select sum(iznos) , sum(iznos_denari)
into tinzos, tiznos_den
 from   os_aneks_faktura 
 where os_aneksid= tos_aneksid_posleden
 and f_rs='R'
and data_faktura>=tdatecrated;
 
 let tos_aneksid=sq_os_aneksid.nextval;
insert into os_aneks(os_aneksid , datecreated, usercreated,
    version, os_aneks , par_yearid, datum_aneks, datum_potpis,
    os_polisaid,par_clientid, par_valutaid, par_tip_platiid,
    br_rati,iznos_premija,     iznos_premija_den,
    par_statusid,godisnica_aneks,gener_aneks)
select  tos_aneksid,current,tusername,0,os_aneks,
    par_yearid,tdatecrated,current,
    tos_polisaid,tdogovoruvac_par_client,par_valutaid,par_tip_platiid,
    br_rati,tinzos,tiznos_den,1,godisnica_aneks,0
	from os_aneks 
where os_aneksid = tos_aneksid_posleden;

update os_aneks set gener_aneks='1'
where os_aneksid = tos_aneksid_posleden;



update  os_aneks_faktura set os_aneksid=tos_aneksid
 where os_aneksid= tos_aneksid_posleden
 and f_rs='R'
and data_faktura>=tdatecrated;


update  fin_stavka  set os_polisaid=tos_polisaid, par_clientid=tdogovoruvac_par_client
 where os_polisaid=tos_polisaid_stara
 and f_rs='R'
and datum>=tdatecrated;


end if; 
end if; 
update  os_aneks  set os_polisaid=tos_polisaid
 where os_polisaid=tos_polisaid_stara;
 
 update  fin_stavka   set os_polisaid=tos_polisaid
 where os_polisaid=tos_polisaid_stara;
end if; 
 execute  FUNCTION appuser.update_aneks_rata() into teee;   
    
    let tpar_statusid_n=17;
    
    if tpar_statusid=18 then 
    let tpar_statusid_n=18;
    end if; 
    if tpar_polisa_promenaid=2 then 
     let tpar_statusid_n=17;
    end if; 
    --DODADENO DA SE POLNI BROJ NA POLISA VO OS_PONUDA TABELATA NA 03.01.2025 ANETA
        update os_ponuda set polisa='t',par_statusid=tpar_statusid_n, 
	     userchanged=tusername, datechanged=current, version=version+1,
	     polisa_broj1=trim(tsifra_polisa)||'/'||tpolisa_broj
        where os_ponudaid=tos_ponudaid;
	--DODADENO NA 21.08.2025 ANETA
	if tos_produktid=2040 then

		LET tponuda_prethodna=0;

		select max(os_ponudaid) into tponuda_prethodna
		from os_ponuda
		where os_produktid=tos_produktid and ponuda_broj=tponuda_broj and par_statusid=17 and os_ponudaid<tos_ponudaid;

		if NVL(tponuda_prethodna,0)>0 then
			select count(*) INTO dali_pretarif
			from par_polisa_promena p ,os_ponuda o
			where o.par_polisa_promenaid=p.par_polisa_promenaid
				and os_ponudaid=tos_ponudaid
				and pretarifiranje>1;

			if dali_pretarif =1 then
				update os_ponuda
				set par_statusid=13,userchanged=tusername, datechanged=current, version=version+1
				where os_ponudaid=tponuda_prethodna;
			END IF;
		END IF;
	end if; 
--end if;
     --   ROLLBACK WORK;
    --    return       -1,'НАСТАНАТА Е ГРЕШКА';

commit work;
return   '1','ПОЛИСАТА Е ИЗГЕНЕРИРАНА';

end function;