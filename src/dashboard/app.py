"""Olist business monitoring dashboard.

This presentation layer only loads prepared outputs from Sections 4 and 5 of
E-commerce.ipynb. It does not recompute analytical baselines or attribution.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(
    page_title="E-Commerce Performance Monitor",
    page_icon="◫",
    layout="wide",
    initial_sidebar_state="collapsed",
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "dashboard_data"

METRICS = {
    "Placed GMV": "placed_gmv",
    "Placed Orders": "placed_order_count",
    "Placed AOV": "placed_aov",
    "Active Customers": "active_customers",
    "New Customers": "new_customers",
    "Returning Customers": "returning_customers",
    "Orders per Active Customer": "orders_per_active_customer",
    "Merchandise Value per Order": "merchandise_value_per_order",
    "Freight per Order": "freight_per_order",
    "Items per Order": "items_per_order",
    "Average Item Price": "avg_item_price",
}

TREE_POSITIONS = {
    "placed_gmv": (5.0, 4.15),
    "placed_order_count": (2.45, 3.10),
    "placed_aov": (7.55, 3.10),
    "active_customers": (1.45, 2.02),
    "orders_per_active_customer": (3.45, 2.02),
    "merchandise_value_per_order": (6.45, 2.02),
    "freight_per_order": (8.55, 2.02),
    "new_customers": (0.55, 0.90),
    "returning_customers": (2.15, 0.90),
    "items_per_order": (5.55, 0.90),
    "avg_item_price": (7.25, 0.90),
}

TREE_EDGES = [
    ("placed_gmv", "placed_order_count"),
    ("placed_gmv", "placed_aov"),
    ("placed_order_count", "active_customers"),
    ("placed_order_count", "orders_per_active_customer"),
    ("active_customers", "new_customers"),
    ("active_customers", "returning_customers"),
    ("placed_aov", "merchandise_value_per_order"),
    ("placed_aov", "freight_per_order"),
    ("merchandise_value_per_order", "items_per_order"),
    ("merchandise_value_per_order", "avg_item_price"),
]

TREE_SHORT_LABELS = {
    "placed_gmv": "Placed GMV",
    "placed_order_count": "Placed Orders",
    "placed_aov": "Placed AOV",
    "active_customers": "Active Customers",
    "new_customers": "New Customers",
    "returning_customers": "Returning Customers",
    "orders_per_active_customer": "Orders / Active<br>Customer",
    "merchandise_value_per_order": "Merchandise Value<br>/ Order",
    "freight_per_order": "Freight / Order",
    "items_per_order": "Items / Order",
    "avg_item_price": "Avg Item Price",
}

CURRENCY_METRICS = {
    "placed_gmv",
    "placed_aov",
    "merchandise_value_per_order",
    "freight_per_order",
    "avg_item_price",
}
COUNT_METRICS = {
    "placed_order_count",
    "active_customers",
    "new_customers",
    "returning_customers",
}

OPERATIONAL_LABELS = {
    "carrier_handoff_orders": "Carrier Handoff Orders",
    "median_fulfillment_time_days": "Median Fulfillment Time",
    "p90_fulfillment_time_days": "P90 Fulfillment Time",
    "delivered_orders": "Delivered Orders",
    "median_carrier_transit_time_days": "Median Carrier Transit Time",
    "p90_carrier_transit_time_days": "P90 Carrier Transit Time",
    "late_delivery_rate": "Late Delivery Rate",
    "reviews_received": "Reviews Received",
    "average_review_score": "Average Review Score",
    "negative_review_rate": "Negative Review Rate",
}


st.markdown(
    """
    <style>
      [data-testid="stAppViewContainer"] {background:#f7f8fb;}
      .block-container {padding-top: 2rem; padding-bottom: 3rem; max-width: 1320px;}
      h1, h2, h3 {letter-spacing: -0.025em;}
      [data-testid="stMetric"] {background: #fff; border: 1px solid #e7eaf0;
        border-radius: 12px; padding: 14px 16px; box-shadow: 0 1px 3px rgba(15,23,42,.04);}
      .section-kicker {font-size:.78rem; font-weight:700; letter-spacing:.10em;
        color:#64748b; margin:1.7rem 0 .25rem;}
      .kpi-card {background:#fff; border:1px solid #e7eaf0; border-radius:14px;
        padding:18px 18px 16px; min-height:148px; box-shadow:0 2px 7px rgba(15,23,42,.045);}
      .kpi-label {font-size:.83rem; color:#64748b; font-weight:650;}
      .kpi-value {font-size:1.78rem; line-height:1.25; color:#0f172a;
        font-weight:750; margin:.35rem 0; letter-spacing:-.035em;}
      .kpi-delta {font-size:.83rem; color:#475569;}
      .pill {display:inline-block; margin-top:.65rem; padding:.22rem .58rem;
        border-radius:999px; font-size:.76rem; font-weight:700;}
      .pill-gray {color:#475569; background:#f1f5f9;}
      .pill-red {color:#b42318; background:#fee4e2;}
      .pill-orange {color:#b54708; background:#ffead5;}
      .pill-green {color:#067647; background:#dcfae6;}
      .pill-lightgreen {color:#087a55; background:#e9f8ef;}
      .selected-strip {background:#fff; border:1px solid #e7eaf0; border-radius:10px;
        padding:10px 14px; color:#475569; font-size:.82rem; margin:.25rem 0 .8rem;}
      .selected-strip strong {color:#0f172a;}
      .op-card {background:#fff; border:1px solid #e7eaf0; border-radius:12px;
        padding:14px 15px; margin-bottom:9px;}
      .op-label {font-size:.82rem; color:#475569; font-weight:650;}
      .op-value {font-size:1.26rem; font-weight:730; color:#0f172a; margin:.25rem 0;}
      .op-compare {font-size:.75rem; color:#64748b;}
      .good {color:#067647; font-weight:700;} .bad {color:#b42318; font-weight:700;}
      .neutral {color:#64748b; font-weight:650;}
      .muted-note {color:#64748b; font-size:.82rem;}
      div[data-testid="stPlotlyChart"] {border:1px solid #eef0f4; border-radius:12px; overflow:hidden;}
      .section-divider {border:0; border-top:1px solid #dfe4eb; margin:2.5rem 0 1.4rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Loading prepared analytical outputs…")
def load_data() -> tuple[pd.DataFrame, ...]:
    required = {
        "commercial": DATA_DIR / "commercial_daily.csv.gz",
        "drivers": DATA_DIR / "driver_attribution_long.csv.gz",
        "dimensions": DATA_DIR / "dimensional_rca_long.csv.gz",
        "operations": DATA_DIR / "operational_health_7d.csv.gz",
        "coverage": DATA_DIR / "operational_duration_coverage.csv",
    }
    missing = [path.name for path in required.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing dashboard export(s): " + ", ".join(missing)
            + ". Run export_dashboard_data.py first."
        )

    commercial = pd.read_csv(required["commercial"], parse_dates=["order_date"])
    drivers = pd.read_csv(required["drivers"], parse_dates=["order_date"])
    dimensions = pd.read_csv(
        required["dimensions"], parse_dates=["order_date"], low_memory=False
    )
    operations = pd.read_csv(
        required["operations"],
        parse_dates=[
            "as_of_date", "current_window_start", "current_window_end",
            "previous_window_start", "previous_window_end",
        ],
    )
    coverage = pd.read_csv(required["coverage"])
    for frame in (commercial, drivers, dimensions, operations, coverage):
        numeric = frame.select_dtypes(include="number").columns
        frame[numeric] = frame[numeric].replace([np.inf, -np.inf], np.nan)
    return commercial, drivers, dimensions, operations, coverage


def compact_number(value: float, currency: bool = False) -> str:
    if pd.isna(value):
        return "N/A"
    sign = "-" if value < 0 else ""
    magnitude = abs(float(value))
    prefix = "$" if currency else ""
    for divisor, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")):
        if magnitude >= divisor:
            precision = 2 if magnitude / divisor < 10 else 1
            return f"{sign}{prefix}{magnitude / divisor:.{precision}f}{suffix}"
    if currency:
        return f"{sign}{prefix}{magnitude:,.2f}"
    return f"{sign}{magnitude:,.0f}"


def signed_compact_currency(value: float) -> str:
    if pd.isna(value):
        return "N/A"
    formatted = compact_number(value, currency=True)
    return f"+{formatted}" if value > 0 else formatted


def metric_value(metric: str, value: float) -> str:
    if pd.isna(value):
        return "N/A"
    if metric in CURRENCY_METRICS:
        return compact_number(value, currency=True)
    if metric in COUNT_METRICS:
        return compact_number(value)
    return f"{value:,.2f}"


def pct(value: float, signed: bool = True) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{value:+.1%}" if signed else f"{value:.1%}"


def kpi_card(label: str, value: str, delta_text: str, pill_text: str | None = None,
             pill_class: str = "pill-gray") -> None:
    pill = (
        f'<div class="pill {pill_class}">{escape(pill_text)}</div>'
        if pill_text else ""
    )
    st.markdown(
        f"""<div class="kpi-card">
          <div class="kpi-label">{escape(label)}</div>
          <div class="kpi-value">{escape(value)}</div>
          <div class="kpi-delta">{escape(delta_text)}</div>{pill}
        </div>""",
        unsafe_allow_html=True,
    )


def anomaly_style(level: str, direction: str) -> tuple[str, str]:
    arrow = "↑" if direction == "Positive" else "↓" if direction == "Negative" else ""
    if level == "Normal":
        return f"Normal {arrow}".strip(), "pill-gray"
    if direction == "Positive":
        return f"{level} {arrow}", "pill-green" if level == "Critical" else "pill-lightgreen"
    return f"{level} {arrow}", "pill-red" if level == "Critical" else "pill-orange"


def time_series_chart(data: pd.DataFrame, selected_date: pd.Timestamp, range_days: int | None) -> go.Figure:
    # Completed Date is the point-in-time cutoff: future observations are never shown.
    chart = data.loc[data["order_date"].le(selected_date)].sort_values("order_date").copy()
    if range_days:
        chart = chart.loc[
            chart["order_date"].between(
                selected_date - pd.Timedelta(days=range_days - 1),
                selected_date,
            )
        ]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=chart["order_date"], y=chart["actual_placed_gmv"],
        mode="lines", name="Actual Placed GMV",
        line=dict(color="#1d4ed8", width=2.5),
        hovertemplate="%{x|%d %b %Y}<br>Actual: $%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=chart["order_date"], y=chart["expected_placed_gmv"],
        mode="lines", name="STL Expected GMV",
        line=dict(color="#94a3b8", width=1.7, dash="dash"),
        hovertemplate="%{x|%d %b %Y}<br>Expected: $%{y:,.0f}<extra></extra>",
    ))
    marker_styles = {
        ("Warning", "Negative"): ("#f59e0b", "Warning · Negative"),
        ("Critical", "Negative"): ("#dc2626", "Critical · Negative"),
        ("Warning", "Positive"): ("#4fbf88", "Warning · Positive"),
        ("Critical", "Positive"): ("#078848", "Critical · Positive"),
    }
    for (level, direction), (color, name) in marker_styles.items():
        points = chart.loc[
            chart["anomaly_level"].eq(level) & chart["direction"].eq(direction)
        ]
        if points.empty:
            continue
        fig.add_trace(go.Scatter(
            x=points["order_date"], y=points["actual_placed_gmv"],
            mode="markers", name=name,
            marker=dict(color=color, size=9, line=dict(color="white", width=1)),
            hovertemplate="%{x|%d %b %Y}<br>$%{y:,.0f}<extra>" + name + "</extra>",
        ))
    selected = data.loc[data["order_date"].eq(selected_date)].iloc[0]
    fig.add_trace(go.Scatter(
        x=[selected_date], y=[selected["actual_placed_gmv"]],
        mode="markers", name="Selected date",
        marker=dict(color="#111827", size=14, symbol="circle-open", line=dict(width=3)),
        hovertemplate="Selected: %{x|%d %b %Y}<br>$%{y:,.0f}<extra></extra>",
    ))
    fig.add_vline(x=selected_date.timestamp() * 1000, line_width=1, line_dash="dot", line_color="#94a3b8")
    x_range_start = chart["order_date"].min()
    if x_range_start == selected_date:
        x_range_start = selected_date - pd.Timedelta(days=1)
    fig.update_layout(
        height=430, margin=dict(l=15, r=15, t=20, b=10),
        paper_bgcolor="white", plot_bgcolor="white", hovermode="x unified",
        legend=dict(orientation="h", y=1.08, x=0),
        yaxis=dict(title="Placed GMV", tickprefix="$", gridcolor="#eef2f7"),
        xaxis=dict(
            title=None, gridcolor="#f8fafc",
            range=[x_range_start, selected_date],
        ),
    )
    return fig


def attribution_tree_chart(
    date_rows: pd.DataFrame,
    selected_metric: str,
) -> tuple[go.Figure, float, bool]:
    """Render Section 4.6 values without changing or renormalizing attribution."""
    if date_rows.empty:
        raise ValueError("No Section 4.6 attribution output is available for this date.")

    indexed = date_rows.set_index("driver_metric")
    first = date_rows.iloc[0]
    driver_gap = float(first["driver_gmv_gap"])
    # One cent is the natural display precision for the currency denominator.
    share_is_meaningful = not np.isclose(driver_gap, 0.0, atol=0.01, rtol=0.0)

    node_values: dict[str, dict[str, object]] = {
        "placed_gmv": {
            "actual": float(first["actual_placed_gmv"]),
            "reference": float(first["driver_reference_gmv"]),
            "delta": driver_gap,
            "delta_pct": (
                driver_gap / float(first["driver_reference_gmv"])
                if float(first["driver_reference_gmv"]) != 0 else np.nan
            ),
            "contribution": driver_gap,
            "share": 1.0 if share_is_meaningful else np.nan,
            "role": "Net GMV movement",
        }
    }
    for metric in METRICS.values():
        if metric == "placed_gmv":
            continue
        row = indexed.loc[metric]
        contribution = float(row["global_gmv_contribution"])
        if np.isclose(contribution, 0.0, atol=0.005, rtol=0.0):
            role = "Neutral contribution"
        elif np.sign(contribution) == np.sign(driver_gap):
            role = "Drove the net movement"
        else:
            role = "Offset the net movement"
        node_values[metric] = {
            "actual": float(row["actual_value"]),
            "reference": float(row["reference_value"]),
            "delta": float(row["delta"]),
            "delta_pct": float(row["delta_pct"]),
            "contribution": contribution,
            "share": (
                float(row["global_gmv_contribution_pct"])
                if share_is_meaningful else np.nan
            ),
            "role": role,
        }

    def accent(metric: str) -> str:
        contribution = float(node_values[metric]["contribution"])
        if metric == "placed_gmv":
            return "#15805d" if driver_gap > 0 else "#c2413b" if driver_gap < 0 else "#64748b"
        if np.isclose(contribution, 0.0, atol=0.005, rtol=0.0):
            return "#64748b"
        drives = np.sign(contribution) == np.sign(driver_gap)
        if driver_gap < 0:
            return "#c2413b" if drives else "#15805d"
        return "#15805d" if drives else "#c76555"

    edge_x, edge_y = [], []
    for parent, child in TREE_EDGES:
        px, py = TREE_POSITIONS[parent]
        cx, cy = TREE_POSITIONS[child]
        midpoint = (py + cy) / 2
        edge_x.extend([px, px, cx, cx, None])
        edge_y.extend([py, midpoint, midpoint, cy, None])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y, mode="lines", hoverinfo="skip",
        line=dict(color="#cbd5e1", width=1.6), showlegend=False,
    ))

    for metric, (x, y) in TREE_POSITIONS.items():
        values = node_values[metric]
        share = values["share"]
        share_text = (
            f"{share:.1%}" if pd.notna(share) and 0 < abs(share) < 0.01
            else f"{share:.0%}" if pd.notna(share)
            else "Share N/M"
        )
        contribution_text = signed_compact_currency(float(values["contribution"]))
        label = TREE_SHORT_LABELS[metric]
        full_name = METRICS_INV[metric]
        delta_text = metric_value(metric, float(values["delta"]))
        if float(values["delta"]) > 0:
            delta_text = "+" + delta_text
        hover_share = f"{share:.1%}" if pd.notna(share) else "Not meaningful"
        node_fill = "#eef2ff" if metric == selected_metric else "#ffffff"
        node_size = 114 if metric == "placed_gmv" else 101
        if metric == selected_metric:
            node_size += 7
        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode="markers+text", name=full_name,
            marker=dict(
                symbol="square", size=node_size, color=node_fill,
                line=dict(color=accent(metric), width=3 if metric == selected_metric else 2),
            ),
            text=[f"<b>{label}</b><br>{share_text}<br><b>{contribution_text}</b>"],
            textposition="middle center",
            textfont=dict(size=11, color=accent(metric)),
            customdata=[[
                metric, full_name,
                metric_value(metric, float(values["actual"])),
                metric_value(metric, float(values["reference"])),
                delta_text,
                pct(float(values["delta_pct"])),
                contribution_text,
                hover_share,
                str(values["role"]),
            ]],
            hovertemplate=(
                "<b>%{customdata[1]}</b><br>%{customdata[8]}<br><br>"
                "Actual: %{customdata[2]}<br>Diagnostic Reference: %{customdata[3]}<br>"
                "Absolute Deviation: %{customdata[4]}<br>Deviation %: %{customdata[5]}<br><br>"
                "GMV Contribution: %{customdata[6]}<br>Contribution Share: %{customdata[7]}"
                "<extra>Click to drill down</extra>"
            ),
            showlegend=False,
        ))

    movement_word = "increase" if driver_gap > 0 else "decline" if driver_gap < 0 else "movement"
    fig.update_layout(
        height=650,
        margin=dict(l=15, r=15, t=45, b=15),
        paper_bgcolor="white", plot_bgcolor="white",
        clickmode="event+select",
        dragmode=False,
        xaxis=dict(range=[-0.15, 9.3], visible=False, fixedrange=True),
        yaxis=dict(range=[0.28, 4.62], visible=False, fixedrange=True),
        annotations=[dict(
            x=0.01, y=1.035, xref="paper", yref="paper", showarrow=False,
            text=(
                f"<b>Net driver GMV gap: {signed_compact_currency(driver_gap)}</b> · "
                f"Color shows whether a node drove or offset the {movement_word}."
            ),
            font=dict(size=12, color="#475569"), xanchor="left",
        )],
    )
    return fig, driver_gap, share_is_meaningful


def dimension_chart(data: pd.DataFrame, title: str, top_n: int, metric: str) -> go.Figure:
    ranked = (
        data.loc[data["delta"].notna()]
        .nlargest(top_n, "abs_delta")
        .sort_values("abs_delta", ascending=True)
    )
    colors = np.where(ranked["delta"].ge(0), "#159a62", "#dc4c4c")
    custom = np.column_stack([
        ranked["actual_value"], ranked["reference_value"], ranked["delta_pct"]
    ]) if len(ranked) else np.empty((0, 3))
    fig = go.Figure(go.Bar(
        x=ranked["delta"], y=ranked["dimension_value"], orientation="h",
        marker_color=colors, customdata=custom,
        hovertemplate=(
            "%{y}<br>Delta: %{x:,.2f}<br>Actual: %{customdata[0]:,.2f}"
            "<br>Reference: %{customdata[1]:,.2f}<br>Delta %: %{customdata[2]:+.1%}<extra></extra>"
        ),
    ))
    fig.add_vline(x=0, line_color="#94a3b8", line_width=1)
    axis_limit = max(float(ranked["abs_delta"].max()) * 1.12, 1.0) if len(ranked) else 1.0
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)), height=350,
        margin=dict(l=10, r=12, t=48, b=15), showlegend=False,
        paper_bgcolor="white", plot_bgcolor="white",
        xaxis=dict(
            title=f"{METRICS_INV[metric]} delta vs diagnostic reference",
            gridcolor="#eef2f7", range=[-axis_limit, axis_limit], zeroline=False,
        ),
        yaxis=dict(title=None),
    )
    if ranked.empty:
        fig.add_annotation(text="No eligible diagnostic reference for this selection", x=.5, y=.5,
                           xref="paper", yref="paper", showarrow=False, font=dict(color="#64748b"))
    return fig


def operational_level(metric: str, value: float) -> str:
    if pd.isna(value):
        return "N/A"
    if metric in {"carrier_handoff_orders", "delivered_orders", "reviews_received"}:
        return f"{value:,.0f}"
    if metric in {"late_delivery_rate", "negative_review_rate"}:
        return f"{value:.1%}"
    if metric == "average_review_score":
        return f"{value:.2f}"
    return f"{value:.2f} days"


def operational_change(metric: str, unit: str, value: float) -> tuple[str, str]:
    if pd.isna(value):
        return "N/A", "neutral"
    if unit == "volume_pct_change":
        return f"{value:+.1%}", "neutral"
    if unit == "percentage_points":
        text = f"{value:+.2f} pp"
    elif unit == "days_difference":
        text = f"{value:+.2f} days"
    else:
        text = f"{value:+.2f}"
    lower_is_better = metric in {
        "median_fulfillment_time_days", "p90_fulfillment_time_days",
        "median_carrier_transit_time_days", "p90_carrier_transit_time_days",
        "late_delivery_rate", "negative_review_rate",
    }
    if value == 0:
        style = "neutral"
    elif lower_is_better:
        style = "good" if value < 0 else "bad"
    else:
        style = "good" if value > 0 else "bad"
    return text, style


def operational_card(row: pd.Series, secondary: bool = False) -> None:
    metric = str(row.name)
    change_text, change_class = operational_change(metric, row.change_unit, row.change_value)
    label = OPERATIONAL_LABELS[metric]
    if secondary:
        label = f"{label} · long tail"
    st.markdown(
        f"""<div class="op-card">
          <div class="op-label">{escape(label)}</div>
          <div class="op-value">{escape(operational_level(metric, row.current_7d_value))}</div>
          <div class="op-compare">Previous: {escape(operational_level(metric, row.previous_7d_value))}
            &nbsp;·&nbsp; <span class="{change_class}">{escape(change_text)}</span></div>
        </div>""",
        unsafe_allow_html=True,
    )


try:
    commercial, drivers, dimensions, operations, coverage = load_data()
except Exception as exc:
    st.error(f"Dashboard data could not be loaded: {exc}")
    st.stop()

METRICS_INV = {value: key for key, value in METRICS.items()}
available_dates = sorted(
    set(commercial["order_date"].dt.normalize())
    & set(operations["as_of_date"].dt.normalize())
    & set(drivers["order_date"].dt.normalize())
)
if not available_dates:
    st.error("No common Commercial and Operational dashboard dates are available.")
    st.stop()

title_col, date_col = st.columns([3.4, 1], vertical_alignment="bottom")
with title_col:
    st.title("E-Commerce Performance Monitor")
    st.caption("Commercial demand monitoring and operational health — kept analytically separate")
with date_col:
    selected_date_value = st.date_input(
        "Completed date",
        value=available_dates[-1].date(),
        min_value=available_dates[0].date(),
        max_value=available_dates[-1].date(),
    )
selected_date = pd.Timestamp(selected_date_value)
if selected_date not in available_dates:
    st.warning("That date has no complete dashboard record. Showing the latest prior available date.")
    selected_date = max(date for date in available_dates if date <= selected_date)

commercial_row = commercial.loc[commercial["order_date"].eq(selected_date)].iloc[0]

st.markdown('<div class="section-kicker">COMMERCIAL PERFORMANCE</div>', unsafe_allow_html=True)
st.subheader("Placed demand — exact selected date")

gmv_delta_vs_expected = (
    (commercial_row.actual_placed_gmv - commercial_row.expected_placed_gmv)
    / commercial_row.expected_placed_gmv
    if pd.notna(commercial_row.expected_placed_gmv) and commercial_row.expected_placed_gmv != 0
    else np.nan
)
status_text, status_class = anomaly_style(commercial_row.anomaly_level, commercial_row.direction)
card_cols = st.columns(4)
with card_cols[0]:
    kpi_card(
        "Placed GMV",
        compact_number(commercial_row.actual_placed_gmv, currency=True),
        f"{pct(gmv_delta_vs_expected)} vs STL Expected",
        status_text,
        status_class,
    )
for column, label, metric in zip(
    card_cols[1:],
    ["Placed Orders", "Placed AOV", "Active Customers"],
    ["placed_order_count", "placed_aov", "active_customers"],
):
    with column:
        kpi_card(
            label,
            metric_value(metric, commercial_row[f"{metric}_actual"]),
            f"{pct(commercial_row[f'{metric}_delta_pct'])} vs diagnostic Reference",
        )

chart_title_col, chart_control_col = st.columns([3.5, 1], vertical_alignment="bottom")
with chart_title_col:
    st.markdown("### Placed GMV Actual vs STL Expected")
with chart_control_col:
    chart_range_label = st.selectbox(
        "Time range", ["30 days", "90 days", "180 days", "All monitoring history"], index=1
    )
range_days = {
    "30 days": 30, "90 days": 90, "180 days": 180, "All monitoring history": None
}[chart_range_label]
st.plotly_chart(time_series_chart(commercial, selected_date, range_days), width="stretch")

st.markdown('<div class="section-kicker">DRIVER ANALYSIS</div>', unsafe_allow_html=True)
st.subheader("What drove the GMV movement?")
st.caption(
    "Click a node to continue from metric attribution to State and Category. "
    "Percentages are signed shares of the Section 4.6 driver GMV gap and are not normalized."
)

if "selected_tree_metric" not in st.session_state:
    st.session_state.selected_tree_metric = "placed_gmv"
selected_metric = st.session_state.selected_tree_metric
date_driver_rows = drivers.loc[drivers["order_date"].eq(selected_date)].copy()
tree_figure, driver_gap, share_is_meaningful = attribution_tree_chart(
    date_driver_rows, selected_metric
)
tree_event = st.plotly_chart(
    tree_figure,
    width="stretch",
    key="interactive_attribution_tree",
    on_select="rerun",
    selection_mode="points",
)
selected_points = tree_event.selection.points if tree_event else []
if selected_points:
    point_customdata = selected_points[0].get("customdata", [])
    clicked_metric = point_customdata[0] if point_customdata else None
    if clicked_metric in METRICS.values() and clicked_metric != selected_metric:
        st.session_state.selected_tree_metric = clicked_metric
        st.rerun()

if not share_is_meaningful:
    st.info(
        "Contribution share is not meaningful when the total Driver GMV Gap is near zero; "
        "the tree therefore prioritizes dollar contributions."
    )

with st.expander("Fallback KPI selector", expanded=False):
    fallback_label = st.selectbox(
        "Select a KPI when keyboard or chart-click selection is unavailable",
        list(METRICS),
        index=list(METRICS).index(METRICS_INV[selected_metric]),
        key=f"fallback_metric_{selected_metric}",
    )
    fallback_metric = METRICS[fallback_label]
    if fallback_metric != selected_metric:
        st.session_state.selected_tree_metric = fallback_metric
        st.rerun()

if selected_metric == "placed_gmv":
    selected_actual = float(date_driver_rows["actual_placed_gmv"].iloc[0])
    selected_reference = float(date_driver_rows["driver_reference_gmv"].iloc[0])
    selected_delta = driver_gap
    selected_delta_pct = selected_delta / selected_reference if selected_reference else np.nan
    selected_contribution = driver_gap
    selected_share = 1.0 if share_is_meaningful else np.nan
else:
    selected_driver_row = date_driver_rows.set_index("driver_metric").loc[selected_metric]
    selected_actual = float(selected_driver_row["actual_value"])
    selected_reference = float(selected_driver_row["reference_value"])
    selected_delta = float(selected_driver_row["delta"])
    selected_delta_pct = float(selected_driver_row["delta_pct"])
    selected_contribution = float(selected_driver_row["global_gmv_contribution"])
    selected_share = (
        float(selected_driver_row["global_gmv_contribution_pct"])
        if share_is_meaningful else np.nan
    )
selected_delta_display = metric_value(selected_metric, selected_delta)
if selected_delta > 0:
    selected_delta_display = "+" + selected_delta_display
selected_share_display = f"{selected_share:.1%}" if pd.notna(selected_share) else "N/M"
st.markdown(
    f"""<div class="selected-strip"><strong>Selected Driver: {escape(METRICS_INV[selected_metric])}</strong>
    &nbsp;&nbsp; Actual {escape(metric_value(selected_metric, selected_actual))}
    &nbsp;·&nbsp; Reference {escape(metric_value(selected_metric, selected_reference))}
    &nbsp;·&nbsp; KPI deviation {escape(selected_delta_display)} ({escape(pct(selected_delta_pct))})
    &nbsp;·&nbsp; GMV contribution <strong>{escape(signed_compact_currency(selected_contribution))}</strong>
    &nbsp;·&nbsp; Share {escape(selected_share_display)}</div>""",
    unsafe_allow_html=True,
)

drilldown_title_col, drilldown_control_col = st.columns([3.2, 1], vertical_alignment="bottom")
with drilldown_title_col:
    st.markdown(f"### Largest dimensional deviations · {METRICS_INV[selected_metric]}")
with drilldown_control_col:
    top_n_label = st.radio(
        "Dimensional Top N", ["Top 3", "Top 5", "Top 10"], index=1, horizontal=True
    )
top_n = int(top_n_label.split()[-1])

selected_dimensions = dimensions.loc[
    dimensions["order_date"].eq(selected_date)
    & dimensions["metric"].eq(selected_metric)
]
state_data = selected_dimensions.loc[selected_dimensions["dimension"].eq("state")]
category_data = selected_dimensions.loc[selected_dimensions["dimension"].eq("category")]
dim_cols = st.columns(2)
with dim_cols[0]:
    st.plotly_chart(
        dimension_chart(state_data, f"By State · {top_n_label}", top_n, selected_metric),
        width="stretch",
    )
with dim_cols[1]:
    st.plotly_chart(
        dimension_chart(category_data, f"By Category · {top_n_label}", top_n, selected_metric),
        width="stretch",
    )
st.markdown(
    '<div class="muted-note">Bars show where the selected-date deviation is concentrated, not causal impact. '
    "Category order/customer metrics are non-additive because an order or customer can span multiple categories; "
    "dimension totals are not forced to reconcile with the parent KPI.</div>",
    unsafe_allow_html=True,
)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
st.markdown('<div class="section-kicker">OPERATIONAL HEALTH</div>', unsafe_allow_html=True)
st.subheader("Last 7D vs Previous 7D")
operational_rows = operations.loc[operations["as_of_date"].eq(selected_date)].copy()
window_row = operational_rows.iloc[0]
if max(window_row.current_window_end, window_row.previous_window_end) > selected_date:
    st.error("Prepared Operational Health windows exceed the selected point-in-time cutoff.")
    st.stop()
st.caption(
    f"Current 7D: {window_row.current_window_start:%d %b %Y}–{window_row.current_window_end:%d %b %Y}  ·  "
    f"Previous 7D: {window_row.previous_window_start:%d %b %Y}–{window_row.previous_window_end:%d %b %Y}"
)

area_columns = st.columns(3, gap="large")
area_specs = {
    "Fulfillment": [
        "carrier_handoff_orders", "median_fulfillment_time_days", "p90_fulfillment_time_days"
    ],
    "Carrier Performance": [
        "delivered_orders", "median_carrier_transit_time_days",
        "p90_carrier_transit_time_days", "late_delivery_rate"
    ],
    "Customer Experience": [
        "reviews_received", "average_review_score", "negative_review_rate"
    ],
}
for column, (area, metric_list) in zip(area_columns, area_specs.items()):
    with column:
        st.markdown(f"#### {area}")
        indexed = operational_rows.set_index("metric")
        for metric in metric_list:
            operational_card(indexed.loc[metric], secondary=metric.startswith("p90_"))

with st.expander("Data Quality / Methodology"):
    coverage_lookup = coverage.set_index("coverage_measure")["coverage_rate"]
    fulfillment_coverage = coverage_lookup.get("fulfillment_duration_coverage", np.nan)
    transit_coverage = coverage_lookup.get("carrier_transit_duration_coverage", np.nan)
    st.markdown(
        f"""
        - Fulfillment duration coverage: **{fulfillment_coverage:.2%}**.
        - Carrier transit duration coverage: **{transit_coverage:.2%}**.
        - Negative timestamp-order durations are excluded from Median/P90 calculations, while the underlying operational events remain in event-volume counts.
        - Continuous durations are calculated directly from event timestamps; earlier rounded or imputed duration fields are not reused.
        - Cancellation Rate is excluded from point-in-time Operational Health because Olist provides final cancellation status but no reliable cancellation-event timestamp.
        - Commercial GMV anomaly detection and Operational Health are separate monitoring layers; operational movements are not presented as causal explanations of GMV anomalies.
        """
    )

st.caption("Prepared analytical outputs only · No STL, Robust Z, attribution, RCA, or rolling-window recomputation occurs in this app")
