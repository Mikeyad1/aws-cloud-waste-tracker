# src/cwt_ui/services/formatters.py

def currency(x) -> str:
    """
    פורמט לערכים כספיים.
    דוגמה: 1234.5 -> "$1,234.50"
    """
    try:
        return f"${float(x):,.2f}"
    except Exception:
        return str(x)


def percent(x, decimals: int = 2) -> str:
    """
    פורמט לאחוזים.
    דוגמה: 0.1234 -> "12.34%"
    אם המספר כבר באחוזים (למשל 85) -> "85.00%"
    """
    try:
        val = float(x)
        if val <= 1:  # נניח שזה יחס
            val *= 100
        return f"{val:.{decimals}f}%"
    except Exception:
        return str(x)


def human_gb(x, decimals: int = 2) -> str:
    """
    פורמט לגודל ב־GB/MB.
    דוגמה: 2048 -> "2,048.00 GB"
    דוגמה: 0.25 -> "256.00 MB"
    """
    try:
        val = float(x)
        if val < 1:  # פחות מ־1GB -> הצג כ־MB
            return f"{val*1024:.{decimals}f} MB"
        return f"{val:.{decimals}f} GB"
    except Exception:
        return str(x)

