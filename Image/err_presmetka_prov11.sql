trace on


delete from t;

set isolation to dirty read;

set optimization high;
expression:(|| (|| (|| "01.", tmesec), "."), tgodina)
evaluates to 01.12.2024 
let tod_odatum = 01.12.2024 
expression:(<procedure> last_day, tod_odatum)
evaluates to 31/12/2024 
let tdo_datum = 31/12/2024 
expression:
  (select par_yearid
    from par_year
    where (= par_year, tgodina))
evaluates to 2514 ; 
let tpar_yearid = 2514 
expression:
  (select (count *)
    from provizija_promotori_zbiren
    where (and (= mesec, tmesec), (= par_yearid, tpar_yearid)))
evaluates to 0 ; 
let dali_presmetana = 0 
expression:(> dali_presmetana, 0)
evaluates to f 
expression:
  (select username
    from adm_user
    where (= userid, tuser_id))
evaluates to admin ; 
let tusername = admin 
start select cursor.
select par_provizijatipid, tip_provizija
  from par_provizijatip
  where (= tip_provizija, "P")
select cursor iteration.
select cursor returns 1093 , P 
start select cursor.
select par_provizija_agentid, par_clientid, par_agentid, par_provizijadefid, par_provizijaispid, par_statusid, (nvl startni_poeni, 0), (nvl lc_vk_bodovi, 0), (nvl storno_bodovi, 0)
  from provizija_agent
  where (and (or (between tdo_datum, pag_datumod, pag_datumdo), (and (>= tdo_datum, pag_datumod), (null pag_datumdo))), (= par_provizijatipid, tpar_provizijatipid))
  order by par_provizijadefiddesc
select cursor iteration.
select cursor returns 4094 , NULL. , 1922 , 1140 , NULL. , 1 , 1800001.00 , 0.00 , 0.00 
expression:
  (select pps_bodoviod, pps_bodovido, par_valutaid, pps_valueval, bod_sorabotnik, meseci_sorabotnik, procent_vtor_uslov, (nvl meseci_vtor_uslov, 0)
    from par_provizijadef_st
    where (and (and (= par_provizijadefid, tpar_provizijadefid), (= (nvl pps_valueden, 1), "1")), (or (between tdo_datum, pps_datumod, pps_datumdo), (and (>= tdo_datum, pps_datumod), (null pps_datumdo)))))
evaluates to 0 ; NULL. ; NULL. ; NULL. ; 24.5000000000000000 ; 1 ; NULL. ; 18000001 ; 
let tppd_from = 18000001 
let tppd_to = NULL. 
let tpar_valutaid = 1 
let tppd_valueval = 24.5000000000000000 
let tbod_sorabotnik = NULL. 
let tmeseci_sorabotnik = NULL. 
let tprocent_vtor_uslov = NULL. 
let tmeseci_vtor_uslov = 0 
expression:
  (select (nvl (max provizija_promotori_zbirenid), 0)
    from provizija_promotori_zbiren
    where (= par_agentid, tpar_agentid))
evaluates to 12960 ; 
let tprovizija_agent_zbirenid = 12960 
expression:
  (select (nvl vk_bodovi, 0)
    from provizija_promotori_zbiren
    where (and (= par_agentid, tpar_agentid), (= provizija_promotori_zbirenid, tprovizija_agent_zbirenid)))
evaluates to 0.00 ; 
let tvk_bodovi_ag = 0.00 
expression:tvk_bodovi_ag
evaluates to 0.0000000000000000 
let tvk_bodovi_ag_preth = 0.0000000000000000 
expression:
  (select (nvl storno_bodovi, 0)
    from provizija_promotori_zbiren
    where (and (= par_agentid, tpar_agentid), (= provizija_promotori_zbirenid, tprovizija_agent_zbirenid)))
evaluates to 0.00 ; 
let tvk_storno_bodovi = 0.00 
expression:
  (select (nvl par_status_aktiven, "A")
    from par_agent
    where (= par_agentid, tpar_agentid))
