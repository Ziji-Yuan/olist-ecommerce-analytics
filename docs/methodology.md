# Methodology

The product separates two questions. **Commercial Performance** asks whether placed demand is unusual and where the movement is concentrated. **Operational Health** tracks recent fulfillment, carrier, and customer-experience conditions. Operational movements are not presented as causal explanations of GMV anomalies.

## Commercial Performance Monitoring

```mermaid
flowchart LR
    A[Placed GMV] --> B[Walk-forward STL]
    B --> C[Expected GMV]
    C --> D[Residual]
    D --> E[MAD-based Robust Z]
    E --> F[Historical dynamic thresholds]
    F --> G[Normal / Warning / Critical]
```

Placed GMV is daily item price plus freight for the project's eligible placed-order population. The first 365 calendar days form the calibration period. Starting after a minimum of eight weekly periods, calibration residuals are built with one-step, history-only STL fits using `period=7` and `robust=True`.

For every monitoring date *t*, expected GMV is estimated using observations strictly before *t*. The residual median, MAD, robust scale, and empirical 95th/97.5th/99th-percentile cutoffs also use residuals available before *t*. The current day is scored only after its expectation and historical distribution are fixed. This prevents look-ahead leakage.

The absolute Robust Z-score determines magnitude and severity; the residual sign supplies direction. A large percentage deviation does not necessarily imply a statistical anomaly, and an anomaly may be positive or negative.

## Metric tree

```text
Placed GMV
├── Placed Orders
│   ├── Active Customers
│   │   ├── New Customers
│   │   └── Returning Customers
│   └── Orders per Active Customer
└── Placed AOV
    ├── Merchandise Value per Order
    │   ├── Items per Order
    │   └── Average Item Price
    └── Freight per Order
```

### Diagnostic reference

Every metric-tree KPI uses the median of up to eight strictly prior observations on the same weekday. At least four historical observations are required. These independent diagnostic references are intentionally different from STL Expected GMV.

### Symmetric / Shapley attribution

For a two-factor identity `Y = A × B`, the parent gap is allocated symmetrically:

```text
Contribution(A) = (A_actual − A_reference) × (B_reference + B_actual) / 2
Contribution(B) = (B_actual − B_reference) × (A_reference + A_actual) / 2
```

This is equivalent to a two-factor Shapley allocation. Additive branches use direct signed differences. Nested contributions are propagated through the hierarchy to GMV while preserving reconciliation where the local parent gap is non-zero.

Contributions are signed. A driver may reinforce the net movement or offset it. Consequently, contribution shares may exceed 100% or be negative; they are never normalized into a cosmetic 0–100% range. When the GMV gap is near zero, dollars are more interpretable than contribution shares.

### Dimensional RCA

State and product-category views apply the same history-only same-weekday reference to each dimensional series and rank by absolute KPI delta. They show **where movement is concentrated**, not causal proof. Category order/customer measures can be non-additive because a single order or customer can span multiple categories; category totals are not forced to reconcile with the global KPI.

## Operational Health

Operational Health compares a trailing Current 7D window with the immediately preceding Previous 7D window. It is period-over-period monitoring, not Robust-Z anomaly detection.

- **Fulfillment:** carrier handoff orders, median fulfillment time, P90 fulfillment time.
- **Carrier Performance:** delivered orders, median/P90 carrier transit time, late-delivery rate.
- **Customer Experience:** reviews received, average review score, negative-review rate.

Cohorts use their natural event time: carrier handoff, customer delivery, or review creation. Durations are calculated continuously from timestamps. Negative timestamp-order durations are excluded from Median/P90 calculations, but valid event timestamps remain in volume counts. Historical duration coverage is approximately 99.83% for fulfillment and 99.98% for carrier transit.

Cancellation Rate is excluded from point-in-time Operational Health. Olist supplies final cancellation status but no reliable cancellation-event timestamp, so using final status for recent historical cohorts would introduce look-ahead bias.
