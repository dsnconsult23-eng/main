CREATE FUNCTION vesna.generiraj_aneks_pretarifiranje(tos_ponudaid integer, tos_polisaid int,za_naredna_godina char(1),
tuser_id integer)
returning integer,char(100);
{
procedurata vraka:

- kod na greska
1 ako se e ok i ako e izvrseno
-1 ako se pojavi nekoja neregularnost
- poraka poradi koja e nastanata greskata
}


define dali_pregled,tpar_agentid,nrows,dali_aneks,tpar_yearid int;
define tskadenca_datum_od date;
define tdogovoruvac_par_client,tpar_valutaid,tpar_tip_platiid,tstara_polisaid,tosaneks_fakturaid,tos_aneks_fakturaid_nova int8;
define tbr_rati,tos_aneksid,  tos_produktid,tpar_nacin_platiid,tos_aneks_fakturaidar,tpar_tip_kniziidzr,tos_produkt_zdravstvenoid int8;
define tvk_iznos_premija,tvk_iznos_premija_den,tar_iznos,tar_iznos_denari,tiznos_premija, tsaldo_faktura, tsaldo_faktura_den decimal;
define tpar_tip_kniziidar,tbr_osig_lica int;
define tpar_tip_dokumentid, tpar_tip_kniziid,tpar_tip_kniziidk, trata , tos_ponuda_detailid,tpar_kursid,tos_polisaid,tpar_tip_kniziiddr,tpar_tip_kniziido int8;
define tdata_faktura, tdata_valuta,tdatum_aneks,tdatecreated,tdatum_aneks_nov,tgodisnica_aneks  date;
define tiznos,tiznos_denari decimal;
define tiznosk,tiznos_denarik,tproc_zgol_premija decimal;
define br_i, i,tos_aneks,dali_polisa,trok_plakanje,tpar_polisa_statusid,kolku_god,tvrska_os_ponudaid,tos_aneksid_star,tos_ponuda_detailid_star integer;
define tusername char(30);
define _ts_vid_rizik char(2);
define tpar_yearid_star,tdali_ima,tstarid int;

define tparfilijalaid,tos_aneks_fakturaid,tos_produkt_uplataid,tos_produkt_ts_id int8;
define  tos_aneks_rataid bigint;

on exception
--ROLLBACK WORK;
return -1,'NASTANATA E GRE[KA';
end exception;

--set debug file to "err_generiraj_prv_aneks.sql";
--trace on;

set isolation to dirty read;

--BEGIN WORK;
--select count(*) into dali_polisa
--from os_polisa
--where os_ponudaid=tos_ponudaid;
--if dali_polisa =0 then
-- ROLLBACK WORK;
-- return           -1,'КОНКРЕТНАТА ПОЛИСА НЕ Е                         ИЗГЕНЕРИРАНА';
--end if;

select username into tusername from adm_user
where userid=tuser_id;
select os_polisaid  into tos_polisaid from os_polisa
where os_ponudaid=tos_ponudaid;

select count(*) into dali_aneks from os_aneks
where os_polisaid =tos_polisaid;

let br_i=0;

if dali_aneks >0 then  --IF1 begin
    --ROLLBACK WORK;
    return -1,'ИЗГЕНЕРИРАН Е           АНЕКС ЗА             ПОЛИСАТА';
end if;  --IF1 end

select skadenca_datum_od,
dogovoruvac_par_client,
par_tip_platiid,vk_iznos_premija,vk_iznos_premija_den,os_produktid,os_produkt_uplataid,nvl(br_osig_lica,1),
par_polisa_statusid,vrska_os_ponudaid, datecreated
into
tskadenca_datum_od,
tdogovoruvac_par_client,
tpar_tip_platiid,tvk_iznos_premija,tvk_iznos_premija_den,tos_produktid,tos_produkt_uplataid,
tbr_osig_lica,tpar_polisa_statusid,tvrska_os_ponudaid, tdatecreated

from os_ponuda where os_ponudaid=tos_ponudaid;

