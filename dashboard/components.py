from typing import Any

import pandas as pd
import streamlit as st

try:
    from st_aggrid import AgGrid, GridOptionsBuilder
except ImportError:  # pragma: no cover - optional until owner runs pip install
    AgGrid = None
    GridOptionsBuilder = None


STATUS_COLORS = {
    "APPROVED": "#16a34a",
    "PAID": "#15803d",
    "SUCCEEDED": "#15803d",
    "ACTIVE": "#2563eb",
    "SETTLED": "#0d9488",
    "IN_TRANSIT": "#2563eb",
    "TRIGGERED": "#d97706",
    "REVIEW_REQUIRED": "#d97706",
    "PENDING": "#6b7280",
    "DRAFT": "#6b7280",
    "REJECTED": "#dc2626",
    "FAILED": "#dc2626",
    "PAYOUT_FAILED": "#dc2626",
    "HARD_BLOCK": "#dc2626",
    "REVIEW": "#d97706",
}


def render_status_badge(status: str) -> None:
    color = STATUS_COLORS.get(status, "#4b5563")
    st.markdown(
        f'<span style="background:{color};color:white;padding:3px 10px;'
        f'border-radius:12px;font-size:0.85em;font-weight:600;">{status}</span>',
        unsafe_allow_html=True,
    )


def render_aggrid_table(
    rows: list[dict[str, Any]],
    *,
    key: str,
    height: int = 320,
) -> None:
    if not rows:
        st.info("No records available.")
        return

    df = pd.DataFrame(rows)
    if AgGrid is not None and GridOptionsBuilder is not None:
        builder = GridOptionsBuilder.from_dataframe(df)
        builder.configure_default_column(
            filterable=True, sortable=True, resizable=True
        )
        builder.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
        grid_options = builder.build()
        AgGrid(
            df,
            gridOptions=grid_options,
            height=height,
            key=key,
            fit_columns_on_grid_load=True,
        )
    else:
        st.dataframe(df, use_container_width=True, height=height)

