"""Small structural checks for source and produced analytical tables."""

from collections.abc import Mapping
from pathlib import Path

import numpy as np
import pandas as pd


EXPECTED_COLUMNS = {
    "orders": {
        "order_id", "customer_id", "order_status", "order_purchase_timestamp",
        "order_approved_at", "order_delivered_carrier_date",
        "order_delivered_customer_date", "order_estimated_delivery_date",
    },
    "items": {
        "order_id", "order_item_id", "product_id", "seller_id", "price",
        "freight_value", "shipping_limit_date",
    },
    "customers": {
        "customer_id", "customer_unique_id", "customer_city", "customer_state",
    },
    "products": {"product_id", "product_category_name"},
    "reviews": {"review_id", "order_id", "review_score", "review_creation_date"},
    "payments": {"order_id", "payment_type", "payment_installments", "payment_value"},
    "sellers": {"seller_id"},
    "geolocation": {"geolocation_zip_code_prefix"},
    "category_translation": {"product_category_name", "product_category_name_english"},
}


def validate_raw_inputs(tables: Mapping[str, pd.DataFrame]) -> None:
    """Fail early on missing schema or broken natural-key assumptions."""
    missing_tables = set(EXPECTED_COLUMNS).difference(tables)
    if missing_tables:
        raise ValueError(f"Missing loaded tables: {sorted(missing_tables)}")
    for name, expected in EXPECTED_COLUMNS.items():
        missing = expected.difference(tables[name].columns)
        if missing:
            raise ValueError(f"{name} is missing columns: {sorted(missing)}")
    for table_name, key in (
        ("orders", "order_id"),
        ("customers", "customer_id"),
        ("products", "product_id"),
    ):
        if tables[table_name][key].isna().any():
            raise ValueError(f"{table_name}.{key} contains nulls")
        if tables[table_name][key].duplicated().any():
            raise ValueError(f"{table_name}.{key} must be unique")


def validate_pipeline_outputs(outputs: Mapping[str, pd.DataFrame]) -> None:
    """Representative contracts only; this is not an audit framework."""
    monitoring = outputs["placed_gmv_daily_monitoring"]
    diagnostics = outputs["daily_diagnostic_comparison"]
    drivers = outputs["driver_attribution_long"]
    dimensions = outputs["dimensional_rca_long"]
    operations = outputs["operational_health_7d"]

    if monitoring["order_date"].duplicated().any():
        raise AssertionError("GMV monitoring is not one row per date")
    if not monitoring["anomaly_level"].isin(["Normal", "Warning", "Critical"]).all():
        raise AssertionError("Unexpected anomaly classification")
    if diagnostics["order_date"].duplicated().any():
        raise AssertionError("Diagnostic output is not one row per date")
    if not np.isfinite(drivers["global_gmv_contribution"].dropna()).all():
        raise AssertionError("Non-finite attribution contribution")
    top = drivers.loc[drivers["driver_level"].eq("top_level")]
    reconciliation = top.groupby("order_date")["global_gmv_contribution"].sum()
    target = top.groupby("order_date")["driver_gmv_gap"].first()
    if not np.allclose(reconciliation, target, atol=1e-8):
        raise AssertionError("Top-level contributions do not reconcile")
    if dimensions[["order_date", "dimension", "dimension_value", "metric"]].duplicated().any():
        raise AssertionError("Dimensional RCA key is not unique")
    if operations.groupby("as_of_date")["metric"].nunique().ne(10).any():
        raise AssertionError("Operational metric coverage is incomplete")


def compare_with_dashboard_reference(
    outputs: Mapping[str, pd.DataFrame],
    reference_dir: Path,
) -> dict[str, str]:
    """Compare only representative final outputs with the validated artifacts."""
    reference_dir = Path(reference_dir)
    monitoring_reference = pd.read_csv(
        reference_dir / "commercial_daily.csv.gz", parse_dates=["order_date"]
    )
    monitoring_actual = outputs["placed_gmv_daily_monitoring"]
    monitoring_columns = [
        "order_date", "actual_placed_gmv", "expected_placed_gmv", "robust_z",
        "warning_cutoff", "critical_cutoff", "anomaly_level", "direction",
    ]
    pd.testing.assert_frame_equal(
        monitoring_actual[monitoring_columns].reset_index(drop=True),
        monitoring_reference[monitoring_columns].reset_index(drop=True),
        check_dtype=False, rtol=1e-10, atol=1e-8,
    )

    diagnostic_reference = monitoring_reference
    diagnostic_actual = outputs["daily_diagnostic_comparison"].loc[
        outputs["daily_diagnostic_comparison"]["order_date"].isin(
            diagnostic_reference["order_date"]
        )
    ]
    diagnostic_columns = [
        "order_date", "placed_gmv_actual", "placed_order_count_actual",
        "placed_aov_reference", "active_customers_reference",
    ]
    pd.testing.assert_frame_equal(
        diagnostic_actual[diagnostic_columns].reset_index(drop=True),
        diagnostic_reference[diagnostic_columns].reset_index(drop=True),
        check_dtype=False, rtol=1e-10, atol=1e-8,
    )

    driver_reference = pd.read_csv(
        reference_dir / "driver_attribution_long.csv.gz", parse_dates=["order_date"]
    )
    driver_actual = outputs["driver_attribution_long"]
    driver_columns = [
        "order_date", "driver_level", "driver_metric", "driver_gmv_gap",
        "global_gmv_contribution", "global_gmv_contribution_pct",
    ]
    pd.testing.assert_frame_equal(
        driver_actual[driver_columns].reset_index(drop=True),
        driver_reference[driver_columns].reset_index(drop=True),
        check_dtype=False, rtol=1e-10, atol=1e-8,
    )

    dimensional_reference = pd.read_csv(
        reference_dir / "dimensional_rca_long.csv.gz",
        usecols=["order_date", "dimension", "dimension_value", "metric"],
        low_memory=False,
    )
    dimensions = outputs["dimensional_rca_long"]
    if len(dimensions) != len(dimensional_reference):
        raise AssertionError("Dimensional RCA row count differs from notebook output")
    if dimensions["order_date"].nunique() != dimensional_reference["order_date"].nunique():
        raise AssertionError("Dimensional RCA date coverage differs from notebook output")

    operational_reference = pd.read_csv(
        reference_dir / "operational_health_7d.csv.gz", parse_dates=["as_of_date"]
    )
    operational_actual = outputs["operational_health_7d"]
    operational_columns = [
        "as_of_date", "metric", "current_7d_value", "previous_7d_value", "change_value"
    ]
    pd.testing.assert_frame_equal(
        operational_actual[operational_columns].reset_index(drop=True),
        operational_reference[operational_columns].reset_index(drop=True),
        check_dtype=False, rtol=1e-10, atol=1e-8,
    )
    return {
        "gmv_monitoring": "MATCH",
        "daily_diagnostics": "MATCH",
        "driver_attribution": "MATCH",
        "dimensional_coverage": "MATCH",
        "operational_health": "MATCH",
    }
