"""Section 5 event-time Current-7D versus Previous-7D monitoring."""

import numpy as np
import pandas as pd


METRIC_SPECS = [
    ("Fulfillment", "carrier_handoff_orders", "volume_pct_change"),
    ("Fulfillment", "median_fulfillment_time_days", "days_difference"),
    ("Fulfillment", "p90_fulfillment_time_days", "days_difference"),
    ("Carrier Performance", "delivered_orders", "volume_pct_change"),
    ("Carrier Performance", "median_carrier_transit_time_days", "days_difference"),
    ("Carrier Performance", "p90_carrier_transit_time_days", "days_difference"),
    ("Carrier Performance", "late_delivery_rate", "percentage_points"),
    ("Customer Experience", "reviews_received", "volume_pct_change"),
    ("Customer Experience", "average_review_score", "score_difference"),
    ("Customer Experience", "negative_review_rate", "percentage_points"),
]


def _change(current, previous, unit):
    if pd.isna(current) or pd.isna(previous):
        return np.nan
    if unit == "volume_pct_change":
        return (current - previous) / previous if previous != 0 else np.nan
    if unit == "percentage_points":
        return (current - previous) * 100
    return current - previous


def build_operational_health(
    orders: pd.DataFrame,
    reviews: pd.DataFrame,
    calendar_dates: pd.Series,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    fulfillment = orders[[
        "order_id", "order_purchase_dt", "order_approved_dt", "order_delivered_carrier_dt"
    ]].dropna(subset=["order_purchase_dt", "order_delivered_carrier_dt"]).copy()
    fulfillment["event_date"] = fulfillment["order_delivered_carrier_dt"].dt.normalize()
    fulfillment["fulfillment_time_days"] = (
        fulfillment["order_delivered_carrier_dt"] - fulfillment["order_purchase_dt"]
    ).dt.total_seconds().div(86400)
    fulfillment["has_invalid_negative_duration"] = fulfillment["fulfillment_time_days"].lt(0)
    fulfillment["fulfillment_time_days"] = fulfillment["fulfillment_time_days"].mask(
        fulfillment["has_invalid_negative_duration"]
    )

    delivery = orders[[
        "order_id", "order_delivered_carrier_dt", "order_delivered_customer_dt",
        "order_estimated_delivery_dt",
    ]].dropna(subset=["order_delivered_customer_dt"]).copy()
    delivery["event_date"] = delivery["order_delivered_customer_dt"].dt.normalize()
    delivery["carrier_transit_time_days"] = (
        delivery["order_delivered_customer_dt"] - delivery["order_delivered_carrier_dt"]
    ).dt.total_seconds().div(86400)
    delivery["has_invalid_negative_duration"] = delivery["carrier_transit_time_days"].lt(0)
    delivery["carrier_transit_time_days"] = delivery["carrier_transit_time_days"].mask(
        delivery["has_invalid_negative_duration"]
    )
    delivery["is_late_delivery"] = (
        delivery["order_estimated_delivery_dt"].notna()
        & delivery["order_delivered_customer_dt"].gt(delivery["order_estimated_delivery_dt"])
    )

    review_events = (
        reviews[["review_id", "order_id", "review_creation_date", "review_score"]]
        .dropna(subset=["review_id", "review_creation_date", "review_score"])
        .sort_values(["review_creation_date", "review_id", "order_id"])
        .drop_duplicates("review_id", keep="first").copy()
    )
    review_events["event_date"] = review_events["review_creation_date"].dt.normalize()
    review_events["is_negative_review"] = review_events["review_score"].le(2)

    start, end = calendar_dates.min(), calendar_dates.max()
    fulfillment_scope = fulfillment.loc[fulfillment["event_date"].between(start, end)]
    delivery_scope = delivery.loc[
        delivery["event_date"].between(start, end)
        & delivery["order_delivered_carrier_dt"].notna()
    ]
    fulfillment_required = fulfillment_scope["order_id"].nunique()
    fulfillment_valid = fulfillment_scope.loc[
        fulfillment_scope["fulfillment_time_days"].notna(), "order_id"
    ].nunique()
    carrier_required = delivery_scope["order_id"].nunique()
    carrier_valid = delivery_scope.loc[
        delivery_scope["carrier_transit_time_days"].notna(), "order_id"
    ].nunique()
    coverage = pd.DataFrame({
        "coverage_measure": ["fulfillment_duration_coverage", "carrier_transit_duration_coverage"],
        "valid_non_negative_duration_orders": [fulfillment_valid, carrier_valid],
        "orders_with_required_timestamps": [fulfillment_required, carrier_required],
        "coverage_rate": [
            fulfillment_valid / fulfillment_required if fulfillment_required else np.nan,
            carrier_valid / carrier_required if carrier_required else np.nan,
        ],
        "event_date_scope_start": [start, start],
        "event_date_scope_end": [end, end],
    })

    def window_values(window_start, window_end):
        fulfillment_window = fulfillment.loc[fulfillment["event_date"].between(window_start, window_end)]
        delivery_window = delivery.loc[delivery["event_date"].between(window_start, window_end)]
        review_window = review_events.loc[review_events["event_date"].between(window_start, window_end)]
        transit = delivery_window["carrier_transit_time_days"].dropna()
        late = delivery_window.loc[delivery_window["order_estimated_delivery_dt"].notna()]
        return {
            "carrier_handoff_orders": fulfillment_window["order_id"].nunique(),
            "median_fulfillment_time_days": fulfillment_window["fulfillment_time_days"].median(),
            "p90_fulfillment_time_days": fulfillment_window["fulfillment_time_days"].quantile(0.90),
            "delivered_orders": delivery_window["order_id"].nunique(),
            "median_carrier_transit_time_days": transit.median(),
            "p90_carrier_transit_time_days": transit.quantile(0.90),
            "late_delivery_rate": late["is_late_delivery"].mean() if len(late) else np.nan,
            "reviews_received": review_window["review_id"].nunique(),
            "average_review_score": review_window["review_score"].mean(),
            "negative_review_rate": review_window["is_negative_review"].mean() if len(review_window) else np.nan,
        }

    rows = []
    for as_of_date in pd.date_range(start + pd.Timedelta(days=13), end, freq="D"):
        current_start, current_end = as_of_date - pd.Timedelta(days=6), as_of_date
        previous_start, previous_end = as_of_date - pd.Timedelta(days=13), as_of_date - pd.Timedelta(days=7)
        current = window_values(current_start, current_end)
        previous = window_values(previous_start, previous_end)
        for area, metric, unit in METRIC_SPECS:
            rows.append({
                "as_of_date": as_of_date, "operational_area": area, "metric": metric,
                "current_7d_value": current[metric], "previous_7d_value": previous[metric],
                "change_value": _change(current[metric], previous[metric], unit),
                "change_unit": unit, "current_window_start": current_start,
                "current_window_end": current_end, "previous_window_start": previous_start,
                "previous_window_end": previous_end,
            })
    health = pd.DataFrame(rows).sort_values(
        ["as_of_date", "operational_area", "metric"]
    ).reset_index(drop=True)
    return health, coverage
