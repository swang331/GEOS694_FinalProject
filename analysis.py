from math import radians
import numpy as np
import pandas as pd

from utils import format_deg_for_filename

GAMMA_AIR = 1.4
R_DRY_AIR = 287.0

def build_profile_dataframe(g2s_obj: dict):
    data = g2s_obj["data"]
    required_params = ["Z0", "Z", "T", "U", "V", "R", "P"]
    missing = [k for k in required_params if k not in data]
    if missing:
        raise KeyError(f"Missing required parameters in JSON: {missing}")

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

    df["z_agl_m"] = df["z_agl_km"] * 1000.0
    df["z_msl_m"] = df["z_msl_km"] * 1000.0
    df["rho_kg_m3"] = df["rho_g_cm3"] * 1000.0
    df["P_Pa"] = df["P_mbar"] * 100.0
    return df

def add_sound_speeds(df: pd.DataFrame, azimuths_deg):
    df["c0_ms"] = np.sqrt(GAMMA_AIR * R_DRY_AIR * df["T_K"].to_numpy())

    azimuths = [float(azimuths_deg)] if np.isscalar(azimuths_deg) else [float(a) for a in azimuths_deg]

    for az in azimuths:
        alpha = radians(az)
        wind_along_path = df["U_ms"] * np.sin(alpha) + df["V_ms"] * np.cos(alpha)
        az_str = format_deg_for_filename(az)
        col = f"cEff_ms_alpha{az_str}deg"
        df[col] = df["c0_ms"] + wind_along_path

    return df

def find_refraction_points(df: pd.DataFrame, azimuths_deg, step_km=1.0):
    results = []

    z_m_full = df["z_agl_m"].to_numpy()
    z_km_full = z_m_full / 1000.0
    target_km = np.arange(0.0, z_km_full.max() + step_km, step_km)
    sample_idx = np.unique([np.abs(z_km_full - zk).argmin() for zk in target_km])

    for az in azimuths_deg:
        az_str = format_deg_for_filename(az)
        col = f"cEff_ms_alpha{az_str}deg"

        c_eff_full = df[col].to_numpy()
        ground_c_eff = c_eff_full[0]

        z_m = z_m_full[sample_idx]
        z_km = z_km_full[sample_idx]
        c_eff = c_eff_full[sample_idx]

        for ce, z_m_i, z_km_i in zip(c_eff, z_m, z_km):
            if ce > ground_c_eff:
                if 0.0 <= z_km_i < 50.0:
                    ref_type = "stratospheric"
                elif 50.0 <= z_km_i <= 180.0:
                    ref_type = "thermospheric"
                else:
                    ref_type = None

                if ref_type is not None:
                    results.append(
                        {
                            "azimuth_deg": az,
                            "type": ref_type,
                            "height_m": z_m_i,
                            "height_km": z_km_i,
                        }
                    )

    return results

def print_refraction_summary(results):
    print("\nRefraction point search results:")

    if not results:
        print("  No stratospheric or thermospheric refraction points found.")
        return

    grouped = {}
    for item in results:
        key = (item["azimuth_deg"], item["type"])
        grouped.setdefault(key, []).append(item["height_km"])

    for (az, ref_type), heights in grouped.items():
        hmin = min(heights)
        hmax = max(heights)
        print(f"  Azimuth {az:g}°: {ref_type} refraction from {hmin:.1f} to {hmax:.1f} km AGL")