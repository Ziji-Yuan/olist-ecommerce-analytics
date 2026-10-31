"""Run the complete V1 full-refresh Olist analytical pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.pipeline.attribution import build_dimensional_rca, build_driver_attribution
from src.pipeline.cleaning import clean_source_tables
from src.pipeline.commercial_monitoring import build_gmv_monitoring
from src.pipeline.export import export_dashboard_outputs
from src.pipeline.ingest import load_raw_data
from src.pipeline.metrics import (
    build_daily_business_mart,
    build_daily_diagnostic_metrics,
    build_diagnostic_comparison,
)
from src.pipeline.operational_health import build_operational_health
from src.pipeline.transformation import build_analysis_tables
from src.pipeline.validation import (
    compare_with_dashboard_reference,
    validate_pipeline_outputs,
    validate_raw_inputs,
)


PROJECT_ROOT = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-dir", type=Path, default=PROJECT_ROOT / "data" / "raw",
        help="Directory containing the nine Olist-format CSV files.",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=PROJECT_ROOT / "dashboard_data",
        help="Destination for dashboard-ready compressed CSV outputs.",
    )
    parser.add_argument(
        "--reference-dir", type=Path,
        help="Optional validated dashboard-data directory for representative reconciliation.",
    )
    return parser.parse_args()


def run_full_refresh(raw_dir: Path, output_dir: Path) -> dict:
    print("[1/9] Ingesting Olist source files")
    raw = load_raw_data(raw_dir)
    validate_raw_inputs(raw)
    print("[2/9] Applying validated cleaning decisions")
    cleaned = clean_source_tables(raw)
    print("[3/9] Building reusable order-level analytical tables")
    analysis = build_analysis_tables(cleaned)
    print("[4/9] Building daily business mart and metric-tree inputs")
    mart, _ = build_daily_business_mart(analysis["orders_analysis"], analysis["items"])
    diagnostics, eligible_orders = build_daily_diagnostic_metrics(
        analysis["orders_analysis"], analysis["items"], mart
    )
    comparison = build_diagnostic_comparison(diagnostics)
    print("[5/9] Running leak-free walk-forward GMV monitoring")
    monitoring = build_gmv_monitoring(diagnostics)
    print("[6/9] Calculating symmetric/Shapley metric-tree attribution")
    gmv_attribution, driver_attribution = build_driver_attribution(comparison, monitoring)
    print("[7/9] Building State and Category dimensional RCA")
    dimensions = build_dimensional_rca(
        eligible_orders, analysis["orders_analysis"], analysis["items"],
        analysis["customers"], analysis["products"], diagnostics["order_date"], monitoring,
    )
    print("[8/9] Building event-time Operational Health windows")
    operations, duration_coverage = build_operational_health(
        analysis["orders"], analysis["reviews"], diagnostics["order_date"]
    )
    outputs = {
        "mart_daily_business_kpi": mart,
        "daily_diagnostic_metrics": diagnostics,
        "daily_diagnostic_comparison": comparison,
        "placed_gmv_daily_monitoring": monitoring,
        "gmv_driver_attribution": gmv_attribution,
        "driver_attribution_long": driver_attribution,
        "dimensional_rca_long": dimensions,
        "operational_health_7d": operations,
        "operational_duration_coverage_summary": duration_coverage,
    }
    validate_pipeline_outputs(outputs)
    print("[9/9] Exporting dashboard-ready datasets")
    export_dashboard_outputs(outputs, output_dir)
    return outputs


def main() -> None:
    args = parse_args()
    outputs = run_full_refresh(args.raw_dir, args.output_dir)
    if args.reference_dir:
        result = compare_with_dashboard_reference(outputs, args.reference_dir)
        print("Representative notebook reconciliation:", result)
    print(f"Full refresh complete: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
