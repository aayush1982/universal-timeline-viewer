# app.py — Universal Milestone Timeline Viewer
# Streamlit + Plotly interactive app to visualize contractual vs actual/anticipated milestone dates
# — Supports Excel/CSV upload, sheet picker, flexible column mapping, status filters, search,
#   anchor selection (NTP or custom), monthly/quarterly granularity, color themes, badges,
#   KPI cards, export (CSV/Excel/HTML/PNG*), and a polished modern UI.

import io
import math
import os
import datetime as dt
from typing import List, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ----------------------------- PAGE SETUP -----------------------------
st.set_page_config(
    page_title="Universal Milestone Timeline",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------- STYLES -----------------------------
CSS = """
<style>
    .metric-card {
        background: linear-gradient(180deg, rgba(250,250,255,0.8), rgba(245,246,255,0.6));
        border: 1px solid rgba(100, 116, 139, 0.15);
        border-radius: 16px; padding: 14px 16px; box-shadow: 0 6px 18px rgba(0,0,0,0.05);
    }
    .tag { display:inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px; margin-right: 6px;
           border: 1px solid rgba(0,0,0,0.1); background: #fff; }
    .success { color: #0f766e; border-color:#99f6e4; background:#ecfeff; }
    .warn { color: #92400e; border-color:#fcd34d; background:#fffbeb; }
    .danger { color:#7f1d1d; border-color:#fecaca; background:#fef2f2; }
    .muted { color:#475569; border-color:#e2e8f0; background:#f8fafc; }
    .small { font-size:12px; color:#64748b; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ----------------------------- HELPERS -----------------------------
COMMON_NAME_COLS = ["Milestones", "Milestone", "Activity", "Name", "Event"]
COMMON_CONTRACT_COLS = [
    "Contractual", "Baseline", "Planned", "Target", "Plan", "Contract",
]
COMMON_ACTUAL_COLS = [
    "Actual/ Anticipated", "Actual/Anticipated", "Actual", "Forecast", "Anticipated", "Revised", "Achieved"
]
OPTIONAL_GROUP_COLS = ["Category", "Discipline", "Phase", "Package", "System", "Area"]

@st.cache_data(show_spinner=False)
def read_file(uploaded, sheet: Optional[str]=None) -> pd.DataFrame:
    if uploaded is None:
        return pd.DataFrame()
    name = uploaded.name.lower()
    if name.endswith((".xlsx", ".xls")):
        xl = pd.ExcelFile(uploaded)
        if sheet is None:
            # default: first sheet
            df = xl.parse(xl.sheet_names[0])
        else:
            df = xl.parse(sheet)
    elif name.endswith(".csv"):
        df = pd.read_csv(uploaded)
    else:
        raise ValueError("Unsupported file type. Please upload Excel (.xlsx/.xls) or CSV.")
    # clean headers
    df.columns = [str(c).strip().replace("\n", " ") for c in df.columns]
    return df

@st.cache_data(show_spinner=False)
def list_sheets(uploaded) -> List[str]:
    if uploaded and uploaded.name.lower().endswith((".xlsx", ".xls")):
        return pd.ExcelFile(uploaded).sheet_names
    return []

@st.cache_data(show_spinner=False)
def to_datetime_safe(s: pd.Series) -> pd.Series:
    # convert to datetime; keep NaT for invalids
    return pd.to_datetime(s, errors='coerce')

@st.cache_data(show_spinner=False)
def month_diff(start: dt.date, end: Optional[pd.Timestamp]) -> Optional[int]:
    if pd.isna(end):
        return None
    return (end.year - start.year) * 12 + (end.month - start.month)

@st.cache_data(show_spinner=False)
def friendly_month(d: pd.Timestamp, mode: str="Mmm-YY") -> str:
    if pd.isna(d):
        return "—"
    if mode == "Mmm-YY":
        return d.strftime("%b-%y")
    elif mode == "YYYY-MM":
        return d.strftime("%Y-%m")
    elif mode == "Mon YYYY":
        return d.strftime("%b %Y")
    return d.strftime("%b-%y")

# status logic: On-Time, Early, Delayed, Pending

def compute_status(contractual: pd.Timestamp, actual: Optional[pd.Timestamp], today: pd.Timestamp) -> str:
    if pd.isna(actual):
        # Pending — if future contractual date, else Overdue Pending
        if not pd.isna(contractual) and contractual < today:
            return "Pending (Overdue)"
        return "Pending"
    if pd.isna(contractual):
        return "Actual Only"
    # compare by date only (ignore time)
    c = contractual.normalize()
    a = actual.normalize()
    if a == c:
        return "On-Time"
    return "Early" if a < c else "Delayed"

# ----------------------------- TEMPLATE GENERATOR -----------------------------
def make_template() -> bytes:
    cols = [
        "Milestones",
        "Contractual",
        "Actual/ Anticipated",
        "Category",
    ]
    data = [
        ["Notice to Proceed", "2025-01-15", "2025-01-15", "Project"],
        ["Boiler Hydrostatic Test", "2026-03-30", "", "Boiler"],
        ["Boiler Light-Up", "2026-07-15", "2026-07-20", "Boiler"],
        ["Synchronization", "2026-09-30", "", "Electrical"],
        ["COD", "2026-12-15", "", "Commercial"],
    ]
    df = pd.DataFrame(data, columns=cols)
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="xlsxwriter") as xw:
        df.to_excel(xw, sheet_name="Unit#1", index=False)
    return out.getvalue()

# ----------------------------- SIDEBAR -----------------------------
st.sidebar.header("⚙️ Controls")

with st.sidebar:
    st.caption("Upload your milestone sheet (Excel/CSV). Choose sheet & map columns.")
    upl = st.file_uploader("Upload Milestones file", type=["xlsx", "xls", "csv"], accept_multiple_files=False)
    sheets = list_sheets(upl)
    selected_sheet = st.selectbox("Sheet (Excel only)", options=[None] + sheets, index=0, format_func=lambda x: x or "— First Sheet —")

    st.divider()
    st.markdown("**Column Mapping**")
    df_preview = read_file(upl, selected_sheet) if upl else pd.DataFrame()
    cols = list(df_preview.columns)

    # heuristics to preselect
    def guess(options, candidates):
        for c in candidates:
            for o in options:
                if str(o).strip().lower() == str(c).strip().lower():
                    return o
        return options[0] if options else None

    name_col = st.selectbox("Milestone name", options=cols, index=cols.index(guess(cols, COMMON_NAME_COLS)) if cols else 0)
    contract_col = st.selectbox("Contractual/Baseline date", options=cols, index=cols.index(guess(cols, COMMON_CONTRACT_COLS)) if cols else 0)
    actual_col = st.selectbox("Actual/Anticipated date", options=cols, index=cols.index(guess(cols, COMMON_ACTUAL_COLS)) if cols else 0)
    group_col = st.selectbox("(Optional) Group/Category", options=["(none)"] + cols, index=0)

    st.divider()
    st.markdown("**Anchor & Display**")
    anchor_mode = st.radio("Anchor timeline from", ["First Contractual date", "Milestone named 'Notice to Proceed'", "Custom date"], index=1, help="Defines Month 0.")
    custom_anchor = st.date_input("Custom anchor date", value=dt.date.today(), disabled=(anchor_mode != "Custom date"))
    tick_mode = st.select_slider("Tick label format", options=["Mmm-YY", "Mon YYYY", "YYYY-MM"], value="Mmm-YY")
    granularity = st.radio("Granularity", ["Monthly", "Quarterly"], index=0)

    st.divider()
    st.markdown("**Filters**")
    status_filter = st.multiselect(
        "Status",
        ["On-Time", "Early", "Delayed", "Pending", "Pending (Overdue)", "Actual Only"],
        default=["On-Time", "Early", "Delayed", "Pending", "Pending (Overdue)"]
    )
    search = st.text_input("Search milestone text")
    show_future_only = st.checkbox("Show future window only (from today)", value=False)

    st.divider()
    st.markdown("**Annotations**")
    show_labels = st.checkbox("Show labels next to markers", value=True)
    show_delay_badge = st.checkbox("Show delay/early badges", value=True)
    show_month_index = st.checkbox("Show month index row", value=True)
    show_today = st.checkbox("Show 'Today' line", value=True)

    st.divider()
    st.markdown("**Theme**")
    theme_choice = st.selectbox("Color theme", ["Default", "Blue/Green", "Purple/Orange", "Teal/Amber"])    

# ----------------------------- MAIN TITLE -----------------------------
st.title("📅 Universal Milestone Timeline Viewer")
st.caption("Upload an Excel/CSV of milestones and visualize Contractual vs Actual/Anticipated dates with rich filters & exports.")

colA, colB = st.columns([1,1])
with colA:
    st.download_button("⬇️ Download Excel Template", data=make_template(), file_name="milestone_template.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
with colB:
    st.info("Pro tip: Keep a row named **Notice to Proceed** if you want Month 0 anchored to NTP automatically.")

# ----------------------------- DATA INGEST -----------------------------
if upl is None:
    st.stop()

raw = read_file(upl, selected_sheet).copy()
if raw.empty:
    st.warning("No data found in the selected sheet.")
    st.stop()

# normalize columns
raw.columns = [str(c).strip() for c in raw.columns]

if group_col == "(none)":
    group_col = None

# select & rename
try:
    df = raw[[name_col, contract_col, actual_col] + ([group_col] if group_col else [])].copy()
except KeyError:
    st.error("Chosen columns not found. Please re-map.")
    st.stop()

rename_map = {
    name_col: "Milestone",
    contract_col: "Contractual",
    actual_col: "Actual",
}
if group_col:
    rename_map[group_col] = "Group"

df = df.rename(columns=rename_map)

# clean rows
df = df[df["Milestone"].notna()]
df["Milestone"] = df["Milestone"].astype(str).str.strip()

# dates
df["Contractual"] = to_datetime_safe(df["Contractual"]) if "Contractual" in df else pd.NaT
df["Actual"] = to_datetime_safe(df["Actual"]) if "Actual" in df else pd.NaT

# infer anchor
today = pd.Timestamp(dt.date.today())
anchor_date: Optional[pd.Timestamp] = None
if anchor_mode == "Custom date":
    anchor_date = pd.Timestamp(custom_anchor)
elif anchor_mode == "Milestone named 'Notice to Proceed'":
    ntp = df[df["Milestone"].str.strip().str.lower() == "notice to proceed"]
    if not ntp.empty and ntp["Contractual"].notna().any():
        anchor_date = ntp["Contractual"].dropna().iloc[0]
    else:
        st.warning("'Notice to Proceed' not found with a contractual date. Falling back to first contractual date.")

if anchor_date is None:
    # first contractual date
    if df["Contractual"].notna().any():
        anchor_date = df["Contractual"].dropna().min().normalize()
    else:
        anchor_date = today.normalize()

# derived fields

df["Status"] = df.apply(lambda r: compute_status(r.get("Contractual", pd.NaT), r.get("Actual", pd.NaT), today), axis=1)

df["ContractualMonthIdx"] = df["Contractual"].apply(lambda d: month_diff(anchor_date, d))
df["ActualMonthIdx"] = df["Actual"].apply(lambda d: month_diff(anchor_date, d))

df["ContractualLabel"] = df["Contractual"].apply(lambda d: friendly_month(d, tick_mode))
df["ActualLabel"] = df["Actual"].apply(lambda d: friendly_month(d, tick_mode))

# search filter
if search:
    df = df[df["Milestone"].str.contains(search, case=False, na=False)]

# status filter
if status_filter:
    df = df[df["Status"].isin(status_filter)]

# future-only filter
if show_future_only:
    df = df[(df["Contractual"].isna()) | (df["Contractual"] >= today)]

# KPI cards
N = len(df)
N_actual = int(df["Actual"].notna().sum())
delays = (df["Actual"].dropna() - df["Contractual"]).dropna().dt.days
on_time = int(((df["Actual"].notna()) & (df["Actual"].dt.normalize() == df["Contractual"].dt.normalize())).sum())

avg_delay = float(delays[delays > 0].mean()) if not delays[delays > 0].empty else 0.0
avg_early = float((-delays[delays < 0]).mean()) if not delays[delays < 0].empty else 0.0
on_time_pct = (on_time / N_actual * 100.0) if N_actual else 0.0

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(f"""
    <div class='metric-card'>
        <div class='small'>Total Milestones</div>
        <h3>{N:,}</h3>
    </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class='metric-card'>
        <div class='small'>With Actual/Forecast</div>
        <h3>{N_actual:,}</h3>
    </div>
    """, unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div class='metric-card'>
        <div class='small'>On-Time %</div>
        <h3>{on_time_pct:.1f}%</h3>
    </div>
    """, unsafe_allow_html=True)
