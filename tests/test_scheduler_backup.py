import unittest
from unittest.mock import patch

from routers import SchedulerBackUp


class SchedulerPostingTypeTests(unittest.TestCase):
    @patch.object(SchedulerBackUp, "scheduled_knizi")
    def test_knizhno_odobrenie_uses_ko_type(self, scheduled_knizi):
        SchedulerBackUp.scheduled_knizi_KO()

        scheduled_knizi.assert_called_once_with("f_ko", 0, "KO")

    @patch.object(SchedulerBackUp, "scheduled_knizi")
    def test_popust_uses_po_type(self, scheduled_knizi):
        SchedulerBackUp.scheduled_knizi_PO()

        scheduled_knizi.assert_called_once_with("f_popust", 1, "PO")


if __name__ == "__main__":
    unittest.main()
