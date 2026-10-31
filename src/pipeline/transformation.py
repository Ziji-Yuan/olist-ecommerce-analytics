"""Order-level transformations shared by commercial and operational outputs."""

import pandas as pd


def build_analysis_tables(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    orders = tables["orders"]
    items = tables["items"]
    reviews = tables["reviews"]

    order_item_values = (
        items.groupby("order_id", as_index=False)
        .agg(
            item_count=("order_item_id", "count"),
            product_value=("price", "sum"),
            freight_value=("freight_value", "sum"),
        )
    )
    order_item_values["order_value"] = (
        order_item_values["product_value"] + order_item_values["freight_value"]
    )
    order_reviews = reviews.groupby("order_id", as_index=False).agg(
        review_score=("review_score", "mean")
    )
    orders_analysis = (
        orders.merge(
            order_item_values[["order_id", "item_count", "freight_value", "order_value"]],
            on="order_id", how="left", validate="one_to_one",
        )
        .merge(
            tables["customers"][["customer_id", "customer_unique_id"]],
            on="customer_id", how="left", validate="many_to_one",
        )
        .merge(order_reviews, on="order_id", how="left", validate="one_to_one")
    )
    if orders_analysis["order_id"].duplicated().any():
        raise AssertionError("Order analysis table must remain one row per order")
    return {
        "orders": orders,
        "items": items,
        "customers": tables["customers"],
        "products": tables["products"],
        "reviews": reviews,
        "orders_analysis": orders_analysis,
    }
