#!/usr/bin/env python3
"""
Convert a downloaded G2S profile JSON into:
  1) a CSV of profiles (T, U, V, density, pressure) plus sound speeds
  2) simple profile plots with height on the y-axis (meters AGL)

G2S JSON -> DataFrame -> CSV + plots

Outputs written next to the JSON:
  - <stem>_profiles.csv (includes z in km and m, plus c0 and c_eff)
  - <stem>_T_profile.png, <stem>_U_profile.png, <stem>_V_profile.png,
    <stem>_rho_profile.png, <stem>_P_profile.png
  - <stem>_cEff_alpha<deg>_profile.png

G2S source code: https://github.com/chetzer-ncpa/ncpag2s-clc
"""

import json
from math import cos, sin, radians
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# User config
JSON_PATH = r"/Users/serinawang/Desktop/g2s_2023-10-18.json"    # Specify G2S file path here

# OR: download JSON file in script
DOWNLOAD_JSON = False          # Default behavior if not prompting
RUN_DOWNLOAD_PROMPT = True     # Ask at runtime whether to download a new JSON

# Path to the existing G2S wrapper
G2S_CLI_PATH = r"/Users/serinawang/Desktop/GEOS694_FinalProject/ncpag2s.py"


# Direction of propagation for effective sound speed, measured clockwise from East:
# One or more azimuths (deg) profiles, clockwise from East: 0=E, 90=N, 180=W, 270=S
DEFAULT_PROPAGATION_AZIMUTHS_DEG = [0.0, 90.0, 180.0, 270.0]
RUN_AZIMUTH_PROMPT = True

# Googled parameters
GAMMA_AIR = 1.4          # heat capacity ratio
R_DRY_AIR = 287.0        # J/(kg*K)

# Plot control
PLOT_MAX_HEIGHT_M = 100000
SHOW_PLOTS = True


class AzimuthConfig:
    """
    Store and manage propagation azimuths for effective sound speed calculations.
    """
    def __init__(self, azimuths_deg=None):
        if azimuths_deg is None:
            azimuths_deg = DEFAULT_PROPAGATION_AZIMUTHS_DEG.copy()
        self.azimuths_deg = [float(az) % 360.0 for az in azimuths_deg]

    def prompt_user(self):
        """
        Prompt user for one or more azimuths and update the stored list.
        """
        default_str = ", ".join(f"{az:g}" for az in self.azimuths_deg)
        reply = input(
            f"Enter propagation azimuth(s) in degrees, comma-separated [{default_str}]: "
        ).strip()

        if reply:
            self.azimuths_deg = [float(item.strip()) % 360.0 for item in reply.split(",")]

        return self.azimuths_deg

    def get_list(self):
        """
        Return azimuths as a list of floats.
        """
        return self.azimuths_deg.copy()


def prompt_g2s_download_specs():
    """
    Prompt user for G2S point-download inputs.
    Returns a dict to be used in the CLI call.
    """
    print("\nEnter G2S point-download parameters:")
    date_str = input("  Date (YYYY-MM-DD): ").strip()
    hour_str = input("  Hour UTC (0-23): ").strip()
    lat_str = input("  Latitude: ").strip()
    lon_str = input("  Longitude: ").strip()

    lat = float(lat_str)
    lon = float(lon_str)

    default_out = Path.home() / "Desktop" / f"g2s_{date_str}_{lat:g}_{lon:g}.json"
    output_str = input(f"  Output JSON path [e.g. {default_out}]: ").strip()
    if not output_str:
        output_str = str(default_out)

    return {
        "date": date_str,
        "hour": hour_str,
        "lat": lat,
        "lon": lon,
        "output": output_str,
    }