with c4:
    st.markdown(f"""
    <div class='metric-card'>
        <div class='small'>Avg Delay (days)</div>
        <h3>{avg_delay:.1f}</h3>
    </div>
    """, unsafe_allow_html=True)
with c5:
    st.markdown(f"""
    <div class='metric-card'>
        <div class='small'>Avg Early (days)</div>
        <h3>{avg_early:.1f}</h3>
    </div>
    """, unsafe_allow_html=True)

# x-axis build
min_c = df["ContractualMonthIdx"].dropna().min() if df["ContractualMonthIdx"].notna().any() else 0
max_c = df["ContractualMonthIdx"].dropna().max() if df["ContractualMonthIdx"].notna().any() else 0
min_a = df["ActualMonthIdx"].dropna().min() if df["ActualMonthIdx"].notna().any() else 0
max_a = df["ActualMonthIdx"].dropna().max() if df["ActualMonthIdx"].notna().any() else 0

x0 = int(min(0, math.floor(min(min_c, min_a))))
x1 = int(max(0, math.ceil(max(max_c, max_a))))

# expand to include today
month_idx_today = month_diff(anchor_date, today)
x0 = min(x0, 0)
x1 = max(x1, month_idx_today + 2)

if granularity == "Quarterly":
    step = 3
else:
    step = 1

