CREATE FUNCTION appuser.fin_izvod_file_create   ( p_FIN_IZVOD_FILEID int, p_tuser_id int)
returning integer,char(100);



define v_fin_izvod_file_red lvarchar(4000);
define v_Smetka_deponent varchar(18);
define  v_Plakac_naziv,v_cel_doznaka varchar(100);
define v_plakac_smetka varchar(20)  ;
define v_iznos_dolzi,  v_iznos_pobaruva , v_iznos_prov varchar(19);
define v_datum_plati varchar(10);
define v_sifra_plakanje varchar(3);
define v_povikuvanje_broj_zad varchar(24);
define v_povikuvanje_broj_odob varchar(24);
define v_nacin_plakanje varchar(1) ;
define v_dolzi, v_pobaruva ,v_provizija decimal(20,2);
define v_datum date;
define v_FIN_IZVOD_FILE_stID , v_par_vid_izvodid,p_tint,tpar_valutaid int  ;
define v_par_vid_izvod varchar(5);
define v_polisa_broj1 varchar(10);
define   p_tpor char(400);
define v_iznos_plati decimal(20,2) ;
define tvaluta varchar(3);
on exception
	ROLLBACK WORK;
        return -1,'NASTANATA E GRE[KA';
end exception;

 --set debug file to "err_FIN_IZVOD_FILE_Create.sql";
 --trace on;

set isolation to dirty read;

BEGIN WORK;

select par_vid_izvodid into v_par_vid_izvodid from fin_izvod_file where FIN_IZVOD_FILEID=p_FIN_IZVOD_FILEID;

select par_vid_izvod into v_par_vid_izvod from par_vid_izvod where PAR_VID_IZVODID=v_par_vid_izvodid;



foreach  select FIN_IZVOD_FILE_stID,fin_izvod_file_red
into v_FIN_IZVOD_FILE_stID,v_fin_izvod_file_red
 from FIN_IZVOD_FILE_st
where FIN_IZVOD_FILEID=p_FIN_IZVOD_FILEID
--and fin_izvod_file_stid=1681357

    let v_Plakac_naziv=null;
    let v_polisa_broj1=null;
    let v_plakac_smetka=null;
    let v_smetka_deponent=null;
    let v_provizija=null;
    let v_datum=null;
    let v_nacin_plakanje=null;

    let v_polisa_broj1=null;
    
    if v_par_vid_izvod='КБ' then


let  v_Smetka_deponent =SUBSTR(v_fin_izvod_file_red, 1, 18);
let v_Plakac_naziv=SUBSTR(v_fin_izvod_file_red, 19, 70);
let v_plakac_smetka=SUBSTR(v_fin_izvod_file_red, 89, 18);
let v_iznos_dolzi=SUBSTR(v_fin_izvod_file_red, 107, 19);
let v_iznos_pobaruva=SUBSTR(v_fin_izvod_file_red, 126, 19);
let v_iznos_prov=SUBSTR(v_fin_izvod_file_red, 145, 19);
let v_datum_plati=SUBSTR(v_fin_izvod_file_red, 164, 10);
let v_cel_doznaka=SUBSTR(v_fin_izvod_file_red, 174, 70);
let v_sifra_plakanje=SUBSTR(v_fin_izvod_file_red, 244, 3);
let v_povikuvanje_broj_zad=SUBSTR(v_fin_izvod_file_red, 247, 24);
let v_povikuvanje_broj_odob=SUBSTR(v_fin_izvod_file_red, 271, 24);
let v_nacin_plakanje=SUBSTR(v_fin_izvod_file_red, 295, 1);


let v_dolzi=cast (SUBSTR(v_iznos_dolzi, PatIndex('%[0-9]%', v_iznos_dolzi), len(v_iznos_dolzi)) as decimal(20,2));
let v_pobaruva=cast (SUBSTR(v_iznos_pobaruva, PatIndex('%[0-9]%', v_iznos_pobaruva), len(v_iznos_pobaruva)) as decimal(20,2));
let v_provizija=cast (SUBSTR(v_iznos_prov, PatIndex('%[0-9]%', v_iznos_prov), len(v_iznos_prov)) as decimal(20,2));
let v_datum= MDY( SUBSTR(v_datum_plati, 6, 2), SUBSTR(v_datum_plati, 9, 2),SUBSTR(v_datum_plati, 1, 4) );



