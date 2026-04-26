import numpy as np
import matplotlib.pyplot as plt

def plot_profile(x_values, z_agl_m, xlabel, out_png, ymax_m=100000, show=True, save=True):
    plt.figure(figsize=(4, 6))
    plt.plot(x_values, z_agl_m)
    plt.xlabel(xlabel)
    plt.ylabel("Height AGL (m)")
    plt.grid(True, linestyle=":", linewidth=0.6)
    plt.ylim(0, ymax_m)
    plt.tight_layout()

    if save:
        plt.savefig(out_png, dpi=200)

    if show:
        plt.show()
    else:
        plt.close()

def plot_refraction_summary(results, max_height_m, out_png, show=False, save=True):
    if not results:
        print("No refraction points to plot.")
        return

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"}, figsize=(7, 7))
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)

    max_height_km = max_height_m / 1000.0
    ax.set_ylim(0, max_height_km)
    ax.set_title("Refraction Summary by Azimuth and Height", va="bottom")

    used_labels = set()

    for item in results:
        theta = np.deg2rad(item["azimuth_deg"])
        r_km = item["height_km"]

        if item["type"] == "stratospheric":
            color = "tab:blue"
            label = "Stratospheric"
        else:
            color = "tab:red"
            label = "Thermospheric"

        plot_label = label if label not in used_labels else None
        if plot_label is not None:
            used_labels.add(label)

        ax.scatter(theta, r_km, color=color, marker="x", s=10, label=plot_label)

    if used_labels:
        ax.legend(loc="upper right", bbox_to_anchor=(1.2, 1.1))

    if save:
        plt.savefig(out_png, dpi=200, bbox_inches="tight")

    if show:
        plt.show()
    else:
        plt.close()