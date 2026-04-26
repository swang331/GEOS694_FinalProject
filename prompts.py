from pathlib import Path

def prompt_g2s_download_specs():
    # Prompt the user for the information needed to download a G2S point profile
    print("\nEnter G2S point-download parameters:")

    # Read the requested date, hour, latitude, and longitude from terminal input
    date_str = input("  Date (YYYY-MM-DD) [e.g. 2023-10-18]: ").strip()
    hour_str = input("  Hour UTC (0-23) [e.g. 15]: ").strip()
    lat_str = input("  Latitude [e.g. 37.238]: ").strip()
    lon_str = input("  Longitude [e.g. -116.159]: ").strip()

    # Convert latitude and longitude from strings to floats
    lat = float(lat_str)
    lon = float(lon_str)

    # Build a default JSON filename on the Desktop using the user inputs
    default_out = Path.home() / "Desktop" / f"g2s_{date_str}_{lat:g}_{lon:g}.json"

    # Let the user choose a custom output path, or press Enter to use the default
    output_str = input(
        f"  Output JSON path [e.g. {default_out} OR press Enter for default Desktop] \n  Remember directory should include JSON file name: "
    ).strip()

    # If the user provides no output path, fall back to the default Desktop path
    if not output_str:
        output_str = str(default_out)

    # Return all download settings in a dictionary
    return {
        "date": date_str,
        "hour": hour_str,
        "lat": lat,
        "lon": lon,
        "output": output_str,
    }


def prompt_plot_behavior():
    # Ask whether the user wants to display the individual vertical profile plots interactively
    show_reply = input("Show all individual profile plots interactively? [y/n]: ").strip().lower()
    show_plots = show_reply in {"y", "yes"}

    # If the plots will be shown, ask whether they should also be saved
    if show_plots:
        save_reply = input("Also save plots to the output directory? [y/n]: ").strip().lower()
        save_plots = save_reply in {"y", "yes"}

    # If the plots will not be shown, ask whether they should still be saved
    else:
        save_reply = input("Do you want to save the produced plots to the output directory? [y/n]: ").strip().lower()
        save_plots = save_reply in {"y", "yes"}

    # Return both user choices
    return show_plots, save_plots


def prompt_refraction_figure_behavior():
    # Ask whether the user wants to display the polar refraction summary figure interactively
    show_reply = input("Show refraction summary figure interactively? [y/n]: ").strip().lower()
    show_fig = show_reply in {"y", "yes"}

    # If the figure will be shown, ask whether it should also be saved
    if show_fig:
        save_reply = input("Also save the refraction summary figure to the output directory? [y/n]: ").strip().lower()
        save_fig = save_reply in {"y", "yes"}

    # If the figure will not be shown, save it by default
    else:
        save_fig = True

    # Return both user choices
    return show_fig, save_fig