select par_valutaid into tpar_valutaid
from os_produkt where os_produktid=tos_produktid;
if tvrska_os_ponudaid is not null then  --IF2 begin


    select os_polisaid into tstara_polisaid from os_polisa
    where os_ponudaid=tvrska_os_ponudaid;

    select max(os_aneksid)
    into tstarid
    from os_aneks
    where  os_polisaid=tstara_polisaid;
    let tstarid=tstarid;
    if tstarid is null then  --IF3 begin
        let tstarid=tstarid;
        while  tstarid is null ---02122022
            select vrska_os_ponudaid
            into tvrska_os_ponudaid
            from os_ponuda where os_ponudaid=tvrska_os_ponudaid;

            select os_polisaid into tstara_polisaid from os_polisa
            where os_ponudaid=tvrska_os_ponudaid;

            select max(os_aneksid)
            into tstarid
            from os_aneks
            where  os_polisaid=tstara_polisaid;

        end while;---02122022
    end if;  --IF3 end

    select max(godisnica_aneks)
    into tdatum_aneks
    from os_aneks
    where  os_polisaid=tstara_polisaid;


    select max(par_yearid) , max(os_aneksid)
    into tpar_yearid , tos_aneksid_star
    from os_aneks
    where  os_polisaid=tstara_polisaid
    and godisnica_aneks =tdatum_aneks;



    select par_year-year(tskadenca_datum_od) into kolku_god
    from par_year
    where par_yearid = tpar_yearid ;
    if za_naredna_godina='0'  then  --IF4 begin
        let tdatum_aneks_nov=tdatecreated;
        let tgodisnica_aneks=tskadenca_datum_od+(kolku_god)UNITS year;
    else  --IF4 else
        let tdatum_aneks_nov=tdatecreated;
        let tgodisnica_aneks=tskadenca_datum_od+(kolku_god+1)UNITS year;
        select par_yearid into tpar_yearid from par_year
        where par_year=year(tgodisnica_aneks);
    end if;  --IF4 end
else  --IF2 else
    select par_yearid into tpar_yearid from par_year
    where par_year=year(tskadenca_datum_od);
    let tdatum_aneks_nov=tskadenca_datum_od;
    let tgodisnica_aneks=tskadenca_datum_od;
end if;  --IF2 end
--where par_year=to_char(tskadenca_datum_od,'YYYY');
select par_nacin_platiid,nvl(proc_zgol_premija,0)
into tpar_nacin_platiid,tproc_zgol_premija
from  os_produkt_uplata
where os_produkt_uplataid=tos_produkt_uplataid;
select br_rati into tbr_rati from par_nacin_plati
where par_nacin_platiid=tpar_nacin_platiid;


select nvl(rok_plakanje,0) into trok_plakanje
from os_produkt
where os_produktid=tos_produktid;

select --nvl(((sum(nvl(iznos_premija,0))+sum(nvl(ar_iznos,0)))*2.6/100)/2,0)
nvl(((sum(nvl(iznos_premija,0))+sum(nvl(ar_iznos,0)))),0) ,
nvl(((sum(nvl(iznos_premija_den,0))+sum(nvl(ar_iznos_den,0)))),0)
into  tvk_iznos_premija,tvk_iznos_premija_den
from os_ponuda_detail
where os_ponudaid=tos_ponudaid;


select nvl(max(nvl(os_aneks,0)),0)+1 into tos_aneks from os_aneks;

let tos_aneksid=sq_os_aneksid.nextval;
if tpar_nacin_platiid=75  then  --IF5 begin


    insert into os_aneks(os_aneksid , datecreated, usercreated,
    version, os_aneks , par_yearid, datum_aneks, datum_potpis,
    os_polisaid,par_clientid, par_valutaid, par_tip_platiid,
    br_rati,iznos_premija, iznos_avans,iznos_faktura,
    iznos_premija_den,iznos_avans_den,iznos_faktura_den,
    par_statusid,gener_aneks,godisnica_aneks)
    values (tos_aneksid,current,tusername,0,tos_aneks,
    tpar_yearid,tdatum_aneks_nov,current,
    tos_polisaid,tdogovoruvac_par_client,tpar_valutaid,tpar_tip_platiid,
    tbr_rati,tvk_iznos_premija, null,null,tvk_iznos_premija_den,null,null,1,'1',tgodisnica_aneks);
