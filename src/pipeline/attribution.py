"""Section 4.6 symmetric attribution and Section 4.7 dimensional RCA."""

import numpy as np
import pandas as pd

from .metrics import safe_divide


ATTRIBUTION_TOLERANCE = 1e-8
ATTRIBUTION_METRICS = [
    "placed_order_count", "placed_aov", "active_customers",
    "orders_per_active_customer", "new_customers", "returning_customers",
    "merchandise_value_per_order", "freight_per_order",
    "items_per_order", "avg_item_price",
]
DIMENSION_METRICS = [
    "placed_gmv", "placed_order_count", "placed_aov", "active_customers",
    "new_customers", "returning_customers", "orders_per_active_customer",
    "merchandise_value_per_order", "freight_per_order", "items_per_order",
    "avg_item_price",
]
ADDITIVE_METRICS = [
    "placed_gmv", "placed_order_count", "active_customers", "new_customers",
    "returning_customers", "merchandise_value", "freight_value", "item_count",
]


def _symmetric(ref_a, ref_b, actual_a, actual_b):
    gap = actual_a * actual_b - ref_a * ref_b
    contribution_a = (actual_a - ref_a) * (ref_b + actual_b) / 2
    contribution_b = (actual_b - ref_b) * (ref_a + actual_a) / 2
    denominator = gap.where(gap.abs().ge(ATTRIBUTION_TOLERANCE))
    return gap, contribution_a, contribution_b, contribution_a.div(denominator), contribution_b.div(denominator)


def _additive(ref_a, ref_b, actual_a, actual_b):
    gap = actual_a + actual_b - ref_a - ref_b
    contribution_a = actual_a - ref_a
    contribution_b = actual_b - ref_b
    denominator = gap.where(gap.abs().ge(ATTRIBUTION_TOLERANCE))
    return gap, contribution_a, contribution_b, contribution_a.div(denominator), contribution_b.div(denominator)


def _propagate(parent_global, local_gap, child_a, child_b):
    valid = parent_global.notna() & local_gap.notna() & local_gap.abs().ge(ATTRIBUTION_TOLERANCE)
    return (
        parent_global.mul(child_a).div(local_gap).where(valid),
        parent_global.mul(child_b).div(local_gap).where(valid),
        valid,
    )