x_vals = list(range(x0, x1 + 1, step))
tick_text = []
for i in x_vals:
    d = (anchor_date + pd.DateOffset(months=i))
    tick_text.append(friendly_month(d, tick_mode))

# colors by theme
if theme_choice == "Blue/Green":
    c_contract, c_actual, c_base_contract, c_base_actual = "#2563eb", "#059669", "#93c5fd", "#a7f3d0"
elif theme_choice == "Purple/Orange":
    c_contract, c_actual, c_base_contract, c_base_actual = "#7c3aed", "#ea580c", "#d8b4fe", "#fed7aa"
elif theme_choice == "Teal/Amber":
    c_contract, c_actual, c_base_contract, c_base_actual = "#0d9488", "#d97706", "#99f6e4", "#fde68a"
else:
    c_contract, c_actual, c_base_contract, c_base_actual = "#1d4ed8", "#16a34a", "#93c5fd", "#86efac"

# Actual point colors by status
status_color = {
    "On-Time": c_actual,
    "Early": "#22c55e",
    "Delayed": "#ef4444",
    "Pending": "#a1a1aa",
    "Pending (Overdue)": "#f59e0b",
    "Actual Only": "#64748b",
}

# Build traces
fig = go.Figure()

# Contractual markers
# Contractual markers (with Notice to Proceed highlighted)
fig.add_trace(go.Scatter(
    x=df["ContractualMonthIdx"],
    y=np.ones(len(df)) * 1.0,
    mode='markers',
    name='Contractual',
    marker=dict(size=18, symbol='circle', color=c_contract, line=dict(width=1, color='black')),
    text=("<b>" + df["Milestone"] + "</b><br><span style='font-size:11px'>Contractual: " + df["ContractualLabel"] + "</span>"),
    hoverinfo='text',
))

