"""Run the same bronze -> silver -> gold logic locally with pandas.

No Azure account needed. Useful to understand the transformations and to
sanity-check data quality rules before running the Spark notebooks.

Usage:
    python src/local_pipeline.py
Outputs go to ./output/{bronze,silver,gold}/
"""
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "sample_orders.csv"
OUT = ROOT / "output"


def bronze(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)  # keep everything as received
    df["_ingested_at"] = datetime.now(timezone.utc).isoformat()
    df["_source_file"] = path.name
    return df


def silver(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["order_id"] = pd.to_numeric(df["order_id"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce").dt.date

    required = ["order_id", "customer_id", "quantity", "unit_price", "order_date"]
    before = len(df)
    df = df.dropna(subset=required)
    df = df[(df["quantity"] > 0) & (df["unit_price"] > 0)]
    df = df.sort_values("_ingested_at", ascending=False).drop_duplicates("order_id")
    df["order_id"] = df["order_id"].astype("int64")
    df["quantity"] = df["quantity"].astype("int64")
    df["total_amount"] = (df["quantity"] * df["unit_price"]).round(2)
    print(f"Silver: kept {len(df)} of {before} rows (dropped invalid/duplicate)")
    return df.sort_values("order_id").reset_index(drop=True)


def gold(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    daily_sales = (
        df.groupby("order_date")
        .agg(orders=("order_id", "nunique"), units_sold=("quantity", "sum"), revenue=("total_amount", "sum"))
        .round(2)
        .reset_index()
    )
    by_category_country = (
        df.groupby(["category", "country"])
        .agg(orders=("order_id", "nunique"), revenue=("total_amount", "sum"))
        .round(2)
        .reset_index()
        .sort_values("revenue", ascending=False)
    )
    top_customers = (
        df.groupby("customer_id")
        .agg(orders=("order_id", "nunique"), lifetime_value=("total_amount", "sum"))
        .round(2)
        .reset_index()
        .sort_values("lifetime_value", ascending=False)
    )
    return {
        "daily_sales": daily_sales,
        "sales_by_category_country": by_category_country,
        "top_customers": top_customers,
    }


def main() -> None:
    for layer in ("bronze", "silver", "gold"):
        (OUT / layer).mkdir(parents=True, exist_ok=True)

    b = bronze(SOURCE)
    b.to_csv(OUT / "bronze" / "sample_orders.csv", index=False)

    s = silver(b)
    s.to_csv(OUT / "silver" / "sample_orders.csv", index=False)

    for name, table in gold(s).items():
        table.to_csv(OUT / "gold" / f"{name}.csv", index=False)
        print(f"\n== gold/{name} ==")
        print(table.to_string(index=False))


if __name__ == "__main__":
    main()