end if;


if v_par_vid_izvod='СБ' then


IF SUBSTR(v_fin_izvod_file_red, 1, 2)='12'
       THEN
        
           CONTINUE foreach;
       END IF;

let v_Plakac_naziv=SUBSTR(v_fin_izvod_file_red, 49, 70);

let  v_Smetka_deponent =SUBSTR(v_fin_izvod_file_red, 34, 15);

let v_iznos_dolzi=SUBSTR(v_fin_izvod_file_red, 20, 14);

let v_iznos_pobaruva=SUBSTR(v_fin_izvod_file_red, 6, 14);
let v_iznos_prov=0;
let v_datum_plati=SUBSTR(v_fin_izvod_file_red, 278, 10);

let v_cel_doznaka=SUBSTR(v_fin_izvod_file_red, 208, 70);
let v_sifra_plakanje=SUBSTR(v_fin_izvod_file_red, 157, 3);
let v_povikuvanje_broj_zad=SUBSTR(v_fin_izvod_file_red, 160, 24);
let v_povikuvanje_broj_odob=SUBSTR(v_fin_izvod_file_red, 184, 24);
let v_nacin_plakanje=SUBSTR(v_fin_izvod_file_red, 2, 1);



/*
1    1        Тип на слог
4    5        Тип на инструмент
14    19              Прилив
14    33        Одлив
15    48        Сметка – налогодавач/налогопримач
70    118        Назив –   налогодавач/налогопримач
25    143        Седиште -             налогодавач/
13    156        Даночен           број
3    159        Шифра на плаќање
24    183        Повик на број должи
24    207        Повик на број побарува
70    277        Цел на дознака
10    287        Датум
30    317        Број   на рекламација


*/
let v_dolzi=v_iznos_dolzi::dec;
let v_pobaruva=v_iznos_pobaruva::dec;
--let v_dolzi=cast (SUBSTR(v_iznos_dolzi, PatIndex('%[0-9]%', v_iznos_dolzi), len(v_iznos_dolzi)) as decimal(20,2));
--let v_pobaruva=cast (SUBSTR(v_iznos_pobaruva, PatIndex('%[0-9]%', v_iznos_pobaruva), len(v_iznos_pobaruva)) as decimal(20,2));
let v_provizija=0;
let v_datum= MDY(  SUBSTR(v_datum_plati, 4, 2), SUBSTR(v_datum_plati, 1, 2),SUBSTR(v_datum_plati, 7, 4) );


--let v_dolzi=cast (SUBSTR(v_iznos_dolzi, PatIndex('%[0-9]%', v_iznos_dolzi), len(v_iznos_dolzi)) as decimal(20,2));
--let v_pobaruva=cast (SUBSTR(v_iznos_pobaruva, PatIndex('%[0-9]%', v_iznos_pobaruva), len(v_iznos_pobaruva)) as decimal(20,2));
let v_provizija=0;
--let v_datum= CONVERT(  date,  SUBSTR(v_datum_plati, 7, 4) + SUBSTR(v_datum_plati, 4, 2) + SUBSTR(v_datum_plati, 1, 2));
--21.04.2018
end if;




if v_par_vid_izvod='СЗ' then


IF SUBSTR(v_fin_izvod_file_red, 2, 2)='12'
       THEN
        
           CONTINUE foreach;
       END IF;

let v_Plakac_naziv=SUBSTR(v_fin_izvod_file_red, 49, 70);

let  v_Smetka_deponent =SUBSTR(v_fin_izvod_file_red, 34, 15);

let v_iznos_dolzi=SUBSTR(v_fin_izvod_file_red, 20, 14);

let v_iznos_pobaruva=SUBSTR(v_fin_izvod_file_red, 6, 14);
let v_iznos_prov=0;
let v_datum_plati=SUBSTR(v_fin_izvod_file_red, 278, 10);

