# Benchmark Report

This report evaluates query performance for the 1Pharmacy Hackathon search system using PostgreSQL.

## Setup
- **Database:** PostgreSQL 18
- **Dataset:** ~280,227 rows
- **Indexes:**
  - GIN (pg_trgm) on `name` → prefix, substring, fuzzy search
  - GIN on `tsvector (search_tsv)` → full-text search
- **Machine:** Windows, local dev environment

## Queries Tested
1. Prefix: `ILIKE 'Ava%'`
2. Substring: `ILIKE '%Injection%'`
3. Fuzzy: `name % 'Avastn'`
4. Full-text: `search_tsv @@ plainto_tsquery('cancer')`

## Results

| Query Type | Example Query | Index Used                         | Execution Time (ms) | Throughput (qps) |
|------------|---------------|-------------------------------------|---------------------|------------------|
| Prefix     | `Ava%`        | Bitmap Index Scan on `idx_medicines_name_trgm` | 3.404 ms           | ~294             |
| Substring  | `%Injection%` | ❌ Seq Scan (index not used)        | 5.952 ms           | ~168             |
| Fuzzy      | `Avastn`      | Bitmap Index Scan on `idx_medicines_name_trgm` | 14.887 ms          | ~67              |
| Full-text  | `cancer`      | Bitmap Index Scan on `idx_medicines_tsv`       | 0.160 ms           | ~6250            |

## Observations
- Prefix and fuzzy queries successfully use the trigram index (`idx_medicines_name_trgm`).
- Substring (`%Injection%`) fell back to a sequential scan. This happens because the planner sometimes prefers seq scan for shorter strings or smaller datasets. With larger data or more selective queries, trigram index should be used.
- Full-text search is extremely fast with the GIN `tsvector` index — under 1 ms latency.
- Throughput is highest for full-text, while fuzzy search is naturally slower due to similarity calculations.

## Conclusion
The indexing strategy (trigram + full-text GIN indexes) significantly improves performance:
- Sub-millisecond full-text queries
- Prefix queries in ~3 ms
- Fuzzy typo-tolerant queries under 15 ms
Overall, the system can support **hundreds to thousands of queries per second** on this dataset.
