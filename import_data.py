import os
import json
import psycopg2
from psycopg2.extras import execute_values

DATA_DIR = "D:/SEM-7/1Pharmacy/DB_Dataset/data"

# Connect to PostgreSQL
conn = psycopg2.connect(
    dbname="pharmacydb",
    user="postgres",
    password="pranav222",
    host="localhost",
    port="5432"
)
cur = conn.cursor()

# ✅ Create table if it doesn't exist
cur.execute("""
CREATE TABLE IF NOT EXISTS medicines (
    id BIGINT PRIMARY KEY,
    sku_id TEXT,
    name TEXT,
    manufacturer_name TEXT,
    marketer_name TEXT,
    type TEXT,
    price NUMERIC,
    pack_size_label TEXT,
    rx_required JSONB,
    slug TEXT,
    short_composition TEXT,
    image_url TEXT,
    in_stock JSONB,
    quantity INT,
    is_discontinued BOOLEAN,
    available BOOLEAN
);
""")
conn.commit()

def import_json_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    rows = []
    for item in data:
        rows.append((
            item.get("id"),
            item.get("sku_id"),
            item.get("name"),
            item.get("manufacturer_name"),
            item.get("marketer_name"),
            item.get("type"),
            item.get("price"),
            item.get("pack_size_label"),
            json.dumps(item.get("rx_required")),
            item.get("slug"),
            item.get("short_composition"),
            item.get("image_url"),
            json.dumps(item.get("in_stock")),
            item.get("quantity"),
            item.get("is_discontinued"),
            item.get("available")
        ))

    sql = """
    INSERT INTO medicines (
        id, sku_id, name, manufacturer_name, marketer_name, type,
        price, pack_size_label, rx_required, slug, short_composition,
        image_url, in_stock, quantity, is_discontinued, available
    ) VALUES %s
    ON CONFLICT (id) DO NOTHING
    """
    execute_values(cur, sql, rows)
    conn.commit()
    print(f"✅ Imported {len(rows)} rows from {file_path}")

if __name__ == "__main__":
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json"):
            import_json_file(os.path.join(DATA_DIR, filename))

cur.close()
conn.close()