# Actual markers by status color
actual_colors = df["Status"].map(status_color).fillna("#9ca3af").tolist()
fig.add_trace(go.Scatter(
    x=df["ActualMonthIdx"],
    y=np.ones(len(df)) * 0.98,
    mode='markers',
    name='Actual / Anticipated',
    marker=dict(size=18, symbol='square', color=actual_colors, line=dict(width=0)),
    text=(df["Milestone"] + "<br><span style='font-size:11px'>Actual: " + df["ActualLabel"] + "</span>"),
    hoverinfo='text',
))

# Baselines
fig.add_shape(type="line", x0=x0, x1=x1, y0=1.00, y1=1.00, line=dict(color=c_base_contract, width=6))
fig.add_shape(type="line", x0=x0, x1=x1, y0=0.98, y1=0.98, line=dict(color=c_base_actual, width=6))

# Today line
if show_today:
    fig.add_shape(type="line", x0=month_idx_today, x1=month_idx_today, y0=0.94, y1=1.04, line=dict(color="#111827", width=4, dash="dot"))
    fig.add_annotation(x=month_idx_today, y=1.045, text="Today", showarrow=False, font=dict(size=16, color="#111827"))


# Increased size maintained, text is bold, and position matches other markers.

annotations = []
if show_labels:
    for i, r in df.iterrows():
        milestone_name = f"<b>{r['Milestone']}</b>"
        if not pd.isna(r["ContractualMonthIdx"]):
            annotations.append(dict(
                x=r["ContractualMonthIdx"], y=1.022, text=milestone_name,
                showarrow=False, textangle=-90, font=dict(size=14, color=c_contract), xanchor='center'))
        if not pd.isna(r["ActualMonthIdx"]):
            badge = ""
            if show_delay_badge and not pd.isna(r["Contractual"]) and not pd.isna(r["Actual"]):
                d_days = int((r["Actual"] - r["Contractual"]).days)
                if d_days > 0:
                    badge = f"<br><span class='tag danger'><b>Delay +{d_days}d</b></span>"
                elif d_days < 0:
                    badge = f"<br><span class='tag success'><b>Early {abs(d_days)}d</b></span>"
                else:
                    badge = f"<br><span class='tag muted'><b>On-Time</b></span>"
            annotations.append(dict(
                x=r["ActualMonthIdx"], y=0.958, text=milestone_name + badge,
                showarrow=False, textangle=-90, font=dict(size=14, color=status_color.get(r["Status"], "#111827")), xanchor='center'))

