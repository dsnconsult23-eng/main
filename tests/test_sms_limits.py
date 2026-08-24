import importlib
import sys
import unittest
from unittest.mock import Mock, patch


def _load_sms_module():
    if "routers.SMS" in sys.modules:
        return sys.modules["routers.SMS"]
    ip_response = Mock()
    ip_response.json.return_value = {"ip": "127.0.0.1"}
    with patch("requests.get", return_value=ip_response):
        return importlib.import_module("routers.SMS")


SMS = _load_sms_module()


class SmsDospeanaLimitTests(unittest.TestCase):
    def test_eur_limit_is_five_in_both_supported_currency_ids(self):
        for currency_id in (1, 363, "EUR"):
            with self.subTest(currency_id=currency_id):
                self.assertFalse(SMS._dpp_meets_sms_limit(currency_id, 4.99))
                self.assertTrue(SMS._dpp_meets_sms_limit(currency_id, 5))

    def test_mkd_limit_is_three_hundred(self):
        self.assertFalse(SMS._dpp_meets_sms_limit(362, 299.99))
        self.assertTrue(SMS._dpp_meets_sms_limit(362, 300))

    def test_invalid_amount_does_not_pass(self):
        self.assertFalse(SMS._dpp_meets_sms_limit(363, None))
        self.assertFalse(SMS._dpp_meets_sms_limit(363, "invalid"))

    def test_tip_a_requires_active_final_policy(self):
        self.assertTrue(SMS._tip_a_has_eligible_final_status({
            "polisa_status": "Активна",
            "polisa_status_desc": "Полисирана",
            "polisa_sosotojba": "Полисирана",
        }))
        self.assertFalse(SMS._tip_a_has_eligible_final_status({
            "polisa_status": "Неактивна",
            "polisa_status_desc": "Откуп",
            "polisa_sosotojba": "Откуп",
        }))

    def test_tip_a_rejects_terminal_description_even_if_marked_active(self):
        self.assertFalse(SMS._tip_a_has_eligible_final_status({
            "polisa_status": "Активна",
            "polisa_status_desc": "Доживеана Исплатена",
            "polisa_sosotojba": "Полисирана",
        }))

    def test_tip_a_fails_closed_when_status_is_missing(self):
        self.assertFalse(SMS._tip_a_has_eligible_final_status({}))

    def test_replacement_policies_are_loaded_in_batches_and_merged(self):
        class FakeCursor:
            def __init__(self):
                self.query_count = 0

            def execute(self, sql, params):
                self.query_count += 1

            def fetchall(self):
                return [("A", "B"), ("B", "C"), ("C", None), ("D", None)]

        cursor = FakeCursor()
        result = SMS._merge_dolg_po_polisa_zamena(cursor, [
            ("A", "070111111", 363, 10),
            ("B", None, 363, 5),
            ("D", "070222222", 363, 7),
        ], has_valuta=True)

        by_policy = {row[0]: row for row in result}
        self.assertEqual(by_policy["C"][3], 15)
        self.assertEqual(by_policy["C"][1], "070111111")
        self.assertEqual(by_policy["D"][3], 7)
        self.assertLessEqual(cursor.query_count, 2)


if __name__ == "__main__":
    unittest.main()