else  --IF5 else

    insert into os_aneks(os_aneksid , datecreated, usercreated,
    version, os_aneks , par_yearid, datum_aneks, datum_potpis,
    os_polisaid,par_clientid, par_valutaid, par_tip_platiid,
    br_rati,iznos_premija, iznos_avans,iznos_faktura,
    iznos_premija_den,iznos_avans_den,iznos_faktura_den,
    par_statusid,godisnica_aneks)
    values (tos_aneksid,current,tusername,0,tos_aneks,
    tpar_yearid,tdatum_aneks_nov,current,
    tos_polisaid,tdogovoruvac_par_client,tpar_valutaid,tpar_tip_platiid,
    tbr_rati,tvk_iznos_premija*tbr_osig_lica, null,null,tvk_iznos_premija_den*tbr_osig_lica,null,null,1,tgodisnica_aneks);

end if;  --IF5 end

if tpar_polisa_statusid=2 then  --IF6 begin



    foreach select os_aneks_fakturaid , sum(nvl(iznos_d,0)- nvl(iznos_p,0)), sum(nvl(iznos_d_den,0)- nvl(iznos_p_den,0))
        into tosaneks_fakturaid, tsaldo_faktura, tsaldo_faktura_den
        from  fin_stavka
        where os_polisaid=tstara_polisaid
        group  by 1
        having sum(nvl(iznos_d,0)- nvl(iznos_p,0))>0

        select os_aneksid into tos_aneksid_star
        from  os_aneks_faktura
        where os_aneks_fakturaid=tosaneks_fakturaid;

        select par_yearid into tpar_yearid_star
        from os_aneks
        where os_aneksid = tos_aneksid_star;

        select count(*)  into tdali_ima
        from os_aneks
        where par_yearid = tpar_yearid_star
        and os_aneks=tos_aneks ;


        if tdali_ima=0 then  --IF7 begin
            let tos_aneksid=sq_os_aneksid.nextval;
            insert into os_aneks(os_aneksid , datecreated, usercreated,
            version, os_aneks , par_yearid, datum_aneks, datum_potpis,
            os_polisaid,par_clientid, par_valutaid, par_tip_platiid,
            br_rati,iznos_premija,     iznos_premija_den,
            par_statusid,godisnica_aneks)
            select  tos_aneksid,current,tusername,0,tos_aneks,
            par_yearid,tdatum_aneks_nov,current,
            tos_polisaid,par_clientid,par_valutaid,par_tip_platiid,
            br_rati,iznos_premija,iznos_premija_den,1,godisnica_aneks
            from os_aneks
            where os_aneksid = tos_aneksid_star;
        else  --IF7 else

            select os_aneksid into tos_aneksid
            from os_aneks
            where par_yearid = tpar_yearid_star
            and os_aneks=tos_aneks ;
        end if;  --IF7 end

        select os_ponuda_detailid into  tos_ponuda_detailid_star
        from os_aneks_faktura
        where  os_aneks_fakturaid=tosaneks_fakturaid;

        select iznos_premija,os_produkt_ts_id
        into tiznos_premija, tos_produkt_ts_id
        from os_ponuda_detail
        where os_ponuda_detailid=tos_ponuda_detailid_star;


        select os_ponuda_detailid  into tos_ponuda_detailid
        from os_ponuda_detail
        where os_ponudaid=tos_ponudaid
        and iznos_premija=tiznos_premija
        and os_produkt_ts_id=tos_produkt_ts_id;



        -----vnes  na obnova vo fin-stavka
        let tos_aneks_fakturaid_nova=sq_os_aneks_fakturaid.nextval;
        select par_yearid into tpar_yearid
        from os_aneks
        where os_aneksid=tos_aneksid ;
        -----vnes  na obnova vo fin-stavka
        insert into os_aneks_faktura(     os_aneks_fakturaid ,
        datecreated ,          usercreated ,
        version ,     os_aneksid ,     par_tip_dokumentid ,
        par_tip_kniziid ,     rata ,     os_ponuda_detailid ,
        data_faktura ,     data_valuta ,     iznos ,
        iznos_denari ,     par_statusid,os_aneks_rataid
        )
        select
        tos_aneks_fakturaid_nova ,  current    ,   tusername,   0,
        tos_aneksid ,     par_tip_dokumentid ,
        par_tip_kniziid ,     rata ,     tos_ponuda_detailid ,     data_faktura ,     data_valuta  ,
        tsaldo_faktura ,tsaldo_faktura_den ,     1, (tos_aneksid || tpar_yearid || rata)  ::int8
        from os_aneks_faktura
        where os_aneks_fakturaid=tosaneks_fakturaid;



        insert into fin_stavka (fin_stavkaid, datecreated, usercreated, version, par_filijalaid,
        par_tip_dokumentid, par_tip_kniziid, par_clientid, os_aneks_fakturaid,
        par_yearid, datum, datum_knizi,datum_stavka,datum_fakt_valuta, par_valutaid,
        par_kursid, os_polisaid,par_agent_id,  pat_tip_platiid,
        iznos_otvoren, f_rs,iznos_d,    iznos_d_den,
        par_statusid)
        select sq_fin_stavka.nextval,current, tusername,0,      par_filijalaid ,
        par_tip_dokumentid ,     par_tip_kniziid ,
        par_clientid ,     tos_aneks_fakturaid_nova ,     par_yearid ,     datum, datum_knizi,    today ,     today ,
        par_valutaid ,    par_kursid ,     tos_polisaid ,
        par_agent_id ,          pat_tip_platiid ,
        iznos_otvoren ,'R',tsaldo_faktura, tsaldo_faktura_den,   1
        from fin_stavka
        where os_aneks_fakturaid=tosaneks_fakturaid
        and iznos_d is not null;

    end foreach;



