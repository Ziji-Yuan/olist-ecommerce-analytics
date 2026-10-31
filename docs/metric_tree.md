# Metric tree and attribution

## Business identities

```text
Placed GMV = Placed Orders × Placed AOV

Placed Orders = Active Customers × Orders per Active Customer
Active Customers = New Customers + Returning Customers

Placed AOV = Merchandise Value per Order + Freight per Order
Merchandise Value per Order = Items per Order × Average Item Price
```

These identities provide an interpretable hierarchy from the commercial outcome to customer, frequency, item, price, and freight components.

## Reference values

Each node receives an independent diagnostic reference: the median of up to eight strictly prior same-weekday observations, requiring at least four observations. These references are diagnostic comparators, not forecasts and not the STL expected value used for GMV anomaly detection.

## Symmetric allocation

For `Y = A × B`, the two-factor symmetric allocation is:

```text
C_A = (A₁ − A₀)(B₀ + B₁) / 2
C_B = (B₁ − B₀)(A₀ + A₁) / 2
```

where `0` denotes reference and `1` denotes actual. The allocation is equivalent to averaging the two possible factor-update orders, i.e. a two-factor Shapley value. For additive branches, each child's signed delta is its local contribution.

Nested local contributions are proportionally propagated through their parent's signed GMV contribution. The output preserves both local KPI-unit contributions and global dollar contributions so a customer-count change is never mislabeled as dollars.

## Reading shares and offsets

Contribution share is `global GMV contribution / driver GMV gap`. It is deliberately signed and unbounded.

Example: if Orders contribute `-$15K`, AOV contributes `+$5K`, and the net driver GMV gap is `-$10K`, the shares are 150% and −50%. Orders more than explain the net decline while AOV offsets part of it. This is valid reconciliation, not an error. When the net gap is near zero, contribution shares are suppressed in favor of dollar contributions.

## Dimensional continuation

After selecting a node, State and Category show the largest same-weekday diagnostic deviations. This locates concentration; it does not establish causality. Category distinct-order and distinct-customer slices may overlap and therefore need not add to the global total.
