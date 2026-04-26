import json
import subprocess
import sys
from pathlib import Path

from prompts import prompt_g2s_download_specs

def download_g2s_json(run_download_prompt, download_json, json_path, g2s_cli_path):
    if run_download_prompt:
        reply = input("Download a new G2S JSON now? [y/n]: ").strip().lower()
        do_download = reply in {"y", "yes"}
    else:
        do_download = download_json

    if not do_download:
        return Path(json_path).expanduser().resolve()

    cli_path = Path(g2s_cli_path).expanduser().resolve()
    if not cli_path.exists():
        raise FileNotFoundError(f"G2S CLI not found: {cli_path}")

    specs = prompt_g2s_download_specs()
    out_json = Path(specs["output"]).expanduser().resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(cli_path),
        "point",
        "--date", specs["date"],
        "--hour", str(specs["hour"]),
        "--lat", str(specs["lat"]),
        "--lon", str(specs["lon"]),
        "--outputformat", "json",
        "--output", str(out_json),
    ]

    print("\nDownloading G2S JSON...")
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)

    if not out_json.exists():
        raise FileNotFoundError(f"Expected downloaded JSON not found: {out_json}")

    return out_json

def read_g2s_json(json_path: Path):
    with open(json_path, "r") as f:
        raw = json.load(f)

    param_map = {}
    for entry in raw.get("data", []):
        param = entry.get("parameter")
        if not param:
            continue
        param_map[param] = {
            "units": entry.get("units"),
            "values": entry.get("values"),
        }

    return {"meta": raw.get("metadata", {}), "data": param_map}