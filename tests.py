# tests.py
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import profiles_update as pu


def create_valid_test_json(path):
    """Write a minimal valid G2S-style JSON file."""
    test_data = {
        "metadata": {},
        "data": [
            {"parameter": "Z0", "values": [1.0]},
            {"parameter": "Z",  "values": [0.0, 1.0]},
            {"parameter": "T",  "values": [280.0, 275.0]},
            {"parameter": "U",  "values": [5.0, 6.0]},
            {"parameter": "V",  "values": [1.0, 2.0]},
            {"parameter": "R",  "values": [0.0012, 0.0011]},
            {"parameter": "P",  "values": [1000.0, 900.0]},
        ],
    }
    with open(path, "w") as f:
        json.dump(test_data, f)


def create_invalid_test_json(path):
    """Write an invalid JSON file missing pressure P."""
    test_data = {
        "metadata": {},
        "data": [
            {"parameter": "Z0", "values": [1.0]},
            {"parameter": "Z",  "values": [0.0, 1.0]},
            {"parameter": "T",  "values": [280.0, 275.0]},
            {"parameter": "U",  "values": [5.0, 6.0]},
            {"parameter": "V",  "values": [1.0, 2.0]},
            {"parameter": "R",  "values": [0.0012, 0.0011]},
        ],
    }
    with open(path, "w") as f:
        json.dump(test_data, f)


def test_main_creates_csv_for_valid_json():
    """Main should run successfully and create the output CSV."""
    with tempfile.TemporaryDirectory() as tmp:
        json_path = Path(tmp) / "sample.json"
        create_valid_test_json(json_path)

        with patch.object(pu, "download_g2s_json", return_value=json_path), \
             patch.object(pu, "RUN_AZIMUTH_PROMPT", False), \
             patch.object(pu, "RUN_PLOT_PROMPT", False), \
             patch.object(pu, "SHOW_PLOTS", False), \
             patch.object(pu, "SAVE_PLOTS", False), \
             patch.object(pu, "plot_profile", return_value=None):

            pu.main()

        output_csv = Path(tmp) / "sample_profiles.csv"
        assert output_csv.exists(), "Expected output CSV was not created"


def test_main_raises_error_for_missing_json_file():
    """Main should raise FileNotFoundError if the JSON file does not exist."""
    fake_path = Path("/tmp/this_file_does_not_exist.json")

    with patch.object(pu, "download_g2s_json", return_value=fake_path):
        try:
            pu.main()
            assert False, "Expected FileNotFoundError"
        except FileNotFoundError:
            pass


def test_main_raises_error_for_missing_required_parameter():
    """Main should raise KeyError if a required JSON parameter is missing."""
    with tempfile.TemporaryDirectory() as tmp:
        json_path = Path(tmp) / "bad.json"
        create_invalid_test_json(json_path)

        with patch.object(pu, "download_g2s_json", return_value=json_path), \
             patch.object(pu, "RUN_AZIMUTH_PROMPT", False), \
             patch.object(pu, "RUN_PLOT_PROMPT", False), \
             patch.object(pu, "SHOW_PLOTS", False), \
             patch.object(pu, "SAVE_PLOTS", False), \
             patch.object(pu, "plot_profile", return_value=None):

            try:
                pu.main()
                assert False, "Expected KeyError"
            except KeyError:
                pass


if __name__ == "__main__":
    test_main_creates_csv_for_valid_json()
    test_main_raises_error_for_missing_json_file()
    test_main_raises_error_for_missing_required_parameter()
    print("All tests passed.")