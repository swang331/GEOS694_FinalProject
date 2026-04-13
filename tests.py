#!/usr/bin/env python3
import json
import tempfile
import builtins
from pathlib import Path

import profiles_update as pu


def _fake_input_factory(responses):
    it = iter(responses)

    def _input(prompt=""):
        try:
            return next(it)
        except StopIteration:
            return ""
    return _input


def test_format_and_azimuth_and_build():
    assert pu.format_deg_for_filename(0.0) == "0"
    assert pu.format_deg_for_filename(45.0) == "45"
    assert pu.format_deg_for_filename(12.5) == "12.5"

    a = pu.AzimuthConfig()
    lst = a.get_list()
    assert isinstance(lst, list) and len(lst) > 0
    c = a.get_list()
    c.append(999.0)
    assert 999.0 not in a.get_list()

    minimal = {"data": {"Z": {"values": [0]}, "T": {"values": [290]}, "U": {"values": [0]}, "V": {"values": [0]}, "R": {"values": [0]}, "P": {"values": [0]}}}
    try:
        pu.build_profile_dataframe(minimal)
        raise AssertionError("Expected KeyError for missing Z0")
    except KeyError:
        pass


def test_prompt_g2s_download_specs():
    responses = [
        "2023-10-18",  # date
        "15",          # hour
        "37.238",      # lat
        "-116.159",    # lon
        "",            # accept default output path
    ]
    orig_input = builtins.input
    builtins.input = _fake_input_factory(responses)
    try:
        specs = pu.prompt_g2s_download_specs()
        assert "date" in specs and "hour" in specs and "lat" in specs and "lon" in specs and "output" in specs
    finally:
        builtins.input = orig_input


def test_prompt_plot_behavior():
    # Case 1: show=True then save=False
    orig_input = builtins.input
    builtins.input = _fake_input_factory(["y", "n"])
    try:
        show, save = pu.prompt_plot_behavior()
        assert show is True and save is False
    finally:
        builtins.input = orig_input

    # Case 2: show=False then save=True
    builtins.input = _fake_input_factory(["n", "y"])
    try:
        show, save = pu.prompt_plot_behavior()
        assert show is False and save is True
    finally:
        builtins.input = orig_input


def test_download_g2s_json_no_download():
    # Ensure when we're not downloading, the function returns the existing JSON path
    td = tempfile.TemporaryDirectory()
    tdpath = Path(td.name)
    jf = tdpath / "dummy.json"
    jf.write_text("{}")

    # Backup and set flags
    orig_RUN_PROMPT = pu.RUN_DOWNLOAD_PROMPT
    orig_DOWNLOAD_JSON = pu.DOWNLOAD_JSON
    orig_JSON_PATH = pu.JSON_PATH
    try:
        pu.RUN_DOWNLOAD_PROMPT = False
        pu.DOWNLOAD_JSON = False
        pu.JSON_PATH = str(jf)
        out = pu.download_g2s_json()
        assert Path(out).resolve() == jf.resolve()
    finally:
        pu.RUN_DOWNLOAD_PROMPT = orig_RUN_PROMPT
        pu.DOWNLOAD_JSON = orig_DOWNLOAD_JSON
        pu.JSON_PATH = orig_JSON_PATH

    td.cleanup()


def test_read_g2s_json():
    td = tempfile.TemporaryDirectory()
    tdpath = Path(td.name)
    sample = {
        "metadata": {"time": {"datetime": "now"}, "location": {"latitude": 1.0, "longitude": 2.0}},
        "data": [
            {"parameter": "Z0", "units": "km", "values": [0.0]},
            {"parameter": "Z", "units": "km", "values": [0.0]},
            {"parameter": "T", "units": "K", "values": [300.0]},
            {"parameter": "U", "units": "m/s", "values": [0.0]},
            {"parameter": "V", "units": "m/s", "values": [0.0]},
            {"parameter": "R", "units": "g/cm^3", "values": [0.001]},
            {"parameter": "P", "units": "mbar", "values": [1013.25]},
        ],
    }
    p = tdpath / "g2s.json"
    p.write_text(json.dumps(sample))

    out = pu.read_g2s_json(p)
    assert "meta" in out and "data" in out
    # data should be a dict keyed by parameter names
    assert isinstance(out["data"], dict)
    assert "Z" in out["data"] and "T" in out["data"]

    td.cleanup()


def main():
    test_format_and_azimuth_and_build()
    test_prompt_g2s_download_specs()
    test_prompt_plot_behavior()
    test_download_g2s_json_no_download()
    test_read_g2s_json()
    print("All minimal tests passed")


if __name__ == "__main__":
    main()