-- N100 Financial Intelligence
-- Exploratory SQL Queries
-- Sprint 1

-- 1. Total number of companies
SELECT COUNT(*) AS total_companies
FROM companies;

-- 2. Companies by broad sector
SELECT broad_sector, COUNT(*) AS company_count
FROM sectors
GROUP BY broad_sector
ORDER BY company_count DESC;

-- 3. Companies by market-cap category
SELECT market_cap_category, COUNT(*) AS company_count
FROM companies
GROUP BY market_cap_category
ORDER BY company_count DESC;

-- 4. Latest financial-ratio records
SELECT *
FROM financial_ratios
ORDER BY company_id, year DESC
LIMIT 20;

-- 5. Companies with the highest latest ROE
SELECT company_id, year, return_on_equity_pct
FROM financial_ratios
WHERE year = (SELECT MAX(year) FROM financial_ratios)
ORDER BY return_on_equity_pct DESC
LIMIT 10;

-- 6. Companies with the highest latest revenue CAGR
SELECT company_id, year, revenue_cagr_5yr
FROM financial_ratios
WHERE year = (SELECT MAX(year) FROM financial_ratios)
ORDER BY revenue_cagr_5yr DESC
LIMIT 10;

-- 7. Companies with positive latest free cash flow
SELECT company_id, year, free_cash_flow_cr
FROM financial_ratios
WHERE year = (SELECT MAX(year) FROM financial_ratios)
  AND free_cash_flow_cr > 0
ORDER BY free_cash_flow_cr DESC
LIMIT 10;

-- 8. Latest debt-to-equity by company
SELECT company_id, year, debt_to_equity
FROM financial_ratios
WHERE year = (SELECT MAX(year) FROM financial_ratios)
ORDER BY debt_to_equity ASC
LIMIT 10;

-- 9. Financial statement year coverage
SELECT
    company_id,
    MIN(year) AS first_year,
    MAX(year) AS latest_year,
    COUNT(*) AS years_available
FROM profitandloss
GROUP BY company_id
ORDER BY years_available DESC;

-- 10. Companies with limited financial history
SELECT
    company_id,
    COUNT(*) AS years_available
FROM profitandloss
GROUP BY company_id
HAVING COUNT(*) < 10
ORDER BY years_available ASC;
