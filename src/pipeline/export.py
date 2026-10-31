"""Stable compressed-CSV outputs consumed by the Streamlit application."""

import json
from pathlib import Path

import pandas as pd


def export_dashboard_outputs(outputs: dict[str, pd.DataFrame], output_dir: Path) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    monitoring_fields = [
        "order_date", "actual_placed_gmv", "expected_placed_gmv",
        "placed_gmv_residual", "robust_z", "abs_robust_z",
        "warning_cutoff", "critical_cutoff", "anomaly_level", "direction",
    ]
    commercial = outputs["daily_diagnostic_comparison"].merge(
        outputs["placed_gmv_daily_monitoring"][monitoring_fields],
        on="order_date", how="inner", validate="one_to_one",
    )
    commercial.to_csv(output_dir / "commercial_daily.csv.gz", index=False, compression="gzip")
    outputs["driver_attribution_long"].to_csv(
        output_dir / "driver_attribution_long.csv.gz", index=False, compression="gzip"
    )
    outputs["dimensional_rca_long"].to_csv(
        output_dir / "dimensional_rca_long.csv.gz", index=False, compression="gzip"
    )
    outputs["operational_health_7d"].to_csv(
        output_dir / "operational_health_7d.csv.gz", index=False, compression="gzip"
    )
    outputs["operational_duration_coverage_summary"].to_csv(
        output_dir / "operational_duration_coverage.csv", index=False
    )
    manifest = {
        "commercial_first_date": str(commercial["order_date"].min().date()),
        "commercial_latest_date": str(commercial["order_date"].max().date()),
        "commercial_dates": int(commercial["order_date"].nunique()),
        "operational_first_date": str(outputs["operational_health_7d"]["as_of_date"].min().date()),
        "operational_latest_date": str(outputs["operational_health_7d"]["as_of_date"].max().date()),
        "operational_dates": int(outputs["operational_health_7d"]["as_of_date"].nunique()),
        "driver_rows": int(len(outputs["driver_attribution_long"])),
        "dimensional_rows": int(len(outputs["dimensional_rca_long"])),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
