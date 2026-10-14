from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


class DataSourceDefaultTests(unittest.TestCase):
    def test_concept2_api_is_default_without_token_or_csv_files(self) -> None:
        app_script = Path(__file__).parent / "treningshistorikk_app" / "app.py"
        with tempfile.TemporaryDirectory() as temporary:
            data_dir = Path(temporary) / "Data"
            with patch.dict(
                os.environ,
                {
                    "SKIERGPORTAL_DATA_DIR": str(data_dir),
                    "CONCEPT2_ACCESS_TOKEN": "",
                },
            ):
                app = AppTest.from_file(str(app_script), default_timeout=30).run()

        self.assertFalse(app.exception, [error.message for error in app.exception])
        source = next(radio for radio in app.radio if radio.label == "Velg datakilde")
        self.assertEqual(source.value, "Concept2 API")


if __name__ == "__main__":
    unittest.main()