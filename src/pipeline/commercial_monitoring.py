"""Leak-free walk-forward STL and dynamic Robust-Z policy from Section 4.4."""

import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL


STL_PERIOD = 7
CALIBRATION_DAYS = 365
WARNING_PERCENTILE = 0.95
CRITICAL_PERCENTILE = 0.975
EXTREME_PERCENTILE = 0.99


def stl_one_step_expected(value_history: pd.Series, period: int = STL_PERIOD) -> float:
    if len(value_history) < 8 * period:
        raise ValueError("STL one-step scoring requires at least eight seasonal periods")
    fitted = STL(value_history, period=period, robust=True).fit()
    return float(fitted.trend.iloc[-1]) + float(fitted.seasonal.iloc[-period])


def build_compatible_calibration_residuals(
    calibration_series: pd.Series,
    period: int = STL_PERIOD,
) -> pd.DataFrame:
    rows = []
    for position in range(8 * period, len(calibration_series)):
        history = calibration_series.iloc[:position].copy()
        actual = float(calibration_series.iloc[position])
        expected = stl_one_step_expected(history, period)
        rows.append({
            "order_date": calibration_series.index[position],
            "actual_value": actual,
            "expected_value": expected,
            "residual": actual - expected,
            "history_end_date": history.index.max(),
        })
    return pd.DataFrame(rows)


def run_dynamic_gmv_monitoring(
    full_series: pd.Series,
    monitoring_dates: pd.Series,
    calibration_residuals: pd.Series,
    period: int = STL_PERIOD,
) -> pd.DataFrame:
    rows = []
    expanding_residuals = list(pd.Series(calibration_residuals, dtype=float))
    initial_history_count = len(expanding_residuals)
    for row_number, monitoring_date in enumerate(pd.to_datetime(monitoring_dates)):
        history = full_series.loc[full_series.index < monitoring_date].copy()
        expected = stl_one_step_expected(history, period)
        residual_history = pd.Series(expanding_residuals, dtype=float)
        median = residual_history.median()
        mad = residual_history.sub(median).abs().median()
        sigma = 1.4826 * mad
        if not np.isfinite(sigma) or sigma <= 0:
            raise ValueError(f"Invalid historical MAD before {monitoring_date.date()}")
        historical_abs_z = residual_history.sub(median).div(sigma).abs()
        warning = historical_abs_z.quantile(WARNING_PERCENTILE)
        critical = historical_abs_z.quantile(CRITICAL_PERCENTILE)
        extreme = historical_abs_z.quantile(EXTREME_PERCENTILE)
        actual = float(full_series.loc[monitoring_date])
        residual = actual - expected
        robust_z = (residual - median) / sigma
        abs_robust_z = abs(robust_z)
        level = "Critical" if abs_robust_z >= critical else (
            "Warning" if abs_robust_z >= warning else "Normal"
        )
        direction = "Positive" if residual > 0 else "Negative" if residual < 0 else "Neutral"
        rows.append({
            "order_date": monitoring_date,
            "actual_placed_gmv": actual,
            "expected_placed_gmv": expected,
            "placed_gmv_residual": residual,
            "historical_residual_median": median,
            "historical_residual_mad": mad,
            "historical_robust_sigma": sigma,
            "robust_z": robust_z,
            "abs_robust_z": abs_robust_z,
            "warning_cutoff": warning,
            "critical_cutoff": critical,
            "extreme_reference_cutoff": extreme,
            "anomaly_level": level,
            "direction": direction,
            "history_end_date": history.index.max(),
            "residual_history_count": len(residual_history),
            "threshold_history_count": len(historical_abs_z),
        })
        if len(residual_history) != initial_history_count + row_number:
            raise AssertionError("Residual history did not expand by exactly one day")
        expanding_residuals.append(residual)
    return pd.DataFrame(rows)


def build_gmv_monitoring(daily_metrics: pd.DataFrame) -> pd.DataFrame:
    daily = daily_metrics[["order_date", "placed_gmv"]].sort_values("order_date").reset_index(drop=True)
    if len(daily) <= CALIBRATION_DAYS:
        raise ValueError("Insufficient history for the fixed 365-day calibration split")
    full_series = daily.set_index("order_date")["placed_gmv"].astype(float)
    full_series.index.freq = "D"
    calibration = full_series.iloc[:CALIBRATION_DAYS].copy()
    calibration_residuals = build_compatible_calibration_residuals(calibration)["residual"]
    monitoring_dates = daily.iloc[CALIBRATION_DAYS:]["order_date"]
    result = run_dynamic_gmv_monitoring(
        full_series, monitoring_dates, calibration_residuals, STL_PERIOD
    )
    if not result["history_end_date"].lt(result["order_date"]).all():
        raise AssertionError("GMV monitoring contains look-ahead leakage")
    return result
