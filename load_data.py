import polars as pl
from sqlalchemy import create_engine

df = pl.read_csv(
    r"D:\OnlineRetail.csv\OnlineRetail.csv",
    encoding="windows-1252",   # dataset gốc thường lưu ở encoding này, không phải UTF-8
    infer_schema_length=10000,
)

df = df.rename({
    "InvoiceNo": "invoice_no",
    "StockCode": "stock_code",
    "Description": "description",
    "Quantity": "quantity",
    "InvoiceDate": "invoice_date",
    "UnitPrice": "unit_price",
    "CustomerID": "customer_id",
    "Country": "country",
})

engine = create_engine("postgresql://cube:cubepass@localhost:5432/demo_ecommerce")
df.write_database("online_retail_raw", engine, if_table_exists="replace")
print("Đã nạp", df.height, "dòng vào Postgres")