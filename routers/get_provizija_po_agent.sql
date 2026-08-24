CREATE FUNCTION appuser.get_provizija_po_agent (p_agentid INT)
   RETURNING VARCHAR(50), VARCHAR(50), DATE, DECIMAL(18,2), DECIMAL(18,2), DECIMAL(18,2);

   DEFINE tkolku INT;
   DEFINE tpolisa VARCHAR(50);
   DEFINE ttip_produkcija VARCHAR(50);
   DEFINE tdatum_presmetka DATE;
   DEFINE tprovizija DECIMAL(18,2);
   DEFINE tisplateno DECIMAL(18,2);
   DEFINE tostanato DECIMAL(18,2);

   --SET DEBUG FILE TO "err_get_provizija_po_agent.sql";
  -- TRACE ON;

 
   /*   SELECT 
         vrati_polisa(os_polisaid) AS polisa,
         tip_produkcija AS tip_produkcija,
         datum_presmetka AS datum_presmetka,
         SUM(iznos_bod) AS provizija,
         SUM(br_bodovi) AS bodovi
      FROM lc_provizija_agent_bodovi
      WHERE par_agentid = p_agentid
        AND par_statusid = 1
        and datum_presmetka>= date(EXTEND(ADD_MONTHS(TODAY, -48), YEAR TO MONTH))
      GROUP BY 1,2,3
      union
   --   INTO TEMP ta;
   --ELSE
      SELECT 
         vrati_polisa(os_polisaid) AS polisa,
         tip_produkcija AS tip_produkcija,
         datum_presmetka AS datum_presmetka,
         SUM(iznos_bod) AS provizija,
         SUM(br_bodovi) AS bodovi
      FROM provizija_promotori_bodovi
      WHERE par_agentid = p_agentid
        AND par_statusid = 1
        and datum_presmetka>= date(EXTEND(ADD_MONTHS(TODAY, -48), YEAR TO MONTH))
      GROUP BY 1,2,3
     INTO TEMP ta ;
   --END IF;
*/
WITH ta AS (
    SELECT
        p.polisa_broj_cel        AS polisa,
        a.tip_produkcija         AS tip_produkcija,
        a.datum_presmetka        AS datum_presmetka,
        SUM(a.iznos_bod)         AS provizija,
        SUM(a.br_bodovi)         AS bodovi
    FROM lc_provizija_agent_bodovi a
    JOIN os_polisa p  ON a.os_polisaid = p.os_polisaid
    JOIN os_ponuda o  ON p.os_ponudaid = o.os_ponudaid
    WHERE a.par_agentid = p_agentid
      AND a.par_statusid = 1
      AND o.skadenca_datum_od >= DATE(EXTEND(ADD_MONTHS(TODAY, -48), YEAR TO MONTH))
    GROUP BY 1,2,3

    UNION ALL

    SELECT
        p.polisa_broj_cel        AS polisa,
        a.tip_produkcija         AS tip_produkcija,
        a.datum_presmetka        AS datum_presmetka,
        SUM(a.iznos_bod)         AS provizija,
        SUM(a.br_bodovi)         AS bodovi
    FROM provizija_promotori_bodovi a
    JOIN os_polisa p  ON a.os_polisaid = p.os_polisaid
    JOIN os_ponuda o  ON p.os_ponudaid = o.os_ponudaid
    WHERE a.par_agentid = p_agentid
      AND a.par_statusid = 1
      AND o.skadenca_datum_od >= DATE(EXTEND(ADD_MONTHS(TODAY, -48), YEAR TO MONTH))
    GROUP BY 1,2,3
),
polisa_max AS (
    SELECT
        op.polisa_broj_cel,
        MAX(op.polisa_pod_broj) AS max_polisa_pod_broj
    FROM os_polisa op
    JOIN ta t
      ON t.polisa = op.polisa_broj_cel
    GROUP BY op.polisa_broj_cel
),
polisa AS (
    SELECT
        op.polisa_broj_cel,
        op.polisa_pod_broj
    FROM os_polisa op
    JOIN polisa_max pm
      ON pm.polisa_broj_cel = op.polisa_broj_cel
     AND pm.max_polisa_pod_broj = op.polisa_pod_broj
    JOIN os_ponuda oo
      ON op.os_ponudaid = oo.os_ponudaid
    WHERE op.status_polisa = 'K'
)
SELECT t.*
FROM ta t
JOIN polisa p
  ON p.polisa_broj_cel = t.polisa into temp ta; 



   -- Create temp table for already paid commissions
   SELECT 
         polisa_broj AS polisa_broj,
         SUM(iznos_provizija) AS prov
   FROM agenti_provizija1
   WHERE par_agentid = p_agentid
   GROUP BY 1
   INTO TEMP sa ;

   -- Return result set
   FOREACH
      SELECT 
         t.polisa,
         t.tip_produkcija,
         t.datum_presmetka,
         t.provizija,
         NVL(s.prov, 0),
         t.provizija - NVL(s.prov, 0)
      INTO tpolisa, ttip_produkcija, tdatum_presmetka, tprovizija, tisplateno, tostanato
      FROM ta t
      LEFT JOIN sa s ON t.polisa = s.polisa_broj

      RETURN tpolisa, ttip_produkcija, tdatum_presmetka, tprovizija, tisplateno, tostanato
      WITH RESUME;
   END FOREACH;

  -- TRACE OFF;

END FUNCTION;