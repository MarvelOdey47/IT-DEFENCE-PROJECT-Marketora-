from sqlalchemy import inspect, text

from app import app
from backend.database import db
import backend.models  

# table -> {column: DDL type/default}
NEW_COLUMNS = {
    "users": {
        "suspended": "BOOLEAN NOT NULL DEFAULT FALSE",
        "avatar_url": "VARCHAR(300)",
    },
    "products": {
        "old_price": "NUMERIC(12,2)",
        "category_id": "INTEGER REFERENCES categories(id)",
        "stock": "INTEGER NOT NULL DEFAULT 0",
        "brand": "VARCHAR(80)",
        "sku": "VARCHAR(60)",
        "condition": "VARCHAR(30)",
        "color": "VARCHAR(60)",
        "size": "VARCHAR(60)",
        "weight": "NUMERIC(8,2)",
        "warranty": "VARCHAR(120)",
        "key_features": "TEXT",
        "specifications": "TEXT",
        "box_contents": "TEXT",
        "return_policy": "VARCHAR(160)",
        "tags": "VARCHAR(255)",
        "rating": "DOUBLE PRECISION NOT NULL DEFAULT 0",
        "rating_count": "INTEGER NOT NULL DEFAULT 0",
        "is_active": "BOOLEAN NOT NULL DEFAULT TRUE",
    },
    "orders": {
        "shipping_name": "VARCHAR(120)",
        "shipping_phone": "VARCHAR(40)",
        "shipping_address": "VARCHAR(300)",
        "shipping_city": "VARCHAR(80)",
    },
}


WIDEN = [
    "ALTER TABLE products ALTER COLUMN name TYPE VARCHAR(160)",
    "ALTER TABLE products ALTER COLUMN image_url TYPE VARCHAR(500)",
    "ALTER TABLE products ALTER COLUMN price TYPE NUMERIC(12,2)",
    "ALTER TABLE orders ALTER COLUMN total TYPE NUMERIC(12,2)",
    "ALTER TABLE order_items ALTER COLUMN price TYPE NUMERIC(12,2)",
]


def run():
    db.create_all() 

    insp = inspect(db.engine)
    for table, cols in NEW_COLUMNS.items():
        existing = {c["name"] for c in insp.get_columns(table)}
        for name, ddl in cols.items():
            if name not in existing:
                db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN "{name}" {ddl}'))
                print(f"Added {table}.{name}")

    for stmt in WIDEN:
        db.session.execute(text(stmt))

    db.session.commit()
    print("Schema is up to date.")


if __name__ == "__main__":
    with app.app_context():
        run()
