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

# Or: download a new G2S JSON before processing
DOWNLOAD_JSON = True

# Path to the existing G2S wrapper
G2S_CLI_PATH = r"/Users/serinawang/Desktop/GEOS694_FinalProject/ncpag2s.py"

# Download settings used only if DOWNLOAD_JSON = True
G2S_DATE = "2023-10-18"
G2S_HOUR = "15"
G2S_LAT = 37.238
G2S_LON = -116.159
DOWNLOADED_JSON_PATH = r"/Users/serinawang/Desktop/g2s_2023-10-18_37-116.json"


# Direction of propagation for effective sound speed, measured clockwise from East:
# One or more azimuths (deg) profiles, clockwise from East: 0=E, 90=N, 180=W, 270=S
PROPAGATION_AZIMUTHS_DEG = [0.0, 90.0, 180.0, 270.0]

# Googled parameters
GAMMA_AIR = 1.4          # heat capacity ratio
R_DRY_AIR = 287.0        # J/(kg*K)

# Plot control
PLOT_MAX_HEIGHT_M = 100000
SHOW_PLOTS = True


def download_g2s_json():    # If not reading from an existing file
    """
    Optionally download a G2S JSON file using the existing ncpag2s.py CLI.
    Returns the JSON path that should be processed.
    """
    if not DOWNLOAD_JSON:
        return Path(JSON_PATH).expanduser().resolve()

    cli_path = Path(G2S_CLI_PATH).expanduser().resolve()
    out_json = Path(DOWNLOADED_JSON_PATH).expanduser().resolve()

    if not cli_path.exists():
        raise FileNotFoundError(f"G2S CLI not found: {cli_path}")

    cmd = [
        sys.executable,
        str(cli_path),
        "point",
        "--date", str(G2S_DATE),
        "--hour", str(G2S_HOUR),
        "--lat", str(G2S_LAT),
        "--lon", str(G2S_LON),
        "--outputformat", "json",
        "--output", str(out_json),
    ]

    print("Downloading G2S JSON...")
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
      wind_along = U * sin(alpha) + V * cos(alpha)
    where U is eastward (+E), V is northward (+N)
    """
    # Compute c0 once
    df["c0_ms"] = np.sqrt(GAMMA_AIR * R_DRY_AIR * df["T_K"].to_numpy())

    # Normalize input to a list (accept float, list, tuple, np array)
    if np.isscalar(azimuths_deg):
        azimuths = [float(azimuths_deg)]
    else:
        azimuths = [float(a) for a in azimuths_deg]

    for az in azimuths:
        alpha = radians(az)
        wind_along_path = df["U_ms"] * sin(alpha) + df["V_ms"] * cos(alpha)

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
    profile_df = add_sound_speeds(profile_df, PROPAGATION_AZIMUTHS_DEG)

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
    if np.isscalar(PROPAGATION_AZIMUTHS_DEG):
        azimuths = [float(PROPAGATION_AZIMUTHS_DEG)]
    else:
        azimuths = [float(a) for a in PROPAGATION_AZIMUTHS_DEG]

    for az in azimuths:
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