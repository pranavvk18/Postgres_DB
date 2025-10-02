# main.py
import os
import json
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql://postgres:pranav222@localhost:5432/pharmacydb"

app = FastAPI(title="Medicine Search API")

# Pydantic model for results
class MedicineOut(BaseModel):
    id: int
    name: str
    manufacturer_name: Optional[str] = None
    price: Optional[float] = None
    score: Optional[float] = None  # similarity or rank

@app.on_event("startup")
async def startup():
    app.state.db = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)

@app.on_event("shutdown")
async def shutdown():
    await app.state.db.close()

# Safety: max query length and default limit
MAX_Q_LEN = 200
DEFAULT_LIMIT = 20
MAX_LIMIT = 200

def check_q(q: str):
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
    if len(q) > MAX_Q_LEN:
        raise HTTPException(status_code=400, detail=f"Query too long (max {MAX_Q_LEN})")
    return q.strip()

# -------------------------------
# Search Endpoints
# -------------------------------

@app.get("/search/prefix", response_model=List[MedicineOut])
async def search_prefix(q: str = Query(...), limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT), offset: int = 0):
    q = check_q(q)
    pattern = f"{q}%"
    sql = """
    SELECT id, name, manufacturer_name, price
    FROM medicines
    WHERE name ILIKE $1
    ORDER BY name
    LIMIT $2 OFFSET $3
    """
    async with app.state.db.acquire() as conn:
        rows = await conn.fetch(sql, pattern, limit, offset)
    return [MedicineOut(**dict(r)) for r in rows]

@app.get("/search/substring", response_model=List[MedicineOut])
async def search_substring(q: str = Query(...), limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT), offset: int = 0):
    q = check_q(q)
    pattern = f"%{q}%"
    sql = """
    SELECT id, name, manufacturer_name, price
    FROM medicines
    WHERE name ILIKE $1
    ORDER BY name
    LIMIT $2 OFFSET $3
    """
    async with app.state.db.acquire() as conn:
        rows = await conn.fetch(sql, pattern, limit, offset)
    return [MedicineOut(**dict(r)) for r in rows]

@app.get("/search/fuzzy", response_model=List[MedicineOut])
async def search_fuzzy(q: str = Query(...), limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT), offset: int = 0):
    q = check_q(q)
    sql = """
    SELECT id, name, manufacturer_name, price, similarity(name, $1) AS score
    FROM medicines
    WHERE name % $1
    ORDER BY score DESC, name
    LIMIT $2 OFFSET $3
    """
    async with app.state.db.acquire() as conn:
        rows = await conn.fetch(sql, q, limit, offset)
    return [MedicineOut(**dict(r)) for r in rows]

@app.get("/search/fulltext", response_model=List[MedicineOut])
async def search_fulltext(q: str = Query(...), limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT), offset: int = 0):
    q = check_q(q)
    sql = """
    SELECT id, name, manufacturer_name, price,
           ts_rank_cd(search_tsv, plainto_tsquery('english', $1)) AS score
    FROM medicines
    WHERE search_tsv @@ plainto_tsquery('english', $1)
    ORDER BY score DESC, name
    LIMIT $2 OFFSET $3
    """
    async with app.state.db.acquire() as conn:
        rows = await conn.fetch(sql, q, limit, offset)
    return [MedicineOut(**dict(r)) for r in rows]

# -------------------------------
# Benchmark Runner Endpoint
# -------------------------------

@app.post("/run-benchmark")
async def run_benchmark():
    """
    Runs all queries from benchmark_queries.json and generates submission.json
    """
    try:
        # Load benchmark queries
        with open("benchmark_queries.json", "r", encoding="utf-8") as f:
            benchmark = json.load(f)

        results = {}

        async with app.state.db.acquire() as conn:
            for test in benchmark["tests"]:
                qid = str(test["id"])
                qtype = test["type"]
                query_str = test["query"]

                if qtype == "prefix":
                    sql = """
                        SELECT name
                        FROM medicines
                        WHERE name ILIKE $1
                        ORDER BY name
                        LIMIT 10;
                    """
                    rows = await conn.fetch(sql, f"{query_str}%")

                elif qtype == "substring":
                    sql = """
                        SELECT name
                        FROM medicines
                        WHERE name ILIKE $1
                        ORDER BY name
                        LIMIT 10;
                    """
                    rows = await conn.fetch(sql, f"%{query_str}%")

                elif qtype == "fuzzy":
                    sql = """
                        SELECT name
                        FROM medicines
                        WHERE name % $1
                        ORDER BY similarity(name, $1) DESC, name
                        LIMIT 10;
                    """
                    rows = await conn.fetch(sql, query_str)

                elif qtype == "fulltext":
                    sql = """
                        SELECT name
                        FROM medicines
                        WHERE search_tsv @@ plainto_tsquery('english', $1)
                        ORDER BY ts_rank_cd(search_tsv, plainto_tsquery('english', $1)) DESC, name
                        LIMIT 10;
                    """
                    rows = await conn.fetch(sql, query_str)

                else:
                    continue

                # Collect just the medicine names
                names = [r["name"] for r in rows]
                results[qid] = names

        # Save to submission.json
        output = {"results": results}
        with open("submission.json", "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        return {"message": "✅ submission.json generated successfully", "results": results}

    except Exception as e:
        return {"error": str(e)}
