#  1Pharmacy Network Hackathon – Postgres DB

This project implements a **high-performance medicine search system** on top of **PostgreSQL** and **FastAPI**, optimized for real-time lookups in large datasets (~280k+ records).  

The system supports:
- **Prefix search** (e.g., `Ava` → `Avastin`)
- **Substring search** (e.g., `Injection` → all medicines containing “Injection”)
- **Full-text search** (e.g., `cancer` → all cancer-related medicines)
- **Fuzzy search** (typo tolerance, e.g., `Avastn` → `Avastin`)
- **Benchmark runner** (`/run-benchmark`) → executes all queries in `benchmark_queries.json` and generates `submission.json`.

---

## Project Structure
```
.
├── schema.sql             # SQL schema & indexes
├── import_data.py         # Data import script (JSON → PostgreSQL)
├── main.py                # FastAPI application with 5 endpoints (search + benchmark)
├── benchmark_queries.json # Benchmark queries input
├── benchmark.md           # Benchmarking results (latency, throughput, index usage)
├── submission.json        # Final output for benchmark queries
├── README.md              # Run instructions (this file)
```

---

## 1. Setup Instructions

### 1.1 Install Dependencies
- Install [PostgreSQL 17+](https://www.postgresql.org/download/).
- Install [Python 3.9+](https://www.python.org/downloads/).
- Install required libraries:
```bash
pip install fastapi uvicorn asyncpg psycopg2-binary python-dotenv
```

### 1.2 Database Setup
1. Create a database:
```sql
CREATE DATABASE pharmacydb;
```

2. Run the schema to create table and indexes:
```bash
psql -U postgres -d pharmacydb -f schema.sql
```

3. Import dataset:
```bash
python import_data.py
```

This loads ~280k+ medicine records (from JSON files `a.json`–`z.json`) into PostgreSQL.

---

## 2. Running the API

Start the FastAPI server:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2.1 Endpoints
- **Prefix Search:**  
  `GET /search/prefix?q=Ava`
- **Substring Search:**  
  `GET /search/substring?q=Injection`
- **Fuzzy Search:**  
  `GET /search/fuzzy?q=Avastn`
- **Full-text Search:**  
  `GET /search/fulltext?q=cancer`
- **Benchmark Runner:**  
  `POST /run-benchmark`  
  - Reads queries from `benchmark_queries.json`  
  - Executes all (prefix, substring, fuzzy, full-text)  
  - Saves results into `submission.json`  
  - Returns results inline in Swagger response  

### 2.2 API Docs
- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)   

---

##  3. Benchmarking

### 3.1 Run Queries (DB-level check)
Open `psql`:
```bash
psql -U postgres -d pharmacydb
```

Run queries with `EXPLAIN ANALYZE`:
```sql
EXPLAIN ANALYZE SELECT id, name FROM medicines WHERE name ILIKE 'Ava%' LIMIT 20;
EXPLAIN ANALYZE SELECT id, name FROM medicines WHERE name ILIKE '%Injection%' LIMIT 20;
EXPLAIN ANALYZE SELECT id, name FROM medicines WHERE name % 'Avastn' ORDER BY similarity(name, 'Avastn') DESC LIMIT 20;
EXPLAIN ANALYZE SELECT id, name FROM medicines WHERE search_tsv @@ plainto_tsquery('english', 'cancer') ORDER BY ts_rank_cd(search_tsv, plainto_tsquery('english','cancer')) DESC LIMIT 20;
```

### 3.2 Run Queries (via API)
Use the new benchmark runner endpoint:
```bash
curl -X POST http://127.0.0.1:8000/run-benchmark
```

- Generates `submission.json` automatically.  
- Results are also returned inline in the response.  

### 3.3 Report
Results are documented in [`benchmark.md`](./benchmark.md).

---

## 4. Approach & Performance Strategy

### 4.1 Data Storage
- Dataset stored in a single table `medicines` (~280k rows).
- JSON attributes (`rx_required`, `in_stock`) stored as `JSONB`.

### 4.2 Indexing
To achieve high performance, we used PostgreSQL’s advanced indexing:
- **Trigram Index (pg_trgm + GIN):**
  - Optimized for prefix, substring, and fuzzy matching.
  - Example:  
    ```sql
    CREATE INDEX idx_medicines_name_trgm
    ON medicines USING GIN (name gin_trgm_ops);
    ```
- **Full-text Index (tsvector + GIN):**
  - Combines `name` + `short_composition` into a searchable vector.
  - Example:  
    ```sql
    CREATE INDEX idx_medicines_tsv
    ON medicines USING GIN (search_tsv);
    ```

### 4.3 Search Queries
- **Prefix:** `ILIKE 'Ava%'`
- **Substring:** `ILIKE '%Injection%'`
- **Fuzzy:** `name % 'Avastn' ORDER BY similarity()`
- **Full-text:** `search_tsv @@ plainto_tsquery('cancer')`

### 4.4 Results
- Prefix: ~3 ms per query
- Substring: ~6 ms per query
- Fuzzy: ~15 ms per query
- Full-text: <1 ms per query
- System supports 100s–1000s queries per second on commodity hardware.

---

## 5. Deliverables
- `schema.sql` → schema + indexes
- `import_data.py` → data import script
- `main.py` → FastAPI REST API with `/search/*` + `/run-benchmark`
- `benchmark_queries.json` → benchmark inputs
- `benchmark.md` → benchmark results
- `submission.json` → generated results from benchmark
- `README.md` → setup + documentation

---

## Contributors
- **Pranav P Kulkarni**
