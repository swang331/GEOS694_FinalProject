#!/usr/bin/env python3
from pathlib import Path

from azimuth import AzimuthConfig
from g2s_io import download_g2s_json, read_g2s_json
from analysis import (
    build_profile_dataframe,
    add_sound_speeds,
    find_refraction_points,
    print_refraction_summary,
)
from plotting import plot_profile, plot_refraction_summary
from prompts import prompt_plot_behavior, prompt_refraction_figure_behavior
from utils import format_deg_for_filename

JSON_PATH = "/Users/serinawang/Desktop/GEOS694_FinalProject/g2s_2023-10-18_37.234_-116.159.json"
DOWNLOAD_JSON = False
RUN_DOWNLOAD_PROMPT = True
G2S_CLI_PATH = r"/Users/serinawang/Desktop/GEOS694_FinalProject/ncpag2s.py"

RUN_AZIMUTH_PROMPT = True
SHOW_PLOTS = True
SAVE_PLOTS = True
RUN_PLOT_PROMPT = True
SHOW_REFRACTION_FIGURE = False
SAVE_REFRACTION_FIGURE = True
RUN_REFRACTION_FIGURE_PROMPT = True
PLOT_MAX_HEIGHT_M = 100000

def write_profiles_csv(df, out_csv: Path):
    base_columns = [
        "z_agl_km", "z_msl_km", "z_agl_m", "z_msl_m",
        "T_K", "U_ms", "V_ms", "rho_g_cm3", "rho_kg_m3",
        "P_mbar", "P_Pa", "c0_ms",
    ]
    c_eff_cols = sorted([c for c in df.columns if c.startswith("cEff_ms_alpha")])
    df.to_csv(out_csv, index=False, float_format="%.8g", columns=base_columns + c_eff_cols)

def main():
    json_path = download_g2s_json(RUN_DOWNLOAD_PROMPT, DOWNLOAD_JSON, JSON_PATH, G2S_CLI_PATH)
    g2s_obj = read_g2s_json(json_path)
    profile_df = build_profile_dataframe(g2s_obj)

    azimuth_config = AzimuthConfig()
    if RUN_AZIMUTH_PROMPT:
        azimuth_config.prompt_user()
    propagation_azimuths_deg = azimuth_config.get_list()

    profile_df = add_sound_speeds(profile_df, propagation_azimuths_deg)
    refraction_results = find_refraction_points(profile_df, propagation_azimuths_deg, step_km=1.0)

    if RUN_REFRACTION_FIGURE_PROMPT:
        show_refraction_fig, save_refraction_fig = prompt_refraction_figure_behavior()
    else:
        show_refraction_fig, save_refraction_fig = SHOW_REFRACTION_FIGURE, SAVE_REFRACTION_FIGURE

    if RUN_PLOT_PROMPT:
        show_plots, save_plots = prompt_plot_behavior()
    else:
        show_plots, save_plots = SHOW_PLOTS, SAVE_PLOTS

    stem = json_path.with_suffix("")
    out_dir = stem.parent

    summary_dir = out_dir / "summaries"
    temp_dir = out_dir / "temperature"
    u_dir = out_dir / "zonal_wind"
    v_dir = out_dir / "meridional_wind"
    rho_dir = out_dir / "density"
    p_dir = out_dir / "pressure"
    ceff_dir = out_dir / "effective_sound_speed"

    for folder in [summary_dir, temp_dir, u_dir, v_dir, rho_dir, p_dir, ceff_dir]:
        folder.mkdir(parents=True, exist_ok=True)

    csv_path = summary_dir / f"{stem.name}_profiles.csv"
    write_profiles_csv(profile_df, csv_path)

    z_m = profile_df["z_agl_m"].to_numpy()
    plot_specs = [
        ("T_K", "Temperature (K)", temp_dir, "_T_profile.png"),
        ("U_ms", "Zonal wind U (m/s, +East)", u_dir, "_U_profile.png"),
        ("V_ms", "Meridional wind V (m/s, +North)", v_dir, "_V_profile.png"),
        ("rho_kg_m3", "Density (kg/m³)", rho_dir, "_rho_profile.png"),
        ("P_Pa", "Pressure (Pa)", p_dir, "_P_profile.png"),
    ]

    for col, xlab, folder, suffix in plot_specs:
        plot_profile(profile_df[col].to_numpy(), z_m, xlab, folder / f"{stem.name}{suffix}",
                     ymax_m=PLOT_MAX_HEIGHT_M, show=show_plots, save=save_plots)

    for az in propagation_azimuths_deg:
        az_str = format_deg_for_filename(az)
        col = f"cEff_ms_alpha{az_str}deg"
        plot_profile(profile_df[col].to_numpy(), z_m, f"c_eff (m/s) @ azimuth={az_str}°",
                     ceff_dir / f"{stem.name}_cEff_alpha{az_str}deg_profile.png",
                     ymax_m=PLOT_MAX_HEIGHT_M, show=show_plots, save=save_plots)

    print_refraction_summary(refraction_results)

    refraction_fig_path = out_dir / f"{stem.name}_refraction_summary.png"
    plot_refraction_summary(refraction_results, profile_df["z_agl_m"].max(), refraction_fig_path,
                            show=show_refraction_fig, save=save_refraction_fig)

if __name__ == "__main__":
    main()