# Dashboard guide

The dashboard follows a five-level decision flow.

1. **What happened?** Placed GMV, Orders, AOV, and Active Customer cards summarize the selected date.
2. **Is it abnormal?** Actual GMV is compared with leak-free STL Expected GMV and classified as Normal, Warning, or Critical with a separate positive/negative direction.
3. **Why did it move?** The interactive attribution tree displays signed contribution shares and dollar contributions. Hover reveals actual, diagnostic reference, KPI deviation, and attribution details.
4. **Where was movement concentrated?** Clicking a tree node updates State and Category Top 3/5/10 diverging bars from the prepared dimensional RCA output.
5. **How healthy are operations?** Fulfillment, carrier, and customer-experience metrics compare Current 7D with Previous 7D using metric-specific business color semantics.

## Point-in-time behavior

Completed Date is the information cutoff for the entire page. Commercial cards show that exact date. The GMV time series never displays a later date. Operational Current 7D ends on the selected date, and Previous 7D ends seven days earlier.

## Baseline labels

GMV anomaly monitoring uses **STL Expected GMV**. Metric-tree KPI deltas and dimensional bars use the **Diagnostic Reference**. They answer different questions and are labeled separately.

## Running the app

From the repository root:

```bash
streamlit run app.py
```

The committed `dashboard_data/` artifacts allow the app to run without raw source files or a pipeline refresh.
