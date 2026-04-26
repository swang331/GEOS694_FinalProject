import numpy as np
import matplotlib.pyplot as plt

def plot_profile(x_values, z_agl_m, xlabel, out_png, ymax_m=100000, show=True, save=True):
    # Create a vertical figure
    plt.figure(figsize=(4, 6))

    # Plot the chosen variable on the x-axis against height above ground level on the y-axis
    plt.plot(x_values, z_agl_m)

    plt.xlabel(xlabel)
    plt.ylabel("Height AGL (m)")

    plt.grid(True, linestyle=":", linewidth=0.6)

    # Set the vertical plotting range from the surface to the chosen maximum height
    plt.ylim(0, ymax_m)

    plt.tight_layout()

    # Save the figure to disk if requested
    if save:
        plt.savefig(out_png, dpi=200)

    # Show the figure interactively if requested
    # Otherwise close it
    if show:
        plt.show()
    else:
        plt.close()


def plot_refraction_summary(results, max_height_m, out_png, show=False, save=True):
    # If no refraction points were found, do not attempt to make the polar plot
    if not results:
        print("No refraction points to plot.")
        return

    # Create a polar plot figure
    fig, ax = plt.subplots(subplot_kw={"projection": "polar"}, figsize=(7, 7))

    # Set the azimuth convention:
    # 0° at North, and angles increasing clockwise
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)

    # Convert the maximum height from meters to kilometers for the radial axis
    max_height_km = max_height_m / 1000.0

    # Set the radial limit from the surface to the top of the model
    ax.set_ylim(0, max_height_km)

    ax.set_title("Refraction Summary by Azimuth and Height", va="bottom")

    # Track legend labels so each refraction type only appears once in the legend
    used_labels = set()

    # Loop through each detected refraction point
    for item in results:
        # Convert azimuth in degrees to radians for polar plotting
        theta = np.deg2rad(item["azimuth_deg"])

        # Radial coordinate is the refraction height in kilometers
        r_km = item["height_km"]

        # Color based on refraction type
        if item["type"] == "stratospheric":
            color = "tab:blue"
            label = "Stratospheric"
        else:
            color = "tab:red"
            label = "Thermospheric"

        # Only show each label once in the legend
        plot_label = label if label not in used_labels else None
        if plot_label is not None:
            used_labels.add(label)

        # Plot the refraction point on the polar diagram
        ax.scatter(theta, r_km, color=color, marker="x", s=10, label=plot_label)

    # Add a legend if at least one refraction type was plotted
    if used_labels:
        ax.legend(loc="upper right", bbox_to_anchor=(1.2, 1.1))

    # Save the polar plot if requested
    if save:
        plt.savefig(out_png, dpi=200, bbox_inches="tight")

    # Show the figure interactively if requested
    # Otherwise close it so it does not remain open in memory
    if show:
        plt.show()
    else:
        plt.close()