# Ensure Notice to Proceed annotation is consistent with other milestones (vertical)
ntp_row = df[df["Milestone"].str.strip().str.lower() == "notice to proceed"]
if not ntp_row.empty:
    for _, ntp in ntp_row.iterrows():
        if not pd.isna(ntp["ContractualMonthIdx"]):
            annotations.append(dict(
                x=ntp["ContractualMonthIdx"],
                y=1.02,
                text="<b>Notice to Proceed</b>",
                showarrow=False,
                textangle=-90,
                font=dict(size=16, color="#111827"),
                xanchor='center'
            ))




# Month index row
if show_month_index:
    for i in x_vals:
        annotations.append(dict(x=i, y=0.99, text=str(i), showarrow=False, font=dict(size=10, color="#334155"), xanchor='center'))

fig.update_layout(
    height=700,
    margin=dict(l=30, r=20, t=50, b=90),
    annotations=annotations,
    yaxis=dict(visible=False, range=[0.94, 1.06]),
    xaxis=dict(
        title="",
        tickmode="array",
        tickvals=x_vals,
        ticktext=tick_text,
        tickangle=90,
        showgrid=True,
        gridcolor="rgba(148,163,184,0.25)",
        zeroline=False,
    ),
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
    dragmode='pan',
    hovermode='closest',
)

st.plotly_chart(fig, use_container_width=True, theme=None)

# ----------------------------- TABS -----------------------------
view_tab, data_tab, export_tab, help_tab = st.tabs(["🔎 View Options", "🗂 Data", "📤 Export", "❓ Help"])

with view_tab:
    if group_col:
        st.subheader("Group/Category breakdown")
        group_counts = df.groupby(["Group", "Status"], dropna=False).size().unstack(fill_value=0)
        st.dataframe(group_counts)
    st.subheader("Status distribution")
    status_counts = df["Status"].value_counts().rename_axis("Status").to_frame("Count")
    st.dataframe(status_counts)

with data_tab:
    st.subheader("Cleaned Milestone Table")
    show_cols = ["Milestone", "Contractual", "Actual", "Status", "ContractualLabel", "ActualLabel", "ContractualMonthIdx", "ActualMonthIdx"]
    if "Group" in df.columns:
        show_cols.insert(1, "Group")
    pretty = df[show_cols].copy()
    # display only dates (no time)
    for c in ["Contractual", "Actual"]:
        pretty[c] = pd.to_datetime(pretty[c], errors='coerce').dt.date
    st.dataframe(pretty, use_container_width=True)

with export_tab:
    st.subheader("Download filtered data")
    csv_bytes = df.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ CSV", data=csv_bytes, file_name="timeline_filtered.csv", mime="text/csv")

    xlsx_buf = io.BytesIO()
    with pd.ExcelWriter(xlsx_buf, engine="xlsxwriter") as xw:
        df.to_excel(xw, sheet_name="Filtered", index=False)
    st.download_button("⬇️ Excel", data=xlsx_buf.getvalue(), file_name="timeline_filtered.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.subheader("Export chart")
    # HTML export
    html_bytes = fig.to_html(full_html=True, include_plotlyjs='cdn').encode('utf-8')
    st.download_button("⬇️ Interactive HTML", data=html_bytes, file_name="timeline_chart.html", mime="text/html")

    # PNG export via kaleido (optional)
    try:
        png_bytes = fig.to_image(format="png", scale=2)
        st.download_button("⬇️ PNG (hi-res)", data=png_bytes, file_name="timeline_chart.png", mime="image/png")
    except Exception as e:
        st.caption("Install `kaleido` in your environment for PNG export: pip install -U kaleido")

with help_tab:
    st.markdown(
        """
        ### How to use
        1. **Upload** your Excel/CSV with columns for milestone name, contractual/baseline date, and actual/anticipated date.
        2. **Choose sheet** (for Excel) and **map columns** in the sidebar.
        3. Select **Anchor** (NTP, first contractual, or custom date) and **granularity**.
        4. Use **filters** (status, search, future-only) and **annotations** toggles.
        5. Explore **KPI cards** and **status breakdowns**; download **data** and **chart exports**.

        **Notes**
        - Row named **"Notice to Proceed"** helps auto-anchor Month 0.
        - Missing dates are handled gracefully and tagged as *Pending*.
        - *Pending (Overdue)* means contractual date has passed but no actual date yet.
        - For PNG export, install `kaleido`.
        """
    )

# ----------------------------- END -----------------------------
