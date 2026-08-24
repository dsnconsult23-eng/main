"""
Unit тестови за филтрите во routers/report_fakturi.py.

Ги тестира само чистите функции _build_sql() / _build_sintetika_sql() —
не бара DB конекција, само проверува дека секој филтер го генерира
очекуваниот WHERE услов и параметар (по редослед).

Стартување:  python -m unittest tests.test_report_fakturi_filters -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routers.report_fakturi import _build_sql, _build_sintetika_sql


class BuildSqlFilterTests(unittest.TestCase):
    """По еден тест за секој филтер во _build_sql — проверува дека
    филтерот се додава во WHERE и параметарот е точната внесена вредност."""

    def test_no_filters_produces_base_query_only(self):
        sql, params = _build_sql({}, "polisa")
        self.assertEqual(params, [])
        self.assertIn("WHERE NVL(x3.f_rs,'R') <> 'N'", sql)

    def test_klient_filter(self):
        sql, params = _build_sql({"klient": "Петровски"}, "polisa")
        self.assertIn("UPPER(pc.desc) LIKE ?", sql)
        self.assertEqual(params, ["%ПЕТРОВСКИ%"])

    def test_faktura_filter(self):
        sql, params = _build_sql({"faktura": "123/2026-1"}, "polisa")
        self.assertIn("LIKE ?", sql)
        self.assertEqual(params, ["%123/2026-1%"])

    def test_tip_knizi_filter(self):
        sql, params = _build_sql({"tip_knizi": "фактура"}, "polisa")
        self.assertEqual(params, ["%ФАКТУРА%"])

    def test_polisa_broj_single(self):
        sql, params = _build_sql({"polisa_broj": "19/12345"}, "polisa")
        self.assertIn("x2.polisa_broj_cel) LIKE ?", sql)
        self.assertEqual(params, ["%19/12345%"])

    def test_polisa_broj_multiple_comma_separated(self):
        sql, params = _build_sql({"polisa_broj": "19/1, 19/2 ,19/3"}, "polisa")
        self.assertEqual(sql.count("polisa_broj_cel) LIKE ?"), 3)
        self.assertEqual(params, ["%19/1%", "%19/2%", "%19/3%"])

    def test_polisa_broj_multiple_semicolon_separated(self):
        sql, params = _build_sql({"polisa_broj": "19/1;19/2"}, "polisa")
        self.assertEqual(params, ["%19/1%", "%19/2%"])

    def test_iznos_od_do(self):
        sql, params = _build_sql({"iznos_od": "100", "iznos_do": "200"}, "polisa")
        self.assertIn("x0.iznos >= ?", sql)
        self.assertIn("x0.iznos <= ?", sql)
        self.assertEqual(params, ["100", "200"])

    def test_iznos_den_od_do(self):
        sql, params = _build_sql({"iznos_den_od": "1000", "iznos_den_do": "2000"}, "polisa")
        self.assertIn("x0.iznos_denari >= ?", sql)
        self.assertIn("x0.iznos_denari <= ?", sql)
        self.assertEqual(params, ["1000", "2000"])

    def test_naplata_od_do(self):
        sql, params = _build_sql({"naplata_od": "50", "naplata_do": "150"}, "polisa")
        self.assertIn("vrati_naplata(x0.os_aneks_fakturaid) >= ?", sql)
        self.assertIn("vrati_naplata(x0.os_aneks_fakturaid) <= ?", sql)
        self.assertEqual(params, ["50", "150"])

    def test_naplata_den_od_do(self):
        sql, params = _build_sql({"naplata_den_od": "500", "naplata_den_do": "1500"}, "polisa")
        self.assertIn("vrati_naplata_den(x0.os_aneks_fakturaid) >= ?", sql)
        self.assertIn("vrati_naplata_den(x0.os_aneks_fakturaid) <= ?", sql)
        self.assertEqual(params, ["500", "1500"])

    def test_datum_aneks_od_do(self):
        sql, params = _build_sql({"datum_aneks_od": "2026-01-01", "datum_aneks_do": "2026-12-31"}, "polisa")
        self.assertEqual(params, ["2026-01-01", "2026-12-31"])
        self.assertIn("datum_aneks", sql)

    def test_datum_valuta_od_do_are_independent(self):
        """Регресионен тест: 'датум валута до' некогаш погрешно ја земаше
        вредноста од 'датум валута од' (copy-paste баг во report_fakturi_post).
        Оваа проверка е на нивото на _build_sql, каде филтрите се веќе
        точно именувани во filters dict-от."""
        sql, params = _build_sql(
            {"datum_valuta_od": "2026-01-01", "datum_valuta_do": "2026-06-30"}, "polisa"
        )
        self.assertIn("x0.data_valuta >= ?", sql)
        self.assertIn("x0.data_valuta <= ?", sql)
        self.assertEqual(params, ["2026-01-01", "2026-06-30"])
        # ако некогаш повторно се "слепи" бага, двата параметри ќе бидат исти
        self.assertNotEqual(params[0], params[1])

    def test_datum_faktura_od_do(self):
        sql, params = _build_sql({"datum_faktura_od": "2026-01-01", "datum_faktura_do": "2026-01-31"}, "polisa")
        self.assertIn("x0.data_faktura >= ?", sql)
        self.assertIn("x0.data_faktura <= ?", sql)
        self.assertEqual(params, ["2026-01-01", "2026-01-31"])

    def test_datum_knizi_od_do(self):
        sql, params = _build_sql({"datum_knizi_od": "2026-01-01", "datum_knizi_do": "2026-01-31"}, "polisa")
        self.assertIn("x3.dat_nalog >= ?", sql)
        self.assertIn("x3.dat_nalog <= ?", sql)
        self.assertEqual(params, ["2026-01-01", "2026-01-31"])

    def test_broker_filter(self):
        sql, params = _build_sql({"broker": "Брокер ДОО"}, "polisa")
        self.assertIn("UPPER(brk.desc) LIKE ?", sql)
        self.assertEqual(params, ["%БРОКЕР ДОО%"])

    def test_agent_filter(self):
        sql, params = _build_sql({"agent": "Иван"}, "polisa")
        self.assertIn("UPPER(agt.desc) LIKE ?", sql)
        self.assertEqual(params, ["%ИВАН%"])

    def test_posrednik_filter(self):
        sql, params = _build_sql({"posrednik": "Посредник"}, "polisa")
        self.assertIn("UPPER(psr.desc) LIKE ?", sql)
        self.assertEqual(params, ["%ПОСРЕДНИК%"])

    def test_promotor_filter(self):
        sql, params = _build_sql({"promotor": "Промотор"}, "polisa")
        self.assertIn("UPPER(prm.desc) LIKE ?", sql)
        self.assertEqual(params, ["%ПРОМОТОР%"])

    def test_dospeana_without_datum_faktura_do_adds_today(self):
        sql, params = _build_sql({"dospeana": True}, "polisa")
        self.assertIn("> 0.005", sql)
        self.assertEqual(len(params), 1)  # автоматски додаден TODAY isoformat

    def test_dospeana_with_datum_faktura_do_does_not_duplicate_date_filter(self):
        sql, params = _build_sql({"dospeana": True, "datum_faktura_do": "2026-05-01"}, "polisa")
        # datum_faktura_do веќе е внесен рачно -> dospeana не додава уште еден TODAY филтер
        self.assertEqual(params, ["2026-05-01"])

    def test_klient_tip_fizicko(self):
        sql, params = _build_sql({"klient_tip": "Физичко"}, "polisa")
        self.assertIn("pc.client_tip_pf = ?", sql)
        self.assertEqual(params, ["F"])

    def test_klient_tip_pravno(self):
        sql, params = _build_sql({"klient_tip": "Правно"}, "polisa")
        self.assertEqual(params, ["P"])

    def test_klient_tip_site_no_filter(self):
        sql, params = _build_sql({"klient_tip": "site"}, "polisa")
        self.assertEqual(params, [])

    def test_kanali_filter(self):
        sql, params = _build_sql({"kanali": ["Банки", "Промотор"]}, "polisa")
        self.assertIn("pk.desc_mk IN (?, ?)", sql)
        self.assertEqual(params, ["Банки", "Промотор"])

    def test_admin_zabrana_klient_filter(self):
        sql, params = _build_sql({"admin_zabrana_klient": "Банка АД"}, "polisa")
        self.assertIn("UPPER(azc.desc) LIKE ?", sql)
        self.assertEqual(params, ["%БАНКА АД%"])

    def test_samo_admin_zabrana_filter(self):
        sql, params = _build_sql({"samo_admin_zabrana": True}, "polisa")
        self.assertIn("x4.banka_par_client IS NOT NULL", sql)
        self.assertEqual(params, [])

    def test_admin_zabrana_klient_takes_precedence_over_samo_admin_zabrana(self):
        sql, params = _build_sql(
            {"admin_zabrana_klient": "Банка АД", "samo_admin_zabrana": True}, "polisa"
        )
        # elif логика: кога е внесено admin_zabrana_klient, samo_admin_zabrana се игнорира
        self.assertEqual(params, ["%БАНКА АД%"])
        self.assertNotIn("x4.banka_par_client IS NOT NULL", sql)

    def test_nivo_polisa_groups_by_polisa(self):
        sql, _ = _build_sql({}, "polisa")
        self.assertIn("GROUP BY x2.polisa_broj_cel, x2.os_polisaid", sql)

    def test_nivo_faktura_groups_by_faktura(self):
        sql, _ = _build_sql({}, "faktura")
        self.assertIn("GROUP BY 1, x2.os_polisaid, 3, 4", sql)

    def test_nivo_red_has_no_group_by(self):
        sql, _ = _build_sql({}, "red")
        self.assertNotIn("GROUP BY", sql)

    def test_all_filters_combined_preserve_param_order(self):
        filters = {
            "klient": "Тест", "faktura": "1/2026-1", "polisa_broj": "19/1",
            "iznos_od": "10", "iznos_do": "20",
            "broker": "Брокер",
        }
        sql, params = _build_sql(filters, "red")
        self.assertEqual(
            params,
            ["%ТЕСТ%", "%1/2026-1%", "%19/1%", "10", "20", "%БРОКЕР%"],
        )


class BuildSintetikaSqlFilterTests(unittest.TestCase):

    def test_no_filters(self):
        sql, params = _build_sintetika_sql({})
        self.assertEqual(params, [])

    def test_polisa_broj_filter(self):
        sql, params = _build_sintetika_sql({"polisa_broj": "19/123"})
        self.assertIn("UPPER(x3.polisa_broj_cel) LIKE ?", sql)
        self.assertEqual(params, ["%19/123%"])

    def test_klient_filter(self):
        sql, params = _build_sintetika_sql({"klient": "Марко"})
        self.assertEqual(params, ["%МАРКО%"])

    def test_admin_zabrana_klient_also_forces_banka_filter(self):
        sql, params = _build_sintetika_sql({"admin_zabrana_klient": "Банка"})
        self.assertIn("UPPER(pcb.desc) LIKE ?", sql)
        self.assertIn("x4.banka_par_client IS NOT NULL", sql)
        self.assertEqual(params, ["%БАНКА%"])

    def test_klient_tip_fizicko_pravno(self):
        _, params_f = _build_sintetika_sql({"klient_tip": "Физичко"})
        self.assertEqual(params_f, ["F"])
        _, params_p = _build_sintetika_sql({"klient_tip": "Правно"})
        self.assertEqual(params_p, ["P"])


if __name__ == "__main__":
    unittest.main()
