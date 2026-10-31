# Data dictionary

This dictionary focuses on fields used by the analytical notebook or reproducible monitoring pipeline. It does not attempt to reproduce every field in the public dataset.

## Source fields

### Orders — `olist_orders_dataset.csv`

| Field | Meaning | Analytical use |
|---|---|---|
| `order_id` | Marketplace order identifier | Order grain, joins, and order counts |
| `customer_id` | Order-specific customer key | Join to the customer table |
| `order_status` | Final recorded order status | Delivered retrospective measures and cleaning eligibility |
| `order_purchase_timestamp` | Order placement time | Commercial event date and customer lifecycle |
| `order_approved_at` | Payment approval time | Timestamp-quality investigation and earlier handling-time fields |
| `order_delivered_carrier_date` | Carrier handoff time | Fulfillment event date and fulfillment duration endpoint |
| `order_delivered_customer_date` | Customer delivery time | Delivery event date and carrier-transit endpoint |
| `order_estimated_delivery_date` | Promised delivery date | Late-delivery classification |

### Order items — `olist_order_items_dataset.csv`

| Field | Meaning | Analytical use |
|---|---|---|
| `order_id` | Order identifier | Join to order context |
| `order_item_id` | Item sequence within an order | Item count |
| `product_id` | Product identifier | Category drill-down |
| `seller_id` | Seller identifier | Notebook exploration |
| `price` | Merchandise value of the item | Merchandise GMV and average item price |
| `freight_value` | Freight charged for the item | Freight contribution and Placed GMV |
| `shipping_limit_date` | Seller shipping deadline | Notebook logistics exploration |

### Customers — `olist_customers_dataset.csv`

| Field | Meaning | Analytical use |
|---|---|---|
| `customer_id` | Order-specific customer key | Join to orders |
| `customer_unique_id` | Cross-order customer identity | Active, new, and returning customers |
| `customer_city` | Recorded customer city | Notebook exploration |
| `customer_state` | Recorded customer state | State dimensional RCA |

### Products — `olist_products_dataset.csv`

| Field | Meaning | Analytical use |
|---|---|---|
| `product_id` | Product identifier | Join to item facts |
| `product_category_name` | Original product category | Category dimensional RCA |
| `product_weight_g` | Product weight | Notebook quality investigation |
| `product_length_cm`, `product_height_cm`, `product_width_cm` | Package dimensions | Notebook quality investigation |

### Reviews — `olist_order_reviews_dataset.csv`

| Field | Meaning | Analytical use |
|---|---|---|
| `review_id` | Review event identifier | Distinct review-event counts |
| `order_id` | Reviewed order | Join to order context |
| `review_score` | Customer rating from 1 to 5 | Average score and negative-review rate |
| `review_creation_date` | Review event date | Customer Experience event cohort |
| `review_answer_timestamp` | Review answer time | Notebook exploration |

### Payments — `olist_order_payments_dataset.csv`

| Field | Meaning | Analytical use |
|---|---|---|
| `order_id` | Order identifier | Payment-to-order reconciliation in the notebook |
| `payment_type` | Payment method | Notebook customer/payment analysis |
| `payment_installments` | Installment count | Notebook cleaning and analysis |
| `payment_value` | Recorded payment amount | Payment reconciliation, not primary Placed GMV |

### Sellers, geolocation, and category translation

`seller_id` supports notebook seller exploration. Geolocation prefixes, latitude/longitude, city, and state support geographic quality checks. `product_category_name` and `product_category_name_english` provide the optional category translation mapping. The production dashboard uses the original product category recorded in the product table.

## Derived business metrics

| Metric | Definition |
|---|---|
| Placed GMV | Sum of item `price + freight_value` for orders with an available item-derived order value, regardless of final status |
| Placed Orders | Distinct eligible orders included in Placed GMV |
| Placed AOV | Placed GMV / Placed Orders |
| Active Customers | Distinct `customer_unique_id` with an eligible placed order on the date |
| New Customers | Active customers whose first eligible purchase date is the selected date |
| Returning Customers | Active customers whose first eligible purchase occurred before the selected date |
| Orders per Active Customer | Placed Orders / Active Customers |
| Merchandise Value per Order | Merchandise value / Placed Orders |
| Freight per Order | Freight value / Placed Orders |
| Items per Order | Item count / Placed Orders |
| Average Item Price | Merchandise value / Item count |
| Fulfillment Time | Carrier handoff timestamp − purchase timestamp, in continuous days |
| Carrier Transit Time | Customer delivery timestamp − carrier handoff timestamp, in continuous days |
| Late Delivery Rate | Delivered events after the estimated delivery timestamp / eligible delivered events |
| Average Review Score | Mean review score for distinct review events in the event window |
| Negative Review Rate | Reviews with score ≤ 2 / distinct eligible reviews |

### Two different baselines

**STL Expected GMV** is a leak-free one-step expected value used only for GMV anomaly scoring. **Diagnostic Reference** is the median of up to eight prior observations on the same weekday, with at least four observations required. It supports metric-tree diagnostics and is not the STL expectation.