def build_driver_attribution(
    comparison: pd.DataFrame,
    monitoring: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    monitoring_fields = [
        "order_date", "actual_placed_gmv", "expected_placed_gmv",
        "placed_gmv_residual", "robust_z", "abs_robust_z",
        "warning_cutoff", "critical_cutoff", "anomaly_level", "direction",
    ]
    view = comparison.merge(
        monitoring[monitoring_fields], on="order_date", how="left", validate="one_to_one"
    )
    required = [f"{metric}_{suffix}" for metric in ATTRIBUTION_METRICS for suffix in ("actual", "reference")]
    base = view.loc[~view[required].isna().any(axis=1)].copy().reset_index(drop=True)

    top = _symmetric(
        base["placed_order_count_reference"], base["placed_aov_reference"],
        base["placed_order_count_actual"], base["placed_aov_actual"],
    )
    base["driver_reference_gmv"] = (
        base["placed_order_count_reference"] * base["placed_aov_reference"]
    )
    base["driver_gmv_gap"] = base["placed_gmv_actual"] - base["driver_reference_gmv"]
    base["orders_contribution_to_gmv"], base["aov_contribution_to_gmv"] = top[1], top[2]
    denominator = base["driver_gmv_gap"].where(
        base["driver_gmv_gap"].abs().ge(ATTRIBUTION_TOLERANCE)
    )
    base["orders_contribution_pct"] = base["orders_contribution_to_gmv"].div(denominator)
    base["aov_contribution_pct"] = base["aov_contribution_to_gmv"].div(denominator)

    orders = _symmetric(
        base["active_customers_reference"], base["orders_per_active_customer_reference"],
        base["active_customers_actual"], base["orders_per_active_customer_actual"],
    )
    base["driver_reference_orders"] = (
        base["active_customers_reference"] * base["orders_per_active_customer_reference"]
    )
    base["driver_orders_gap"] = base["placed_order_count_actual"] - base["driver_reference_orders"]
    base["active_customer_contribution_to_orders"] = orders[1]
    base["purchase_frequency_contribution_to_orders"] = orders[2]
    base["active_customer_local_contribution_pct"] = orders[3]
    base["purchase_frequency_local_contribution_pct"] = orders[4]

    customers = _additive(
        base["new_customers_reference"], base["returning_customers_reference"],
        base["new_customers_actual"], base["returning_customers_actual"],
    )
    base["driver_reference_active_customers"] = (
        base["new_customers_reference"] + base["returning_customers_reference"]
    )
    base["driver_active_customer_gap"] = (
        base["active_customers_actual"] - base["driver_reference_active_customers"]
    )
    base["new_customer_contribution"], base["returning_customer_contribution"] = customers[1], customers[2]
    base["new_customer_local_contribution_pct"], base["returning_customer_local_contribution_pct"] = customers[3], customers[4]

    aov = _additive(
        base["merchandise_value_per_order_reference"], base["freight_per_order_reference"],
        base["merchandise_value_per_order_actual"], base["freight_per_order_actual"],
    )
    base["driver_reference_aov"] = (
        base["merchandise_value_per_order_reference"] + base["freight_per_order_reference"]
    )
    base["driver_aov_gap"] = base["placed_aov_actual"] - base["driver_reference_aov"]
    base["merchandise_per_order_contribution_to_aov"] = aov[1]
    base["freight_per_order_contribution_to_aov"] = aov[2]
    base["merchandise_per_order_local_contribution_pct"] = aov[3]
    base["freight_per_order_local_contribution_pct"] = aov[4]

    merchandise = _symmetric(
        base["items_per_order_reference"], base["avg_item_price_reference"],
        base["items_per_order_actual"], base["avg_item_price_actual"],
    )
    base["driver_reference_merchandise_per_order"] = (
        base["items_per_order_reference"] * base["avg_item_price_reference"]
    )
    base["driver_merchandise_gap"] = (
        base["merchandise_value_per_order_actual"] - base["driver_reference_merchandise_per_order"]
    )
    base["items_per_order_contribution"], base["avg_item_price_contribution"] = merchandise[1], merchandise[2]
    base["items_per_order_local_contribution_pct"], base["avg_item_price_local_contribution_pct"] = merchandise[3], merchandise[4]

    (
        base["active_customer_global_gmv_contribution"],
        base["purchase_frequency_global_gmv_contribution"],
        orders_valid,
    ) = _propagate(
        base["orders_contribution_to_gmv"], base["driver_orders_gap"],
        base["active_customer_contribution_to_orders"],
        base["purchase_frequency_contribution_to_orders"],
    )
    (
        base["new_customer_global_gmv_contribution"],
        base["returning_customer_global_gmv_contribution"],
        customers_valid,
    ) = _propagate(
        base["active_customer_global_gmv_contribution"], base["driver_active_customer_gap"],
        base["new_customer_contribution"], base["returning_customer_contribution"],
    )
    (
        base["merchandise_per_order_global_gmv_contribution"],
        base["freight_per_order_global_gmv_contribution"],
        aov_valid,
    ) = _propagate(
        base["aov_contribution_to_gmv"], base["driver_aov_gap"],
        base["merchandise_per_order_contribution_to_aov"],
        base["freight_per_order_contribution_to_aov"],
    )
    (
        base["items_per_order_global_gmv_contribution"],
        base["avg_item_price_global_gmv_contribution"],
        merchandise_valid,
    ) = _propagate(
        base["merchandise_per_order_global_gmv_contribution"], base["driver_merchandise_gap"],
        base["items_per_order_contribution"], base["avg_item_price_contribution"],
    )
    base["fully_propagatable"] = orders_valid & customers_valid & aov_valid & merchandise_valid
    base["non_propagatable_branch_count"] = (~pd.concat(
        [orders_valid, customers_valid, aov_valid, merchandise_valid], axis=1
    )).sum(axis=1)
    base["independent_reference_orders_minus_driver_reference_orders"] = (
        base["placed_order_count_reference"] - base["driver_reference_orders"]
    )
    base["independent_reference_aov_minus_driver_reference_aov"] = (
        base["placed_aov_reference"] - base["driver_reference_aov"]
    )

    gmv = base[[
        "order_date", "anomaly_level", "direction", "actual_placed_gmv",
        "expected_placed_gmv", "placed_gmv_residual", "robust_z",
        "driver_reference_gmv", "driver_gmv_gap", "orders_contribution_to_gmv",
        "orders_contribution_pct", "aov_contribution_to_gmv", "aov_contribution_pct",
        "independent_reference_orders_minus_driver_reference_orders",
        "independent_reference_aov_minus_driver_reference_aov", "fully_propagatable",
        "non_propagatable_branch_count",
    ]].rename(columns={"placed_gmv_residual": "stl_gmv_residual"})

    specs = [
        ("top_level", "placed_gmv", "placed_order_count", "driver_gmv_gap", "orders_contribution_to_gmv", "orders_contribution_pct", "orders_contribution_to_gmv"),
        ("top_level", "placed_gmv", "placed_aov", "driver_gmv_gap", "aov_contribution_to_gmv", "aov_contribution_pct", "aov_contribution_to_gmv"),
        ("orders_branch", "placed_order_count", "active_customers", "driver_orders_gap", "active_customer_contribution_to_orders", "active_customer_local_contribution_pct", "active_customer_global_gmv_contribution"),
        ("orders_branch", "placed_order_count", "orders_per_active_customer", "driver_orders_gap", "purchase_frequency_contribution_to_orders", "purchase_frequency_local_contribution_pct", "purchase_frequency_global_gmv_contribution"),
        ("active_customer_branch", "active_customers", "new_customers", "driver_active_customer_gap", "new_customer_contribution", "new_customer_local_contribution_pct", "new_customer_global_gmv_contribution"),
        ("active_customer_branch", "active_customers", "returning_customers", "driver_active_customer_gap", "returning_customer_contribution", "returning_customer_local_contribution_pct", "returning_customer_global_gmv_contribution"),
        ("aov_branch", "placed_aov", "merchandise_value_per_order", "driver_aov_gap", "merchandise_per_order_contribution_to_aov", "merchandise_per_order_local_contribution_pct", "merchandise_per_order_global_gmv_contribution"),
        ("aov_branch", "placed_aov", "freight_per_order", "driver_aov_gap", "freight_per_order_contribution_to_aov", "freight_per_order_local_contribution_pct", "freight_per_order_global_gmv_contribution"),
        ("merchandise_branch", "merchandise_value_per_order", "items_per_order", "driver_merchandise_gap", "items_per_order_contribution", "items_per_order_local_contribution_pct", "items_per_order_global_gmv_contribution"),
        ("merchandise_branch", "merchandise_value_per_order", "avg_item_price", "driver_merchandise_gap", "avg_item_price_contribution", "avg_item_price_local_contribution_pct", "avg_item_price_global_gmv_contribution"),
    ]
    frames = []
    context_columns = [
        "order_date", "anomaly_level", "direction", "actual_placed_gmv",
        "expected_placed_gmv", "placed_gmv_residual", "driver_reference_gmv",
        "driver_gmv_gap", "robust_z",
    ]
    for level, parent, metric, gap_col, local_col, local_pct_col, global_col in specs:
        frame = base[context_columns].copy()
        frame["driver_level"], frame["parent_metric"], frame["driver_metric"] = level, parent, metric
        for output, source in (
            ("actual_value", f"{metric}_actual"),
            ("reference_value", f"{metric}_reference"),
            ("delta", f"{metric}_delta"),
            ("delta_pct", f"{metric}_delta_pct"),
            ("local_parent_gap", gap_col),
            ("local_contribution", local_col),
            ("local_contribution_pct", local_pct_col),
            ("global_gmv_contribution", global_col),
        ):
            frame[output] = base[source]
        frame["global_gmv_contribution_pct"] = frame["global_gmv_contribution"].div(denominator)
        frames.append(frame)
    long = (
        pd.concat(frames, ignore_index=True)
        .rename(columns={"placed_gmv_residual": "stl_gmv_residual"})
        .sort_values(["order_date", "driver_level", "driver_metric"])
        .reset_index(drop=True)
    )
    return gmv, long


def _build_dimensional_daily(source, dates, item_grain):
    working = source.copy()
    working["new_customer_unique_id"] = working["customer_unique_id"].where(working["is_new_customer"])
    working["returning_customer_unique_id"] = working["customer_unique_id"].where(working["is_returning_customer"])
    group = ["order_date", "dimension_value"]
    if item_grain:
        grouped = working.groupby(group, as_index=False, observed=True).agg(
            placed_gmv=("item_placed_gmv", "sum"), placed_order_count=("order_id", "nunique"),
            active_customers=("customer_unique_id", "nunique"),
            new_customers=("new_customer_unique_id", "nunique"),
            returning_customers=("returning_customer_unique_id", "nunique"),
            merchandise_value=("price", "sum"), freight_value=("freight_value", "sum"),
            item_count=("order_item_id", "count"),
        )
    else:
        grouped = working.groupby(group, as_index=False, observed=True).agg(
            placed_gmv=("order_value", "sum"), placed_order_count=("order_id", "nunique"),
            active_customers=("customer_unique_id", "nunique"),
            new_customers=("new_customer_unique_id", "nunique"),
            returning_customers=("returning_customer_unique_id", "nunique"),
            merchandise_value=("merchandise_value", "sum"), freight_value=("freight_value", "sum"),
            item_count=("item_count", "sum"),
        )
    values = sorted(working["dimension_value"].dropna().unique())
    grid = pd.MultiIndex.from_product([dates, values], names=group).to_frame(index=False)
    result = grid.merge(grouped, on=group, how="left", validate="one_to_one")
    result[ADDITIVE_METRICS] = result[ADDITIVE_METRICS].fillna(0)
    result["placed_aov"] = safe_divide(result["placed_gmv"], result["placed_order_count"])
    result["orders_per_active_customer"] = safe_divide(result["placed_order_count"], result["active_customers"])
    result["merchandise_value_per_order"] = safe_divide(result["merchandise_value"], result["placed_order_count"])
    result["freight_per_order"] = safe_divide(result["freight_value"], result["placed_order_count"])
    result["items_per_order"] = safe_divide(result["item_count"], result["placed_order_count"])
    result["avg_item_price"] = safe_divide(result["merchandise_value"], result["item_count"])
    return result[["order_date", "dimension_value", *DIMENSION_METRICS]].sort_values(group).reset_index(drop=True)


def _dimensional_long(daily: pd.DataFrame, name: str) -> pd.DataFrame:
    working = daily.copy()
    working["weekday"] = working["order_date"].dt.dayofweek
    frames = []
    for metric in DIMENSION_METRICS:
        actual = working[metric].astype(float)
        keys = [working["dimension_value"], working["weekday"]]
        reference = actual.groupby(keys, sort=False).transform(
            lambda values: values.shift(1).rolling(8, min_periods=4).median()
        )
        history = actual.groupby(keys, sort=False).transform(
            lambda values: values.shift(1).rolling(8, min_periods=1).count()
        ).astype("int64")
        delta = actual - reference
        frames.append(pd.DataFrame({
            "order_date": working["order_date"], "dimension": name,
            "dimension_value": working["dimension_value"], "metric": metric,
            "actual_value": actual, "reference_value": reference, "delta": delta,
            "delta_pct": delta.div(reference.where(reference.ne(0))),
            "reference_history_count": history,
        }))
    result = pd.concat(frames, ignore_index=True)
    result["abs_delta"] = result["delta"].abs()
    result["delta_rank"] = result.groupby(
        ["order_date", "metric", "dimension"]
    )["abs_delta"].rank(method="first", ascending=False, na_option="keep").astype("Int64")
    return result


def build_dimensional_rca(
    eligible_orders: pd.DataFrame,
    orders_analysis: pd.DataFrame,
    items: pd.DataFrame,
    customers: pd.DataFrame,
    products: pd.DataFrame,
    diagnostic_dates: pd.Series,
    monitoring: pd.DataFrame,
) -> pd.DataFrame:
    state = (
        eligible_orders.merge(
            orders_analysis[["order_id", "customer_id"]],
            on="order_id", how="left", validate="one_to_one",
        ).merge(
            customers[["customer_id", "customer_state"]],
            on="customer_id", how="left", validate="many_to_one",
        )
    )
    state["dimension_value"] = state["customer_state"].astype("string").fillna("Missing Customer State")
    context = eligible_orders[[
        "order_id", "order_date", "customer_unique_id", "is_new_customer", "is_returning_customer"
    ]]
    category = (
        items.merge(context, on="order_id", how="inner", validate="many_to_one")
        .merge(
            products[["product_id", "product_category_name"]],
            on="product_id", how="left", validate="many_to_one",
        )
    )
    category["dimension_value"] = category["product_category_name"].astype("string").fillna("Missing Product Category")
    category["item_placed_gmv"] = category["price"] + category["freight_value"]

    state_daily = _build_dimensional_daily(state, diagnostic_dates, item_grain=False)
    category_daily = _build_dimensional_daily(category, diagnostic_dates, item_grain=True)
    result = pd.concat([
        _dimensional_long(state_daily, "state"),
        _dimensional_long(category_daily, "category"),
    ], ignore_index=True)
    context = monitoring[[
        "order_date", "anomaly_level", "direction", "robust_z",
        "actual_placed_gmv", "expected_placed_gmv",
    ]]
    columns = [
        "order_date", "dimension", "dimension_value", "metric", "actual_value",
        "reference_value", "delta", "delta_pct", "abs_delta", "delta_rank",
        "reference_history_count", "anomaly_level", "direction", "robust_z",
        "actual_placed_gmv", "expected_placed_gmv",
    ]
    return (
        result.merge(context, on="order_date", how="left", validate="many_to_one")[columns]
        .sort_values(["order_date", "metric", "dimension", "delta_rank"])
        .reset_index(drop=True)
    )
