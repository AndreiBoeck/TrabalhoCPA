import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from backend import main
from backend.main import BRT, _fetch_live


def xml_for(measured):
    return ("<DataTable><DadosHidrometereologicos><CodEstacao>87450020</CodEstacao>"
            f"<DataHora>{measured:%Y-%m-%d %H:%M:%S}</DataHora><Nivel>88.00</Nivel>"
            "</DadosHidrometereologicos></DataTable>").encode()


class CurrentLevelTests(unittest.TestCase):
    def setUp(self):
        _fetch_live.cache_clear()
        main._ANA_DAYS.clear()
        main._LAST_LIVE.clear()

    def test_recent_measurement_is_displayable(self):
        response = Mock(content=xml_for(datetime.now(BRT).replace(tzinfo=None) - timedelta(minutes=15)))
        response.raise_for_status.return_value = None
        with patch("backend.main.requests.get", return_value=response):
            result = _fetch_live(1)
        self.assertEqual(result["status"], "recent")
        self.assertEqual(result["level_m"], 0.88)
        self.assertEqual(result["level_regua_m"], 2.06)
        self.assertEqual(result["station_code"], "87450020")

    def test_stale_measurement_is_not_current(self):
        response = Mock(content=xml_for(datetime.now(BRT).replace(tzinfo=None) - timedelta(hours=4)))
        response.raise_for_status.return_value = None
        with patch("backend.main.requests.get", return_value=response):
            result = _fetch_live(2)
        self.assertEqual(result["status"], "stale")
        self.assertEqual(result["level_m"], 0.88)
        self.assertEqual(result["level_regua_m"], 2.06)

    def test_source_failure_keeps_last_good_reading(self):
        response = Mock(content=xml_for(datetime.now(BRT).replace(tzinfo=None) - timedelta(minutes=15)))
        response.raise_for_status.return_value = None
        with patch("backend.main.requests.get", return_value=response):
            _fetch_live(3)
        main._ANA_DAYS.clear()
        with patch("backend.main.requests.get", side_effect=main.requests.Timeout()):
            result = _fetch_live(4)
        self.assertEqual(result["level_m"], 0.88)
        self.assertTrue(result["source_error"])


if __name__ == "__main__":
    unittest.main()