evaluates to A ; 
let tpar_status_aktiven = A 
expression:(= ttip_provizija, "P")
evaluates to t 
expression:
  (select ppd_from, ppd_to, ppd_tipprodukcija, ppd_valueden, par_valutaid, ppd_valueval, ppd_nadredenid, (nvl denovi_lp, 0), (nvl denovi_tp, 0), ppd_level
    from par_provizijadef
    where (= par_provizijadefid, tpar_provizijadefid))
evaluates to 18 ; 0 ; 0 ; NULL. ; NULL. ; NULL. ; NULL. ; 2 ; NULL. ; NULL. ; 
let tppd_from = NULL. 
let tppd_to = NULL. 
let tppd_tipprodukcija = 2 
let tppd_valueden = NULL. 
let tpar_valutaid = NULL. 
let tppd_valueval = NULL. 
let tppd_nadredenid = NULL. 
let tdenovi_lp = 0 
let tdenovi_tp = 0 
let tppd_level = 18 
start select cursor.
select os_aneks_fakturaid, p.os_polisaid, o.period_osig, o.os_produktid, o.dogovoruvac_par_client, os_produkt_uplataid, (<procedure> vrati_premija_zivot, o.os_ponudaid, o.os_produktid), (nvl o.br_osig_lica, 1), o.datum_ponuda, f.par_tip_kniziid, o.os_ponudaid, o.datecreated, p.polisa_broj, (sum iznos_p), (sum iznos_p_den)
  from fin_stavka as f, os_polisa as p, os_ponuda as o
  where (and (and (and (and (and (and (and (and (= p.os_polisaid, f.os_polisaid), (= o.os_ponudaid, p.os_ponudaid)), (not-null iznos_p)), (not-in (<procedure> vrati_polisa, p.os_polisaid), 
    (select (<procedure> vrati_polisa, os_polisaid)
      from provizija_promotori_bodovi
      where (and (= tip_produkcija, "1"), (= par_agentid, tpar_agentid))))), (= o.promotor_par_agent, tpar_agentid)), (>= skadenca_datum_od, (date "01.02.2023"))), (in f.par_tip_kniziid, 285, 1128, 1567)), (between datum, (date "01.02.2023"), tdo_datum)), (<= datum_polisa, (mdy (+ (month tdo_datum), 1), 15, (year tdo_datum))))
  group by 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13
  having (<> (sum iznos_p_den), 0)
  order by o.datum_ponuda, o.datecreated, p.polisa_broj, f.par_tip_kniziid

execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 61117 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 19/000558 ; 
let poms = 19/000558 
expression:poms
evaluates to 19/000558       
procedure vrati_polisa returns 19/000558       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 7244 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 21/000309 ; 
let poms = 21/000309 
expression:poms
evaluates to 21/000309       
procedure vrati_polisa returns 21/000309       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 7731 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000108 ; 
let poms = 28/000108 
expression:poms
evaluates to 28/000108       
procedure vrati_polisa returns 28/000108       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 7991 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000168 ; 
let poms = 28/000168 
expression:poms
evaluates to 28/000168       
procedure vrati_polisa returns 28/000168       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 7991 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000168 ; 
let poms = 28/000168 
expression:poms
evaluates to 28/000168       
procedure vrati_polisa returns 28/000168       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 8240 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000241 ; 
let poms = 28/000241 
expression:poms
evaluates to 28/000241       
procedure vrati_polisa returns 28/000241       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 8292 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000246 ; 
let poms = 28/000246 
expression:poms
evaluates to 28/000246       
procedure vrati_polisa returns 28/000246       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 8580 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000312 ; 
let poms = 28/000312 
expression:poms
evaluates to 28/000312       
procedure vrati_polisa returns 28/000312       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 8777 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000357 ; 
let poms = 28/000357 
expression:poms
evaluates to 28/000357       
procedure vrati_polisa returns 28/000357       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 8803 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000365 ; 
let poms = 28/000365 
expression:poms
evaluates to 28/000365       
procedure vrati_polisa returns 28/000365       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 8828 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000367 ; 
let poms = 28/000367 
expression:poms
evaluates to 28/000367       
procedure vrati_polisa returns 28/000367       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 9014 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000416 ; 
let poms = 28/000416 
expression:poms
evaluates to 28/000416       
procedure vrati_polisa returns 28/000416       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 9014 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000416 ; 
let poms = 28/000416 
expression:poms
evaluates to 28/000416       
procedure vrati_polisa returns 28/000416       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 9021 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000420 ; 
let poms = 28/000420 
expression:poms
evaluates to 28/000420       
procedure vrati_polisa returns 28/000420       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 9151 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000443 ; 
let poms = 28/000443 
expression:poms
evaluates to 28/000443       
procedure vrati_polisa returns 28/000443       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 9163 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000448 ; 
let poms = 28/000448 
expression:poms
evaluates to 28/000448       
procedure vrati_polisa returns 28/000448       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 9319 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000504 ; 
let poms = 28/000504 
expression:poms
evaluates to 28/000504       
procedure vrati_polisa returns 28/000504       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 9324 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000507 ; 
let poms = 28/000507 
expression:poms
evaluates to 28/000507       
procedure vrati_polisa returns 28/000507       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 9478 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000563 ; 
let poms = 28/000563 
expression:poms
evaluates to 28/000563       
procedure vrati_polisa returns 28/000563       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 9492 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000168 ; 
let poms = 28/000168 
expression:poms
evaluates to 28/000168       
procedure vrati_polisa returns 28/000168       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 9577 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000608 ; 
let poms = 28/000608 
expression:poms
evaluates to 28/000608       
procedure vrati_polisa returns 28/000608       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 9578 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000609 ; 
let poms = 28/000609 
expression:poms
evaluates to 28/000609       
procedure vrati_polisa returns 28/000609       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 9580 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000610 ; 
let poms = 28/000610 
expression:poms
evaluates to 28/000610       
procedure vrati_polisa returns 28/000610       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 9757 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000707 ; 
let poms = 28/000707 
expression:poms
evaluates to 28/000707       
procedure vrati_polisa returns 28/000707       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 9759 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000709 ; 
let poms = 28/000709 
expression:poms
evaluates to 28/000709       
procedure vrati_polisa returns 28/000709       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 9759 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000709 ; 
let poms = 28/000709 
expression:poms
evaluates to 28/000709       
procedure vrati_polisa returns 28/000709       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 10659 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000842 ; 
let poms = 28/000842 
expression:poms
evaluates to 28/000842       
procedure vrati_polisa returns 28/000842       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 10932 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000889 ; 
let poms = 28/000889 
expression:poms
evaluates to 28/000889       
procedure vrati_polisa returns 28/000889       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 10933 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000890 ; 
let poms = 28/000890 
expression:poms
evaluates to 28/000890       
procedure vrati_polisa returns 28/000890       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 10975 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000899 ; 
let poms = 28/000899 
expression:poms
evaluates to 28/000899       
procedure vrati_polisa returns 28/000899       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 11441 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/000992 ; 
let poms = 28/000992 
expression:poms
evaluates to 28/000992       
procedure vrati_polisa returns 28/000992       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 20591 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/001862 ; 
let poms = 28/001862 
expression:poms
evaluates to 28/001862       
procedure vrati_polisa returns 28/001862       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 20651 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/001870 ; 
let poms = 28/001870 
expression:poms
evaluates to 28/001870       
procedure vrati_polisa returns 28/001870       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 20766 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/001889 ; 
let poms = 28/001889 
expression:poms
evaluates to 28/001889       
procedure vrati_polisa returns 28/001889       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 21839 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/002006 ; 
let poms = 28/002006 
expression:poms
evaluates to 28/002006       
procedure vrati_polisa returns 28/002006       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 21918 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/002018 ; 
let poms = 28/002018 
expression:poms
evaluates to 28/002018       
procedure vrati_polisa returns 28/002018       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 24405 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/002209 ; 
let poms = 28/002209 
expression:poms
evaluates to 28/002209       
procedure vrati_polisa returns 28/002209       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 24405 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/002209 ; 
let poms = 28/002209 
expression:poms
evaluates to 28/002209       
procedure vrati_polisa returns 28/002209       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 24661 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/002229 ; 
let poms = 28/002229 
expression:poms
evaluates to 28/002229       
procedure vrati_polisa returns 28/002229       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 24661 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/002229 ; 
let poms = 28/002229 
expression:poms
evaluates to 28/002229       
procedure vrati_polisa returns 28/002229       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 25189 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/002247 ; 
let poms = 28/002247 
expression:poms
evaluates to 28/002247       
procedure vrati_polisa returns 28/002247       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 25373 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/002257 ; 
let poms = 28/002257 
expression:poms
evaluates to 28/002257       
procedure vrati_polisa returns 28/002257       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 25414 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/002259 ; 
let poms = 28/002259 
expression:poms
evaluates to 28/002259       
procedure vrati_polisa returns 28/002259       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 27577 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/002571 ; 
let poms = 28/002571 
expression:poms
evaluates to 28/002571       
procedure vrati_polisa returns 28/002571       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 27669 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/002592 ; 
let poms = 28/002592 
expression:poms
evaluates to 28/002592       
procedure vrati_polisa returns 28/002592       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 27669 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/002592 ; 
let poms = 28/002592 
expression:poms
evaluates to 28/002592       
procedure vrati_polisa returns 28/002592       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 28163 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/002622 ; 
let poms = 28/002622 
expression:poms
evaluates to 28/002622       
procedure vrati_polisa returns 28/002622       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 28382 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/002624 ; 
let poms = 28/002624 
expression:poms
evaluates to 28/002624       
procedure vrati_polisa returns 28/002624       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 28712 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/002635 ; 
let poms = 28/002635 
expression:poms
evaluates to 28/002635       
procedure vrati_polisa returns 28/002635       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 28712 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/002635 ; 
let poms = 28/002635 
expression:poms
evaluates to 28/002635       
procedure vrati_polisa returns 28/002635       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 29879 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/002715 ; 
let poms = 28/002715 
expression:poms
evaluates to 28/002715       
procedure vrati_polisa returns 28/002715       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 29879 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/002715 ; 
let poms = 28/002715 
expression:poms
evaluates to 28/002715       
procedure vrati_polisa returns 28/002715       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 32254 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/002889 ; 
let poms = 28/002889 
expression:poms
evaluates to 28/002889       
procedure vrati_polisa returns 28/002889       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 32326 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/002890 ; 
let poms = 28/002890 
expression:poms
evaluates to 28/002890       
procedure vrati_polisa returns 28/002890       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 32326 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/002890 ; 
let poms = 28/002890 
expression:poms
evaluates to 28/002890       
procedure vrati_polisa returns 28/002890       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 33834 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/002937 ; 
let poms = 28/002937 
expression:poms
evaluates to 28/002937       
procedure vrati_polisa returns 28/002937       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 33834 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/002937 ; 
let poms = 28/002937 
expression:poms
evaluates to 28/002937       
procedure vrati_polisa returns 28/002937       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 33946 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/002941 ; 
let poms = 28/002941 
expression:poms
evaluates to 28/002941       
procedure vrati_polisa returns 28/002941       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 38639 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/003102 ; 
let poms = 28/003102 
expression:poms
evaluates to 28/003102       
procedure vrati_polisa returns 28/003102       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 41771 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/003305 ; 
let poms = 28/003305 
expression:poms
evaluates to 28/003305       
procedure vrati_polisa returns 28/003305       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 43194 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/003553 ; 
let poms = 28/003553 
expression:poms
evaluates to 28/003553       
procedure vrati_polisa returns 28/003553       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 43194 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/003553 ; 
let poms = 28/003553 
expression:poms
evaluates to 28/003553       
procedure vrati_polisa returns 28/003553       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 44485 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/003616 ; 
let poms = 28/003616 
expression:poms
evaluates to 28/003616       
procedure vrati_polisa returns 28/003616       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 45050 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/003636 ; 
let poms = 28/003636 
expression:poms
evaluates to 28/003636       
procedure vrati_polisa returns 28/003636       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 45687 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/003652 ; 
let poms = 28/003652 
expression:poms
evaluates to 28/003652       
procedure vrati_polisa returns 28/003652       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 51119 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/003872 ; 
let poms = 28/003872 
expression:poms
evaluates to 28/003872       
procedure vrati_polisa returns 28/003872       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 51138 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/003873 ; 
let poms = 28/003873 
expression:poms
evaluates to 28/003873       
procedure vrati_polisa returns 28/003873       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 51325 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/003898 ; 
let poms = 28/003898 
expression:poms
evaluates to 28/003898       
procedure vrati_polisa returns 28/003898       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 51325 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/003898 ; 
let poms = 28/003898 
expression:poms
evaluates to 28/003898       
procedure vrati_polisa returns 28/003898       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 52310 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/003931 ; 
let poms = 28/003931 
expression:poms
evaluates to 28/003931       
procedure vrati_polisa returns 28/003931       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 52310 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/003931 ; 
let poms = 28/003931 
expression:poms
evaluates to 28/003931       
procedure vrati_polisa returns 28/003931       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 54729 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/004000 ; 
let poms = 28/004000 
expression:poms
evaluates to 28/004000       
procedure vrati_polisa returns 28/004000       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 55899 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/004138 ; 
let poms = 28/004138 
expression:poms
evaluates to 28/004138       
procedure vrati_polisa returns 28/004138       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 55899 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/004138 ; 
let poms = 28/004138 
expression:poms
evaluates to 28/004138       
procedure vrati_polisa returns 28/004138       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 57297 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/004178 ; 
let poms = 28/004178 
expression:poms
evaluates to 28/004178       
procedure vrati_polisa returns 28/004178       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 57298 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/004179 ; 
let poms = 28/004179 
expression:poms
evaluates to 28/004179       
procedure vrati_polisa returns 28/004179       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 57298 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/004179 ; 
let poms = 28/004179 
expression:poms
evaluates to 28/004179       
procedure vrati_polisa returns 28/004179       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 57299 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/004180 ; 
let poms = 28/004180 
expression:poms
evaluates to 28/004180       
procedure vrati_polisa returns 28/004180       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 57299 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/004180 ; 
let poms = 28/004180 
expression:poms
evaluates to 28/004180       
procedure vrati_polisa returns 28/004180       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 57312 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/004181 ; 
let poms = 28/004181 
expression:poms
evaluates to 28/004181       
procedure vrati_polisa returns 28/004181       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 57312 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/004181 ; 
let poms = 28/004181 
expression:poms
evaluates to 28/004181       
procedure vrati_polisa returns 28/004181       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 58555 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/004230 ; 
let poms = 28/004230 
expression:poms
evaluates to 28/004230       
procedure vrati_polisa returns 28/004230       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 59252 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/004506 ; 
let poms = 28/004506 
expression:poms
evaluates to 28/004506       
procedure vrati_polisa returns 28/004506       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 61669 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 27/033489 ; 
let poms = 27/033489 
expression:poms
evaluates to 27/033489       
procedure vrati_polisa returns 27/033489       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 61669 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 27/033489 ; 
let poms = 27/033489 
expression:poms
evaluates to 27/033489       
procedure vrati_polisa returns 27/033489       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 62271 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/004587 ; 
let poms = 28/004587 
expression:poms
evaluates to 28/004587       
procedure vrati_polisa returns 28/004587       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 62271 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/004587 ; 
let poms = 28/004587 
expression:poms
evaluates to 28/004587       
procedure vrati_polisa returns 28/004587       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 62778 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/004594 ; 
let poms = 28/004594 
expression:poms
evaluates to 28/004594       
procedure vrati_polisa returns 28/004594       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 63482 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/004606 ; 
let poms = 28/004606 
expression:poms
evaluates to 28/004606       
procedure vrati_polisa returns 28/004606       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 65178 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 25/002982 ; 
let poms = 25/002982 
expression:poms
evaluates to 25/002982       
procedure vrati_polisa returns 25/002982       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 66330 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 27/035918 ; 
let poms = 27/035918 
expression:poms
evaluates to 27/035918       
procedure vrati_polisa returns 27/035918       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 66330 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 27/035918 ; 
let poms = 27/035918 
expression:poms
evaluates to 27/035918       
procedure vrati_polisa returns 27/035918       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 67491 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/004709 ; 
let poms = 28/004709 
expression:poms
evaluates to 28/004709       
procedure vrati_polisa returns 28/004709       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 68614 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/004746 ; 
let poms = 28/004746 
expression:poms
evaluates to 28/004746       
procedure vrati_polisa returns 28/004746       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 72764 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/004839 ; 
let poms = 28/004839 
expression:poms
evaluates to 28/004839       
procedure vrati_polisa returns 28/004839       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 72764 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/004839 ; 
let poms = 28/004839 
expression:poms
evaluates to 28/004839       
procedure vrati_polisa returns 28/004839       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 73496 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/004877 ; 
let poms = 28/004877 
expression:poms
evaluates to 28/004877       
procedure vrati_polisa returns 28/004877       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 74151 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/004891 ; 
let poms = 28/004891 
expression:poms
evaluates to 28/004891       
procedure vrati_polisa returns 28/004891       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 74152 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/004892 ; 
let poms = 28/004892 
expression:poms
evaluates to 28/004892       
procedure vrati_polisa returns 28/004892       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 74152 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/004892 ; 
let poms = 28/004892 
expression:poms
evaluates to 28/004892       
procedure vrati_polisa returns 28/004892       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 74335 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/004935 ; 
let poms = 28/004935 
expression:poms
evaluates to 28/004935       
procedure vrati_polisa returns 28/004935       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 74335 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/004935 ; 
let poms = 28/004935 
expression:poms
evaluates to 28/004935       
procedure vrati_polisa returns 28/004935       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 77185 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/005049 ; 
let poms = 28/005049 
expression:poms
evaluates to 28/005049       
procedure vrati_polisa returns 28/005049       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 77185 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/005049 ; 
let poms = 28/005049 
expression:poms
evaluates to 28/005049       
procedure vrati_polisa returns 28/005049       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 77185 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/005049 ; 
let poms = 28/005049 
expression:poms
evaluates to 28/005049       
procedure vrati_polisa returns 28/005049       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 77187 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/005050 ; 
let poms = 28/005050 
expression:poms
evaluates to 28/005050       
procedure vrati_polisa returns 28/005050       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 77192 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/005051 ; 
let poms = 28/005051 
expression:poms
evaluates to 28/005051       
procedure vrati_polisa returns 28/005051       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 77195 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/005052 ; 
let poms = 28/005052 
expression:poms
evaluates to 28/005052       
procedure vrati_polisa returns 28/005052       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 78704 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/005091 ; 
let poms = 28/005091 
expression:poms
evaluates to 28/005091       
procedure vrati_polisa returns 28/005091       


execute function vesna.vrati_polisa[procid=679] ( tos_polisaid = 78817 )
expression:
  (select (|| (|| o.sifra_polisa, "/"), l.polisa_broj)
    from os_ponuda as p, os_produkt as o, os_polisa as l
    where (and (and (= o.os_produktid, p.os_produktid), (= l.os_ponudaid, p.os_ponudaid)), (= l.os_polisaid, tos_polisaid)))
evaluates to 28/005094 ; 
let poms = 28/005094 
expression:poms
evaluates to 28/005094       
procedure vrati_polisa returns 28/005094       

exception : looking for handler
SQL error = -1205 ISAM error = 0  error string =  = ""
exception : handler FOUND
expression:(- 1)
evaluates to -1 
procedure presmetka_prov_promotori returns -1 , NASTANATA E GRE[KA 

iteration of cursory procedure presmetka_prov_promotori
