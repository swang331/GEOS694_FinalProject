from pathlib import Path

def prompt_g2s_download_specs():
    print("\nEnter G2S point-download parameters:")
    date_str = input("  Date (YYYY-MM-DD) [e.g. 2023-10-18]: ").strip()
    hour_str = input("  Hour UTC (0-23) [e.g. 15]: ").strip()
    lat_str = input("  Latitude [e.g. 37.238]: ").strip()
    lon_str = input("  Longitude [e.g. -116.159]: ").strip()

    lat = float(lat_str)
    lon = float(lon_str)

    default_out = Path.home() / "Desktop" / f"g2s_{date_str}_{lat:g}_{lon:g}.json"
    output_str = input(
        f"  Output JSON path [e.g. {default_out} OR press Enter for default Desktop] \n  Remember directory should include JSON file name: "
    ).strip()
    if not output_str:
        output_str = str(default_out)

    return {
        "date": date_str,
        "hour": hour_str,
        "lat": lat,
        "lon": lon,
        "output": output_str,
    }

def prompt_plot_behavior():
    show_reply = input("Show all individual profile plots interactively? [y/n]: ").strip().lower()
    show_plots = show_reply in {"y", "yes"}

    if show_plots:
        save_reply = input("Also save plots to the output directory? [y/n]: ").strip().lower()
        save_plots = save_reply in {"y", "yes"}
    else:
        save_reply = input("Do you want to save the produced plots to the output directory? [y/n]: ").strip().lower()
        save_plots = save_reply in {"y", "yes"}

    return show_plots, save_plots

def prompt_refraction_figure_behavior():
    show_reply = input("Show refraction summary figure interactively? [y/n]: ").strip().lower()
    show_fig = show_reply in {"y", "yes"}

    if show_fig:
        save_reply = input("Also save the refraction summary figure to the output directory? [y/n]: ").strip().lower()
        save_fig = save_reply in {"y", "yes"}
    else:
        save_fig = True

    return show_fig, save_fig