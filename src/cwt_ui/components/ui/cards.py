# cwt_ui/components/cards.py
import streamlit as st

def metric(label: str, value, help_text: str | None = None) -> None:
    """
    מציג כרטיס KPI אחד עם label, value וטקסט עזרה אופציונלי.
    עטיפה ל-st.metric כדי לאחד שימוש.
    """
    st.metric(label, value)


def three_metrics(metrics: list[tuple[str, str, str | None]]):
    """
    מציג 3 כרטיסים בשורה אחת.
    metrics = [(label, value, help_text), ...] עד 3.
    """
    cols = st.columns(len(metrics))
    for col, (label, value, help_text) in zip(cols, metrics):
        with col:
            st.metric(label, value)


def kpi_card(label: str, value, delta: str | None = None, delta_color: str = "normal"):
    """
    מציג כרטיס KPI עם שינוי (delta).
    delta_color יכול להיות "normal", "inverse", "off".
    """
    st.metric(label=label, value=value, delta=delta, delta_color=delta_color)
