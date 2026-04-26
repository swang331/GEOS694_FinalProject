def format_deg_for_filename(deg: float):
    # If the degree value is very close to an integer, write it as an integer string
    # Example: 90.0 -> "90" instead of "90.0"
    if abs(deg - round(deg)) < 1e-6:
        return str(int(round(deg)))

    # Otherwise, keep the decimal value in a compact readable format
    # Example: 12.5 -> "12.5"
    return f"{deg:g}"