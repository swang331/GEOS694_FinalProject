def format_deg_for_filename(deg: float):
    if abs(deg - round(deg)) < 1e-6:
        return str(int(round(deg)))
    return f"{deg:g}"