let v_cel_doznaka=SUBSTR(v_fin_izvod_file_red, 208, 70);
let v_sifra_plakanje=SUBSTR(v_fin_izvod_file_red, 157, 3);
let v_povikuvanje_broj_zad=SUBSTR(v_fin_izvod_file_red, 160, 24);
let v_povikuvanje_broj_odob=SUBSTR(v_fin_izvod_file_red, 184, 24);
let v_nacin_plakanje=SUBSTR(v_fin_izvod_file_red, 2, 1);

/*select  first 1 vrati_polisa(os_polisaid),par_valutaid into v_polisa_broj1,tpar_valutaid from os_ponuda,os_polisa
 where os_ponuda.os_ponudaid=os_polisa.os_ponudaid
 and  ponuda_broj=v_povikuvanje_broj_odob
 and os_ponuda.par_statusid=17;
 
 if v_polisa_broj1 is null then 
 
select  first 1 vrati_polisa(os_polisaid),par_valutaid into v_polisa_broj1,tpar_valutaid from os_ponuda,os_polisa
 where os_ponuda.os_ponudaid=os_polisa.os_ponudaid
 and  kreditna_partija=v_povikuvanje_broj_zad
 and os_ponuda.par_statusid=17;
 end if; napravena promena prvo po kreditna partija pa po broj na ponuda 25.03.2020*/
if  nvl(trim(v_povikuvanje_broj_zad),'') <>'' then 
 select  first 1 vrati_polisa(os_polisaid), vrati_valutaid_ponuda (os_ponuda.os_ponudaid) into v_polisa_broj1,tpar_valutaid from os_ponuda,os_polisa
 where os_ponuda.os_ponudaid=os_polisa.os_ponudaid
  and  kreditna_partija=v_povikuvanje_broj_zad
 and os_ponuda.par_statusid=17;
 end if; 
 
 if v_polisa_broj1 is null then 
 
select  first 1 vrati_polisa(os_polisaid), vrati_valutaid_ponuda (os_ponuda.os_ponudaid) into v_polisa_broj1,tpar_valutaid from os_ponuda,os_polisa
 where os_ponuda.os_ponudaid=os_polisa.os_ponudaid
 and  os_ponuda.ponuda_broj=v_povikuvanje_broj_odob
 and os_ponuda.par_statusid=17;
 end if; 
 
 select valuta into tvaluta
 from par_valuta
 where par_valutaid=tpar_valutaid;
 
 
 
/*
1    1        Тип на       слог
4    5        Тип на               инструмент
14    19                  Прилив
14    33        Одлив
15    48              Сметка – налогодавач/налогопримач
70    118        Назив –                                                  налогодавач/налогопримач
25    143                  Седиште -                   налогодавач/
13    156        Даночен број
3    159                Шифра на плаќање
24    183        Повик на број   должи
24    207          Повик на број побарува
70    277        Цел на               дознака
10    287        Датум
30    317        Број на           рекламација


*/


let v_dolzi=v_iznos_dolzi::dec;
let v_pobaruva=v_iznos_pobaruva::dec;
--let v_dolzi=cast (SUBSTR(v_iznos_dolzi, PatIndex('%[0-9]%', v_iznos_dolzi), len(v_iznos_dolzi)) as decimal(20,2));
--let v_pobaruva=cast (SUBSTR(v_iznos_pobaruva, PatIndex('%[0-9]%', v_iznos_pobaruva), len(v_iznos_pobaruva)) as decimal(20,2));
let v_provizija=0;
let v_datum= MDY(  SUBSTR(v_datum_plati, 4, 2), SUBSTR(v_datum_plati, 1, 2),SUBSTR(v_datum_plati, 7, 4) );
--let v_dolzi=cast (SUBSTR(v_iznos_dolzi, PatIndex('%[0-9]%', v_iznos_dolzi), len(v_iznos_dolzi)) as decimal(20,2));
--let v_pobaruva=cast (SUBSTR(v_iznos_pobaruva, PatIndex('%[0-9]%', v_iznos_pobaruva), len(v_iznos_pobaruva)) as decimal(20,2));

--let v_datum= CONVERT(  date,  SUBSTR(v_datum_plati, 7, 4) + SUBSTR(v_datum_plati, 4, 2) + SUBSTR(v_datum_plati, 1, 2));
--21.04.2018
end if;






