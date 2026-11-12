from __future__ import annotations

import os

import pandas as pd
import requests
import streamlit as st

try:
    from st_aggrid import AgGrid, GridOptionsBuilder

    HAS_AGGRID = True
except ImportError:
    HAS_AGGRID = False

st.set_page_config(page_title="PCMSC Dashboard", layout="wide")


def _grid(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No rows yet.")
        return
    if HAS_AGGRID:
        builder = GridOptionsBuilder.from_dataframe(df)
        builder.configure_pagination(paginationAutoPageSize=True)
        builder.configure_default_column(resizable=True, filter=True, sortable=True)
        AgGrid(df, gridOptions=builder.build(), theme="streamlit", height=380)
    else:
        st.dataframe(df, use_container_width=True, height=380)


def api_get(base_url: str, path: str, api_key: str) -> tuple[int, object]:
    response = requests.get(
        f"{base_url.rstrip('/')}{path}",
        headers={"X-API-Key": api_key},
        timeout=20,
    )
    try:
        payload = response.json()
    except ValueError:
        payload = {"raw": response.text}
    return response.status_code, payload


def api_post(base_url: str, path: str, api_key: str, body: dict) -> tuple[int, object]:
    response = requests.post(
        f"{base_url.rstrip('/')}{path}",
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        json=body,
        timeout=60,
    )
    try:
        payload = response.json()
    except ValueError:
        payload = {"raw": response.text}
    return response.status_code, payload


st.sidebar.title("PCMSC")
base_url = st.sidebar.text_input(
    "API base URL", os.environ.get("PCMSC_API_URL", "http://localhost:8000")
)
api_key = st.sidebar.text_input(
    "API key", os.environ.get("ADMIN_API_KEY", "demo-admin-key"), type="password"
)

health_code, health_body = api_get(base_url, "/health", api_key)
ready_code, ready_body = api_get(base_url, "/ready", api_key)
if health_code == 200 and ready_code == 200:
    st.sidebar.success("API healthy and ready")
else:
    st.sidebar.error(f"API unavailable (health={health_code}, ready={ready_code})")

st.sidebar.caption(str(health_body))

page = st.sidebar.radio(
    "Views",
    [
        "Overview",
        "Shipments",
        "Policies",
        "Claims",
        "Fraud",
        "Payouts",
        "Evidence",
        "Audit",
        "Scenario runner",
    ],
)

st.title("Parametric Climate Micro-Insurance")
st.caption("Explainable claims, fraud gates, and mock/sandbox payouts.")

if page == "Overview":
    cols = st.columns(4)
    for col, path, label in zip(
        cols,
        ["/api/v1/shipments", "/api/v1/policies", "/api/v1/claims", "/api/v1/payouts"],
        ["Shipments", "Policies", "Claims", "Payouts"],
    ):
        code, body = api_get(base_url, path, api_key)
        count = len(body) if code == 200 and isinstance(body, list) else "—"
        col.metric(label, count)

elif page == "Shipments":
    code, body = api_get(base_url, "/api/v1/shipments", api_key)
    if code == 200:
        _grid(pd.DataFrame(body))
    else:
        st.error(body)

elif page == "Policies":
    code, body = api_get(base_url, "/api/v1/policies", api_key)
    if code == 200:
        _grid(pd.DataFrame(body))
    else:
        st.error(body)

elif page == "Claims":
    code, body = api_get(base_url, "/api/v1/claims", api_key)
    if code == 200:
        _grid(pd.DataFrame(body))
        claim_ids = [row["id"] for row in body] if isinstance(body, list) else []
        if claim_ids:
            selected = st.selectbox("Inspect claim trace", claim_ids)
            detail_code, detail = api_get(base_url, f"/api/v1/claims/{selected}", api_key)
            if detail_code == 200:
                st.subheader("Decision trace")
                st.json(detail.get("decision_trace"))
                st.write(
                    f"Status `{detail.get('status')}` · decision hash `{detail.get('decision_hash')}`"
                )
    else:
        st.error(body)

elif page == "Fraud":
    code, shipments = api_get(base_url, "/api/v1/shipments", api_key)
    if code == 200 and shipments:
        shipment_id = st.selectbox(
            "Shipment",
            [row["id"] for row in shipments],
            format_func=lambda sid: next(
                f"{row['id']} · {row['external_ref']}"
                for row in shipments
                if row["id"] == sid
            ),
        )
        sig_code, signals = api_get(
            base_url, f"/api/v1/fraud/signals/{shipment_id}", api_key
        )
        ver_code, vers = api_get(
            base_url, f"/api/v1/fraud/verifications/{shipment_id}", api_key
        )
        st.subheader("Fraud signals")
        if sig_code == 200:
            _grid(pd.DataFrame(signals))
        st.subheader("Evidence verification")
        if ver_code == 200:
            _grid(pd.DataFrame(vers))
    else:
        st.info("Create a shipment or run a scenario first.")

elif page == "Payouts":
    code, body = api_get(base_url, "/api/v1/payouts", api_key)
    if code == 200:
        rows = []
        for payout in body:
            flat = dict(payout)
            flat.pop("attempt_history", None)
            rows.append(flat)
        _grid(pd.DataFrame(rows))
        if body:
            selected = st.selectbox("Payout attempts", [row["id"] for row in body])
            payout = next(row for row in body if row["id"] == selected)
            st.json(payout.get("attempt_history"))
    else:
        st.error(body)

elif page == "Evidence":
    code, shipments = api_get(base_url, "/api/v1/shipments", api_key)
    if code == 200 and shipments:
        shipment_id = st.selectbox("Shipment", [row["id"] for row in shipments])
        ev_code, docs = api_get(
            base_url, f"/api/v1/evidence/shipment/{shipment_id}", api_key
        )
        if ev_code == 200:
            _grid(pd.DataFrame(docs))
    else:
        st.info("No shipments yet.")

elif page == "Audit":
    code, body = api_get(base_url, "/api/v1/audit", api_key)
    if code == 200:
        _grid(pd.DataFrame(body))
    else:
        st.error(body)

elif page == "Scenario runner":
    st.write(
        "Scenario A pays a valid heat-breach claim once via the mock provider. "
        "Scenario B spoofs sensors and must produce no payout."
    )
    col_a, col_b = st.columns(2)
    if col_a.button("Run Scenario A — valid claim", type="primary"):
        code, body = api_post(
            base_url, "/api/v1/scenarios/run", api_key, {"scenario": "A", "seed": 42}
        )
        if code == 200:
            st.success(
                f"Claim {body.get('claim_status')} · payout {body.get('payout_status')}"
            )
            st.json(body)
        else:
            st.error(body)
    if col_b.button("Run Scenario B — fraud block"):
        code, body = api_post(
            base_url, "/api/v1/scenarios/run", api_key, {"scenario": "B", "seed": 99}
        )
        if code == 200:
            st.warning(
                f"Claim {body.get('claim_status')} · hard_block={body.get('hard_block')}"
            )
            st.json(body)
        else:
            st.error(body)
