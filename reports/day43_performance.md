# Sprint 6 Day 43 — Performance Benchmark

## Test Environment

- Project: N100 Financial Intelligence
- Python: 3.12.7
- Pytest: 7.4.4
- Database: SQLite `data/nifty100.db`
- API: FastAPI
- Benchmark date: 2026-09-11

## API Performance Baseline

| Endpoint | Average | P95 | Maximum | Status |
|---|---:|---:|---:|---|
| `/api/v1/health` | 15.34 ms | 16.43 ms | 32.37 ms | 200 |
| `/api/v1/companies` | 14.96 ms | 17.11 ms | 17.51 ms | 200 |
| `/api/v1/companies/TCS` | 11.08 ms | 11.82 ms | 13.50 ms | 200 |
| `/api/v1/companies/TCS/pl` | 11.52 ms | 13.40 ms | 14.72 ms | 200 |
| `/api/v1/companies/TCS/bs` | 11.87 ms | 13.78 ms | 14.14 ms | 200 |
| `/api/v1/companies/TCS/cashflow` | 11.15 ms | 11.96 ms | 14.05 ms | 200 |
| `/api/v1/companies/TCS/ratios` | 15.30 ms | 16.77 ms | 16.84 ms | 200 |
| `/api/v1/companies/TCS/tearsheet` | 18.92 ms | 16.57 ms | 47.70 ms | 200 |
| `/api/v1/screener` | 330.47 ms | 359.06 ms | 359.13 ms | 200 |
| `/api/v1/sectors` | 10.51 ms | 11.93 ms | 12.11 ms | 200 |
| `/api/v1/sectors/Information Technology/companies` | 13.28 ms | 13.83 ms | 14.91 ms | 200 |
| `/api/v1/peers/IT Services` | 48.58 ms | 46.01 ms | 117.82 ms | 200 |
| `/api/v1/companies/TCS/peers/compare` | 54.27 ms | 61.44 ms | 63.16 ms | 200 |
| `/api/v1/market-cap/TCS` | 11.46 ms | 12.01 ms | 12.70 ms | 200 |
| `/api/v1/portfolio/stats` | 19.87 ms | 19.87 ms | 37.55 ms | 200 |
| `/api/v1/companies/TCS/documents` | 12.38 ms | 13.31 ms | 14.17 ms | 200 |

## Concurrent Screener Load Test

- Requests: 50
- Workers: 10
- Successful HTTP 200 responses: 50/50
- Total execution time: 2.503 sec
- Throughput: 19.98 requests/sec
- Average response time: 473.35 ms
- P95 response time: 597.92 ms
- Maximum response time: 663.89 ms

## Performance Assessment

The API baseline is within acceptable performance limits.

The Company Profile endpoint averaged approximately 11 ms, significantly below the Sprint 6 acceptance target of 3 seconds.

The screener was the slowest single API operation at approximately 330 ms average response time. Under 50 concurrent requests using 10 workers, all requests returned HTTP 200 with approximately 20 requests/sec throughput and a P95 response time below 600 ms.

No immediate database or API optimization is required based on this baseline.

## Result

**PASS — Day 43 API performance baseline**

## Dashboard Company Profile Benchmark

The underlying Company Profile data-loading path was benchmarked for five representative Nifty 100 companies. Each ticker was tested for five runs with the Streamlit cache cleared between runs.

| Ticker | Average | Minimum | Maximum | Ratios Rows | P&L Rows | Pros/Cons Rows |
|---|---:|---:|---:|---:|---:|---:|
| TCS | 110.08 ms | 21.46 ms | 448.67 ms | 12 | 12 | 3 |
| RELIANCE | 28.36 ms | 23.48 ms | 33.58 ms | 12 | 12 | 0 |
| HDFCBANK | 21.44 ms | 21.05 ms | 22.07 ms | 12 | 12 | 4 |
| INFY | 20.17 ms | 19.48 ms | 20.57 ms | 12 | 12 | 2 |
| ITC | 21.34 ms | 20.75 ms | 22.08 ms | 12 | 12 | 0 |

Overall average data-loading time: **40.28 ms**.

The slowest ticker was TCS at **110.08 ms average**, which is substantially below the Sprint 6 Company Profile acceptance target of **3 seconds**.

**Dashboard data-loading result: PASS.**

Note: this benchmark measures the underlying database/data-loading operations used by the Streamlit Company Profile page, rather than full browser rendering time.

## Day 43 API + Dashboard Result

**PASS — API performance baseline and Company Profile dashboard data-loading benchmark.**

## SQLite Index Optimization

Initial query-plan analysis showed full table scans on the primary dashboard/API lookup tables. Targeted indexes were therefore added to:

- `financial_ratios(company_id, year)`
- `profitandloss(company_id, year)`
- `balancesheet(company_id, year)`
- `cashflow(company_id, year)`
- `sectors(company_id)`
- `peer_groups(peer_group_name)`

Post-optimization query-plan verification confirmed indexed searches for all six tested query patterns. The historical `(company_id, year)` queries no longer required a temporary B-tree for the year ordering.

## Post-Index API Benchmark

| Endpoint | Average | P95 | Maximum | Status |
|---|---:|---:|---:|---|
| `/api/v1/health` | 12.18 ms | 11.89 ms | 25.14 ms | 200 |
| `/api/v1/companies` | 12.49 ms | 13.23 ms | 18.45 ms | 200 |
| `/api/v1/companies/TCS` | 10.70 ms | 12.30 ms | 15.00 ms | 200 |
| `/api/v1/companies/TCS/pl` | 9.77 ms | 11.16 ms | 13.69 ms | 200 |
| `/api/v1/companies/TCS/bs` | 8.45 ms | 8.88 ms | 8.97 ms | 200 |
| `/api/v1/companies/TCS/cashflow` | 8.55 ms | 9.08 ms | 10.27 ms | 200 |
| `/api/v1/companies/TCS/ratios` | 11.37 ms | 12.81 ms | 13.12 ms | 200 |
| `/api/v1/companies/TCS/tearsheet` | 11.18 ms | 11.80 ms | 13.32 ms | 200 |
| `/api/v1/screener` | 17.84 ms | 19.15 ms | 20.69 ms | 200 |
| `/api/v1/sectors` | 7.90 ms | 8.12 ms | 8.72 ms | 200 |
| `/api/v1/sectors/Information Technology/companies` | 8.37 ms | 9.18 ms | 9.64 ms | 200 |
| `/api/v1/peers/IT Services` | 29.00 ms | 24.13 ms | 77.49 ms | 200 |
| `/api/v1/companies/TCS/peers/compare` | 32.96 ms | 33.34 ms | 34.41 ms | 200 |
| `/api/v1/market-cap/TCS` | 8.55 ms | 9.31 ms | 9.92 ms | 200 |
| `/api/v1/portfolio/stats` | 12.60 ms | 11.87 ms | 23.45 ms | 200 |
| `/api/v1/companies/TCS/documents` | 8.63 ms | 8.97 ms | 10.16 ms | 200 |

## Before vs After Optimization

The screener average response time decreased from **330.47 ms to 17.84 ms**, an improvement of approximately **94.6%**.

Screener P95 decreased from **359.06 ms to 19.15 ms**, an improvement of approximately **94.7%**.

Concurrent screener throughput increased from **19.98 requests/sec to 54.29 requests/sec**, approximately **2.72x higher**.

Concurrent average response time decreased from **473.35 ms to 176.41 ms**, while P95 decreased from **597.92 ms to 203.89 ms**.

All 50 concurrent requests returned HTTP 200.

## Optimized Performance Result

**PASS — SQLite indexing and API performance optimization.**
