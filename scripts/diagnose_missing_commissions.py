import argparse
import csv
import re
import sys
from calendar import monthrange
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_ifx import Informixdriver


def reason(row):
    polisa, invoice_id, _, paid, debt, lc_count, lc_amount, promoter_count, lc_calc, promoter_calc = row
    paid = float(paid or 0)
    debt = float(debt or 0)
    if lc_calc + promoter_calc > 0:
        return "IMA_PRESMETKA"
    if abs(paid - debt) > 0.01:
        return "NECELOSNO_NAPLATENA_DO_KRAJ_NA_PERIOD"
    if lc_count == 0 and promoter_count == 0:
        return "NEMA_BODOVI"
    if lc_count > 0 and float(lc_amount or 0) == 0:
        return "LC_IZNOS_BOD_NULA"
    if lc_count > 0:
        return "LC_BODOVI_NO_NEMA_PRESMETKA"
    return "PROMOTOR_BODOVI_NO_NEMA_PRESMETKA"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("policy_file", type=Path)
    parser.add_argument("month", type=int)
    parser.add_argument("year", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    policies = sorted(set(re.findall(r"\d{2}/\d{6}", args.policy_file.read_text(encoding="utf-8", errors="ignore"))))
    if not policies:
        raise SystemExit("No policy numbers found.")
    if not 1 <= args.month <= 12:
        raise SystemExit("Month must be 1-12.")

    quoted = ",".join("'" + value.replace("'", "''") + "'" for value in policies)
    last_day = monthrange(args.year, args.month)[1]
    period_start = f"{args.month:02d}/01/{args.year:04d}"
    period_end = f"{args.month:02d}/{last_day:02d}/{args.year:04d}"
    sql = f"""
        SELECT TRIM(p.polisa_broj_cel), f.os_aneks_fakturaid, p.os_polisaid,
               SUM(CASE WHEN f.par_tip_dokumentid=285 AND f.iznos_p IS NOT NULL
                         AND f.datum<=DATE('{period_end}') THEN f.iznos_p ELSE 0 END),
               SUM(NVL(f.iznos_d,0)),
               (SELECT COUNT(*) FROM lc_provizija_agent_bodovi b WHERE b.os_polisaid=p.os_polisaid),
               (SELECT NVL(SUM(ABS(b.iznos_bod)),0) FROM lc_provizija_agent_bodovi b WHERE b.os_polisaid=p.os_polisaid),
               (SELECT COUNT(*) FROM provizija_promotori_bodovi b WHERE b.os_polisaid=p.os_polisaid),
               (SELECT COUNT(*) FROM lc_provizija_agent_presmetka x WHERE x.os_aneks_fakturaid=f.os_aneks_fakturaid),
               (SELECT COUNT(*) FROM provizija_promotori_presmetka x WHERE x.os_aneks_fakturaid=f.os_aneks_fakturaid)
        FROM os_polisa p JOIN fin_stavka f ON f.os_polisaid=p.os_polisaid
        WHERE TRIM(p.polisa_broj_cel) IN ({quoted})
          AND EXISTS (
              SELECT 1 FROM fin_stavka fm
              WHERE fm.os_aneks_fakturaid=f.os_aneks_fakturaid
                AND fm.iznos_p IS NOT NULL
                AND fm.datum BETWEEN DATE('{period_start}') AND DATE('{period_end}')
          )
        GROUP BY 1,2,3
        ORDER BY 1,2
    """

    conn = Informixdriver()
    try:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()

    output = args.output or Path(f"outputs/commission_diagnosis_{args.year}_{args.month:02d}.csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["polisa", "os_aneks_fakturaid", "naplata_do_period", "dolg", "lc_bodovi", "lc_iznos_bod", "promotor_bodovi", "lc_presmetki", "promotor_presmetki", "pricina"])
        for row in rows:
            writer.writerow([row[0], row[1], row[3], row[4], row[5], row[6], row[7], row[8], row[9], reason(row)])

    print(f"Policies: {len(policies)}; invoices: {len(rows)}; output: {output.resolve()}")


if __name__ == "__main__":
    main()
