"""Validated cleaning decisions extracted from the notebook ETL section."""

import numpy as np
import pandas as pd


ORDER_TIMESTAMP_COLUMNS = {
    "order_purchase_timestamp": "order_purchase_dt",
    "order_approved_at": "order_approved_dt",
    "order_delivered_carrier_date": "order_delivered_carrier_dt",
    "order_delivered_customer_date": "order_delivered_customer_dt",
    "order_estimated_delivery_date": "order_estimated_delivery_dt",
}


def clean_source_tables(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Apply the notebook's date scope, timestamp fills, and structural cleaning."""
    tables = {name: frame.copy() for name, frame in raw.items()}
    orders = tables["orders"]
    for source, target in ORDER_TIMESTAMP_COLUMNS.items():
        orders[target] = pd.to_datetime(orders[source], format="%Y-%m-%d %H:%M:%S")
    orders = orders.drop(columns=list(ORDER_TIMESTAMP_COLUMNS))

    reviews = tables["reviews"]
    reviews["review_creation_date"] = pd.to_datetime(
        reviews["review_creation_date"], format="%Y-%m-%d %H:%M:%S"
    )
    if "review_answer_timestamp" in reviews:
        reviews["review_answer_timestamp"] = pd.to_datetime(
            reviews["review_answer_timestamp"], format="%Y-%m-%d %H:%M:%S"
        )
    if "shipping_limit_date" in tables["items"]:
        tables["items"]["shipping_limit_date"] = pd.to_datetime(
            tables["items"]["shipping_limit_date"], format="%Y-%m-%d %H:%M:%S"
        )

    orders = orders.loc[
        orders["order_purchase_dt"].between("2017-01-01", "2018-09-01", inclusive="left")
        | orders["order_purchase_dt"].isna()
    ].copy()
    reviews = reviews.loc[
        reviews["review_creation_date"].ge("2017-01-01")
        | reviews["review_creation_date"].isna()
    ].copy()

    tables["customers"] = tables["customers"].merge(
        orders[["customer_id"]], on="customer_id", how="inner", validate="one_to_one"
    )
    for table_name in ("payments", "items"):
        tables[table_name] = tables[table_name].merge(
            orders[["order_id"]], on="order_id", how="inner", validate="many_to_one"
        )
    reviews = reviews.merge(
        orders[["order_id"]], on="order_id", how="inner", validate="many_to_one"
    )

    carrier_missing = orders["order_delivered_carrier_dt"].isna() & (
        orders["order_status"].eq("delivered")
        | orders["order_delivered_customer_dt"].notna()
    )
    median_carrier_time = (
        orders["order_delivered_carrier_dt"] - orders["order_approved_dt"]
    ).median()
    orders.loc[carrier_missing, "order_delivered_carrier_dt"] = (
        orders.loc[carrier_missing, "order_approved_dt"] + median_carrier_time
    )

    customer_missing = (
        orders["order_delivered_customer_dt"].isna()
        & orders["order_status"].eq("delivered")
    )
    valid_customer_delivery = (
        orders["order_delivered_carrier_dt"].notna()
        & orders["order_delivered_customer_dt"].notna()
        & orders["order_delivered_customer_dt"].ge(orders["order_delivered_carrier_dt"])
    )
    median_customer_delivery_time = (
        orders.loc[valid_customer_delivery, "order_delivered_customer_dt"]
        - orders.loc[valid_customer_delivery, "order_delivered_carrier_dt"]
    ).median()
    orders.loc[customer_missing, "order_delivered_customer_dt"] = (
        orders.loc[customer_missing, "order_delivered_carrier_dt"]
        + median_customer_delivery_time
    )

    products = tables["products"].copy()
    products["product_category_name"] = (
        products["product_category_name"].astype("string").fillna("Missing in Products")
    )
    physical = [
        "product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"
    ]
    present_physical = [column for column in physical if column in products]
    products[present_physical] = products[present_physical].fillna(
        products.groupby("product_category_name")[present_physical].transform("median")
    )
    if "product_weight_g" in products:
        positive_category_median = (
            products["product_weight_g"].where(products["product_weight_g"].gt(0))
            .groupby(products["product_category_name"]).transform("median")
        )
        zero_weight = products["product_weight_g"].eq(0)
        products.loc[zero_weight, "product_weight_g"] = positive_category_median[zero_weight]

    tables["payments"].loc[
        tables["payments"]["payment_installments"].eq(0), "payment_installments"
    ] = 1

    orders["order_handling_time_days"] = np.ceil(
        (orders["order_delivered_carrier_dt"] - orders["order_approved_dt"])
        .dt.total_seconds().div(86400)
    ).astype("Int64")
    valid_handling_median = int(np.ceil(
        orders.loc[orders["order_handling_time_days"].ge(0), "order_handling_time_days"].median()
    ))
    orders.loc[
        orders["order_handling_time_days"].lt(0), "order_handling_time_days"
    ] = valid_handling_median
    orders["delivery_time_days"] = np.ceil(
        (orders["order_delivered_customer_dt"] - orders["order_purchase_dt"])
        .dt.total_seconds().div(86400)
    ).astype("Int64")
    orders["carrier_time_days"] = np.ceil(
        (orders["order_delivered_customer_dt"] - orders["order_delivered_carrier_dt"])
        .dt.total_seconds().div(86400)
    ).astype("Int64")
    valid_carrier_median = int(np.ceil(
        orders.loc[orders["carrier_time_days"].ge(0), "carrier_time_days"].median()
    ))
    orders.loc[orders["carrier_time_days"].lt(0), "carrier_time_days"] = valid_carrier_median
    orders["is_late_delivery"] = pd.Series(pd.NA, index=orders.index, dtype="boolean")
    delivered = (
        orders["order_status"].eq("delivered")
        & orders["order_delivered_customer_dt"].notna()
        & orders["order_estimated_delivery_dt"].notna()
    )
    orders.loc[delivered, "is_late_delivery"] = orders.loc[
        delivered, "order_delivered_customer_dt"
    ].gt(orders.loc[delivered, "order_estimated_delivery_dt"])
    orders["is_delivered"] = orders["order_status"].eq("delivered")

    tables["orders"] = orders.reset_index(drop=True)
    tables["reviews"] = reviews.reset_index(drop=True)
    tables["products"] = products.reset_index(drop=True)
    tables["cleaning_audit"] = pd.DataFrame({
        "measure": ["carrier_timestamp_fills", "customer_delivery_timestamp_fills"],
        "count": [int(carrier_missing.sum()), int(customer_missing.sum())],
    })
    return tables
