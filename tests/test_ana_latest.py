import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from backend.main import _fetch_ana_latest


def xml_for(measured):
    return ("<DataTable><DadosHidrometereologicos><CodEstacao>87450020</CodEstacao>"
            f"<DataHora>{measured:%Y-%m-%d %H:%M:%S}</DataHora><Nivel>88.00</Nivel>"
            "</DadosHidrometereologicos></DataTable>").encode()


class CurrentLevelTests(unittest.TestCase):
    def setUp(self):
        _fetch_ana_latest.cache_clear()

    def test_recent_measurement_is_displayable(self):
        response = Mock(content=xml_for(datetime.now() - timedelta(minutes=15)))
        response.raise_for_status.return_value = None
        with patch("backend.main.requests.get", return_value=response):
            result = _fetch_ana_latest(1)
        self.assertEqual(result["status"], "recent")
        self.assertEqual(result["level_m"], 0.88)
        self.assertEqual(result["station_code"], "87450020")

    def test_stale_measurement_is_not_current(self):
        response = Mock(content=xml_for(datetime.now() - timedelta(hours=4)))
        response.raise_for_status.return_value = None
        with patch("backend.main.requests.get", return_value=response):
            result = _fetch_ana_latest(2)
        self.assertEqual(result["status"], "stale")
        self.assertEqual(result["level_m"], 0.88)


if __name__ == "__main__":
    unittest.main()
