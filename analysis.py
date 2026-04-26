from math import radians
import numpy as np
import pandas as pd

from utils import format_deg_for_filename  # helper to format azimuth nicely in column/file names

# Constants for adiabatic sound speed in dry air:
GAMMA_AIR = 1.4
R_DRY_AIR = 287.0


def build_profile_dataframe(g2s_obj: dict):
    # Extract the "data" portion of the parsed G2S JSON object
    data = g2s_obj["data"]

    # Required parameters expected from the G2S JSON file
    required_params = ["Z0", "Z", "T", "U", "V", "R", "P"]

    # Check whether any required parameters are missing
    missing = [k for k in required_params if k not in data]
    if missing:
        raise KeyError(f"Missing required parameters in JSON: {missing}")

    # Z0 is the reference elevation (km above mean sea level)
    ref_height_msl_km = float(data["Z0"]["values"][0])

    # Z is the height profile above ground level (km)
    height_agl_km = np.asarray(data["Z"]["values"], dtype=float)

    # Build the main dataframe with original profile quantities
    df = pd.DataFrame(
        {
            "z_agl_km": height_agl_km,                              # height above ground level (km)
            "z_msl_km": height_agl_km + ref_height_msl_km,          # height above mean sea level (km)
            "T_K": np.asarray(data["T"]["values"], dtype=float),    # temperature (K)
            "U_ms": np.asarray(data["U"]["values"], dtype=float),   # zonal wind, positive east (m/s)
            "V_ms": np.asarray(data["V"]["values"], dtype=float),   # meridional wind, positive north (m/s)
            "rho_g_cm3": np.asarray(data["R"]["values"], dtype=float),  # density (g/cm^3)
            "P_mbar": np.asarray(data["P"]["values"], dtype=float),     # pressure (mbar)
        }
    )

    # Add useful converted units
    df["z_agl_m"] = df["z_agl_km"] * 1000.0      # height above ground level (m)
    df["z_msl_m"] = df["z_msl_km"] * 1000.0      # height above mean sea level (m)
    df["rho_kg_m3"] = df["rho_g_cm3"] * 1000.0   # density converted to kg/m^3
    df["P_Pa"] = df["P_mbar"] * 100.0            # pressure converted to Pa

    return df


def add_sound_speeds(df: pd.DataFrame, azimuths_deg):
    # Compute adiabatic sound speed at each height:
    # c0 = sqrt(gamma * R * T)
    df["c0_ms"] = np.sqrt(GAMMA_AIR * R_DRY_AIR * df["T_K"].to_numpy())

    # Allow either a single azimuth or a list of azimuths
    azimuths = [float(azimuths_deg)] if np.isscalar(azimuths_deg) else [float(a) for a in azimuths_deg]

    # Compute effective sound speed for each azimuth
    for az in azimuths:
        alpha = radians(az)  # convert azimuth from degrees to radians

        # Project wind onto the propagation direction
        # Azimuth is measured clockwise from North:
        # 0°=N, 90°=E, 180°=S, 270°=W
        wind_along_path = df["U_ms"] * np.sin(alpha) + df["V_ms"] * np.cos(alpha)

        # Create an azimuth string for the output column name
        az_str = format_deg_for_filename(az)
        col = f"cEff_ms_alpha{az_str}deg"

        # Effective sound speed = adiabatic sound speed + along-path wind component
        df[col] = df["c0_ms"] + wind_along_path

    return df


def find_refraction_points(df: pd.DataFrame, azimuths_deg, step_km=1.0):
    # Store all detected refraction points across all azimuths
    results = []

    # Full height arrays from the profile
    z_m_full = df["z_agl_m"].to_numpy()
    z_km_full = z_m_full / 1000.0

    # Build a vertical sampling grid (default every 1 km)
    # and find the closest actual model levels to those target heights
    target_km = np.arange(0.0, z_km_full.max() + step_km, step_km)
    sample_idx = np.unique([np.abs(z_km_full - zk).argmin() for zk in target_km])

    # Search for refraction points separately for each azimuth
    for az in azimuths_deg:
        az_str = format_deg_for_filename(az)
        col = f"cEff_ms_alpha{az_str}deg"

        # Effective sound speed profile for this azimuth
        c_eff_full = df[col].to_numpy()

        # Ground-level effective sound speed is used as the reference value
        ground_c_eff = c_eff_full[0]

        # Downsample to the chosen vertical step size
        z_m = z_m_full[sample_idx]
        z_km = z_km_full[sample_idx]
        c_eff = c_eff_full[sample_idx]

        # A refraction point is identified where c_eff exceeds the ground value
        for ce, z_m_i, z_km_i in zip(c_eff, z_m, z_km):
            if ce > ground_c_eff:
                # Classify the refraction point by altitude range
                if 0.0 <= z_km_i < 50.0:
                    ref_type = "stratospheric"
                elif 50.0 <= z_km_i <= 180.0:
                    ref_type = "thermospheric"
                else:
                    ref_type = None

                # Only save points within the defined height ranges
                if ref_type is not None:
                    results.append(
                        {
                            "azimuth_deg": az,   # azimuth where refraction is found
                            "type": ref_type,    # stratospheric or thermospheric
                            "height_m": z_m_i,   # refraction height in meters
                            "height_km": z_km_i, # refraction height in kilometers
                        }
                    )

    return results


def print_refraction_summary(results):
    # Print a simple terminal summary of all detected refraction points
    print("\nRefraction point search results:")

    # Handle the case where no refraction points are found
    if not results:
        print("  No stratospheric or thermospheric refraction points found.")
        return

    # Group results by azimuth and refraction type
    grouped = {}
    for item in results:
        key = (item["azimuth_deg"], item["type"])
        grouped.setdefault(key, []).append(item["height_km"])

    # Print the altitude range over which refraction points were found
    for (az, ref_type), heights in grouped.items():
        hmin = min(heights)
        hmax = max(heights)
        print(f"  Azimuth {az:g}°: {ref_type} refraction from {hmin:.1f} to {hmax:.1f} km AGL")