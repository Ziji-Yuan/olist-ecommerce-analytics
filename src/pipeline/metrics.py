"""Commercial mart and same-weekday diagnostic metrics from Sections 4.1/4.5."""

import numpy as np
import pandas as pd


DIAGNOSTIC_METRIC_NODES = [
    "placed_gmv", "placed_order_count", "placed_aov",
    "active_customers", "new_customers", "returning_customers",
    "orders_per_active_customer", "merchandise_value",
    "merchandise_value_per_order", "freight_value", "freight_per_order",
    "item_count", "items_per_order", "avg_item_price",
]


def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return numerator.div(denominator.where(denominator.ne(0)))


def build_daily_business_mart(
    orders_analysis: pd.DataFrame,
    items: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    item_agg = items.groupby("order_id", as_index=False).agg(
        mart_item_count=("order_item_id", "count"),
        mart_item_revenue=("price", "sum"),
        mart_item_freight_value=("freight_value", "sum"),
    )
    required = {
        "order_id", "customer_unique_id", "order_purchase_dt", "order_status",
        "order_value", "is_late_delivery", "review_score",
        "order_handling_time_days", "carrier_time_days", "delivery_time_days",
    }
    base = orders_analysis[list(required)].merge(
        item_agg, on="order_id", how="left", validate="one_to_one"
    )
    base["order_date"] = base["order_purchase_dt"].dt.normalize()
    base["is_placed_value_order"] = base["order_value"].notna()
    base["placed_order_value"] = base["order_value"].where(
        base["is_placed_value_order"], 0.0
    )
    base["is_revenue_order"] = (
        base["order_status"].eq("delivered") & base["order_value"].notna()
    )
    base["delivered_order_value"] = base["order_value"].where(
        base["is_revenue_order"], 0.0
    )
    item_columns = ["mart_item_count", "mart_item_revenue", "mart_item_freight_value"]
    base[item_columns] = base[item_columns].fillna(0)
    base["mart_item_count"] = base["mart_item_count"].astype("int64")
    first_purchase = base.groupby("customer_unique_id")["order_date"].min()
    base = base.merge(
        first_purchase.rename("first_purchase_date"),
        on="customer_unique_id", how="left", validate="many_to_one",
    )
    base["is_canceled_order"] = base["order_status"].eq("canceled")
    base["is_late_delivery_eligible"] = (
        base["order_status"].eq("delivered") & base["is_late_delivery"].notna()
    )
    base["is_late_delivered_order"] = (
        base["is_late_delivery_eligible"]
        & base["is_late_delivery"].fillna(False).astype(bool)
    )
    base["delivered_items"] = base["mart_item_count"].where(base["is_revenue_order"], 0)
    base["delivered_item_revenue"] = base["mart_item_revenue"].where(
        base["is_revenue_order"], 0.0
    )
    base["delivered_freight_value"] = base["mart_item_freight_value"].where(
        base["is_revenue_order"], 0.0
    )
    base["is_reviewed_order"] = base["review_score"].notna()
    base["is_new_customer"] = base["order_date"].eq(base["first_purchase_date"])
    base["is_returning_customer"] = base["order_date"].gt(base["first_purchase_date"])

    daily = base.groupby("order_date", as_index=False).agg(
        placed_gmv=("placed_order_value", "sum"),
        placed_order_count=("is_placed_value_order", "sum"),
        delivered_gmv=("delivered_order_value", "sum"),
        revenue_order_count=("is_revenue_order", "sum"),
        order_count=("order_id", "nunique"),
        active_customers=("customer_unique_id", "nunique"),
        total_items=("mart_item_count", "sum"),
        delivered_items=("delivered_items", "sum"),
        delivered_item_revenue=("delivered_item_revenue", "sum"),
        delivered_freight_value=("delivered_freight_value", "sum"),
        canceled_order_count=("is_canceled_order", "sum"),
        late_delivery_count=("is_late_delivered_order", "sum"),
        late_delivery_eligible_order_count=("is_late_delivery_eligible", "sum"),
        reviewed_order_count=("is_reviewed_order", "sum"),
        review_score_sum=("review_score", "sum"),
        avg_handling_time_days=("order_handling_time_days", "mean"),
        avg_carrier_time_days=("carrier_time_days", "mean"),
        avg_delivery_time_days=("delivery_time_days", "mean"),
    )
    customer_type = (
        base[["order_date", "customer_unique_id", "is_new_customer", "is_returning_customer"]]
        .drop_duplicates(["order_date", "customer_unique_id"])
        .groupby("order_date", as_index=False)
        .agg(
            new_customers=("is_new_customer", "sum"),
            returning_customers=("is_returning_customer", "sum"),
        )
    )
    spine = pd.DataFrame({
        "order_date": pd.date_range(base["order_date"].min(), base["order_date"].max(), freq="D")
    })
    mart = (
        spine.merge(daily, on="order_date", how="left", validate="one_to_one")
        .merge(customer_type, on="order_date", how="left", validate="one_to_one")
    )
    count_columns = [
        "placed_order_count", "revenue_order_count", "order_count", "active_customers",
        "new_customers", "returning_customers", "total_items", "delivered_items",
        "canceled_order_count", "late_delivery_count",
        "late_delivery_eligible_order_count", "reviewed_order_count",
    ]
    value_columns = [
        "placed_gmv", "delivered_gmv", "delivered_item_revenue",
        "delivered_freight_value", "review_score_sum",
    ]
    mart[count_columns] = mart[count_columns].fillna(0).astype("int64")
    mart[value_columns] = mart[value_columns].fillna(0.0)
    mart["placed_aov"] = safe_divide(mart["placed_gmv"], mart["placed_order_count"])
    mart["delivered_aov"] = safe_divide(mart["delivered_gmv"], mart["revenue_order_count"])
    mart["new_customer_rate"] = safe_divide(mart["new_customers"], mart["active_customers"])
    mart["returning_customer_rate"] = safe_divide(
        mart["returning_customers"], mart["active_customers"]
    )
    mart["purchase_frequency"] = safe_divide(mart["order_count"], mart["active_customers"])
    mart["items_per_order"] = safe_divide(mart["delivered_items"], mart["revenue_order_count"])
    mart["avg_item_price"] = safe_divide(
        mart["delivered_item_revenue"], mart["delivered_items"]
    )
    mart["cancellation_rate"] = safe_divide(mart["canceled_order_count"], mart["order_count"])
    mart["late_delivery_rate"] = safe_divide(
        mart["late_delivery_count"], mart["late_delivery_eligible_order_count"]
    )
    mart["avg_review_score"] = safe_divide(mart["review_score_sum"], mart["reviewed_order_count"])
    return mart.sort_values("order_date").reset_index(drop=True), base


def build_daily_diagnostic_metrics(
    orders_analysis: pd.DataFrame,
    items: pd.DataFrame,
    mart: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    item_agg = items.groupby("order_id", as_index=False).agg(
        item_count=("order_item_id", "count"),
        merchandise_value=("price", "sum"),
        freight_value=("freight_value", "sum"),
    )
    base = orders_analysis[[
        "order_id", "customer_unique_id", "order_purchase_dt", "order_status", "order_value"
    ]].merge(item_agg, on="order_id", how="left", validate="one_to_one")
    base["order_date"] = base["order_purchase_dt"].dt.normalize()
    eligible = base.loc[base["order_value"].notna()].copy()
    first_purchase = eligible.groupby("customer_unique_id")["order_date"].min()
    eligible = eligible.merge(
        first_purchase.rename("first_eligible_purchase_date"),
        on="customer_unique_id", how="left", validate="many_to_one",
    )
    eligible["is_new_customer"] = eligible["order_date"].eq(
        eligible["first_eligible_purchase_date"]
    )
    eligible["is_returning_customer"] = eligible["order_date"].gt(
        eligible["first_eligible_purchase_date"]
    )
    additive = eligible.groupby("order_date", as_index=False).agg(
        placed_gmv=("order_value", "sum"),
        placed_order_count=("order_id", "nunique"),
        active_customers=("customer_unique_id", "nunique"),
        merchandise_value=("merchandise_value", "sum"),
        freight_value=("freight_value", "sum"),
        item_count=("item_count", "sum"),
    )
    customer_type = (
        eligible[["order_date", "customer_unique_id", "is_new_customer", "is_returning_customer"]]
        .drop_duplicates(["order_date", "customer_unique_id"])
        .groupby("order_date", as_index=False)
        .agg(
            new_customers=("is_new_customer", "sum"),
            returning_customers=("is_returning_customer", "sum"),
        )
    )
    result = (
        mart[["order_date"]].merge(additive, on="order_date", how="left", validate="one_to_one")
        .merge(customer_type, on="order_date", how="left", validate="one_to_one")
    )
    additive_columns = [
        "placed_gmv", "placed_order_count", "active_customers", "new_customers",
        "returning_customers", "merchandise_value", "freight_value", "item_count",
    ]
    result[additive_columns] = result[additive_columns].fillna(0)
    for column in [
        "placed_order_count", "active_customers", "new_customers",
        "returning_customers", "item_count",
    ]:
        result[column] = result[column].astype("int64")
    result["placed_aov"] = safe_divide(result["placed_gmv"], result["placed_order_count"])
    result["orders_per_active_customer"] = safe_divide(
        result["placed_order_count"], result["active_customers"]
    )
    result["merchandise_value_per_order"] = safe_divide(
        result["merchandise_value"], result["placed_order_count"]
    )
    result["freight_per_order"] = safe_divide(result["freight_value"], result["placed_order_count"])
    result["items_per_order"] = safe_divide(result["item_count"], result["placed_order_count"])
    result["avg_item_price"] = safe_divide(result["merchandise_value"], result["item_count"])
    result = result[["order_date", *DIAGNOSTIC_METRIC_NODES]].sort_values("order_date").reset_index(drop=True)
    return result, eligible


def build_diagnostic_comparison(metrics: pd.DataFrame) -> pd.DataFrame:
    comparison = metrics[["order_date"]].copy()
    comparison["weekday"] = comparison["order_date"].dt.dayofweek
    comparison["reference_history_count"] = comparison.groupby("weekday").cumcount().clip(upper=8)
    comparison["reference_status"] = np.select(
        [comparison["reference_history_count"].eq(8), comparison["reference_history_count"].between(4, 7)],
        ["full_8_week", "partial_4_to_7_week"], default="unavailable",
    )
    for metric in DIAGNOSTIC_METRIC_NODES:
        actual = metrics[metric].astype(float)
        reference = actual.groupby(comparison["weekday"], sort=False).transform(
            lambda values: values.shift(1).rolling(8, min_periods=4).median()
        )
        history = actual.groupby(comparison["weekday"], sort=False).transform(
            lambda values: values.shift(1).rolling(8, min_periods=1).count()
        ).astype("int64")
        delta = actual - reference
        comparison[f"{metric}_actual"] = actual
        comparison[f"{metric}_reference"] = reference
        comparison[f"{metric}_delta"] = delta
        comparison[f"{metric}_delta_pct"] = delta.div(reference.where(reference.ne(0)))
        comparison[f"{metric}_reference_history_count"] = history

    gaps = {
        "a": comparison["placed_gmv_reference"]
        - comparison["placed_order_count_reference"] * comparison["placed_aov_reference"],
        "b": comparison["placed_order_count_reference"]
        - comparison["active_customers_reference"] * comparison["orders_per_active_customer_reference"],
        "c": comparison["active_customers_reference"]
        - comparison["new_customers_reference"] - comparison["returning_customers_reference"],
        "d": comparison["placed_gmv_reference"]
        - comparison["merchandise_value_reference"] - comparison["freight_value_reference"],
        "e": comparison["placed_aov_reference"]
        - comparison["merchandise_value_per_order_reference"] - comparison["freight_per_order_reference"],
        "f": comparison["merchandise_value_per_order_reference"]
        - comparison["items_per_order_reference"] * comparison["avg_item_price_reference"],
    }
    for key, values in gaps.items():
        comparison[f"reference_gap_{key}"] = values
    return comparison