if v_par_vid_izvod='ТБ' then



/*Име на                        
налогопримач 1 70 Петре Петревски

Сметка на                        
налогопримач 71 18 999-0000000132-95
8.     Износ 89 19
-100.00 (За одлив од сметката
пред       износот       стои знак минус “-“,
за           прилив на сметка нема знак)
9.       Шифра 108 6 220
10. Цел на             дознака 114 70
Плаќање по основ на извршени        
услуги   помеѓу           правни               субјекти
11.
Две празни
места 184 2
12.
Повикување
на број                                    
налогопримач 186 24 123456789
13.                  
Повикување
на         број                  
налогодавач 210 24 123456789
*/

let v_dolzi=null;
let v_pobaruva=null; 

let v_Plakac_naziv=SUBSTR(v_fin_izvod_file_red, 1, 70);
 let v_plakac_smetka=SUBSTR(v_fin_izvod_file_red, 71, 18);
 let v_iznos_dolzi=trim(SUBSTR(v_fin_izvod_file_red, 89, 19));
 let v_sifra_plakanje=SUBSTR(v_fin_izvod_file_red, 108, 6);
 let v_cel_doznaka=SUBSTR(v_fin_izvod_file_red, 114, 70);
 let v_povikuvanje_broj_zad=SUBSTR(v_fin_izvod_file_red, 186, 24);
let v_povikuvanje_broj_odob=SUBSTR(v_fin_izvod_file_red, 210, 24);

if nvl(v_iznos_dolzi,'')<>'' then  
IF SUBSTR(v_iznos_dolzi, 1, 1)='-' THEN 
let v_dolzi= CAST(REPLACE(REPLACE(SUBSTR(v_iznos_dolzi, 2, len(v_iznos_dolzi)),',',''),'.00','') AS decimal(20,2));
else
let v_pobaruva= CAST(REPLACE(REPLACE(v_iznos_dolzi,',',''),'.00','') AS decimal(20,2));
END IF;
end if; 

--let @provizija=cast (SUBSTR(@iznos_prov, PatIndex('%[0-9]%', @iznos_prov), len(@iznos_prov)) as decimal(20,2));
--let @datum= CONVERT(  date,  SUBSTR(@datum_plati, 1, 4) + SUBSTR(@datum_plati, 6, 2) + SUBSTR(@datum_plati, 9, 2));
end if;

if v_par_vid_izvod='СЗ' then
execute procedure konverzija_z(v_datum,v_pobaruva,'MKD',tvaluta) into v_iznos_plati;    
else 
 execute procedure konverzija_z(v_datum,v_pobaruva,'MKD','EUR') into v_iznos_plati;
end if;
if v_par_vid_izvod='СЗ' and (v_iznos_plati - TRUNC(v_iznos_plati))=0.99 then 
let v_iznos_plati=round(v_iznos_plati);
end if;

