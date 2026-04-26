import numpy as np

DEFAULT_PROPAGATION_AZIMUTHS_DEG = [0.0, 90.0, 180.0, 270.0]

class AzimuthConfig:
    """
    Store and manage propagation azimuths for effective sound speed calculations.
    """
    def __init__(self, azimuths_deg=None):
        if azimuths_deg is None:
            azimuths_deg = DEFAULT_PROPAGATION_AZIMUTHS_DEG.copy()
        self.azimuths_deg = [float(az) % 360.0 for az in azimuths_deg]

    def prompt_user(self):
        default_str = ", ".join(f"{az:g}" for az in self.azimuths_deg)

        mode_reply = input(
            'Choose azimuth input mode [type "list" or "sweep"; e.g. sweep]: '
        ).strip().lower()

        if not mode_reply:
            mode_reply = "list"

        if mode_reply == "sweep":
            print("Running full 360° sweep at 1° spacing. This may create many columns and plots.")
            self.azimuths_deg = list(np.arange(0.0, 360.0, 1.0))
            return self.azimuths_deg

        az_reply = input(
            f"Enter propagation azimuth(s) in degrees clockwise from North "
            f'[e.g. 0, 90, 180, 270 | press Enter for default: {default_str}]: '
        ).strip()

        if az_reply:
            self.azimuths_deg = [float(item.strip()) % 360.0 for item in az_reply.split(",")]

        return self.azimuths_deg

    def get_list(self):
        return self.azimuths_deg.copy()