else  --IF6 else
    select par_tip_dokumentid into tpar_tip_dokumentid from par_tip_dokument where
    par_tip_dokument='PREM';

    select par_tip_dokumentid into tpar_tip_dokumentid from par_tip_dokument where
    par_tip_dokument='PREM';

    select par_tip_kniziid into tpar_tip_kniziido from par_tip_knizi where
    par_tip_knizi='POLIS';

    select par_tip_kniziid into tpar_tip_kniziidk from par_tip_knizi where
    par_tip_knizi='KAMAT';

    select par_tip_kniziid into tpar_tip_kniziidar from par_tip_knizi where
    par_tip_knizi='ARIZN';

    select par_tip_kniziid into tpar_tip_kniziiddr from par_tip_knizi where
    par_tip_knizi='DPREM';

    select par_tip_kniziid into tpar_tip_kniziidzr from par_tip_knizi where
    par_tip_knizi='ZPREM';

    let tiznosk=0;
    let tiznos_denarik=0;
    --prvo ide premijata





    foreach
        select os_ponuda_detailid, nvl((iznos_premija*tbr_osig_lica)/tbr_rati,0) , round(nvl((iznos_premija_den*tbr_osig_lica)/tbr_rati,0)), par_kursid,
        nvl(ar_iznos*tbr_osig_lica/tbr_rati,0) , round(nvl(ar_iznos_den*tbr_osig_lica/tbr_rati,0)), ts_vid_rizik,
        nvl(os_produkt_zdravstvenoid,0)
        into tos_ponuda_detailid, tiznos,tiznos_denari, tpar_kursid,tar_iznos,tar_iznos_denari, _ts_vid_rizik,tos_produkt_zdravstvenoid
        from os_ponuda_detail
        where os_ponudaid=tos_ponudaid
        if tpar_polisa_statusid=2 then  --IF8 begin
            let tdata_faktura=tgodisnica_aneks+(kolku_god)UNITS year;
            --let tdata_valuta=tskadenca_datum_od+ trok_plakanje UNITS DAY;
            let tdata_valuta=tdata_faktura+(12/tbr_rati)UNITS month;
        else  --IF8 else
            let tdata_faktura=tgodisnica_aneks;
            --let tdata_valuta=tskadenca_datum_od+ trok_plakanje UNITS DAY;
            let tdata_valuta=tgodisnica_aneks+(12/tbr_rati)UNITS month;
        end if;  --IF8 end

        let i=1;
        while i <=tbr_rati

            if _ts_vid_rizik='Dr' then  --IF9 begin
                if tos_produkt_zdravstvenoid>0 then  --IF10 begin
                    let tpar_tip_kniziid =tpar_tip_kniziidzr;
                else  --IF10 else
                    let tpar_tip_kniziid =tpar_tip_kniziiddr;
                end if;  --IF10 end
            else  --IF9 else
                let tpar_tip_kniziid =tpar_tip_kniziido;
            end if;  --IF9 end

            --let tiznosk=tiznosk+tiznos*tproc_zgol_premija/100;
            --let tiznos_denarik=tiznos_denarik+tiznos_denari*tproc_zgol_premija/100;


            --let tdata_valuta=tskadenca_datum_od+ trok_plakanje UNITS DAY+(12/tbr_rati)UNITS month;


            select par_filijalaid, par_agentid into tparfilijalaid,tpar_agentid from os_ponuda where os_ponudaid=tos_ponudaid;
            let tos_aneks_fakturaid=sq_os_aneks_fakturaid.nextval;
            let tos_aneks_rataid=  (tos_aneksid || tpar_yearid || i)  ::int8;
            insert into os_aneks_faktura(os_aneks_fakturaid , datecreated , usercreated,
            version, os_aneksid, par_tip_dokumentid, par_tip_kniziid, rata , os_ponuda_detailid,
            data_faktura, data_valuta, iznos,iznos_denari,par_statusid,os_aneks_rataid)
            values( tos_aneks_fakturaid,current, tusername,
            0, tos_aneksid,tpar_tip_dokumentid, tpar_tip_kniziid, i , tos_ponuda_detailid,
            tdata_faktura, tdata_valuta, tiznos,tiznos_denari,1,tos_aneks_rataid);
            if tar_iznos_denari<>0 then  --IF11 begin
                let tos_aneks_fakturaidar=sq_os_aneks_fakturaid.nextval;
                let tos_aneks_rataid=  (tos_aneksid || tpar_yearid || i)  ::int8;
                insert into os_aneks_faktura(os_aneks_fakturaid , datecreated , usercreated,
                version, os_aneksid, par_tip_dokumentid, par_tip_kniziid, rata , os_ponuda_detailid,
                data_faktura, data_valuta, iznos,iznos_denari,par_statusid,os_aneks_rataid)
                values( tos_aneks_fakturaidar,current, tusername,
                0, tos_aneksid,tpar_tip_dokumentid, tpar_tip_kniziidar, i , tos_ponuda_detailid,
                tdata_faktura, tdata_valuta, tar_iznos,tar_iznos_denari,1,tos_aneks_rataid);

                insert into fin_stavka (fin_stavkaid, datecreated, usercreated, version, par_filijalaid,
                par_tip_dokumentid, par_tip_kniziid, par_clientid, os_aneks_fakturaid,
                par_yearid, datum, datum_knizi,datum_stavka,datum_fakt_valuta, par_valutaid,
                par_kursid, os_polisaid,par_agent_id, fin_izvod_iid, pat_tip_platiid,
                sifra_zatvaranje, grupa_fin_stavkaid,iznos_otvoren, f_rs,iznos_d,
                iznos_d_den,iznos_p,   iznos_p_den,  edinica, nal_vid ,
                nalog, dat_nalog, br_stavka, par_statusid)
                values (sq_fin_stavka.nextval,current, tusername,0, tparfilijalaid,
                tpar_tip_dokumentid,tpar_tip_kniziidar,tdogovoruvac_par_client,tos_aneks_fakturaidar,
                tpar_yearid,tdata_faktura,tdata_valuta ,current,tdata_faktura,tpar_valutaid,
                tpar_kursid,tos_polisaid, tpar_agentid,null,tpar_tip_platiid,
                null,null,tar_iznos_denari, 'R',tar_iznos,
                tar_iznos_denari, null, null, null, null,
                null, null, null, 1);
            end if;  --IF11 end



            let i=i+1;

            insert into fin_stavka (fin_stavkaid, datecreated, usercreated, version, par_filijalaid,
            par_tip_dokumentid, par_tip_kniziid, par_clientid, os_aneks_fakturaid,
            par_yearid, datum, datum_knizi,datum_stavka,datum_fakt_valuta, par_valutaid,
            par_kursid, os_polisaid,par_agent_id, fin_izvod_iid, pat_tip_platiid,
            sifra_zatvaranje, grupa_fin_stavkaid,iznos_otvoren, f_rs,iznos_d,
            iznos_d_den,iznos_p,   iznos_p_den,  edinica, nal_vid ,
            nalog, dat_nalog, br_stavka, par_statusid)
            values (sq_fin_stavka.nextval,current, tusername,0, tparfilijalaid,
            tpar_tip_dokumentid,tpar_tip_kniziid,tdogovoruvac_par_client,tos_aneks_fakturaid,
            tpar_yearid,tdata_faktura,tdata_valuta,current, tdata_faktura,tpar_valutaid,
            tpar_kursid,tos_polisaid, tpar_agentid,null,tpar_tip_platiid,
            null,null,tiznos_denari, 'R',tiznos,
            tiznos_denari, null, null, null, null,
            null, null, null, 1);

            let tdata_faktura=tdata_faktura+(12/tbr_rati)UNITS month;
            let tdata_valuta=date(tdata_faktura) +(12/tbr_rati)UNITS month;---promena pobarana na 04.01.2013
            --let tdata_valuta=date(tdata_faktura)+ trok_plakanje UNITS DAY;
        end while;


    end foreach;
    ---podeleni posebno stavka za kamata
    foreach
        select --nvl(((sum(nvl(iznos_premija,0))+sum(nvl(ar_iznos,0)))*2.6/100)/2,0)
        nvl(((sum(nvl(iznos_premija,0))+sum(nvl(ar_iznos,0)))*tproc_zgol_premija*tbr_osig_lica/100)/tbr_rati,0) ,
        round(nvl(((sum(nvl(iznos_premija_den,0))+sum(nvl(ar_iznos_den,0)))*tproc_zgol_premija*tbr_osig_lica/100)/tbr_rati,0))
        into  tiznosk,tiznos_denarik
        from os_ponuda_detail
        where os_ponudaid=tos_ponudaid
        if tiznos_denarik<>0 then  --IF12 begin


            let tdata_faktura=tgodisnica_aneks;
            let tdata_valuta=tgodisnica_aneks+(12/tbr_rati)UNITS month;
            --let tdata_valuta=tskadenca_datum_od+ trok_plakanje UNITS DAY;
            let i=1;
            while i <=tbr_rati




                if tiznos_denarik<>0 then  --IF13 begin
                    let tos_aneks_fakturaid=sq_os_aneks_fakturaid.nextval;
                    let tos_aneks_rataid=  (tos_aneksid || tpar_yearid || i)  ::int8;
                    insert into os_aneks_faktura(os_aneks_fakturaid , datecreated , usercreated,
                    version, os_aneksid, par_tip_dokumentid, par_tip_kniziid, rata , os_ponuda_detailid,
                    data_faktura, data_valuta, iznos,iznos_denari,par_statusid,os_aneks_rataid)
                    values(tos_aneks_fakturaid, current, tusername,
                    0, tos_aneksid,tpar_tip_dokumentid, tpar_tip_kniziidk, i , tos_ponuda_detailid,
                    tdata_faktura, tdata_valuta, tiznosk,tiznos_denarik,1,tos_aneks_rataid);
                end if;  --IF13 end


                select par_filijalaid, par_agentid into tparfilijalaid,tpar_agentid from os_ponuda where os_ponudaid=tos_ponudaid;

                let i=i+1;

                insert into fin_stavka (fin_stavkaid, datecreated, usercreated, version, par_filijalaid,
                par_tip_dokumentid, par_tip_kniziid, par_clientid, os_aneks_fakturaid,
                par_yearid, datum, datum_knizi,datum_stavka,datum_fakt_valuta, par_valutaid,
                par_kursid, os_polisaid,par_agent_id, fin_izvod_iid, pat_tip_platiid,
                sifra_zatvaranje, grupa_fin_stavkaid,iznos_otvoren, f_rs,iznos_d,
                iznos_d_den,iznos_p,   iznos_p_den,  edinica, nal_vid ,
                nalog, dat_nalog, br_stavka, par_statusid)
                values (sq_fin_stavka.nextval,current, tusername,0, tparfilijalaid,
                tpar_tip_dokumentid,tpar_tip_kniziidk,tdogovoruvac_par_client,tos_aneks_fakturaid,
                tpar_yearid,tdata_faktura, tdata_valuta,current,tdata_faktura,tpar_valutaid,
                tpar_kursid,tos_polisaid, tpar_agentid,null,tpar_tip_platiid,
                null,null,tiznos_denarik, 'R',tiznosk,
                tiznos_denarik, null, null, null, null,
                null, null, null, 1);

                let tdata_faktura=tdata_faktura+(12/tbr_rati)UNITS month;

                --let tdata_valuta=date(tdata_faktura)+ trok_plakanje UNITS DAY;



                let tdata_valuta=date(tdata_faktura) +(12/tbr_rati)UNITS month;---promena pobarana na 04.01.2013
            end while;


        end if;  --IF12 end

    end foreach;
end if;  --IF6 end
-------------------

--commit work;
return                '1','ПРВИОТ   АНЕКС   Е                     ИЗГЕНЕРИРАН';

end function;
GO