if v_par_vid_izvod='БЕ' then

    -- Прескокни header ред (содржи "ID")
    IF INSTR(v_fin_izvod_file_red, '"ID"') > 0 THEN
        CONTINUE foreach;
    END IF;

    -- Плаќач: Ime + Prezime (field 2 + 3)
    LET v_Plakac_naziv = TRIM(get_field(v_fin_izvod_file_red, 2) || ' ' || get_field(v_fin_izvod_file_red, 3));

    -- Полиса број — field 7 (ако има повеќе, земи само прваот)
    LET v_plakac_smetka = TRIM(get_field(v_fin_izvod_file_red, 7));
    IF INSTR(v_plakac_smetka, ' ') > 0 THEN
        LET v_polisa_broj1 = SUBSTR(v_plakac_smetka, 1, INSTR(v_plakac_smetka, ' ') - 1);
    ELSE
        LET v_polisa_broj1 = v_plakac_smetka;
    END IF;

    -- Цел на дознака — field 8 (Опис)
    LET v_cel_doznaka = get_field(v_fin_izvod_file_red, 8);

    -- Трансакциски број — field 15
    LET v_povikuvanje_broj_odob = get_field(v_fin_izvod_file_red, 15);

    -- Износ EUR -> v_pobaruva (field 9: формат "58,44 €")
    LET v_iznos_pobaruva = SUBSTR(
        get_field(v_fin_izvod_file_red, 9), 1,
        INSTR(get_field(v_fin_izvod_file_red, 9), ' ') - 1
    );
    LET v_pobaruva = CAST(
        REPLACE(REPLACE(v_iznos_pobaruva, '.', ''), ',', '.')
        AS DECIMAL(20,2)
    );

    LET v_dolzi    = null;
    LET v_provizija = 0;

    -- Датум од field 13 (формат: "15.06.2026 01:49:55") — земи само DD.MM.YYYY
    LET v_datum_plati = SUBSTR(get_field(v_fin_izvod_file_red, 13), 1, 10);
    LET v_datum = MDY(
        SUBSTR(v_datum_plati, 4, 2),   -- MM
        SUBSTR(v_datum_plati, 1, 2),   -- DD
        SUBSTR(v_datum_plati, 7, 4)    -- YYYY
    );

    -- Пребарај ја полисата по polisa_broj_cel (Иуте го праќа во форматот "28/006008")
    if nvl(trim(v_polisa_broj1), '') <> '' then
        select first 1 vrati_polisa(os_polisaid), vrati_valutaid_ponuda(os_ponuda.os_ponudaid)
        into v_polisa_broj1, tpar_valutaid
        from os_ponuda, os_polisa
        where os_ponuda.os_ponudaid = os_polisa.os_ponudaid
          and os_ponuda.polisa_broj_cel = v_polisa_broj1
          and os_ponuda.par_statusid = 17;
    end if;

    -- Ако не е најдена, пробај по kreditna_partija (полн string со сите полиси)
    if v_polisa_broj1 is null then
        select first 1 vrati_polisa(os_polisaid), vrati_valutaid_ponuda(os_ponuda.os_ponudaid)
        into v_polisa_broj1, tpar_valutaid
        from os_ponuda, os_polisa
        where os_ponuda.os_ponudaid = os_polisa.os_ponudaid
          and os_ponuda.kreditna_partija = v_plakac_smetka
          and os_ponuda.par_statusid = 17;
    end if;

    select valuta into tvaluta
    from par_valuta
    where par_valutaid = tpar_valutaid;

end if;

UPDATE
  FIN_IZVOD_FILE_st
set
  version = version+1,
  Smetka_deponent = v_Smetka_deponent,
  Plakac_naziv = v_Plakac_naziv,
  plakac_smetka = v_plakac_smetka,
  dolzi = v_dolzi,
  pobaruva = v_pobaruva,
  provizija = v_provizija,
  datum = v_datum,
 cel_doznaka = v_cel_doznaka,
  sifra_plakanje = v_sifra_plakanje,
  povikuvanje_broj_zad =v_povikuvanje_broj_zad,
  povikuvanje_broj_odob =v_povikuvanje_broj_odob,
  nacin_plakanje =v_nacin_plakanje, iznos1=v_iznos_plati, par_statusid=1,
  DATECHANGED=current, userchanged=p_tuser_id, polisa_broj1=v_polisa_broj1

WHERE
  FIN_IZVOD_FILE_stID = v_FIN_IZVOD_FILE_stID;



	if v_par_vid_izvod  not in ('КБ', 'СБ', 'ТБ', 'СЗ','БЕ')
	then 
	return               '-1','Изводот     може да       биде само од КБ, СБ, ТБ, СЗ,БЕ ';

	end if;
	 






end foreach;

delete from FIN_IZVOD_FILE_st
where FIN_IZVOD_FILEID=p_FIN_IZVOD_FILEID
and nvl(pobaruva,0) =0;

update FIN_IZVOD_FILE set version = version+1,DATECHANGED=current, userchanged=p_tuser_id
, par_statusid=1 where FIN_IZVOD_FILEID=p_FIN_IZVOD_FILEID;

/*
update FIN_IZVOD_FILE set version = version+1,DATECHANGED=current, userchanged=p_tuser_id
, par_statusid=1 where FIN_IZVOD_FILEID=p_FIN_IZVOD_FILEID;*/
commit work;
return '1','STAVKITE  SE KREIRANI';

end function;