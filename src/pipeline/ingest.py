"""Read the Olist source files from a repository-relative raw directory."""

from pathlib import Path

import pandas as pd


SOURCE_FILES = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}


def load_raw_data(raw_dir: Path) -> dict[str, pd.DataFrame]:
    """Load all source tables expected by the analytical notebook."""
    raw_dir = Path(raw_dir)
    missing = [name for name in SOURCE_FILES.values() if not (raw_dir / name).is_file()]
    if missing:
        formatted = "\n  - ".join(missing)
        raise FileNotFoundError(
            f"Missing Olist source files in {raw_dir.resolve()}:\n  - {formatted}\n"
            "See data/README.md for download and placement instructions."
        )
    return {
        name: pd.read_csv(raw_dir / filename)
        for name, filename in SOURCE_FILES.items()
    }