def download_g2s_json():
    """
    Either use an existing JSON file or interactively download a new one
    using the existing ncpag2s.py CLI.
    Returns the JSON path that should be processed.
    """
    if RUN_DOWNLOAD_PROMPT:
        reply = input("Download a new G2S JSON now? [y/N]: ").strip().lower()
        do_download = reply in {"y", "yes"}
    else:
        do_download = DOWNLOAD_JSON

    if not do_download:
        return Path(JSON_PATH).expanduser().resolve()

    cli_path = Path(G2S_CLI_PATH).expanduser().resolve()
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
    """
    Read in G2S JSON file

    Returns:
    dict with keys:
      - "meta": metadata dict (may be empty)
      - "data": dict mapping parameter name -> {"units": str|None, "values": list}
    """
    with open(json_path, "r") as f:
        raw = json.load(f)

    # Convert G2S data list into a dict keyed by parameter name for easy access
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


def build_profile_dataframe(g2s_obj: dict):
    """
    Convert the G2S parameter dict into a DataFrame with column names

    Required parameters in the JSON file:
      - Z0: station elevation / reference height (km) (used to convert AGL->MSL)
      - Z: height above ground level (km)
      - T: temperature (K)
      - U: zonal wind (m/s), positive east
      - V: meridional wind (m/s), positive north
      - R: density (g/cm^3)
      - P: pressure (mbar)

    Returns:
      z_agl_km, z_msl_km, z_agl_m, z_msl_m,
      T_K, U_ms, V_ms, rho_g_cm3, rho_kg_m3, P_mbar, P_Pa
    """
    data = g2s_obj["data"]

    required_params = ["Z0", "Z", "T", "U", "V", "R", "P"]  # Catch if any are missing from the JSON
    missing = [k for k in required_params if k not in data]
    if missing:
        raise KeyError(f"Missing required parameters in JSON: {missing}")

    # Z0 is a scalar (km)
    # Z is a profile (km AGL)
    ref_height_msl_km = float(data["Z0"]["values"][0])
    height_agl_km = np.asarray(data["Z"]["values"], dtype=float)

    df = pd.DataFrame(
        {
            "z_agl_km": height_agl_km,
            "z_msl_km": height_agl_km + ref_height_msl_km,
            "T_K": np.asarray(data["T"]["values"], dtype=float),
            "U_ms": np.asarray(data["U"]["values"], dtype=float),
            "V_ms": np.asarray(data["V"]["values"], dtype=float),
            "rho_g_cm3": np.asarray(data["R"]["values"], dtype=float),
            "P_mbar": np.asarray(data["P"]["values"], dtype=float),
        }
    )

    # Height conversions
    df["z_agl_m"] = df["z_agl_km"] * 1000.0
    df["z_msl_m"] = df["z_msl_km"] * 1000.0

    # Unit conversions
    # 1 g/cm^3 = 1000 kg/m^3
    df["rho_kg_m3"] = df["rho_g_cm3"] * 1000.0
    # 1 mbar = 100 Pa
    df["P_Pa"] = df["P_mbar"] * 100.0

    return df


def add_sound_speeds(df: pd.DataFrame, azimuths_deg):
    """
    Add:
      - c0_ms: adiabatic sound speed from temperature (m/s)
      - cEff_ms_alpha<deg>: effective sound speed for each azimuth in azimuths_deg

    Effective sound speed:
        c_eff = c0 + wind_along_path

    With azimuth measured clockwise from East:
      wind_along = U * cos(alpha) + V * sin(alpha)
    where U is eastward (+E), V is northward (+N)
    """
    df["c0_ms"] = np.sqrt(GAMMA_AIR * R_DRY_AIR * df["T_K"].to_numpy())

    if np.isscalar(azimuths_deg):
        azimuths = [float(azimuths_deg)]
    else:
        azimuths = [float(a) for a in azimuths_deg]

    for az in azimuths:
        alpha = radians(az)
        wind_along_path = df["U_ms"] * cos(alpha) + df["V_ms"] * sin(alpha)

        az_str = format_deg_for_filename(az)
        col = f"cEff_ms_alpha{az_str}deg"
        df[col] = df["c0_ms"] + wind_along_path

    return df


