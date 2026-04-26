#!/usr/bin/env python3
from pathlib import Path

# Import custom classes and functions from the project modules
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

# User specifications
# Default path to an existing G2S JSON file (change to YOUR own directory)
JSON_PATH = "/Users/serinawang/Desktop/GEOS694_FinalProject/g2s_2023-10-18_37.234_-116.159.json"

# If False, use the existing JSON unless the user chooses to download one
DOWNLOAD_JSON = False

# If True, ask the user whether they want to download a new JSON
RUN_DOWNLOAD_PROMPT = True

# Path to the G2S command-line wrapper script (change to YOUR own directory)
G2S_CLI_PATH = r"/Users/serinawang/Desktop/GEOS694_FinalProject/ncpag2s.py"

# Prompt / plotting defaults

# If True, ask the user for azimuth choices at runtime
RUN_AZIMUTH_PROMPT = True

# Default behavior for showing/saving vertical profile plots
SHOW_PLOTS = True
SAVE_PLOTS = True
RUN_PLOT_PROMPT = True  # If True, ask the user whether to show/save plots

# Default behavior for showing/saving the polar refraction summary plot
SHOW_REFRACTION_FIGURE = False
SAVE_REFRACTION_FIGURE = True
RUN_REFRACTION_FIGURE_PROMPT = True  # If True, ask the user whether to show/save refraction figure

# Maximum height shown on the vertical profile plots
PLOT_MAX_HEIGHT_M = 100000


def write_profiles_csv(df, out_csv: Path):
    """
    Write the processed atmospheric profile DataFrame to CSV.

    The output CSV includes:
      - base atmospheric profile quantities
      - the adiabatic sound speed
      - all effective sound speed columns for the chosen azimuths
    """
    # Standard columns always written to the CSV
    base_columns = [
        "z_agl_km", "z_msl_km", "z_agl_m", "z_msl_m",
        "T_K", "U_ms", "V_ms", "rho_g_cm3", "rho_kg_m3",
        "P_mbar", "P_Pa", "c0_ms",
    ]

    # Collect all effective sound speed columns created for each azimuth
    c_eff_cols = sorted([c for c in df.columns if c.startswith("cEff_ms_alpha")])

    # Write selected columns to CSV without the DataFrame index
    df.to_csv(out_csv, index=False, float_format="%.8g", columns=base_columns + c_eff_cols)


def main():
    # Read or download the JSON
    # Get the JSON path, either by using an existing file or downloading a new one
    json_path = download_g2s_json(RUN_DOWNLOAD_PROMPT, DOWNLOAD_JSON, JSON_PATH, G2S_CLI_PATH)

    # Read the JSON file into a Python dictionary
    g2s_obj = read_g2s_json(json_path)

    # Convert the G2S data into a structured pandas DataFrame
    profile_df = build_profile_dataframe(g2s_obj)

    # Azimuth selection
    # Initialize azimuth configuration with default values
    azimuth_config = AzimuthConfig()

    # Prompt the user for azimuth choices if enabled
    if RUN_AZIMUTH_PROMPT:
        azimuth_config.prompt_user()

    # Get the final azimuth list to use for effective sound speed calculations
    propagation_azimuths_deg = azimuth_config.get_list()

    # Sound speed + refraction analysis
    # Add adiabatic sound speed and effective sound speed columns to the DataFrame
    profile_df = add_sound_speeds(profile_df, propagation_azimuths_deg)

    # Search the effective sound speed profiles for refraction points
    # using a vertical sampling interval of 1 km
    refraction_results = find_refraction_points(profile_df, propagation_azimuths_deg, step_km=1.0)

    # Ask user about refraction summary figure behavior
    if RUN_REFRACTION_FIGURE_PROMPT:
        show_refraction_fig, save_refraction_fig = prompt_refraction_figure_behavior()
    else:
        show_refraction_fig, save_refraction_fig = SHOW_REFRACTION_FIGURE, SAVE_REFRACTION_FIGURE

    # Ask user about profile plot behavior
    if RUN_PLOT_PROMPT:
        show_plots, save_plots = prompt_plot_behavior()
    else:
        show_plots, save_plots = SHOW_PLOTS, SAVE_PLOTS

    # Set up output folders
    # Remove the .json suffix to get the file stem
    stem = json_path.with_suffix("")

    # Use the JSON file's parent directory as the main output location
    out_dir = stem.parent

    # Create subdirectories for different output types
    summary_dir = out_dir / "summaries"
    temp_dir = out_dir / "temperature"
    u_dir = out_dir / "zonal_wind"
    v_dir = out_dir / "meridional_wind"
    rho_dir = out_dir / "density"
    p_dir = out_dir / "pressure"
    ceff_dir = out_dir / "effective_sound_speed"

    # Make sure all output directories exist
    for folder in [summary_dir, temp_dir, u_dir, v_dir, rho_dir, p_dir, ceff_dir]:
        folder.mkdir(parents=True, exist_ok=True)

    # Write summary CSV
    # Save the full processed profile table to the summaries folder
    csv_path = summary_dir / f"{stem.name}_profiles.csv"
    write_profiles_csv(profile_df, csv_path)

    # Plot basic atmospheric profiles
    # Height array (meters above ground level) used for all vertical profile plots
    z_m = profile_df["z_agl_m"].to_numpy()

    # Define the variables to plot, their axis labels, output folders, and file suffixes
    plot_specs = [
        ("T_K", "Temperature (K)", temp_dir, "_T_profile.png"),
        ("U_ms", "Zonal wind U (m/s, +East)", u_dir, "_U_profile.png"),
        ("V_ms", "Meridional wind V (m/s, +North)", v_dir, "_V_profile.png"),
        ("rho_kg_m3", "Density (kg/m³)", rho_dir, "_rho_profile.png"),
        ("P_Pa", "Pressure (Pa)", p_dir, "_P_profile.png"),
    ]

    # Loop through each standard atmospheric variable and plot it versus height
    for col, xlab, folder, suffix in plot_specs:
        plot_profile(
            profile_df[col].to_numpy(),
            z_m,
            xlab,
            folder / f"{stem.name}{suffix}",
            ymax_m=PLOT_MAX_HEIGHT_M,
            show=show_plots,
            save=save_plots,
        )

    # Plot effective sound speed profiles for each azimuth
    for az in propagation_azimuths_deg:
        # Format the azimuth value for use in column names and filenames
        az_str = format_deg_for_filename(az)

        # Construct the effective sound speed column name for this azimuth
        col = f"cEff_ms_alpha{az_str}deg"

        # Plot the effective sound speed profile for this azimuth
        plot_profile(
            profile_df[col].to_numpy(),
            z_m,
            f"c_eff (m/s) @ azimuth={az_str}°",
            ceff_dir / f"{stem.name}_cEff_alpha{az_str}deg_profile.png",
            ymax_m=PLOT_MAX_HEIGHT_M,
            show=show_plots,
            save=save_plots,
        )

    # Print and plot refraction summary
    # Print a text summary of the detected refraction points to terminal
    print_refraction_summary(refraction_results)

    # Create and optionally show/save the polar refraction summary plot
    refraction_fig_path = out_dir / f"{stem.name}_refraction_summary.png"
    plot_refraction_summary(
        refraction_results,
        profile_df["z_agl_m"].max(),
        refraction_fig_path,
        show=show_refraction_fig,
        save=save_refraction_fig,
    )


# Run the main workflow only if this file is executed directly
if __name__ == "__main__":
    main()