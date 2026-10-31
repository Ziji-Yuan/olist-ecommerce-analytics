# Data setup

This project uses the [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), a historical marketplace dataset covering orders, items, customers, products, payments, logistics, sellers, and reviews.

Raw extracts are intentionally excluded from Git because they are third-party source data and are reproducibly obtainable from Kaggle. Download and unzip the dataset, then place these files in `data/raw/`:

- `olist_orders_dataset.csv`
- `olist_order_items_dataset.csv`
- `olist_order_payments_dataset.csv`
- `olist_order_reviews_dataset.csv`
- `olist_customers_dataset.csv`
- `olist_products_dataset.csv`
- `olist_sellers_dataset.csv`
- `olist_geolocation_dataset.csv`
- `product_category_name_translation.csv`

From the repository root, regenerate all analytical outputs with:

```bash
python run_pipeline.py
```

The pipeline validates the source schema, applies the notebook's cleaning decisions, performs a full analytical refresh, and writes compressed dashboard artifacts to `dashboard_data/`.

The committed prepared datasets are sufficient to run the dashboard without downloading the raw data.