def write_profiles_csv(df: pd.DataFrame, out_csv: Path):
    """
    Save a consistent set of columns to CSV (no index column)
    Includes any cEff_ms_alpha<deg>deg columns if present
    """
    base_columns = [
        "z_agl_km",
        "z_msl_km",
        "z_agl_m",
        "z_msl_m",
        "T_K",
        "U_ms",
        "V_ms",
        "rho_g_cm3",
        "rho_kg_m3",
        "P_mbar",
        "P_Pa",
        "c0_ms",
    ]

    # Pick up all effective sound speed columns (sorted for stable output)
    c_eff_cols = sorted([c for c in df.columns if c.startswith("cEff_ms_alpha")])

    df.to_csv(
        out_csv,
        index=False,
        float_format="%.8g",
        columns=base_columns + c_eff_cols,
    )


def plot_profile(   # Takes care of repetative plotting
    x_values: np.ndarray,
    z_agl_m: np.ndarray,
    xlabel: str,
    out_png: Path,
    ymax_m: float = PLOT_MAX_HEIGHT_M,
    show: bool = SHOW_PLOTS,
):
    """
    Plot x vs height (AGL, meters) and save to PNG
    """
    plt.figure(figsize=(4, 6))
    plt.plot(x_values, z_agl_m)
    plt.xlabel(xlabel)
    plt.ylabel("Height AGL (m)")
    plt.grid(True, linestyle=":", linewidth=0.6)
    plt.ylim(0, ymax_m)
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    if show:
        plt.show()
    else:
        plt.close()


def format_deg_for_filename(deg: float):
    """
    Make a compact degree string for filenames (e.g., 0, 45, 12.5)
    """
    if abs(deg - round(deg)) < 1e-6:
        return str(int(round(deg)))
    return f"{deg:g}"


def main():
    json_path = download_g2s_json()
    if not json_path.exists():
        raise FileNotFoundError(f"Input not found: {json_path}")

    g2s_obj = read_g2s_json(json_path)
    profile_df = build_profile_dataframe(g2s_obj)
    azimuth_config = AzimuthConfig()

    if RUN_AZIMUTH_PROMPT:
        azimuth_config.prompt_user()

    propagation_azimuths_deg = azimuth_config.get_list()
    profile_df = add_sound_speeds(profile_df, propagation_azimuths_deg)

    # Output paths
    stem = json_path.with_suffix("")  # removes .json
    out_dir = stem.parent

    csv_path = out_dir / f"{stem.name}_profiles.csv"
    write_profiles_csv(profile_df, csv_path)

    # Plotting (reduced repetition)
    z_m = profile_df["z_agl_m"].to_numpy()

    # Each entry: (column_name, x_label, filename_suffix)
    plot_specs = [
        ("T_K",       "Temperature (K)",              "_T_profile.png"),
        ("U_ms",      "Zonal wind U (m/s, +East)",     "_U_profile.png"),
        ("V_ms",      "Meridional wind V (m/s, +North)","_V_profile.png"),
        ("rho_kg_m3", "Density (kg/m³)",              "_rho_profile.png"),
        ("P_Pa",      "Pressure (Pa)",                "_P_profile.png"),
    ]

    for col, xlab, suffix in plot_specs:
        plot_profile(
            profile_df[col].to_numpy(),
            z_m,
            xlab,
            out_dir / f"{stem.name}{suffix}",
        )

    # Effective sound speed plots for each azimuth
    for az in propagation_azimuths_deg:
        az_str = format_deg_for_filename(az)
        col = f"cEff_ms_alpha{az_str}deg"
        plot_profile(
            profile_df[col].to_numpy(),
            z_m,
            f"c_eff (m/s) @ azimuth={az_str}°",
            out_dir / f"{stem.name}_cEff_alpha{az_str}deg_profile.png",
        )

    # Small terminal summary
    meta = g2s_obj.get("meta", {})
    time_str = meta.get("time", {}).get("datetime", "unknown time")
    loc = meta.get("location", {})
    print(f"Wrote: {csv_path}")
    print(f"Time: {time_str}")
    print(f"Location: lat {loc.get('latitude')}, lon {loc.get('longitude')}")
    # print(profile_df[["z_agl_m", "c0_ms", "cEff_ms"]].describe())   # Error, need fixing for multiple azimuths


if __name__ == "__main__":
    main()