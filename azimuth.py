import numpy as np

# Default azimuth list, measured clockwise from North:
# 0°=N, 90°=E, 180°=S, 270°=W
DEFAULT_PROPAGATION_AZIMUTHS_DEG = [0.0, 90.0, 180.0, 270.0]


class AzimuthConfig:
    """
    Store and manage propagation azimuths for effective sound speed calculations
    """
    def __init__(self, azimuths_deg=None):
        # If no azimuth list is provided, use the default cardinal directions
        if azimuths_deg is None:
            azimuths_deg = DEFAULT_PROPAGATION_AZIMUTHS_DEG.copy()

        # Store azimuths as floats and wrap them into the range [0, 360)
        self.azimuths_deg = [float(az) % 360.0 for az in azimuths_deg]

    def prompt_user(self):
        # Build a printable default string for the terminal prompt
        default_str = ", ".join(f"{az:g}" for az in self.azimuths_deg)

        # Ask the user whether they want to enter a custom azimuth list
        # or run a full sweep through all azimuths
        mode_reply = input(
            # Choose azimuth input mode [type "list" or "sweep"; e.g. sweep]:
        ).strip().lower()

        # If the user presses Enter, default to a manual azimuth list
        if not mode_reply:
            mode_reply = "list"

        # If the user chooses "sweep", create azimuths from 0° to 360° in 1° steps
        if mode_reply == "sweep":
            print("Running full 360° sweep at 1° spacing. This may create many columns and plots")
            self.azimuths_deg = list(np.arange(0.0, 360.0, 1.0))
            return self.azimuths_deg

        # Otherwise, prompt for one or more comma-separated azimuth values
        az_reply = input(
            f"Enter propagation azimuth(s) in degrees clockwise from North "
            f'[e.g. 0, 90, 180, 270 | press Enter for default: {default_str}]: '
        ).strip()

        # If the user entered values, parse them and wrap into [0, 360)
        if az_reply:
            self.azimuths_deg = [float(item.strip()) % 360.0 for item in az_reply.split(",")]

        # Return the updated azimuth list
        return self.azimuths_deg

    def get_list(self):
        # Return a copy 
        return self.azimuths_deg.copy()